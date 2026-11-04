"""Isolated dated campus paving interpretation, never active source edits.

Run python tools/prepare_campus_hardscape.py --output data/diagnostics/<new-folder>.
2025 returned-frame pixel polygons are conservative visible paving, checked
qualitatively against2024. No stalls, capacity, access, survey edges or hidden
under-canopy ground inferred. Local review only: imagery rights remain unresolved
for public derivative distribution. Geometry is a proposal, not an API product.
"""
from pathlib import Path
import os,sys,json,hashlib,argparse,datetime
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf,UsdLux
from PIL import Image
from shapely.geometry import Polygon,mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from pyproj import Transformer
from build_rear_parking import pixel_ground

SAMPLE_INPUT=Path('data/diagnostics/next_landmark_20261030/full_campus_references/hardscape_samples.json')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def world_footprint(prim,transforms):
    mesh=UsdGeom.Mesh(prim);points=mesh.GetPointsAttr().Get() or [];ids=mesh.GetFaceVertexIndicesAttr().Get() or [];counts=mesh.GetFaceVertexCountsAttr().Get() or []
    matrix=transforms.GetLocalToWorldTransform(prim);world=[matrix.Transform(Gf.Vec3d(*v)) for v in points];parts=[];offset=0
    for n in counts:
        coords=[(world[i][0],world[i][1]) for i in ids[offset:offset+n]];offset+=n
        if len(coords)<3:continue
        polygon=Polygon(coords)
        if polygon.area>1e-8:
            if not polygon.is_valid:raise ValueError('Invalid projected blocking face: '+str(prim.GetPath()))
            parts.append(polygon)
    return unary_union(parts)

