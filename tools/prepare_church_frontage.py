"""Prepare a separate, photo-interpreted church entrance appearance proposal.

Inputs: frozen v3 roof manifest, dated OCPA exterior, original TWIN brick material.
Run: python tools/prepare_church_frontage.py --output data/diagnostics/<new-folder>
Outputs: appearance/review USD and provenance; no active/source/network writes.
Dimensions and window/door placement are estimates; no current/as-built claim.
"""
from pathlib import Path
import argparse,hashlib,json,math,os,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Usd,UsdGeom,UsdShade,UsdLux,Sdf,Gf
from build_detailed_assets import mesh,box

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def relative(path,folder):return os.path.relpath(path,folder).replace('\\','/')

def build(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'data/diagnostics'):
        raise ValueError('Use a new output directory under data/diagnostics')
    folder=root/'data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v3'
    manifest=folder/'manifest.json';data=json.loads(manifest.read_text(encoding='utf-8'))
    source=folder/'site.usda';review=folder/'review.usda'
    for name,digest in data['outputs'].items():
        if sha(folder/name)!=digest:raise ValueError('Frozen church candidate changed')
    for name,digest in data['dependencies'].items():
        dependency=(root/name).resolve()
        if not dependency.is_relative_to(root) or sha(dependency)!=digest:raise ValueError('Church source dependency changed')
    v2=root/'data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v2/manifest.json'
    if v2.relative_to(root).as_posix() not in data['dependencies']:raise ValueError('Original snapshot lineage missing')
    data['source_snapshot']=json.loads(v2.read_text(encoding='utf-8'))['source_snapshot']
    active=root/'data/processed/active.json'
    if data['source_snapshot']!=json.loads(active.read_text())['snapshot']:raise ValueError('Church snapshot changed')
    photo=root/'data/diagnostics/next_landmark_20261030/full_campus_references/drive_second_parcel_ocpa_front.jpg'
    if sha(photo)!='b67887612b6b58875f3a50a785168ca4a1ef45d230c04786c38470b7c3f08c70':raise ValueError('Dated exterior reference changed')
    material=root/'scene/office_brick_material_proposal.usda'
    source_material=Sdf.Layer.FindOrOpen(str(material));material_data=source_material.customLayerData
    textures=json.loads(material_data['textureHashesJson'])
    dependencies=[manifest,source,review,photo,material,active,root/'tools/build_detailed_assets.py',Path(__file__)]
    dependencies.extend(root/name for name in data['dependencies'])
    for name,digest in textures.items():
        path=root/'assets/generated/office_brick'/name
        if sha(path)!=digest:raise ValueError('Original masonry texture changed')
        dependencies.append(path)
    protected={p:sha(p) for p in dependencies+[root/'scene/college_park_connected.usda',root/'scene/manual_edits.usda']}
    a=data['frontage_alignment'];x=a['front_x_local_m'];lo=a['y_min_local_m'];hi=a['y_max_local_m'];ground=a['ground_local_m']
    ridge_y=a['front_roof_ridge_y_local_m'];ridge_z=a['front_roof_ridge_z_local_m']
    low_z=a['front_roof_eave_min_z_local_m'];high_z=a['front_roof_eave_max_z_local_m']
    if not all(math.isfinite(v) for v in [x,lo,hi,ground,ridge_y,ridge_z,low_z,high_z]) or not lo<ridge_y<hi or min(low_z,high_z)<=ground:
        raise ValueError('Invalid source-interpreted frontage frame')
    def top(y):
        return low_z+(ridge_z-low_z)*(y-lo)/(ridge_y-lo) if y<=ridge_y else ridge_z+(high_z-ridge_z)*(y-ridge_y)/(hi-ridge_y)
    output.mkdir(parents=True);stage=Usd.Stage.CreateNew(str(output/'appearance.usda'));UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    base='/World/ChurchFrontageAppearance';prim=stage.DefinePrim(base,'Xform')
    metadata={'quality':'illustrative_photo_interpreted_historical_appearance','appearanceId':'appearance:1914-edgewater:entrance:v1',
        'sourceSnapshot':data['source_snapshot'],'sourceURL':'https://ocpaimages.ocpafl.org/api/Image/GetPIDImage?pid=292214146005190',
        'photoCaption':'11/8/2021 12:04 PM','photoDate':'2021-11-08','photoTimeZone':'unknown',
        'method':'Qualitative photo proportions aligned to interpreted roof; not photogrammetry or measured facade',
        'measuredDimensions':False,'currentConditionsVerified':False,'physicalIdentityPromoted':False,'steepleIncluded':False}
    for k,v in metadata.items():prim.SetCustomDataByKey(k,v)
    brick=UsdShade.Material.Define(stage,base+'/Materials/Brick')
    brick.GetPrim().GetReferences().AddReference(relative(material,output),'/World/OfficeFrontageProposal/Materials/Brick')
    def mat(name,color,rough):
        m=UsdShade.Material.Define(stage,base+'/Materials/'+name);s=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'))
        s.CreateIdAttr('UsdPreviewSurface');s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough)
        m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface');return m
    trim=mat('CreamPaint',(.77,.77,.70),.61);glass=mat('DarkGlazing',(.022,.037,.045),.16);metal=mat('WindowFrames',(.035,.04,.038),.43)
    def face(name,yz,material,depth=.025):
        points=[(x+depth,y,z) for y,z in yz];uv=[((y-lo)/material_data['tileWidthMeters'],z/material_data['tileHeightMeters']) for y,z in yz]
        return mesh(stage,base+'/'+name,points,[list(range(len(points)))],material,uv=uv,smooth=False)
    face('MasonrySkin',[(lo,ground),(hi,ground),(hi,high_z),(ridge_y,ridge_z),(lo,low_z)],brick,.012)
    # Four tall pale frames and three dark vertical glazing strips are visible
    # in the dated exterior. Widths, depths and subdivisions remain estimated.
    columns=[lo+.17+(hi-lo-.34)*i/3 for i in range(4)]
    for i,y in enumerate(columns):
        height=top(y)-ground-.07
        box(stage,base+'/Pier'+str(i),(x+.15,y,ground+height/2),(.30,.32,height),trim)
    beam_z=ground+3.0
    box(stage,base+'/EntranceBeam',(x+.15,(lo+hi)/2,beam_z),(.30,hi-lo,.22),trim)
    for i,(left,right) in enumerate(zip(columns,columns[1:])):
        sy=left+.38;ey=sy+.43;bottom=beam_z+.14
        face('TallGlazing'+str(i),[(sy,bottom),(ey,bottom),(ey,top(ey)-.17),(sy,top(sy)-.17)],glass,.038)
        for j in range(1,7):
            z=bottom+j*(top(sy)-.17-bottom)/7
            box(stage,base+f'/GlazingBar{i}_{j}',(x+.045,(sy+ey)/2,z),(.025,ey-sy,.025),metal)
        cy=(left+right)/2;width=min(2.4,right-left-.8);z0=ground+.18;z1=beam_z-.14
        face('LowerEntryGlazing'+str(i),[(cy-width/2,z0),(cy+width/2,z0),(cy+width/2,z1),(cy-width/2,z1)],glass,.045)
        box(stage,base+'/EntryDivider'+str(i),(x+.065,cy,(z0+z1)/2),(.045,.045,z1-z0),metal)
    for i,(ay,by) in enumerate([(lo,ridge_y),(ridge_y,hi)]):
        face('GableTrim'+str(i),[(ay,top(ay)-.18),(by,top(by)-.18),(by,top(by)+.025),(ay,top(ay)+.025)],trim,.20)
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'));stage.GetRootLayer().Save()
    work=Usd.Stage.CreateNew(str(output/'review.usda'));UsdGeom.SetStageUpAxis(work,'Z');UsdGeom.SetStageMetersPerUnit(work,1)
    work.GetRootLayer().subLayerPaths=['appearance.usda',relative(review,output)]
    camera=UsdGeom.Camera.Define(work,'/World/Cameras/ChurchEntranceAppearance');target=Gf.Vec3d(x,(lo+hi)/2,(ground+ridge_z)/2)
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(target+Gf.Vec3d(29,-20,9),target,Gf.Vec3d(0,0,1)).GetInverse())
    camera.CreateFocalLengthAttr(45);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25);camera.CreateFStopAttr(0);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,1000));work.GetRootLayer().Save()
    reopened=Usd.Stage.Open(str(output/'review.usda'))
    if reopened.GetCompositionErrors():raise ValueError('Appearance composition errors')
    for p in reopened.Traverse():
        for attr in p.GetAttributes():
            if attr.GetTypeName()==Sdf.ValueTypeNames.Asset:
                value=attr.Get()
                if value and value.path and not value.resolvedPath:raise ValueError('Unresolved appearance resource')
    if any(sha(p)!=h for p,h in protected.items()):raise ValueError('Protected source changed')
    report={'schema':'twin.church-frontage-proposal/1','source_snapshot':data['source_snapshot'],'quality':metadata,
        'source_candidate_sha256':sha(source),'frontage_alignment':a,'estimated_appearance_dimensions':True,
        'source_preserved':True,'activated':False,'steeple_modeled':False,'render_status':'not_run',
        'camera':'/World/Cameras/ChurchEntranceAppearance','dependencies':{p.relative_to(root).as_posix():h for p,h in protected.items()},
        'outputs':{n:sha(output/n) for n in ['appearance.usda','review.usda']}}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(build(args.output),indent=2))
