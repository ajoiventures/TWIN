"""Photo-guided coherent architectural roof proposal; immutable base geometry.

No downloads, source-image tracing, activation, or edits to the existing model.
"""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[key]='1'
import sys,json,hashlib,datetime,collections
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
import shapely
from shapely.geometry import shape,box,Polygon
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from pyproj import Transformer
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
from reconstruct_landmarks import verify_source,SITES,read,sha,planar_region_geometry,quantized_valid_geometry
from princeton_evidence import write_surface
from correct_wellesley import mesh_geometry
from mesh_topology import closed_shell_report

BASE_SHA='c81964557d188cb3920bebb1334ed34762532f1043f99a58e18d0456b3eea86b'
OUTLINE_SHA='a3215f0c352efe0dc86afd07c191346ccc647ab1d3da2d373742eba71b3ff0da'
TARGET='/World/Landmarks/AndersenOffice1615/RoofBand0_Component1'
LEFT=461930.;BOTTOM=3159974.;GROUND=29.8
ORIGIN=Transformer.from_crs(4326,32617,always_xy=True).transform(-81.389,28.572)


def fit_plane(points,initial,selector,name):
    A=np.c_[points[:,0]-LEFT,points[:,1]-BOTTOM,np.ones(len(points))];z=points[:,2]
    chosen=selector&(np.abs(A@np.asarray(initial)-z)<=.22)
    if chosen.sum()<50:raise ValueError('Insufficient guided plane support: '+name)
    X=A[chosen];y=z[chosen];coeff=np.asarray(initial,float)
    for _ in range(10):
        residual=X@coeff-y;weights=np.minimum(1.,.08/np.maximum(np.abs(residual),1e-6))
        coeff=np.linalg.lstsq(X*weights[:,None],y*weights,rcond=None)[0]
    residual=np.abs(X@coeff-y);classes,counts=np.unique(points[chosen,3].astype(int),return_counts=True)
    return coeff.tolist(),{'name':name,'source_points':int(chosen.sum()),'source_classes':{str(k):int(v) for k,v in zip(classes,counts)},
        'coefficients_model_xy':coeff.tolist(),'fit_residual_p50_p95_max_m':np.percentile(residual,[50,95,100]).tolist(),
        'support_window_m':.22,'quality':'guided source fit within photo-interpreted architectural form, not survey'}


def halfspace(geometry,a,b,c):
    if abs(a)+abs(b)<1e-12:return geometry if c<=1e-8 else shapely.GeometryCollection()
    x0,y0,x1,y1=geometry.bounds;vertices=[(x0-100,y0-100),(x1+100,y0-100),(x1+100,y1+100),(x0-100,y1+100)]
    output=[]
    for p,q in zip(vertices,vertices[1:]+vertices[:1]):
        fp=a*p[0]+b*p[1]+c;fq=a*q[0]+b*q[1]+c
        if fp<=0:output.append(p)
        if (fp<=0)!=(fq<=0):
            t=fp/(fp-fq);output.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
    return geometry.intersection(Polygon(output)) if len(output)>=3 else shapely.GeometryCollection()


def coherent_regions(outline,points):
    # These two transitions are observed changes in broad40.55m returns; narrow
    # central clock-pediment returns are not mistaken for a whole high roof wing.
    y=points[:,1]-ORIGIN[1];outer=(y< -640)|(y>=-609);center=~outer
    plane_data={};proof=[]
    for name,initial,selector in [
        ('outer_west',[.4934,.0043,36.9707],outer),('outer_east',[-.4919,-.0038,48.0713],outer),
        ('central_west',[.4772,.0048,36.2085],center),('central_east',[-.4398,-.0030,47.7148],center)]:
        plane_data[name],report=fit_plane(points,initial,selector,name);proof.append(report)
    for name,target,selector in [('outer_crown',40.55,outer),('central_crown',37.85,center)]:
        chosen=selector&(np.abs(points[:,2]-target)<=.15)
        if chosen.sum()<100:raise ValueError('Insufficient broad roof level')
        z=float(np.median(points[chosen,2]));plane_data[name]=[0.,0.,z]
        proof.append({'name':name,'source_points':int(chosen.sum()),'coefficients_model_xy':[0.,0.,z],
                      'fit_residual_p50_p95_max_m':np.percentile(np.abs(points[chosen,2]-z),[50,95,100]).tolist()})
    model=shapely.transform(outline,lambda x,y:(x-LEFT,y-BOTTOM),interleaved=False)
    regions=[];sections=[]
    for name,lo,hi,prefix in [('south',-10000.,-640.,'outer'),('central',-640.,-609.,'central'),('north',-609.,10000.,'outer')]:
        domain=model.intersection(box(-1000,lo+ORIGIN[1]-BOTTOM,1000,hi+ORIGIN[1]-BOTTOM))
        if domain.is_empty:continue
        names=[prefix+'_west',prefix+'_east',prefix+'_crown'];coeffs=[plane_data[n] for n in names]
        sections.append({'name':name,'y_local_m':[max(lo,outline.bounds[1]-ORIGIN[1]),min(hi,outline.bounds[3]-ORIGIN[1])],
                         'interpretation':'coherent pitched sides and source-supported crown; source transition location approximate to1m'})
        for i,(plane,coef) in enumerate(zip(names,coeffs)):
            patch=domain
            for j,other in enumerate(coeffs):
                if i!=j:patch=halfspace(patch,coef[0]-other[0],coef[1]-other[1],coef[2]-other[2])
                if patch.is_empty:break
            if patch.is_empty or patch.area<.001:continue
            absolute=shapely.transform(patch,lambda x,y:(x+LEFT,y+BOTTOM),interleaved=False)
            regions.append({'geometry':absolute,'coefficients_cell_xy':coef,'architectural_patch':name+'_'+plane})
    covered=unary_union([r['geometry'] for r in regions])
    if outline.symmetric_difference(covered).area>.001:raise ValueError('Coherent roof did not preserve existing envelope')
    return regions,plane_data,{'guided_planes':proof,'sections':sections,'architectural_patch_count':len(regions),
        'form':'Two higher end roof blocks, lower central connector, continuous source-fitted pitched sides with observed crown levels; no pixel/cell-label fragments'}


