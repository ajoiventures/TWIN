"""Small architectural work view; full-district integration remains a separate check."""
from pathlib import Path
import argparse,hashlib,json,sys,math,shutil,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Gf,Sdf,Usd,UsdGeom,UsdLux,UsdShade

def build(root=ROOT):
    folder=root/'scene';layers=['office_frontage_proposal.usda','landmark_appearance_proposal.usda']
    if (folder/'office_brick_material_proposal.usda').exists():layers.insert(0,'office_brick_material_proposal.usda')
    manifest=json.loads((root/'data/heights/landmarks/proposal_manifest.json').read_text())
    if hashlib.sha256((folder/'landmark_building_proposal.usda').read_bytes()).hexdigest()!=manifest['layer_sha256']:raise ValueError('Landmark geometry changed')
    extra=folder/'office_architectural_roof_proposal.usda'
    if extra.exists():layers.insert(layers.index('landmark_appearance_proposal.usda'),extra.name)
    for name in layers:
        if not (folder/name).exists():raise ValueError('Missing proposal '+name)
        evidence=Sdf.Layer.FindOrOpen(str(folder/name)).customLayerData
        if evidence.get('geometryProposalSha256')!=manifest['layer_sha256']:raise ValueError('Rebuild stale derived proposal '+name)
        if name=='office_frontage_proposal.usda' and extra.exists() and evidence.get('architecturalRoofSha256')!=hashlib.sha256(extra.read_bytes()).hexdigest():raise ValueError('Rebuild frontage against architectural roof')
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    stage.GetRootLayer().subLayerPaths=[str(folder/name) for name in layers]
    UsdGeom.Xform.Define(stage,'/World')
    UsdGeom.Imageable(stage.OverridePrim('/World/Landmarks/CollegeParkPostOffice')).CreateVisibilityAttr('invisible')
    ground=UsdGeom.Cube.Define(stage,'/World/ReviewGround');ground.CreateSizeAttr(1)
    ground.AddTranslateOp().Set(Gf.Vec3d(-18,-624,-.11));ground.AddScaleOp().Set(Gf.Vec3f(180,180,.2))
    mat=UsdShade.Material.Define(stage,'/World/ReviewMaterial');shader=UsdShade.Shader.Define(stage,'/World/ReviewMaterial/Surface')
    shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.34,.34,.32));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.9)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(ground.GetPrim()).Bind(mat)
    sun=UsdLux.DistantLight.Define(stage,'/World/ReviewLighting/Sun');sun.CreateIntensityAttr(1800);sun.CreateAngleAttr(1.2);sun.AddRotateXYZOp().Set(Gf.Vec3f(-35,-35,-25))
    sky=UsdLux.DomeLight.Define(stage,'/World/ReviewLighting/Sky');sky.CreateIntensityAttr(350);sky.CreateColorAttr(Gf.Vec3f(.8,.88,1))
    camera=UsdGeom.Camera.Define(stage,'/World/Cameras/OfficeFrontage')
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(-95,-684,28),Gf.Vec3d(-16,-624,5),Gf.Vec3d(0,0,1)).GetInverse())
    camera.CreateFocalLengthAttr(32);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,1000))
    stage.GetRootLayer().customLayerData={'purpose':'Isolated architectural draft, neutral context; not full-district/site/lighting acceptance','proposalHashesJson':json.dumps({name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in layers},sort_keys=True)}
    output=folder/'office_frontage_review.usda';stage.GetRootLayer().Export(str(output));return output

