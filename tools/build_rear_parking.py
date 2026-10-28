"""Add bounded historical asphalt interpretation, preserving all source geometry."""
from pathlib import Path
import datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from pyproj import Transformer
from constrain_scene import mesh_footprint,ground_footprint

def pixel_ground(points,extent,width,height,project,origin):
    if any(not 0<=x<=width or not 0<=y<=height for x,y in points):raise ValueError('Sample outside image')
    coords=[]
    for x,y in points:
        a=extent['xmin']+x/width*(extent['xmax']-extent['xmin']);b=extent['ymax']-y/height*(extent['ymax']-extent['ymin'])
        e,n=project.transform(a,b);coords.append((e-origin[0],n-origin[1]))
    result=Polygon(coords)
    if not result.is_valid or result.area<=0:raise ValueError('Invalid surface polygon')
    return result

def build(root=ROOT):
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    config=read(root/'config/rear_parking_samples.json');manifest=read(root/'data/imagery/pilot_imagery_manifest.json')
    ref=next(r for r in manifest['references'] if r['service_name']==config['image_service']);image=root/ref['image_path']
    if hashlib.sha256(image.read_bytes()).hexdigest()!=ref['image_fetch']['sha256']:raise ValueError('Image checksum mismatch')
    extent=ref['export_extent']
    if extent['spatialReference'].get('latestWkid')!=2236:raise ValueError('Unsupported aerial frame')
    active=read(root/'data/processed/active.json');study=read(root/'config/study_area.json')
    origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*study['local_origin_wgs84']);project=Transformer.from_crs(2236,32617,always_xy=True)
    source=Usd.Stage.Open(str(root/'scene/college_park_connected.usda'));blocked=[];blockers=[]
    for scope in ['Buildings','Streets','Sidewalks']:
        parent=source.GetPrimAtPath('/World/'+scope)
        if parent:
            for prim in Usd.PrimRange(parent):
                if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':
                    geometry=mesh_footprint(prim);blocked.append(geometry);blockers.append((str(prim.GetPath()),geometry))
    obstacles=unary_union(blocked);ground=ground_footprint(source)
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z');records=[]
    for sample in config['samples']:
        polygon=pixel_ground(sample['pixels'],extent,ref['image_fetch']['width'],ref['image_fetch']['height'],project,origin)
        clipped=polygon.intersection(ground).difference(obstacles.buffer(.15));points=[]
        for tri in constrained_delaunay_triangles(clipped).geoms:
            if clipped.covers(tri):points.extend([(x,y,.045) for x,y in list(tri.exterior.coords)[:3]])
        if not points:raise ValueError('Sample has no supported unblocked surface')
        path='/World/RearParkingSamples/'+sample['id'];mesh=UsdGeom.Mesh.Define(stage,path);mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr([3]*(len(points)//3));mesh.CreateFaceVertexIndicesAttr(list(range(len(points))));mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True)
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set([(x/4,y/4) for x,y,z in points])
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).GetDirectBindingRel().SetTargets([Sdf.Path('/World/DetailMaterials/Asphalt')])
        mesh.GetPrim().SetCustomData({'quality':'historical_aerial_visual_interpretation_not_surveyed','sourceSnapshot':active['snapshot'],'imageAcquisition':'2025-01','publicAccess':'unknown','capacityVerified':False,'completeLotBoundary':False})
        rendered=unary_union([Polygon([(p[0],p[1]) for p in points[i:i+3]]) for i in range(0,len(points),3)])
        if abs(rendered.area-clipped.area)>1e-5:raise ValueError('Triangulation lost supported surface area')
        if rendered.intersection(obstacles).area>1e-6 or rendered.difference(ground).area>1e-6:raise ValueError('Surface overlap or spillover')
        conflicts=[{'usd_path':path,'overlap_m2':round(geometry.intersection(polygon).area,3)} for path,geometry in blockers if geometry.intersection(polygon).area>.1]
        records.append({'id':sample['id'],'source_pixels':sample['pixels'],'interpreted_area_m2':polygon.area,'rendered_area_m2':rendered.area,'removed_for_obstacles_or_extent_m2':polygon.area-rendered.area,'triangles':len(points)//3,'source_model_conflicts':sorted(conflicts,key=lambda r:-r['overlap_m2']),'requires_edge_and_conflict_review':True})
    stage.GetRootLayer().customLayerData={'purpose':config['interpretation'],'sourceSnapshot':active['snapshot'],'surveyAccepted':False,'imageryPixelsEmbedded':False}
    output=root/'scene/rear_parking_samples.usda';stage.GetRootLayer().Export(str(output))
    report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_image_sha256':ref['image_fetch']['sha256'],'records':records,'acceptance':'Historical visual interpretation only; full lot edges, islands, access, capacity and field accuracy remain unresolved','layer_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (root/'data/transport/rear_parking_samples.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return report

if __name__=='__main__':build()