def build(output,root=ROOT,samples=None):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'data/diagnostics'):raise ValueError('Use a new diagnostic folder; preserve previous candidate')
    samples_path=Path(samples).resolve() if samples else root/SAMPLE_INPUT
    if not samples_path.is_relative_to(root):raise ValueError('Local sample input must stay inside project')
    samples=json.loads(samples_path.read_text(encoding='utf-8'))['samples']
    folder=root/'data/diagnostics/next_landmark_20261030/full_campus_references';manifest_path=folder/'aerial_manifest.json';manifest=json.loads(manifest_path.read_text())
    active_path=root/'data/processed/active.json';snapshot=json.loads(active_path.read_text())['snapshot'];study=json.loads((root/'config/study_area.json').read_text());origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*study['local_origin_wgs84']);project=Transformer.from_crs(2236,32617,always_xy=True)
    scene=root/'scene/college_park_connected.usda';stage=Usd.Stage.Open(str(scene));transforms=UsdGeom.XformCache();bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']);raw=[];dependencies={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in [Path(__file__),samples_path,root/'tools/build_rear_parking.py',manifest_path,active_path,root/'config/study_area.json']}
    for layer in stage.GetUsedLayers():
        if layer.realPath:
            p=Path(layer.realPath).resolve()
            if not p.is_relative_to(root):raise ValueError('Source layer outside project')
            dependencies[str(p.relative_to(root)).replace('\\','/')]=sha(p)
    for sample in samples:
        refs=[r for r in manifest['references'] if r['site_id']==sample['site_id']]
        ref=next(r for r in refs if r['acquisition']['month']=='2025-01');previous=next(r for r in refs if r['acquisition']['month']=='2024-01')
        for r in (ref,previous):
            image=root/r['image']
            if sha(image)!=r['image_receipt']['sha256']:raise ValueError('Dated source image changed')
            dependencies[r['image']]=sha(image)
            with Image.open(image) as im:
                if im.size!=(r['width'],r['height']):raise ValueError('Image frame size changed')
        extent=ref['returned_extent']
        if extent['spatialReference'].get('latestWkid')!=2236:raise ValueError('Unsupported returned image CRS')
        outer=pixel_ground(sample['outline'],extent,ref['width'],ref['height'],project,origin)
        holes=unary_union([pixel_ground(p,extent,ref['width'],ref['height'],project,origin) for p in sample['holes']])
        candidate=outer.difference(holes)
        if not candidate.is_valid or candidate.is_empty:raise ValueError('Invalid interpreted paving')
        raw.append((sample,ref,previous,outer,holes,candidate))
    all_raw=unary_union([r[-1] for r in raw]);blocked=[];blocker_records=[];ground=[];previous_samples=[]
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        path=str(prim.GetPath());is_ground=path=='/World/Ground' or path.startswith('/World/Ground/');is_previous=path.startswith('/World/RearParkingSamples/')
        is_blocker=any(path.startswith('/World/'+p+'/') for p in ['Buildings','Streets','Landmarks','Sidewalks','OfficeFrontageProposal','OfficeFrontageDetail'])
        if not(is_ground or is_previous or is_blocker):continue
        bb=bounds.ComputeWorldBound(prim).ComputeAlignedRange()
        if not is_ground and (bb.IsEmpty() or bb.GetMax()[0]<all_raw.bounds[0] or bb.GetMin()[0]>all_raw.bounds[2] or bb.GetMax()[1]<all_raw.bounds[1] or bb.GetMin()[1]>all_raw.bounds[3]):continue
        geometry=world_footprint(prim,transforms)
        if is_ground:ground.append(geometry)
        elif is_previous:previous_samples.append(geometry)
        elif not geometry.is_empty:blocked.append(geometry);blocker_records.append((path,geometry))
    ground=unary_union(ground);obstacles=unary_union(blocked);prior=unary_union(previous_samples)
    if ground.is_empty:raise ValueError('Actual model ground unavailable')
    proposal=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(proposal,'Z');UsdGeom.SetStageMetersPerUnit(proposal,1)
    parent=UsdGeom.Xform.Define(proposal,'/World/CampusHardscapeCandidate');parent.GetPrim().SetCustomData({'quality':'historical_aerial_visual_interpretation_not_surveyed','sourceSnapshot':snapshot,'active':False,'localReviewOnly':True,'publicDerivativeRightsEstablished':False})
    # Reuse the project's physical-scale paving, not a flat albedo swatch.
    material=UsdShade.Material(stage.GetPrimAtPath('/World/DetailMaterials/Asphalt'))
    if not material:raise ValueError('Existing project paving material unavailable')
    for prim in Usd.PrimRange(material.GetPrim()):
        for attr in prim.GetAttributes():
            if attr.GetTypeName()==Sdf.ValueTypeNames.Asset:
                value=attr.Get()
                if value and value.path:
                    texture=Path(value.resolvedPath)
                    if not texture.is_file() or not texture.is_relative_to(root):raise ValueError('Unresolved project paving texture')
                    dependencies[texture.relative_to(root).as_posix()]=sha(texture)
    pale=UsdShade.Material.Define(proposal,'/World/CampusHardscapeCandidate/Materials/UnclassifiedPaleFeature')
    shader=UsdShade.Shader.Define(proposal,pale.GetPath().AppendChild('Surface'));shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.40,.40,.36));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.92);pale.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    records=[];features=[];occupied=unary_union([]);review_geometries=[]
    for sample,ref,previous,outer,holes,candidate in raw:
        clipped=candidate.intersection(ground).difference(obstacles.buffer(.15)).difference(occupied);points=[]
        if clipped.is_empty:raise ValueError('All supported paving excluded; requires conflict review')
        for triangle in constrained_delaunay_triangles(clipped).geoms:
            if clipped.covers(triangle):points.extend([(x,y,.045) for x,y in list(triangle.exterior.coords)[:3]])
        mesh=UsdGeom.Mesh.Define(proposal,'/World/CampusHardscapeCandidate/'+sample['id']);mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr([3]*(len(points)//3));mesh.CreateFaceVertexIndicesAttr(list(range(len(points))));mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True);UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set([(x/4,y/4) for x,y,z in points])
        context={'publisher':'Orange County Property Appraiser aerial service','sourceURL':ref['service_url'],'sourceSnapshot':snapshot,'acquisitionStart':'2025-01','acquisitionEnd':'2025-01','effectiveDate':'unknown','quality':'historical_aerial_visual_interpretation_not_surveyed','rights':'local review only; public derivative distribution not established'}
        mesh.GetPrim().SetCustomData({'sourceContext':context,'siteId':sample['site_id'],'quality':context['quality'],'capacityVerified':False,'publicAccess':'unknown','completeLotBoundary':False,'surveyAccepted':False})
        serialized=mesh.GetPointsAttr().Get();rendered=unary_union([Polygon([(p[0],p[1]) for p in serialized[i:i+3]]) for i in range(0,len(serialized),3)])
        if rendered.symmetric_difference(clipped).area>.03:raise ValueError('Float mesh projection differs from interpreted surface')
        if rendered.intersection(obstacles).area>1e-5 or rendered.difference(ground.buffer(.001)).area>1e-5:raise ValueError('Paving overlaps building/road or spills beyond ground')
        occupied=occupied.union(clipped)
        review_geometries.append((sample['id'],outer,rendered))
        record={'id':sample['id'],'site_id':sample['site_id'],'source_pixels':sample['outline'],'island_exclusion_pixels':sample['holes'],'acquisition_month':'2025-01','comparison_month':'2024-01','comparison_policy':'Qualitative visible continuity, no quantitative source-registration/control claim','source_image_sha256':ref['image_receipt']['sha256'],'returned_extent':ref['returned_extent'],'pixel_to_source':{'x':'xmin +pixel_x/width*(xmax-xmin)','y':'ymax -pixel_y/height*(ymax-ymin)','width':ref['width'],'height':ref['height'],'source_crs':'EPSG:2236 US survey feet','project_crs':'EPSG:32617 meters','local_origin_utm_m':origin,'sampling_resolution':ref['export_resolution']},'outer_interpretation_m2':outer.area,'visible_island_exclusions_m2':outer.intersection(holes).area,'candidate_after_islands_m2':candidate.area,'after_model_building_road_ground_exclusions_m2':rendered.area,'removed_for_model_conflicts_or_extent_m2':candidate.area-clipped.area,'overlap_with_prior_three_samples_m2':rendered.intersection(prior).area,'additional_paving_beyond_prior_samples_m2':rendered.difference(prior).area,'building_road_overlap_after_m2':rendered.intersection(obstacles).area,'outside_ground_after_m2':rendered.difference(ground.buffer(.001)).area,'triangles':len(points)//3,'source_model_conflicts':[{'prim':path,'overlap_m2':candidate.intersection(g).area} for path,g in blocker_records if candidate.intersection(g).area>.1],'limits':sample['limits']}
        records.append(record);features.append({'type':'Feature','geometry':mapping(rendered),'properties':{'id':sample['id'],'coordinate_system':'local EPSG32617 offset meters','quality':context['quality'],'local_review_only':True}})
        # The source shows pale features, not planting. Leaving these holes
        # exposed the green base and falsely depicted grass in the first view.
        pale_geometry=outer.intersection(holes).intersection(ground).difference(obstacles.buffer(.15)).difference(occupied)
        pale_points=[]
        for triangle in constrained_delaunay_triangles(pale_geometry).geoms:
            if pale_geometry.covers(triangle):pale_points.extend([(x,y,.045) for x,y in list(triangle.exterior.coords)[:3]])
        if pale_points:
            feature=UsdGeom.Mesh.Define(proposal,'/World/CampusHardscapeCandidate/'+sample['id']+'_pale_features');feature.CreatePointsAttr(pale_points);feature.CreateFaceVertexCountsAttr([3]*(len(pale_points)//3));feature.CreateFaceVertexIndicesAttr(list(range(len(pale_points))));feature.CreateSubdivisionSchemeAttr('none');feature.CreateDoubleSidedAttr(True);UsdShade.MaterialBindingAPI.Apply(feature.GetPrim()).Bind(pale)
            feature.GetPrim().SetCustomData({'quality':context['quality'],'sourceContext':context,'surfaceAppearance':'pale ground feature visible in dated aerial','function':'unknown; not classified planting, curb, pole or accessible facility','measuredDimensions':False})
            serialized=feature.GetPointsAttr().Get();pale_rendered=unary_union([Polygon([(p[0],p[1]) for p in serialized[i:i+3]]) for i in range(0,len(serialized),3)])
            if pale_rendered.symmetric_difference(pale_geometry).area>.01 or pale_rendered.intersection(obstacles).area>1e-5:raise ValueError('Pale feature projection/conflict mismatch')
            record['unclassified_pale_feature_area_m2']=pale_rendered.area;record['unclassified_pale_feature_triangles']=len(pale_points)//3
            record['pale_feature_semantics']='Source-visible pale surface only; function/material unknown, no planting inference'
            occupied=occupied.union(pale_geometry)
        else:record['unclassified_pale_feature_area_m2']=0.0
    output.mkdir(parents=True);layer=output/'site.usda';proposal.GetRootLayer().customLayerData={'proposalOnly':True,'sourceSnapshot':snapshot,'imageryPixelsEmbedded':False,'rights':'Local review only; no public derivative release or activation accepted'};proposal.GetRootLayer().Export(str(layer))
    review=Usd.Stage.CreateInMemory();review.GetRootLayer().subLayerPaths=[str(layer),str(scene)];UsdGeom.SetStageUpAxis(review,'Z');UsdGeom.SetStageMetersPerUnit(review,1)
    cameras=[]
    for name,outer,rendered in review_geometries:
        left,bottom,right,top=outer.bounds;cx,cy=(left+right)/2,(bottom+top)/2;span=max(right-left,top-bottom)
        path='/World/Cameras/CampusHardscape_'+name;camera=UsdGeom.Camera.Define(review,path)
        camera.CreateFocalLengthAttr(35);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,2000))
        camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(cx-span*.8,cy-span*1.1,span*1.15),Gf.Vec3d(cx,cy,0),Gf.Vec3d(0,0,1)).GetInverse());cameras.append(path)
    review.GetRootLayer().Export(str(output/'review.usda'))
    (output/'paving_local.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},indent=2))
    # Vector-only QA maps: proposed outline, retained paving and model conflicts.
    for name,outer,rendered in review_geometries:
        left,bottom,right,top=outer.buffer(3).bounds;scale=800/(right-left);height=(top-bottom)*scale;paths=[]
        for geometry,fill,stroke in [(outer,'none','#ca8b12'),(rendered,'#626663','#222'),(obstacles.intersection(outer),'#d78989','#9c4545')]:
            for polygon in __import__('shapely').get_parts(geometry):
                if polygon.geom_type!='Polygon':continue
                d=' '.join('M '+' L '.join(f'{(x-left)*scale:.3f},{(top-y)*scale:.3f}' for x,y in ring.coords)+' Z' for ring in [polygon.exterior,*polygon.interiors])
                paths.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="1" fill-rule="evenodd"/>')
        (output/(name+'_geometry.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height:.3f}"><title>Local historical paving review: gray retained, gold interpretation outline, red existing model conflict; no aerial pixels</title><rect width="800" height="{height}" fill="#dbe5d2"/>'+''.join(paths)+'</svg>')
    if any(sha(root/n)!=v for n,v in dependencies.items()):raise ValueError('Source changed during proposal build')
    report={'schema':'twin.campus-hardscape-candidate/1','source_snapshot':snapshot,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':records,'review_cameras':cameras,'dependencies':dependencies,'outputs':{p.name:sha(p) for p in output.iterdir() if p.is_file()},'source_scene_changed':False,'active':False,'rights_publication_accepted':False,'source_pixels_embedded':False,'geometry_acceptance':'Local historical visual-interpretation proposal only; independent source/geometry/actual visual review pending','limits':['No full parking inventory, stalls, access, use, legal boundary, capacity, ADA slope/clearance or current-condition claims.','Pixel sampling resolution is not positional accuracy; no surveyed controls or alignment residuals available.','Building/road exclusion uses current visible world-transformed model geometry and0.15m display margin, not measured real curb clearance.','Existing ground is flat prototype; pavementZ0.045m is an explicit cartographic display offset, not measured elevation.','No existing sample, building, road, tree or manual opinions hidden/changed.']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({'layer':str(layer),'records':[{k:r[k] for k in ['id','candidate_after_islands_m2','after_model_building_road_ground_exclusions_m2','additional_paving_beyond_prior_samples_m2','triangles']} for r in records],'manifest_sha256':sha(output/'manifest.json')},indent=2));return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--samples',type=Path);a=ap.parse_args();build(a.output,samples=a.samples)
