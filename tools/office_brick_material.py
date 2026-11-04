"""Original physical-scale masonry and glazing work layer; no reference pixels."""
from pathlib import Path
import hashlib,json,os,sys
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from pxr import Gf,Sdf,Usd,UsdGeom,UsdShade

def textures(folder,resolution=2048):
    folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(1615)
    size_m=(2.4384,.8001) # twelve nominal 8-inch bricks / twelve nominal courses
    y,x=np.mgrid[:resolution,:resolution];u=(x+.5)/resolution*12;v=(y+.5)/resolution*12
    row=np.floor(v).astype(int);shifted=u+(row%2)*.5;column=np.floor(shifted).astype(int)%12
    edge_u=np.minimum(shifted%1,1-shifted%1)*.2032
    edge_v=np.minimum(v%1,1-v%1)*.066675
    edge=np.minimum(edge_u,edge_v)
    mask=np.clip((edge-.0038)/.003,0,1).astype(np.float32)
    brick_variation=rng.normal(0,1,(12,12,1)).astype(np.float32)[row,column]
    noise=gaussian_filter(rng.normal(0,1,(resolution,resolution)).astype(np.float32),.7,mode='wrap')
    coarse=gaussian_filter(noise,12,mode='wrap')
    brick=np.array([159,67,46],dtype=np.float32)+brick_variation*np.array([13,7,5])+noise[...,None]*6+coarse[...,None]*90
    mortar=np.array([169,156,135],dtype=np.float32)+noise[...,None]*3
    color=np.clip(brick*mask[...,None]+mortar*(1-mask[...,None]),0,255).astype(np.uint8)
    height=mask*.0025+noise*.00018*mask
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*size_m[0]/resolution)
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*size_m[1]/resolution)
    normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    normal=np.clip((normal*.5+.5)*255,0,255).astype(np.uint8)
    rough=np.clip(211+(1-mask)*18+noise*5,0,255).astype(np.uint8)
    for name,pixels in [('color',color),('normal',normal),('roughness',rough)]:Image.fromarray(pixels).save(folder/(name+'.png'))
    return size_m

def build(root=ROOT):
    folder=root/'assets/generated/office_brick';size=textures(folder)
    source=root/'scene/office_frontage_proposal.usda';geometry=root/'scene/landmark_building_proposal.usda'
    original=Usd.Stage.Open(str(source));source_hash=hashlib.sha256(geometry.read_bytes()).hexdigest()
    if original.GetRootLayer().customLayerData['geometryProposalSha256']!=source_hash:raise ValueError('Stale frontage geometry')
    stage=Usd.Stage.CreateInMemory();base='/World/OfficeFrontageProposal';mat=UsdShade.Material.Define(stage,base+'/Materials/Brick')
    surface=UsdShade.Shader.Define(stage,mat.GetPath().AppendChild('Surface'));surface.CreateIdAttr('UsdPreviewSurface')
    reader=UsdShade.Shader.Define(stage,mat.GetPath().AppendChild('UV'));reader.CreateIdAttr('UsdPrimvarReader_float2');reader.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st');reader.CreateOutput('result',Sdf.ValueTypeNames.Float2)
    for name,target in [('color','diffuseColor'),('normal','normal'),('roughness','roughness')]:
        texture=UsdShade.Shader.Define(stage,mat.GetPath().AppendChild(name));texture.CreateIdAttr('UsdUVTexture')
        texture.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('../assets/generated/office_brick/'+name+'.png'))
        texture.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB' if name=='color' else 'raw')
        texture.CreateInput('wrapS',Sdf.ValueTypeNames.Token).Set('repeat');texture.CreateInput('wrapT',Sdf.ValueTypeNames.Token).Set('repeat')
        texture.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(),'result')
        if name=='normal':
            texture.CreateInput('scale',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2,2,2,1));texture.CreateInput('bias',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1,-1,-1,0))
        output='r' if name=='roughness' else 'rgb';texture.CreateOutput(output,Sdf.ValueTypeNames.Float if output=='r' else Sdf.ValueTypeNames.Float3)
        surface.CreateInput(target,Sdf.ValueTypeNames.Float if output=='r' else Sdf.ValueTypeNames.Normal3f if name=='normal' else Sdf.ValueTypeNames.Color3f).ConnectToSource(texture.ConnectableAPI(),output)
    mat.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(),'surface')
    skin=UsdGeom.Mesh(original.GetPrimAtPath(base+'/BrickFrontSkin'));points=skin.GetPointsAttr().Get();indices=skin.GetFaceVertexIndicesAttr().Get()
    override=UsdGeom.Mesh(stage.OverridePrim(skin.GetPath()))
    UsdGeom.PrimvarsAPI(override).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set([(points[i][1]/size[0],points[i][2]/size[1]) for i in indices])
    glass=UsdShade.Shader.Define(stage,base+'/Materials/Glazing/Surface');glass.CreateIdAttr('UsdPreviewSurface');glass.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.13);glass.CreateInput('clearcoat',Sdf.ValueTypeNames.Float).Set(.8);glass.CreateInput('clearcoatRoughness',Sdf.ValueTypeNames.Float).Set(.08)
    stage.GetRootLayer().customLayerData={'purpose':'Original masonry microdetail and reflective glazing; interpreted nominal brick scale, no source imagery','geometryProposalSha256':source_hash,'sourceSnapshot':original.GetRootLayer().customLayerData['sourceSnapshot'],'frontageSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tileWidthMeters':size[0],'tileHeightMeters':size[1],'license':'CC0-1.0 original procedural textures','textureHashesJson':json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.png')},sort_keys=True)}
    destination=root/'scene/office_brick_material_proposal.usda';stage.GetRootLayer().Export(str(destination));print(destination)
    return destination

if __name__=='__main__':build()
