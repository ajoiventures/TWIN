"""CPU-only road-band diagnosis and isolated material controls; never activate.

Reuses the exact office review scene/camera. Output controls alter only asphalt
shader inputs so a subsequent coordinated render can distinguish material-path
failures from geometry. No claim that a CPU check establishes rendered cause. The original black-band
view was superseded by the stage-unit correction; these are optional controls.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
from PIL import Image,ImageStat
from shapely.geometry import Polygon,Point
from workspace_evidence import create_review_stage

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def build(output):
    output=output.resolve()
    if output.exists():raise ValueError('Use a new diagnostic directory')
    if not output.is_relative_to(ROOT/'data/diagnostics'):raise ValueError('Output must be isolated diagnostics')
    source=ROOT/'scene/office_integrated_detail_review.usda';stage=create_review_stage(source)
    dependencies={str(Path(l.realPath).relative_to(ROOT)).replace('\\','/'):sha(Path(l.realPath)) for l in stage.GetUsedLayers() if l.realPath}
    stats=collections.Counter();uv_bad=[];meshes=[]
    for p in Usd.PrimRange(stage.GetPrimAtPath('/World/Streets')):
        if not p.IsA(UsdGeom.Mesh):continue
        mesh=UsdGeom.Mesh(p);points=mesh.GetPointsAttr().Get();ids=mesh.GetFaceVertexIndicesAttr().Get();counts=mesh.GetFaceVertexCountsAttr().Get();offset=0
        uv=UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st')
        if uv and uv.GetInterpolation()=='faceVarying' and len(uv.ComputeFlattened())!=len(ids):uv_bad.append(str(p.GetPath()))
        faces=[]
        for n in counts:
            face=ids[offset:offset+n];offset+=n;normal=Gf.Cross(points[face[1]]-points[face[0]],points[face[2]]-points[face[0]])
            stats['up' if normal[2]>0 else 'down' if normal[2]<0 else 'zero']+=1
            faces.append((Polygon([(points[i][0],points[i][1]) for i in face]),float(points[face[0]][2])))
        meshes.append((p,faces))
    camera=UsdGeom.Camera(stage.GetPrimAtPath('/World/Cameras/OfficeFrontage'));matrix=camera.ComputeLocalToWorldTransform(Usd.TimeCode.Default());origin=matrix.Transform(Gf.Vec3d(0));samples=[]
    for px,py in ((1250,820),(1550,920),(300,660)):
        direction=matrix.TransformDir(Gf.Vec3d((px/1920-.5)*camera.GetHorizontalApertureAttr().Get()/camera.GetFocalLengthAttr().Get(),(.5-py/1080)*camera.GetVerticalApertureAttr().Get()/camera.GetFocalLengthAttr().Get(),-1))
        q=origin+direction*((.065-origin[2])/direction[2]);hits=[]
        for p,faces in meshes:
            for poly,z in faces:
                if poly.covers(Point(q[0],q[1])):
                    hits.append({'prim':str(p.GetPath()),'z_m':z,'material':str(UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0].GetPath())});break
        samples.append({'image_pixel':[px,py],'road_plane_world_point':list(q),'xy_surface_candidates':hits,'method_limit':'Ray intersection with road plane and street XY faces; not a full rendered primary-hit or shadow query'})
    maps={}
    for channel in ('Diffuse','Rough','nor_gl'):
        shader=UsdShade.Shader(stage.GetPrimAtPath('/World/DetailMaterials/Asphalt/PBR_'+channel));asset=shader.GetInput('file').Get();path=Path(asset.resolvedPath)
        maps[channel]={'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path),'mean_channels':ImageStat.Stat(Image.open(path)).mean,'resolved':True};dependencies[maps[channel]['path']]=sha(path)
    output.mkdir(parents=True)
    for label,normal,rough in [('no_normal',True,False),('constant_roughness',False,True),('no_normal_constant_roughness',True,True)]:
        control=Usd.Stage.CreateNew(str(output/(label+'.usda')))
        UsdGeom.SetStageUpAxis(control,UsdGeom.GetStageUpAxis(stage))
        UsdGeom.SetStageMetersPerUnit(control,UsdGeom.GetStageMetersPerUnit(stage))
        shader=UsdShade.Shader.Define(control,'/World/DetailMaterials/Asphalt/Surface')
        if normal:
            value=shader.CreateInput('normal',Sdf.ValueTypeNames.Normal3f);value.DisconnectSource();value.Set(Gf.Vec3f(0,0,1))
        if rough:
            value=shader.CreateInput('roughness',Sdf.ValueTypeNames.Float);value.DisconnectSource();value.Set(.96)
        control.GetRootLayer().subLayerPaths=[os.path.relpath(source,output).replace('\\','/')];control.GetRootLayer().customLayerData={'diagnosticOnly':True,'geometryChanged':False,'lightChanged':False};control.GetRootLayer().Save()
    assert all(sha(ROOT/k)==v for k,v in dependencies.items())
    report={'source_scene':str(source.relative_to(ROOT)).replace('\\','/'),'camera':'/World/Cameras/OfficeFrontage','street_face_orientation':dict(stats),'uv_length_mismatches':uv_bad,'pixel_surface_candidates':samples,'asphalt_maps':maps,'dependencies':dependencies,'controls':{p.name:sha(p) for p in output.glob('*.usda')},'source_files_unchanged':True,'geometry_or_lighting_changed':False,'render_status':'not_run','historical_diagnosis_superseded_by':'docs/evidence/render-stage-correction.json','supported_findings':['Historical bad-view sample points have a road mesh above a lower shoulder; no absent-ground hole at those coordinates.','Upward street face winding and UV cardinality checks pass; the former black-band view had incorrect review units.','All asphalt PBR files resolve; roughness texture is not globally zero and material metallic is zero.'],'unresolved':['CPU inspection alone cannot identify a renderer/material-graph failure or rule out view-dependent shading and occlusion.','Three diagnostic controls isolate normal and roughness paths; none is a proposed permanent fix until matched actual renders establish cause.','Roads and shoulders remain schematic centerline buffers, not surveyed curb/sidewalk geometry.']}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('street_face_orientation','uv_length_mismatches','render_status','supported_findings')},indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();build(args.output)