def roof_height(plane_data,x,y):
    prefix='outer' if y < -640 or y>=-609 else 'central'
    model=np.array([x+ORIGIN[0]-LEFT,y+ORIGIN[1]-BOTTOM,1])
    return min(float(model@plane_data[prefix+'_'+part]) for part in ['west','east','crown'])-GROUND+.1


def material(stage,name,color):
    path='/World/LandmarkMaterials/OfficeArchitecture'+name;m=UsdShade.Material.Define(stage,path);shader=UsdShade.Shader.Define(stage,path+'/Surface')
    shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.88)
    m.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');return m


def finish_mesh(stage,path,geometry,wall,roof):
    geometry,validation=quantized_valid_geometry(geometry,minimum_roof_xy_area_m2=0.)
    if validation['input_faces']!=validation['output_faces']:raise ValueError('Architectural shell lost a face')
    gate=closed_shell_report(*geometry)
    if not gate['passed_closed_shell']:raise ValueError('Architectural mesh is open: '+str(gate))
    mesh=write_surface(stage,path,geometry);mesh.GetPrim().CreateAttribute('primvars:st:indices',Sdf.ValueTypeNames.IntArray,custom=False).Block()
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(wall);roof_faces=[];offset=0
    for index,count in enumerate(geometry[1]):
        q=np.asarray([geometry[0][i] for i in geometry[2][offset:offset+count]]);offset+=count;n=np.cross(q[1]-q[0],q[2]-q[0])
        if n[2]>0 and n[2]/np.linalg.norm(n)>.5:roof_faces.append(index)
    for name,indices,mat in [('RoofMaterial',roof_faces,roof),('WallMaterial',[i for i in range(len(geometry[1])) if i not in set(roof_faces)],wall)]:
        subset=UsdGeom.Subset.Define(stage,path+'/'+name);subset.CreateElementTypeAttr('face');subset.CreateFamilyNameAttr('materialBind');subset.CreateIndicesAttr(indices)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(mat)
    UsdGeom.Subset.SetFamilyType(mesh,'materialBind',UsdGeom.Tokens.partition)
    return mesh,gate


def gabled_prism(x0,x1,y0,y1,base,eave,peak):
    center=(y0+y1)/2
    front=[(x0,y0,base),(x0,y1,base),(x0,y1,eave),(x0,center,peak),(x0,y0,eave)]
    back=[(x1,y0,base),(x1,y1,base),(x1,y1,eave),(x1,center,peak),(x1,y0,eave)]
    faces=[front,back]+[[front[i],back[i],back[(i+1)%5],front[(i+1)%5]] for i in range(5)]
    centroid=np.mean(front+back,axis=0);points=[];counts=[];indices=[]
    for face in faces:
        q=np.asarray(face);n=np.cross(q[1]-q[0],q[2]-q[0])
        if np.dot(n,q.mean(axis=0)-centroid)<0:face=list(reversed(face))
        start=len(points);points.extend(face);counts.append(len(face));indices.extend(range(start,len(points)))
    return points,counts,indices


