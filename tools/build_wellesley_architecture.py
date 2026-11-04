"""Coherent, evidence-bounded Wellesley architectural interpretation; raw retained."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,datetime,hashlib,json,math,os,shutil,statistics,sys,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
import numpy as np
import shapely
from shapely.geometry import shape,Polygon,box,mapping
from shapely.ops import unary_union
from pyproj import Transformer
from pxr import Usd,UsdGeom,UsdShade,Gf,Sdf
from correct_wellesley import mesh_geometry

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def parts(g):
    if g.geom_type=='Polygon':return [g]
    return [p for c in getattr(g,'geoms',[]) for p in parts(c)]

def build(root=ROOT):
    manifest_path=root/'data/heights/wellesley_correction/manifest.json'
    manifest=json.loads(manifest_path.read_text());config=json.loads((root/'config/building_corrections.json').read_text())
    active=json.loads((root/'data/processed/active.json').read_text())
    if manifest['source_snapshot']!=active['snapshot']:raise ValueError('Raw Wellesley source snapshot is stale')
    if abs(manifest['main_roof_height_m']-23.35)>.001 or abs(manifest['maximum_raised_height_m']-28.393)>.001 or manifest['reported_stories']!=7:raise ValueError('Reviewed height/documentary guards changed')
    source_path=root/'scene/landmark_corrections.usda';source_hash=sha(source_path)
    source=Usd.Stage.Open(str(source_path));identifier=manifest['resolved_building_id']
    path='/World/Buildings/'+identifier;raw_mesh=UsdGeom.Mesh(source.GetPrimAtPath(path))
    if not raw_mesh.GetPrim() or not raw_mesh.GetPointsAttr().HasAuthoredValueOpinion():raise ValueError('Resolved source mesh is absent')
    raw=shape(manifest['upper_footprint_local_m']);coordinates=list(raw.exterior.coords);x0,y0,x1,y1=raw.bounds
    origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*config['origin_wgs84'])
    protected=[]
    for item in config['roof_extraction']['protected_upper_voids_utm']:
        a,b,c,d=item['bounds'];protected.append(box(a-origin[0],b-origin[1],c-origin[0],d-origin[1]))
    core=unary_union(protected);a,b,c,d=core.bounds
    median=statistics.median
    # Fit sustained envelope bands, rather than extruding every noisy/balcony
    # roof-return tooth down through seven storeys. These are interpreted wall
    # planes, not a surveyed facade. Quantitative departures are release gates.
    fitted={'west':median(x for x,y in coordinates if x<x0+7),
            'east':median(x for x,y in coordinates if x>x1-1),
            'north':median(y for x,y in coordinates if y>y1-5),
            'south':median(y for x,y in coordinates if y<y0+5),
            'courtyard_west':median(x for x,y in coordinates if a-14<x<a-4 and b+1.5<y<d+4.5),
            'courtyard_south':median(y for x,y in coordinates if x>a-4 and b-4<y<b+3),
            'courtyard_north':median(y for x,y in coordinates if x>a-4 and d+1<y<d+9)}
    w,e,n,s,iw,cs,cn=[fitted[k] for k in ('west','east','north','south','courtyard_west','courtyard_south','courtyard_north')]
    chamfer=min(9,(n-s)*.15)
    proposed=Polygon([(w,s+chamfer),(w+chamfer,s),(e,s),(e,cs),(iw,cs),(iw,cn),(e,cn),(e,n),(w,n)])
    if not proposed.is_valid or proposed.intersection(core).area>1e-7:raise ValueError('Courtyard or shell validity failed')
    deviation={'raw_area_m2':raw.area,'proposed_area_m2':proposed.area,'added_area_m2':proposed.difference(raw).area,'removed_area_m2':raw.difference(proposed).area,
               'symmetric_difference_m2':raw.symmetric_difference(proposed).area,'symmetric_difference_fraction':raw.symmetric_difference(proposed).area/raw.area,
               'hausdorff_m':raw.hausdorff_distance(proposed),'raw_coverage_fraction':raw.intersection(proposed).area/raw.area,
               'raw_boundary_vertices':len(raw.exterior.coords)-1,'proposed_boundary_vertices':len(proposed.exterior.coords)-1,
               'protected_courtyard_overlap_m2':proposed.intersection(core).area,'tax_envelope_fraction':proposed.area/manifest['tax_envelope_area_m2']}
    parcel_path=root/active['relative_path']/'parcels.json'
    parcels=[f for f in json.loads(parcel_path.read_text())['features'] if f['properties'].get('site_address','').startswith(config['source_address_prefix'])]
    if len(parcels)!=114:raise ValueError('Whole-property evidence group changed')
    property_mask=unary_union([shapely.force_2d(shape(f['geometry'])) for f in parcels])
    project=Transformer.from_crs(4326,32617,always_xy=True)
    property_mask=shapely.transform(property_mask,project.transform,interleaved=False)
    property_mask=shapely.transform(property_mask,lambda x,y:(x-origin[0],y-origin[1]),interleaved=False)
    deviation['outside_official_property_search_mask_m2']=proposed.difference(property_mask).area
    if deviation['outside_official_property_search_mask_m2']>.05:raise ValueError('Architectural candidate leaves official property search mask')
    if deviation['hausdorff_m']>6 or deviation['symmetric_difference_fraction']>.14 or deviation['raw_coverage_fraction']<.92 or deviation['tax_envelope_fraction']>.8:raise ValueError('Architectural departure exceeds interpretation bounds: '+json.dumps(deviation))
    points=raw_mesh.GetPointsAttr().Get();indices=raw_mesh.GetFaceVertexIndicesAttr().Get();counts=raw_mesh.GetFaceVertexCountsAttr().Get();offset=0;tops={}
    for count in counts:
        q=[Gf.Vec3d(points[i]) for i in indices[offset:offset+count]];offset+=count
        normal=Gf.Cross(q[1]-q[0],q[2]-q[0])
        if normal[2]<=1e-8 or max(v[2] for v in q)-min(v[2] for v in q)>.002:continue
        z=round(float(q[0][2]),3);polygon=Polygon([(v[0],v[1]) for v in q])
        if polygon.is_valid and polygon.area>1e-6:tops.setdefault(z,[]).append(polygon)
    main_top=.1+manifest['main_roof_height_m'];maximum_top=.1+manifest['maximum_raised_height_m']
    lower=unary_union([g for z,polys in tops.items() if .2<z<main_top-1 for g in polys]).difference(proposed)
    equipment=[];equipment_audit=[]
    for z,polys in sorted(tops.items()):
        if z<=main_top+.01:continue
        for polygon in parts(unary_union(polys)):
            rectangle=box(*polygon.bounds)
            # Small mechanical/roof patches become coherent planar prisms.
            # Never bridge arbitrary gaps or expand beyond a bounded source band.
            fitted_patch=rectangle if rectangle.area<=polygon.area*1.6 and rectangle.difference(polygon.buffer(.8)).area<.01 else polygon.convex_hull
            fitted_patch=fitted_patch.intersection(proposed).difference(core)
            if fitted_patch.is_empty:
                equipment_audit.append({'source_top_m':z,'action':'not_rendered_outside_interpreted_main_roof','raw_area_m2':polygon.area});continue
            equipment.append((fitted_patch,main_top,z))
            equipment_audit.append({'source_top_m':z,'raw_area_m2':polygon.area,'proposed_area_m2':fitted_patch.area,'hausdorff_m':polygon.hausdorff_distance(fitted_patch),'action':'bounded_planar_prism'})
    if abs(max(z for _,_,z in equipment)-maximum_top)>.002:raise ValueError('Equipment maximum would be lost')
    # Source points corroborate the dominant deck; geometry fit is independent
    # of assumed storey heights and never creates occupied floors at equipment Z.
    cloud_path=root/'data/heights/wellesley_correction/local_points.npz';cloud=np.load(cloud_path)['points'];cx=cloud[:,0]-origin[0];cy=cloud[:,1]-origin[1]
    deck=(np.abs(cloud[:,2]-manifest['extraction']['roof_support_median_z_m'])<=.4)
    source_inside=shapely.contains_xy(raw,cx,cy)&deck;proposed_inside=shapely.contains_xy(proposed,cx,cy)&deck
    support={'dominant_deck_point_count_raw':int(source_inside.sum()),'dominant_deck_points_retained':int((source_inside&proposed_inside).sum()),
             'retained_deck_point_fraction':float((source_inside&proposed_inside).sum()/max(1,source_inside.sum())),
             'interpretation':'Point coverage supports roof mass, not exact facade setback/edge confidence.'}
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    def material(name,color):
        m=UsdShade.Material.Define(stage,'/World/WellesleyArchitectureMaterials/'+name)
        shader=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'));shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.85)
        m.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');return m
    wall=material('NeutralUnverifiedFacade',(.67,.63,.52));roof=material('LightRoofReference',(.63,.65,.62))
    components=[(proposed,.1,main_top),*equipment]
    if not lower.is_empty:components.append((lower,.1,.1+manifest['prior_height_record']['height_m']))
    def write_mesh(target,roofs_only=False):
        pts,faces,ids=mesh_geometry(components,roofs_only)
        mesh=UsdGeom.Mesh(stage.OverridePrim(target));mesh.CreatePointsAttr(pts);mesh.CreateFaceVertexCountsAttr(faces);mesh.CreateFaceVertexIndicesAttr(ids)
        mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True);normals=[];off=0
        for size in faces:
            face=[Gf.Vec3d(pts[i]) for i in ids[off:off+size]];off+=size;normal=Gf.Cross(face[1]-face[0],face[2]-face[0]);normal.Normalize();normals.append(Gf.Vec3f(normal))
        mesh.CreateNormalsAttr(normals);mesh.SetNormalsInterpolation('uniform')
        mesh.CreateExtentAttr([Gf.Vec3f(*(min(p[i] for p in pts) for i in range(3))),Gf.Vec3f(*(max(p[i] for p in pts) for i in range(3)))])
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set([(pts[i][0]/5,pts[i][1 if roofs_only else 2]/5) for i in ids])
        mesh.GetPrim().CreateAttribute('primvars:st:indices',Sdf.ValueTypeNames.IntArray,custom=False).Block()
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(roof if roofs_only else wall)
        return len(pts),len(faces)
    mesh_counts={'body':write_mesh(path),'roof':write_mesh('/World/Roofs/Roof_'+identifier.split('_')[-1],True)}
    stage.GetPrimAtPath(path).SetCustomDataByKey('architecturalInterpretation',{'status':'inactive_evidence_bounded_plane_interpretation','documentaryStoreys':7,'mainRoofHeightMeters':23.35,'equipmentMaximumMeters':28.393,'currentSurveyAccepted':False,'sourceSnapshot':active['snapshot']})
    inputs={'scene/landmark_corrections.usda':source_hash,'data/heights/wellesley_correction/manifest.json':sha(manifest_path),'data/heights/wellesley_correction/local_points.npz':sha(cloud_path),'config/building_corrections.json':sha(root/'config/building_corrections.json'),'data/imagery/wellesley/wellesley2025.jpg':sha(root/'data/imagery/wellesley/wellesley2025.jpg'),str(parcel_path.relative_to(root)):sha(parcel_path)}
    report={'source_snapshot':active['snapshot'],'resolved_building_id':identifier,'main_roof_height_m':23.35,'maximum_equipment_height_m':28.393,'documentary_storeys':7,
            'method':'Sustained source roof-envelope bands fit coherent orthogonal wall/roof planes, with source-supported southwest chamfer; bounded mechanical patch prisms. Not a smoothed cloud or parcel extrusion.',
            'fitted_planes_local_m':fitted,'deviation':deviation,'source_point_support':support,'equipment':equipment_audit,'equipment_rendered_patches':len(equipment),'mesh_counts':mesh_counts,
            'lower_legacy_area_retained_m2':lower.area,'dependencies':inputs,
            'limitations':['Roof envelope is not a surveyed wall line; balcony/cornice modulation is intentionally not extruded through seven storeys.','Historical LiDAR 2018–2019 and January2025 aerial differ in date; current architecture and equipment are not accepted.','Courtyard core and open east arm retained; no pool, ground-access or occupied-storey inference.','Neutral original facade color is unverified; no source image pixels, windows or logos embedded.','Same-camera render and architectural acceptance remain pending.']}
    stage.GetRootLayer().customLayerData={'purpose':'Inactive Wellesley coherent architectural mass proposal; raw historical source retained separately.','sourceSnapshot':active['snapshot'],'reportJson':json.dumps(report,sort_keys=True)}
    if any(sha(root/key)!=digest for key,digest in inputs.items()):raise ValueError('Source changed during architecture build')
    output=root/'scene/wellesley_architectural_proposal.usda';stage.GetRootLayer().Export(str(output))
    report.update(proposal_sha256=sha(output),output=str(output))
    out=root/'data/heights/wellesley_architecture';out.mkdir(exist_ok=True,parents=True)
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (out/'raw_and_proposed.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_frame':'local EPSG32617 minus project origin','features':[{'type':'Feature','id':'raw_historical_roof','properties':{'preserved':True},'geometry':mapping(raw)},{'type':'Feature','id':'architectural_roof','properties':{'accepted':False},'geometry':mapping(proposed)},{'type':'Feature','id':'protected_courtyard','properties':{'upper_roof_overlap_m2':0},'geometry':mapping(core)}]}),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('equipment','dependencies')},indent=2));return report

def checked_path(root,value,within=None):
    path=(root/value).resolve()
    if not path.is_relative_to((within or root).resolve()):raise ValueError('Evidence path leaves permitted directory')
    return path

def validate_activation(root=ROOT,render_manifest=None):
    root=Path(root).resolve();out=root/'data/heights/wellesley_architecture'
    report=json.loads((out/'report.json').read_text())
    proposal=root/'scene/wellesley_architectural_proposal.usda'
    if sha(proposal)!=report['proposal_sha256']:raise ValueError('Proposal changed after geometry review')
    embedded=json.loads(Sdf.Layer.FindOrOpen(str(proposal)).customLayerData['reportJson'])
    if any(report.get(key)!=value for key,value in embedded.items()):raise ValueError('Review report differs from rendered proposal metadata')
    if report.get('documentary_storeys')!=7 or report.get('main_roof_height_m')!=23.35 or report.get('maximum_equipment_height_m')!=28.393:raise ValueError('Reviewed vertical scope changed')
    if json.loads((root/'data/processed/active.json').read_text())['snapshot']!=report['source_snapshot']:raise ValueError('Activation snapshot is stale')
    for relative,digest in report['dependencies'].items():
        if sha(checked_path(root,relative))!=digest:raise ValueError('Source evidence changed: '+relative)
    if render_manifest is None:raise ValueError('--render-manifest is required for activation validation')
    proof_path=checked_path(root,render_manifest,root/'data/renders')
    proof=json.loads(proof_path.read_text())
    if proof.get('source_snapshot')!=report['source_snapshot'] or proof.get('proposal_layer')!=proposal.name:raise ValueError('Render is not bound to this proposal/snapshot')
    if proof.get('layer_hashes',{}).get('scene/'+proposal.name)!=report['proposal_sha256']:raise ValueError('Rendered proposal SHA does not match')
    if proof.get('camera') not in ('/World/Cameras/CivilPrincetonEdgewater','/World/Cameras/WellesleyEvidence'):raise ValueError('Render camera is not a bounded Wellesley review view')
    image=checked_path(root,proof['image'],root/'data/renders')
    if sha(image)!=proof.get('image_sha256') or image.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n' or image.stat().st_size<1024:raise ValueError('Successful render image evidence is missing or changed')
    return {'report':report,'proposal':proposal,'render_manifest':proof_path,'render_manifest_sha256':sha(proof_path),'render_image_sha256':sha(image)}

def validate_active_wellesley(root=ROOT):
    root=Path(root).resolve();path=root/'scene/wellesley_architecture.usda'
    if not path.exists():return False
    record_path=root/'data/heights/wellesley_architecture/activation.json'
    record=json.loads(record_path.read_text())
    if sha(path)!=record['active_layer_sha256']:raise ValueError('Active Wellesley layer changed')
    checked=validate_activation(root,record['render_manifest'])
    if checked['render_manifest_sha256']!=record['render_manifest_sha256']:raise ValueError('Active Wellesley render evidence changed')
    metadata=Sdf.Layer.FindOrOpen(str(path)).customLayerData
    if metadata.get('sourceProposalSha256')!=checked['report']['proposal_sha256'] or metadata.get('activationStatus')!='interpreted_historical_current_unverified':raise ValueError('Active Wellesley status/provenance mismatch')
    return True

def activate(root=ROOT,render_manifest=None):
    root=Path(root).resolve();checked=validate_activation(root,render_manifest);report=checked['report']
    destination=root/'scene/wellesley_architecture.usda';assembly=root/'scene/college_park_connected.usda'
    original=assembly.read_bytes();original_hash=sha(assembly)
    root_layer=Sdf.Layer.FindOrOpen(str(assembly))
    if root_layer.dirty:raise ValueError('Root has unsaved opinions; activation refused')
    copy=Sdf.Layer.CreateAnonymous();copy.TransferContent(root_layer)
    names=[name for name in copy.subLayerPaths if Path(name).name!=destination.name]
    protected=[i for i,name in enumerate(names) if Path(name).name in ('manual_edits.usda','map_extent_guard.usda')]
    position=max(protected,default=-1)+1
    landmark=next((i for i,name in enumerate(names) if Path(name).name=='landmark_corrections.usda'),None)
    if landmark is None or position>landmark:raise ValueError('Cannot preserve manual/extent strength above architectural correction')
    names.insert(position,destination.name);copy.subLayerPaths=names
    # Prove no root opinions other than the sublayer list changed.
    compare=Sdf.Layer.CreateAnonymous();compare.TransferContent(copy);compare.subLayerPaths=list(root_layer.subLayerPaths)
    if compare.ExportToString()!=root_layer.ExportToString():raise ValueError('Root opinions would change')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=root/'data/heights/wellesley_architecture/activation_backups'/stamp;backup.mkdir(parents=True)
    shutil.copy2(assembly,backup/assembly.name)
    if destination.exists():shutil.copy2(destination,backup/destination.name)
    prepared=Sdf.Layer.CreateAnonymous();prepared.ImportFromString(checked['proposal'].read_text(encoding='utf-8'))
    metadata=dict(prepared.customLayerData);metadata.update({'purpose':'Active interpreted historical Wellesley architectural mass; current conditions and facade unverified.',
        'activationStatus':'interpreted_historical_current_unverified','sourceProposalSha256':report['proposal_sha256'],
        'maximumOutlineDeviationMeters':report['deviation']['hausdorff_m'],'symmetricDifferenceFraction':report['deviation']['symmetric_difference_fraction'],
        'sourceSnapshot':report['source_snapshot'],'renderManifest':str(checked['render_manifest'].relative_to(root)),
        'renderManifestSha256':checked['render_manifest_sha256'],'sourceDependenciesJson':json.dumps(report['dependencies'],sort_keys=True)})
    prepared.customLayerData=metadata
    temp_stage=Usd.Stage.Open(prepared)
    prim=temp_stage.GetPrimAtPath('/World/Buildings/'+report['resolved_building_id'])
    interpretation=dict(prim.GetCustomDataByKey('architecturalInterpretation'))
    interpretation.update(status='active_interpreted_historical_current_unverified',maximumOutlineDeviationMeters=report['deviation']['hausdorff_m'],symmetricDifferenceFraction=report['deviation']['symmetric_difference_fraction'])
    prim.SetCustomDataByKey('architecturalInterpretation',interpretation)
    token=uuid.uuid4().hex;pending=root/'scene'/('wellesley_architecture.pending.'+token+'.usda');root_pending=root/'scene'/('college_park_connected.pending.'+token+'.usda')
    installed=False;root_installed=False
    try:
        prepared.Export(str(pending));copy.Export(str(root_pending))
        if sha(assembly)!=original_hash:raise ValueError('Root changed during activation; retry after reviewing latest edits')
        # Check provenance again immediately before the two atomic replacements.
        validate_activation(root,render_manifest)
        os.replace(pending,destination);installed=True
        composed=Usd.Stage.Open(str(root_pending))
        if not composed.GetPrimAtPath('/World/Buildings/'+report['resolved_building_id']):raise ValueError('Prepared composition lost Wellesley')
        os.replace(root_pending,assembly);root_installed=True
        record={'activated_utc':stamp,'source_snapshot':report['source_snapshot'],'active_layer_sha256':sha(destination),'source_proposal_sha256':report['proposal_sha256'],
            'render_manifest':str(checked['render_manifest'].relative_to(root)),'render_manifest_sha256':checked['render_manifest_sha256'],
            'root_before_sha256':original_hash,'root_after_sha256':sha(assembly),'root_backup':str((backup/assembly.name).relative_to(root)),
            'status':'interpreted_historical_current_unverified','deviation':report['deviation'],'facade_status':'blank neutral unverified; no facade completion claimed'}
        (root/'data/heights/wellesley_architecture/activation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps(record,indent=2));return record
    except Exception:
        if installed and not root_installed:
            if (backup/destination.name).exists():shutil.copy2(backup/destination.name,destination)
            elif destination.exists():destination.unlink()
        raise
    finally:
        for path in (pending,root_pending):
            if path.exists():path.unlink()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_mutually_exclusive_group();actions.add_argument('--activate',action='store_true');actions.add_argument('--validate-activation',action='store_true')
    parser.add_argument('--render-manifest',type=Path)
    args=parser.parse_args()
    if args.activate:activate(render_manifest=args.render_manifest)
    elif args.validate_activation:
        checked=validate_activation(render_manifest=args.render_manifest)
        print(json.dumps({'ready':True,'proposal_sha256':checked['report']['proposal_sha256'],'render_manifest':str(checked['render_manifest']),'activation_performed':False},indent=2))
    else:build()
