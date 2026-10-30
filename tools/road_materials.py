"""Acquire licensed road texture quality tiers and author a reversible PBR layer."""
from pathlib import Path
import sys,json,hashlib,urllib.request,urllib.parse,argparse,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdShade,Sdf,Gf
from data_pipeline import atomic_json
ASSET='asphalt_02'
TIERS={'preview':'1k','balanced':'2k','presentation':'4k'}
CHANNELS={'Diffuse':'jpg','nor_gl':'png','Rough':'jpg'}

def download(url,path,expected=None):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ['api.polyhaven.com','dl.polyhaven.org']:raise ValueError('Unapproved material URL')
    if path.exists():raw=path.read_bytes()
    else:
        request=urllib.request.Request(url,headers={'User-Agent':'CollegeParkTWIN/0.4 (Powered by Poly Haven)'})
        with urllib.request.urlopen(request,timeout=90) as response:
            if urllib.parse.urlparse(response.geturl()).hostname not in ['api.polyhaven.com','dl.polyhaven.org']:raise ValueError('Unapproved redirect')
            raw=response.read(50*1024*1024+1)
        if len(raw)>50*1024*1024:raise ValueError('Material exceeds bounded download size')
    if expected and (len(raw)!=expected['size'] or hashlib.md5(raw).hexdigest()!=expected['md5']):raise ValueError('Material bytes do not match publisher file metadata')
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(raw);temporary.replace(path)
    return {'url':url,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'publisher_md5':expected.get('md5') if expected else None}

def build(quality='balanced'):
    folder=ROOT/'assets/generated/road_materials';folder.mkdir(parents=True,exist_ok=True)
    files_path=folder/'publisher_files.json';info_path=folder/'publisher_info.json'
    download('https://api.polyhaven.com/files/'+ASSET,files_path)
    download('https://api.polyhaven.com/info/'+ASSET,info_path)
    files=json.loads(files_path.read_text());info=json.loads(info_path.read_text());records=[]
    for tier,resolution in TIERS.items():
        for channel,extension in CHANNELS.items():
            expected=files[channel][resolution][extension];name=f'{ASSET}_{channel}_{resolution}.{extension}'
            receipt=download(expected['url'],folder/resolution/name,expected)
            records.append({'tier':tier,'resolution':resolution,'channel':channel,'file':str((folder/resolution/name).relative_to(ROOT)).replace('\\','/'),**receipt})
    selected=[r for r in records if r['tier']==quality]
    stage=Usd.Stage.CreateInMemory();shader=UsdShade.Shader.Define(stage,'/World/DetailMaterials/Asphalt/Surface')
    uv=UsdShade.Shader.Define(stage,'/World/DetailMaterials/Asphalt/UV');uv.CreateIdAttr('UsdPrimvarReader_float2');uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
    scale=UsdShade.Shader.Define(stage,'/World/DetailMaterials/Asphalt/PhysicalScale');scale.CreateIdAttr('UsdTransform2d');scale.CreateInput('in',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result')
    # Existing road UVs repeat every 4 m. Publisher records a 3 x 3 m tile.
    tile_m=float(info['dimensions'][0])/1000
    scale.CreateInput('scale',Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(4/tile_m))
    for row in selected:
        channel=row['channel'];texture=UsdShade.Shader.Define(stage,'/World/DetailMaterials/Asphalt/PBR_'+channel);texture.CreateIdAttr('UsdUVTexture')
        texture.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('../'+row['file']))
        texture.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB' if channel=='Diffuse' else 'raw')
        texture.CreateInput('wrapS',Sdf.ValueTypeNames.Token).Set('repeat');texture.CreateInput('wrapT',Sdf.ValueTypeNames.Token).Set('repeat');texture.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(scale.ConnectableAPI(),'result')
        if channel=='Diffuse':shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).ConnectToSource(texture.ConnectableAPI(),'rgb')
        elif channel=='Rough':shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).ConnectToSource(texture.ConnectableAPI(),'r')
        else:
            texture.CreateInput('scale',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2,2,2,1));texture.CreateInput('bias',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1,-1,-1,0));shader.CreateInput('normal',Sdf.ValueTypeNames.Normal3f).ConnectToSource(texture.ConnectableAPI(),'rgb')
    stage.GetRootLayer().customLayerData={'qualityTier':quality,'source':'Powered by Poly Haven — Asphalt 02 by Rob Tuytel','license':'CC0','purpose':'Representative asphalt appearance; not a measured Orlando pavement condition map','tileMeters':tile_m,'geometry_changed':False}
    stage.GetRootLayer().Export(str(ROOT/'scene/road_materials.usda'))
    report={'asset':ASSET,'publisher':'Poly Haven','credit':'Powered by Poly Haven','license':'CC0','license_url':'https://polyhaven.com/license','asset_url':'https://polyhaven.com/a/'+ASSET,'acquired_or_verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selected_quality':quality,'tile_m':tile_m,'tiers':{'preview':'1K for iteration and distant views','balanced':'2K for working scene and normal playback','presentation':'4K for close rendered inspection; performance must be measured'},'maps':records,'geometry_changed':False,'limits':['Representative material is not a local road-condition survey.','Normal detail changes shading, not road-edge geometry or pedestrian accessibility.','Higher texture resolution alone does not establish realism or performance.']}
    atomic_json(ROOT/'data/processed/road_materials.json',report);print(json.dumps({'quality':quality,'files':len(records),'bytes':sum(r['bytes'] for r in records),'tile_m':tile_m},indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--quality',choices=TIERS,default='balanced');build(parser.parse_args().quality)