def cube(stage,path,position,scale,mat):
    prim=UsdGeom.Cube.Define(stage,path);prim.CreateSizeAttr(1);prim.AddTranslateOp().Set(Gf.Vec3d(*position));prim.AddScaleOp().Set(Gf.Vec3f(*scale));UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(mat)


def build():
    base=ROOT/'scene/landmark_building_proposal.usda'
    if sha(base)!=BASE_SHA:raise ValueError('Original geometry proposal changed; architecture needs review')
    active=read(ROOT/'data/processed/active.json');points,evidence,evidence_sha=verify_source(ROOT,SITES[1],active)
    existing=read(ROOT/'data/heights/landmarks/proposal_manifest.json');site=next(s for s in existing['sites'] if s['site_id']=='andersen_office_1615');outline_json=site['components'][0]['footprint_utm']
    if hashlib.sha256(json.dumps(outline_json,sort_keys=True).encode()).hexdigest()!=OUTLINE_SHA:raise ValueError('Original office envelope changed')
    outline=shape(outline_json);source=points[np.isin(points[:,3],[1,6])&shapely.contains_xy(outline,points[:,0],points[:,1])&(points[:,2]>36)&(points[:,2]<41.2)]
    _,indices=cKDTree(source[:,:3]).query(source[:,:3],k=16);neighborhood=source[indices,:3];centered=neighborhood-neighborhood.mean(axis=1,keepdims=True);cov=np.einsum('nki,nkj->nij',centered,centered)/16
    values,vectors=np.linalg.eigh(cov);source=source[(np.abs(vectors[:,2,0])>=.65)&(values[:,0]/np.maximum(values[:,1],1e-10)<=.12)]
    regions,planes,fit=coherent_regions(outline,source)
    geometry,mesh_proof=planar_region_geometry(regions,{'left_utm_m':LEFT,'bottom_utm_m':BOTTOM,'cell_m':1},ORIGIN,GROUND)
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    brick=material(stage,'Brick',(.3,.095,.045));roof=material(stage,'Roof',(.1,.115,.105));white=material(stage,'Trim',(.82,.82,.76));glass=material(stage,'Window',(.07,.11,.12))
    main,gate=finish_mesh(stage,TARGET,geometry,brick,roof)
    main.GetPrim().SetCustomDataByKey('roofArchitectureQuality','historical source-fitted/photo-interpreted coherent proposal; not current architectural survey')
    details=[];local=shapely.transform(outline,lambda x,y:(x-ORIGIN[0],y-ORIGIN[1]),interleaved=False)
    # Four front dormers are visible in brokerphotos. Width/depth/positions are
    # approximate proportions, NOT measured photo-derived coordinates or back detail.
    for wing,lo,hi in [('South',local.bounds[1],-640.),('North',-609.,local.bounds[3])]:
        for number,fraction in enumerate([.25,.75],1):
            y=lo+(hi-lo)*fraction;section=local.intersection(box(-100,y-.05,100,y+.05));front=section.bounds[0]+1.2;back=front+2.3
            basez=roof_height(planes,front,y)-.03;backz=roof_height(planes,back,y)
            eave=max(basez+1.05,backz+.08);peak=eave+.62;width=1.9
            path='/World/Landmarks/AndersenOffice1615/ArchitecturalDormers/'+wing+str(number)
            dormer,dgate=finish_mesh(stage,path,gabled_prism(front,back,y-width/2,y+width/2,basez,eave,peak),white,roof)
            dormer.GetPrim().SetCustomData({'quality':'photo-established front dormer, approximate placement/proportions; no survey dimensions','photoDate':'unknown'})
            cube(stage,path+'/Window',(front-.012,y,basez+.58),(.018,.67,.88),glass)
            cube(stage,path+'/WindowVertical',(front-.025,y,basez+.58),(.025,.035,.88),white)
            cube(stage,path+'/WindowHorizontal',(front-.025,y,basez+.58),(.025,.67,.035),white)
            details.append({'id':wing+str(number),'type':'photo_front_dormer_approximate','position_local_m':[front,y,basez],'closed_shell':dgate,'maximum_z_m':peak})
    # Only the two front chimneys are both visible in photos and independently
    # supported by high point clusters. An ambiguous back cluster is not modeled.
    for name,ylo,yhi in [('South',-656.,-653.),('North',-595.,-592.)]:
        high=points[np.isin(points[:,3],[1,6])&(points[:,0]-ORIGIN[0]>-18.5)&(points[:,0]-ORIGIN[0]<-15.5)&(points[:,1]-ORIGIN[1]>ylo)&(points[:,1]-ORIGIN[1]<yhi)&(points[:,2]>41)&(points[:,2]<45)]
        if len(high)<8:raise ValueError('Photo chimney lacks expected high source returns')
        x,y=np.median(high[:,:2],axis=0)-ORIGIN;top=float(np.percentile(high[:,2],90)-GROUND+.1);bottom=roof_height(planes,x,y)-.1
        footprint=box(x-.32,y-.65,x+.32,y+.65).intersection(local)
        path='/World/Landmarks/AndersenOffice1615/ArchitecturalChimneys/'+name
        chimney,cgate=finish_mesh(stage,path,mesh_geometry([(footprint,bottom,top)]),brick,roof)
        chimney.GetPrim().SetCustomData({'quality':'photo-established chimney and historical high-return cluster; footprint thickness approximate','sourcePoints':len(high)})
        details.append({'id':name,'type':'photo_and_point_supported_chimney','source_points':len(high),'z_p10_p50_p90_navd88_m':np.percentile(high[:,2],[10,50,90]).tolist(),
                        'position_local_m':[float(x),float(y),bottom],'maximum_z_m':top,'closed_shell':cgate})
    residual=[];main_residual=[]
    for point in source:
        x,y=point[:2]-ORIGIN;predicted=roof_height(planes,x,y)+GROUND-.1;error=abs(point[2]-predicted);residual.append(error)
        if not (-630<y< -618 and x< -15):main_residual.append(error)
    fit['all_roof_oriented_point_residual_p50_p90_p95_m']=np.percentile(residual,[50,90,95]).tolist()
    fit['excluding_known_front_clock_portico_zone_residual_p50_p90_p95_m']=np.percentile(main_residual,[50,90,95]).tolist()
    fit['all_points_within25cm']=int((np.asarray(residual)<=.25).sum());fit['roof_oriented_points_evaluated']=len(source)
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'geometry_proposal_sha256':BASE_SHA,
        'source_cloud_sha256':SITES[1]['cloud_sha256'],'source_evidence_sha256':evidence_sha,'source_acquisition':'2018-12-04 to2019-04-12; exact local flight date unknown',
        'source_footprint_sha256':OUTLINE_SHA,'parcel_id':SITES[1]['pin'],'ground_reference_navd88_m':GROUND,'ground_reference_observed_p05_p95_m':[29.60,29.91],
        'fit':fit,'geometry':mesh_proof,'main_closed_shell':gate,'details':details,
        'central_portico_alignment':{'center_y_local_m':-624.156,'main_roof_level_navd88_m':planes['central_crown'][2],
            'suggested_pediment_base_local_m':8.05,'suggested_pediment_tip_local_m':10.75,'portico_roof_authored':False},
        'photo_reference':{'url':'https://www.bbdre.com/wp-content/uploads/2023/05/1615-Edgewater-Dr-2025-1.pdf','reviewed_pages':[3,4,9],'capture_date':'unknown',
            'use':'qualitative roof form/visible detail interpretation; no source pixels traced, textured, embedded or redistributed'},
        'limits':['Architectural mass is historically source-fitted and photo-interpreted, not current/as-built acceptance.',
            'Source supports roof planes/crown levels; roof block transitions and dormer proportions are approximate.',
            'Two visible front chimneys modeled; speculative back dormers/chimneys omitted.',
            'Existing base geometry, raw tax links, snapshot, active model and global heights remain unchanged.'],
        'status':'architectural_proposal_pending_actual_visual_review','worker_thread_caps':1}
    stage.GetRootLayer().customLayerData={'geometryProposalSha256':BASE_SHA,'sourceSnapshot':active['snapshot'],'purpose':'Office-only coherent architectural roof proposal; no activation',
        'sourceCloudSha256':SITES[1]['cloud_sha256'],'photoInterpretationStatus':'qualitative broker reference; photo date unknown; no image reuse',
        'sourceFitEvidenceJson':json.dumps(report,sort_keys=True)}
    out=ROOT/'scene/office_architectural_roof_proposal.usda';tmp=out.with_name(out.stem+'.tmp.usda');stage.GetRootLayer().Export(str(tmp));os.replace(tmp,out)
    if sha(base)!=BASE_SHA:raise ValueError('Original geometry changed during proposal generation')
    report['layer']=str(out);report['layer_sha256']=sha(out)
    manifest=ROOT/'data/heights/landmarks/office_architectural_roof.json';temporary=manifest.with_suffix('.json.tmp');temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');os.replace(temporary,manifest)
    print(json.dumps({'layer':str(out),'layer_sha256':report['layer_sha256'],'manifest':str(manifest),'manifest_sha256':sha(manifest),
        'architectural_patches':len(regions),'main_faces':len(geometry[1]),'main_closed_shell':gate,'roof_fit':fit['all_roof_oriented_point_residual_p50_p90_p95_m'],
        'details':len(details),'old_geometry_unchanged':True},indent=2));return report

if __name__=='__main__':build()
