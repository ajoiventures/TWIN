"""Explicit flat-normal review layer; preserves architectural geometry exactly."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Gf

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def face_normals(points,counts,indices):
    normals=[];offset=0;degenerate=0
    for count in counts:
        face=[Gf.Vec3d(points[i]) for i in indices[offset:offset+count]];offset+=count
        normal=Gf.Vec3d(0)
        for i in range(1,len(face)-1):normal+=Gf.Cross(face[i]-face[0],face[i+1]-face[0])
        if normal.GetLength()<1e-12:normal=Gf.Vec3d(0,0,1);degenerate+=1
        else:normal.Normalize()
        normals.append(Gf.Vec3f(normal))
    return normals,degenerate

def build(root=ROOT):
    source_path=root/'scene/corridor_workview.usda';before=sha(source_path)
    source=Usd.Stage.Open(str(source_path));stage=Usd.Stage.CreateInMemory()
    changed=[];existing=[];schemes={};degenerate=0;normal_count=0
    for prim in source.Traverse():
        path=str(prim.GetPath())
        if not prim.IsA(UsdGeom.Mesh) or not path.startswith(('/World/Buildings/','/World/Roofs/','/World/Landmarks/')):continue
        mesh=UsdGeom.Mesh(prim);scheme=mesh.GetSubdivisionSchemeAttr().Get();schemes[str(scheme)]=schemes.get(str(scheme),0)+1
        points=mesh.GetPointsAttr().Get();counts=mesh.GetFaceVertexCountsAttr().Get();indices=mesh.GetFaceVertexIndicesAttr().Get()
        if sum(counts)!=len(indices) or any(i<0 or i>=len(points) for i in indices):raise ValueError('Invalid source topology '+path)
        normals=mesh.GetNormalsAttr().Get();interpolation=mesh.GetNormalsInterpolation()
        expected={'uniform':len(counts),'vertex':len(points),'varying':len(points),'faceVarying':len(indices),'constant':1}.get(str(interpolation))
        valid=bool(normals) and len(normals)==expected and all(math.isfinite(v) for n in normals for v in n)
        if valid:
            record={'path':path,'faces':len(counts),'points':len(points),'subdivision':str(scheme),'normals_interpolation':str(interpolation),'normal_count':len(normals)}
            if str(interpolation)=='uniform':
                computed,_=face_normals(points,counts,indices)
                dots=[max(-1,min(1,Gf.Dot(Gf.Vec3d(a).GetNormalized(),Gf.Vec3d(b).GetNormalized()))) for a,b in zip(normals,computed)]
                record['maximum_authored_vs_geometric_normal_angle_degrees']=math.degrees(math.acos(min(dots))) if dots else None
            existing.append(record)
            continue
        computed,zero=face_normals(points,counts,indices);degenerate+=zero;normal_count+=len(computed)
        override=UsdGeom.Mesh(stage.OverridePrim(path))
        override.CreateSubdivisionSchemeAttr('none');override.CreateNormalsAttr(computed);override.SetNormalsInterpolation('uniform')
        override.GetPrim().SetCustomDataByKey('flatShadingReview','Explicit original-topology face normals only; points/indices/extents/UV/materials unchanged. Render comparison pending.')
        changed.append(path)
    if sha(source_path)!=before:raise ValueError('Source workview changed during preparation')
    summary={'source_workview_sha256':before,'source_subdivision_counts':schemes,'changed_meshes':len(changed),'authored_normals':normal_count,
             'degenerate_faces_with_fallback_normal':degenerate,'existing_landmark_normals_retained':existing,
             'finding':'All inspected source meshes already author subdivision none. Missing subdivision is ruled out. Generic meshes without normals receive explicit flat normals for comparison; smoothing as the generic cause remains unverified until rendered. Princeton/Wellesley already have face normals; jagged silhouettes there are authored geometry, not repaired by this layer.',
             'geometry_changed':False,'visual_fix_accepted':False}
    stage.GetRootLayer().customLayerData={'purpose':'Bounded flat-normal comparison only; no raw geometry repair or subdivision change claimed','auditJson':json.dumps(summary,sort_keys=True)}
    output=root/'scene/architectural_flat_shading_proposal.usda';stage.GetRootLayer().Export(str(output))
    view=Usd.Stage.CreateInMemory()
    names=[name for name in ('manual_edits.usda','map_extent_guard.usda') if (root/'scene'/name).exists()]
    names+=['architectural_flat_shading_proposal.usda','corridor_workview.usda']
    view.GetRootLayer().subLayerPaths=[str(root/'scene'/name) for name in names]
    UsdGeom.SetStageMetersPerUnit(view,1);UsdGeom.SetStageUpAxis(view,'Z');view.SetDefaultPrim(view.GetPrimAtPath('/World'))
    workview=root/'scene/architectural_flat_workview.usda';view.GetRootLayer().Export(str(workview))
    composed=Usd.Stage.Open(str(workview));composed.GetRootLayer().subLayerPaths=names;composed.GetRootLayer().Save()
    # No point, topology, height, UV, extent or material opinions are authored.
    for prim in stage.Traverse():
        for attribute in prim.GetAuthoredAttributes():
            if attribute.GetName() not in ('normals','subdivisionScheme'):raise ValueError('Unexpected geometry opinion '+attribute.GetName())
    summary.update({'proposal':str(output),'proposal_sha256':sha(output),'workview':str(workview),'workview_sha256':sha(workview),'changed_paths':changed})
    (root/'data/transport/architectural_shading_review.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='changed_paths'},indent=2));return summary

if __name__=='__main__':build()
