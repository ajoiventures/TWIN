"""Inactive per-component QEM pilot on pinned untextured CarConcept surfaces.

Uses isolated receipt-pinned fast-simplification, never installs or launches GPU.
No welding: source seams/material parts stay separate. Textured primitives exact.
Small/unsafe components fall back unchanged. Sampled errors are NOT Hausdorff
certificates; visual/silhouette/runtime review remains required before adoption.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'PXR_WORK_THREAD_LIMIT'):
    os.environ.setdefault(key, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
TOOLS = ROOT / 'data/diagnostics/mesh_tools_20261102'
sys.path.insert(1, str(TOOLS / 'site-packages'))
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils, Vt
import fast_simplification


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def edges(f):
    return np.unique(np.sort(np.concatenate((f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]])), axis=1), axis=0, return_counts=True)


def boundary(p, f):
    e, c = edges(f)
    return sorted(tuple(sorted((tuple(p[a]), tuple(p[b])))) for a, b in e[c == 1])


def samples(p, f):
    # Deterministic source vertices + face centroids, not an exhaustive surface.
    return np.vstack((p[::max(1, len(p) // 500)], p[f].mean(axis=1)[::max(1, len(f) // 500)]))


def surface_distances(q, p, f):
    """Distance to best of 32 centroid-near triangles: upper bound on nearest.

    An accepted small upper bound is conservative at these sampled locations;
    failure can be a false rejection. Unsampled surface maxima remain unknown.
    """
    tri = p[f]; tree = cKDTree(tri.mean(axis=1)); _, ix = tree.query(q, k=min(32, len(f)))
    ix = np.asarray(ix).reshape(len(q), -1); t = tri[ix]; x = q[:, None, :]
    a, b, c = t[:, :, 0], t[:, :, 1], t[:, :, 2]
    u, v, w = b-a, c-a, x-a
    uu=(u*u).sum(2); uv=(u*v).sum(2); vv=(v*v).sum(2); wu=(w*u).sum(2); wv=(w*v).sum(2)
    det=uu*vv-uv*uv; good=det>1e-24; safe=np.where(good,det,1)
    s=(wu*vv-wv*uv)/safe; z=(wv*uu-wu*uv)/safe
    projected=a+s[:,:,None]*u+z[:,:,None]*v
    dist=np.where(good & (s>=0) & (z>=0) & (s+z<=1), ((x-projected)**2).sum(2), np.inf)
    for first,second in ((a,b),(b,c),(c,a)):
        d=second-first; denom=(d*d).sum(2); tval=np.clip(((x-first)*d).sum(2)/np.maximum(denom,1e-30),0,1)
        close=first+tval[:,:,None]*d; dist=np.minimum(dist,((x-close)**2).sum(2))
    best=dist.argmin(1)
    return np.sqrt(dist[np.arange(len(q)),best]), ix[np.arange(len(q)),best]


def textured(prim):
    material,_=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    stack=[material.ComputeSurfaceSource()[0]]; seen=set()
    while stack:
        shader=stack.pop(); path=str(shader.GetPath())
        if path in seen: continue
        seen.add(path)
        if shader.GetIdAttr().Get()=='UsdUVTexture': return True
        for inp in shader.GetInputs():
            stack.extend(UsdShade.Shader(c.source.GetPrim()) for c in inp.GetConnectedSources()[0])
    return False


def source_normal_field(query,p,f,normals):
    """Barycentric normal on the selected nearest original triangle, not KNN."""
    _,indices=surface_distances(query,p,f);tri=p[f[indices]]
    a,b,c=tri[:,0],tri[:,1],tri[:,2];u=b-a;v=c-a;w=query-a
    uu=(u*u).sum(1);uv=(u*v).sum(1);vv=(v*v).sum(1)
    det=np.maximum(uu*vv-uv*uv,1e-30);s=((w*u).sum(1)*vv-(w*v).sum(1)*uv)/det;t=((w*v).sum(1)*uu-(w*u).sum(1)*uv)/det
    weights=np.column_stack((1-s-t,s,t));best=np.where((weights>=0).all(1),((query-(a+s[:,None]*u+t[:,None]*v))**2).sum(1),np.inf)
    for i,j in ((0,1),(1,2),(2,0)):
        start=tri[:,i];direction=tri[:,j]-start
        k=np.clip(((query-start)*direction).sum(1)/np.maximum((direction*direction).sum(1),1e-30),0,1)
        distance=((query-start-k[:,None]*direction)**2).sum(1);change=distance<best
        edgeweights=np.zeros_like(weights);edgeweights[:,i]=1-k;edgeweights[:,j]=k
        weights[change]=edgeweights[change];best[change]=distance[change]
    result=(normals[f[indices]]*weights[:,:,None]).sum(1)
    return result/np.maximum(np.linalg.norm(result,axis=1)[:,None],1e-30)


def reduce_component(p, f, normals, target_reduction=.4):
    if len(f)<100: return p,f,normals,{'status':'small_component_retained'}
    e,c=edges(f)
    if (c>2).any(): return p,f,normals,{'status':'source_nonmanifold_retained'}
    out,faces=fast_simplification.simplify(p.astype(np.float64),f.astype(np.int32),target_reduction=target_reduction,agg=3.,preserve_border=True)
    out=out.astype(np.float32); faces=faces.astype(np.int32)
    reason=None
    if not np.isfinite(out).all() or len(faces)>=len(f): reason='no_reduction_or_nonfinite'
    elif len(faces)==0 or faces.min()<0 or faces.max()>=len(out): reason='invalid_indices'
    if reason: return p,f,normals,{'status':reason}
    oe,oc=edges(faces); cross=np.cross(out[faces[:,1]]-out[faces[:,0]],out[faces[:,2]]-out[faces[:,0]])
    if (oc>2).any() or (np.linalg.norm(cross,axis=1)<1e-12).any(): reason='degenerate_or_nonmanifold'
    elif boundary(p,f)!=boundary(out,faces): reason='boundary_changed'
    elif len(p)-len(e)+len(f)!=len(out)-len(oe)+len(faces): reason='euler_changed'
    elif np.max(np.abs(np.array([p.min(0),p.max(0)])-np.array([out.min(0),out.max(0)])))>.002: reason='bounds_error'
    adjacency=coo_matrix((np.ones(len(oe)),(oe[:,0],oe[:,1])),shape=(len(out),len(out)))
    if connected_components(adjacency,directed=False)[0]!=1: reason='component_changed'
    if reason: return p,f,normals,{'status':reason}
    forward,_=surface_distances(samples(p,f),out,faces); backward,_=surface_distances(samples(out,faces),p,f)
    maximum=float(max(forward.max(),backward.max()))
    if maximum>.002: return p,f,normals,{'status':'sampled_surface_error','sample_max_upper_bound_m':maximum}
    _,nearest=surface_distances(out[faces].mean(1),p,f)
    oldcross=np.cross(p[f[nearest,1]]-p[f[nearest,0]],p[f[nearest,2]]-p[f[nearest,0]])
    dots=(cross*oldcross).sum(1)/np.maximum(np.linalg.norm(cross,axis=1)*np.linalg.norm(oldcross,axis=1),1e-30)
    if dots.min()<.5: return p,f,normals,{'status':'orientation_guard'}
    result=source_normal_field(out,p,f,normals)
    distances,indices=cKDTree(p).query(out);exact=distances<1e-9;result[exact]=normals[indices[exact]]
    centroids=out[faces].mean(1);actual=result[faces].mean(1);actual/=np.maximum(np.linalg.norm(actual,axis=1)[:,None],1e-30)
    reference=source_normal_field(centroids,p,f,normals)
    normal_angles=np.degrees(np.arccos(np.clip((actual*reference).sum(1),-1,1)))
    if normal_angles.max()>3.:
        return p,f,normals,{'status':'source_shading_normal_field_error','maximum_centroid_normal_field_deviation_degrees':float(normal_angles.max())}
    return out,faces,result.astype(np.float32),{'status':'reduced','source_triangles':len(f),'triangles':len(faces),
        'sample_max_upper_bound_m':maximum,'sample_p95_upper_bound_m':float(np.quantile(np.r_[forward,backward],.95)),
        'minimum_near_source_face_normal_dot':float(dots.min()),'maximum_centroid_normal_field_deviation_degrees':float(normal_angles.max())}


def build(output, target_reduction=.1):
    captured_helper=Path(__file__).read_bytes()
    captured_helper_sha=hashlib.sha256(captured_helper).hexdigest()
    output=Path(output).resolve()
    if not 0<target_reduction<=.4:raise ValueError('Target reduction must be >0 and <=0.4; acceptance gates stay fixed')
    if output.exists(): raise FileExistsError('Fresh output directory required')
    output.mkdir(parents=True)
    (output/'captured_helper.py').write_bytes(captured_helper)
    receipt=json.loads((TOOLS/'acquisition.json').read_text())
    expected='ce22a6f015707eb1d6d431c4896a18eb15c5f3cbaf32533d90371ea1b06875ad'
    if receipt['sha256']!=expected or sha(TOOLS/'wheels'/receipt['wheel'])!=expected: raise ValueError('Tool wheel receipt mismatch')
    if not Path(fast_simplification.__file__).resolve().is_relative_to(TOOLS/'site-packages'): raise ValueError('Wrong decimator import')
    source=ROOT/'data/diagnostics/car_concept_20261030/converted_v3';manifest=json.loads((source/'manifest.json').read_text())
    if sha(source/'car.usda')!='28737a869c9ee1ac0fd96abd9c847f385c842c71c78446ca95dd93005132cc7b':raise ValueError('Wrong source geometry')
    for name,digest in manifest['files'].items():
        path=(source/name).resolve()
        if not path.is_relative_to(source) or sha(path)!=digest:raise ValueError('Source dependency mismatch')
    protected={str(p):sha(p) for p in source.rglob('*') if p.is_file()}
    shutil.copytree(source/'textures',output/'textures')
    for name in ('car.usda','ATTRIBUTION.md','SOURCE_LICENSE.md'):shutil.copy2(source/name,output/name)
    shutil.copy2(source/'car.usda',output/'qem.usda');stage=Usd.Stage.Open(str(output/'qem.usda'));records=[]
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):continue
        mesh=UsdGeom.Mesh(prim);p=np.array(mesh.GetPointsAttr().Get());f=np.array(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1,3);norm=np.array(mesh.GetNormalsAttr().Get())
        record={'path':str(prim.GetPath()),'source_triangles':len(f),'textured':textured(prim)}
        if record['textured']:
            record.update(triangles=len(f),status='textured_exact');records.append(record);continue
        material,_=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial();material_id=str(material.GetPath()).rsplit('/',1)[-1]
        name=prim.GetParent().GetName().split('_',1)[-1]
        if name.startswith('Body') or material_id in ('M1','M10','M11','M18','M19','M20'):
            record.update(triangles=len(f),status='appearance_critical_exact');records.append(record);continue
        e,_=edges(f);adj=coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(len(p),len(p)));count,labels=connected_components(adj,directed=False)
        parts=[];offset=0;components=[]
        face_labels=labels[f[:,0]]
        for label in range(count):
            selected=f[face_labels==label]
            if not len(selected):continue
            used=np.unique(selected);local=np.searchsorted(used,selected)
            a,b,n,result=reduce_component(p[used],local,norm[used],target_reduction);components.append(result);parts.append((a,b+offset,n));offset+=len(a)
        a=np.vstack([x[0] for x in parts]);b=np.vstack([x[1] for x in parts]);n=np.vstack([x[2] for x in parts])
        record.update(triangles=len(b),components=components)
        if len(b)<len(f):
            mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(a.astype(np.float32)));mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray.FromNumpy(b.astype(np.int32).reshape(-1)));mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]*len(b)))
            mesh.GetNormalsAttr().Set(Vt.Vec3fArray.FromNumpy(n.astype(np.float32)))
            # No reachable texture reads these primvars. Keep no stale cardinality.
            for pv in UsdGeom.PrimvarsAPI(mesh).GetPrimvars():
                if pv.GetInterpolation() in ('vertex','varying','faceVarying'):prim.RemoveProperty(pv.GetAttr().GetName());prim.RemoveProperty(pv.GetAttr().GetName()+':indices')
            prim.SetCustomDataByKey('geometryQuality','Inactive per-component QEM; sampled2mm guard, no silhouette/render acceptance')
        records.append(record)
    stage.GetRootLayer().Save()
    original=Usd.Stage.Open(str(output/'car.usda'));reopened=Usd.Stage.Open(str(output/'qem.usda'))
    for record in records:
        if record['textured']:
            a=original.GetPrimAtPath(record['path']);b=reopened.GetPrimAtPath(record['path'])
            if {x.GetName():str(x.Get()) for x in a.GetAttributes()}!={x.GetName():str(x.Get()) for x in b.GetAttributes()}:raise ValueError('Textured primitive changed')
    for level,asset in [('full','car.usda'),('qem','qem.usda')]:
        review=Usd.Stage.CreateNew(str(output/(level+'_review.usda')));review.GetRootLayer().subLayerPaths=[asset]
        UsdGeom.SetStageUpAxis(review,'Z');UsdGeom.SetStageMetersPerUnit(review,1)
        # Reuse the already framed original review camera/lights/ground subtree.
        source_review=Sdf.Layer.FindOrOpen(str(source/'review.usda'));Sdf.CopySpec(source_review,'/Review',review.GetRootLayer(),'/Review')
        for name,eye,up in [('Front',(0,-8,2.2),(0,0,1)),('Rear',(0,8,2.2),(0,0,1)),('Side',(8,0,2.2),(0,0,1)),('Top',(0,0,16),(0,1,0))]:
            cam=UsdGeom.Camera.Define(review,'/Review/'+name);cam.CreateFocalLengthAttr(45);cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(20.25);cam.CreateClippingRangeAttr(Gf.Vec2f(.05,1000))
            cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(0,0,.55),Gf.Vec3d(*up)).GetInverse())
        review.GetRootLayer().Save()
        if UsdUtils.ComputeAllDependencies(str(output/(level+'_review.usda')))[2]:raise ValueError('Unresolved package')
    with (output/'ATTRIBUTION.md').open('a',encoding='utf8') as handle:handle.write('\nAdditional modification: conservative per-component quadric simplification on untextured primitives; original textured primitives retained. No active adoption or performance acceptance.\n')
    if protected!={str(p):sha(p) for p in source.rglob('*') if p.is_file()}:raise ValueError('Original source modified')
    report={'schema':'twin.vehicle-qem-pilot/2','source_sha256':sha(source/'car.usda'),'tool_sha256':sha(__file__),'decimator_receipt_sha256':sha(TOOLS/'acquisition.json'),'wheel_sha256':expected,'source_files_preserved':len(protected),'records':records,'source_triangles':sum(r['source_triangles'] for r in records),'triangles':sum(r['triangles'] for r in records),'method':f'Per indexed connected component; no welding; preserve_border=True; target_reduction={target_reduction:g}; agg3; components<100faces unchanged. All Body-named meshes/glass/paint/tires/glossy rims exact after v2 actual visual rejection.','normals':'Component-local original triangle barycentric source-normal field; exact at retained source coordinates; new face centroid field deviation<=3degrees; no cross-seam smoothing','error_scope':'Bidirectional sampled vertices+centroids, nearest of32 centroid-near triangles gives distance upper bound at samples; NOT exhaustive Hausdorff or silhouette proof','activation':False,'render_status':'not_run','files':{str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}}
    report['target_reduction_per_eligible_component']=target_reduction
    if Path(__file__).read_bytes()!=captured_helper:raise ValueError('Producer helper changed during build; candidate has no valid completion manifest')
    report['requested_target_reduction']=float(target_reduction)
    report['tool_sha256']=captured_helper_sha
    report['captured_helper_path']='captured_helper.py'
    report['captured_helper_sha256']=captured_helper_sha
    report['working_helper_unchanged_during_build']=True
    (output/'manifest.json').write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--target-reduction',type=float,default=.1);args=parser.parse_args();r=build(args.output,args.target_reduction);print(json.dumps({k:r[k] for k in ('source_triangles','triangles','source_files_preserved')}))