def build_site(site_id,output,root=ROOT):
    """Copy a guarded historical site into a fresh self-contained review package.

    Opt-in only; the existing default office build above remains unchanged.
    No active composition, architectural invention or source-layer writes.
    """
    root=Path(root).resolve();output=Path(output).resolve()
    if site_id!='college_park_post_office':raise ValueError('Only the reviewed post-office site is supported')
    if output.exists():raise ValueError('Existing output preserved; choose a new directory')
    if not output.is_relative_to(root/'data/diagnostics'):raise ValueError('Site output must be under data/diagnostics')
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    manifest_path=root/'data/heights/landmarks/proposal_manifest.json';manifest=json.loads(manifest_path.read_text())
    record=next(x for x in manifest['sites'] if x['site_id']==site_id)
    proposal=root/'scene/landmark_building_proposal.usda'
    if sha(proposal)!=manifest['layer_sha256']:raise ValueError('Landmark proposal hash changed')
    active=json.loads((root/'data/processed/active.json').read_text())
    if record['source_snapshot']!=active['snapshot']:raise ValueError('Historical proposal snapshot stale')
    from reconstruct_landmarks import verify_source,SITES
    config=next(x for x in SITES if x['id']==site_id)
    _,evidence,evidence_hash=verify_source(root,config,active)
    if evidence_hash!=record['evidence_sha256']:raise ValueError('Historical evidence changed')
    readiness_path=root/'docs/evidence/post-office-readiness.json';readiness=json.loads(readiness_path.read_text())
    for path,digest in readiness['dependencies'].items():
        # Current root is deliberately irrelevant to an isolated source-copy;
        # preserve its bytes below but do not inherit its materials or geometry.
        if path!='scene/college_park_connected.usda' and sha(root/path)!=digest:raise ValueError('Readiness dependency stale: '+path)
    protected={p:sha(p) for p in [proposal,manifest_path,root/'scene/college_park_connected.usda',root/'scene/manual_edits.usda',root/'data/processed/active.json']}
    source=Usd.Stage.Open(str(proposal));selected=source.GetPrimAtPath(record['prim_path'])
    meshes=[p for p in Usd.PrimRange(selected) if p.IsA(UsdGeom.Mesh)]
    if len(meshes)!=4:raise ValueError('Expected four reviewed post-office components')
    flattened=source.Flatten();output.mkdir(parents=True)
    site=Usd.Stage.CreateNew(str(output/'site.usda'));UsdGeom.SetStageUpAxis(site,'Z');UsdGeom.SetStageMetersPerUnit(site,1)
    # Retain ancestor transform attributes without copying unrelated siblings.
    for path in selected.GetPath().GetPrefixes()[:-1]:
        ancestor=source.GetPrimAtPath(path)
        if not ancestor:continue
        target=site.DefinePrim(path,ancestor.GetTypeName())
        for attr in ancestor.GetAttributes():
            if attr.GetName().startswith('xformOp:') or attr.GetName()=='xformOpOrder':Sdf.CopySpec(flattened,attr.GetPath(),site.GetRootLayer(),target.GetPath().AppendProperty(attr.GetName()))
    Sdf.CopySpec(flattened,selected.GetPath(),site.GetRootLayer(),selected.GetPath())
    materials=set()
    for prim in Usd.PrimRange(selected):
        material=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
        if material:materials.add(material.GetPath())
    for path in sorted(materials):
        Sdf.CreatePrimInLayer(site.GetRootLayer(),path.GetParentPath());Sdf.CopySpec(flattened,path,site.GetRootLayer(),path)
    # Contain any authored material file dependencies; do not leave source paths.
    assets={}
    for path in materials:
        for prim in Usd.PrimRange(site.GetPrimAtPath(path)):
            for attr in prim.GetAttributes():
                if attr.GetTypeName()!=Sdf.ValueTypeNames.Asset:continue
                value=attr.Get()
                if not value or not value.path:continue
                original=Path(value.resolvedPath or value.path)
                if not original.is_file():raise ValueError('Unresolved material dependency: '+value.path)
                name=sha(original)[:16]+'_'+original.name;dest=output/'textures'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(original,dest);attr.Set(Sdf.AssetPath('textures/'+name));assets[str(original)]=sha(original)
    site.SetDefaultPrim(site.GetPrimAtPath('/World'));site.GetRootLayer().customLayerData={'sourceSnapshot':active['snapshot'],'quality':'Historical2018-2019 source-derived mass; current geometry/occupancy/facade unknown','parcelLinkStatus':'Raw tax associations not promoted; parcel is search context only','sourceProposalSha256':sha(proposal)};site.GetRootLayer().Save()
    reopened=Usd.Stage.Open(str(output/'site.usda'));proof=[]
    for old in meshes:
        new=reopened.GetPrimAtPath(old.GetPath());attributes={a.GetName():str(a.Get()) for a in old.GetAttributes()}
        if any(str(new.GetAttribute(k).Get())!=v for k,v in attributes.items()):raise ValueError('Copied mesh attributes changed: '+str(old.GetPath()))
        a=UsdGeom.Xformable(old).ComputeLocalToWorldTransform(Usd.TimeCode.Default());b=UsdGeom.Xformable(new).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        if a!=b:raise ValueError('Copied world transform changed')
        proof.append({'prim':str(old.GetPath()),'all_composed_attribute_values_equal':True,'world_transform_equal':True,'attribute_digest':hashlib.sha256(json.dumps(attributes,sort_keys=True).encode()).hexdigest()})
    review=Usd.Stage.CreateNew(str(output/'review.usda'));UsdGeom.SetStageUpAxis(review,'Z');UsdGeom.SetStageMetersPerUnit(review,1);review.GetRootLayer().subLayerPaths=['site.usda']
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']).ComputeWorldBound(reopened.GetPrimAtPath(record['prim_path'])).ComputeAlignedRange();lo,hi=bbox.GetMin(),bbox.GetMax();center=(lo+hi)*.5
    ground=UsdGeom.Cube.Define(review,'/World/ReviewGround');ground.CreateSizeAttr(1);ground.AddTranslateOp().Set(Gf.Vec3d(center[0],center[1],lo[2]-.12));ground.AddScaleOp().Set(Gf.Vec3f((hi[0]-lo[0])*1.5,(hi[1]-lo[1])*1.5,.2))
    mat=UsdShade.Material.Define(review,'/World/ReviewMaterial');shader=UsdShade.Shader.Define(review,mat.GetPath().AppendChild('Surface'));shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.34,.34,.32));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.9);mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(ground.GetPrim()).Bind(mat)
    sun=UsdLux.DistantLight.Define(review,'/World/ReviewLighting/Sun');sun.CreateIntensityAttr(1800);sun.CreateAngleAttr(1.2);UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-35,-35,-25));UsdLux.DomeLight.Define(review,'/World/ReviewLighting/Sky').CreateIntensityAttr(350)
    direction=Gf.Vec3d(-1,-1,.72).GetNormalized();orientation=Gf.Matrix4d().SetLookAt(center+direction,center,Gf.Vec3d(0,0,1));corners=[Gf.Vec3d(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])];tan_h=36/(2*45);tan_v=20.25/(2*45)
    local=[orientation.Transform(q) for q in corners];distance=max(q[2]+1+max(abs(q[0])/(tan_h*.82),abs(q[1])/(tan_v*.82)) for q in local)
    camera=UsdGeom.Camera.Define(review,'/World/Cameras/PostOfficeHistoricalMass');matrix=Gf.Matrix4d().SetLookAt(center+direction*distance,center,Gf.Vec3d(0,0,1));camera.AddTransformOp().Set(matrix.GetInverse());camera.CreateFocalLengthAttr(45);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,1000));camera.CreateFStopAttr(0)
    ndc=[[matrix.Transform(q)[0]/(-matrix.Transform(q)[2]*tan_h),matrix.Transform(q)[1]/(-matrix.Transform(q)[2]*tan_v)] for q in corners]
    if max(abs(v) for q in ndc for v in q)>.83:raise ValueError('Camera corner framing failed')
    review.GetRootLayer().customLayerData={'quality':'Isolated historical mass review only; no facade/current condition or district integration acceptance','sourceSiteSha256':sha(output/'site.usda')};review.GetRootLayer().Save()
    if any(sha(p)!=h for p,h in protected.items()):raise ValueError('Protected source changed during preparation')
    report={'site_id':site_id,'source_snapshot':active['snapshot'],'source_proposal_sha256':sha(proposal),'source_manifest_sha256':sha(manifest_path),'readiness_review_sha256':sha(readiness_path),'cloud_sha256':record['cloud_sha256'],'source_evidence_sha256':evidence_hash,'acquisition':evidence['source']['acquisition'],'crs':evidence['source']['coordinate_reference'],'up_axis':'Z','meters_per_unit':1,'components':proof,'bound_material_subtrees_copied':len(materials),'copied_material_files':assets,'bbox_m':[list(lo),list(hi)],'camera':'/World/Cameras/PostOfficeHistoricalMass','camera_corner_ndc':ndc,'protected_files_unchanged':{str(p.relative_to(root)):h for p,h in protected.items()},'outputs':{p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()},'raw_tax_links_promoted':False,'current_geometry_accepted':False,'facade_invented':False,'render_status':'not_run','activated':False}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return output/'review.usda'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--site',choices=['college_park_post_office']);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.site and not args.output:parser.error('--site requires a fresh --output directory')
    if args.output and not args.site:parser.error('--output requires --site')
    print(build_site(args.site,args.output) if args.site else build())
