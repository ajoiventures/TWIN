"""Original procedural, editable 3D assets. No third-party models or photographs.

Produces leaf/branch vegetation and a curved-body sedan, replacing prototype blobs/boxes.
Placements remain illustrative until pedestrian and parking evidence is accepted.
"""
from pathlib import Path
import sys,math,random,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
from PIL import Image,ImageDraw
OUT=ROOT/'assets/generated';OUT.mkdir(exist_ok=True,parents=True);(OUT/'textures').mkdir(exist_ok=True)

def material(stage,name,color,rough=.7,metal=0,leaf=False,emit=None):
 m=UsdShade.Material.Define(stage,'/Asset/Materials/'+name);s=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'));s.CreateIdAttr('UsdPreviewSurface');s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough);s.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(metal)
 if emit:s.CreateInput('emissiveColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emit))
 if leaf:
  tex=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Texture'));tex.CreateIdAttr('UsdUVTexture');tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('textures/leaf_cluster.png'));tex.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB')
  uv=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('UV'));uv.CreateIdAttr('UsdPrimvarReader_float2');uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st');tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result');s.GetInput('diffuseColor').ConnectToSource(tex.ConnectableAPI(),'rgb');s.CreateInput('opacity',Sdf.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(),'a');s.CreateInput('opacityThreshold',Sdf.ValueTypeNames.Float).Set(.45)
 m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface');return m
def mesh(stage,path,pts,faces,mat,uv=None,smooth=True):
 path=path.replace('-','n')
 m=UsdGeom.Mesh.Define(stage,path);m.CreatePointsAttr(pts);m.CreateFaceVertexCountsAttr([len(f) for f in faces]);m.CreateFaceVertexIndicesAttr([v for f in faces for v in f]);m.CreateSubdivisionSchemeAttr('none');m.CreateDoubleSidedAttr(True);UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
 if uv:UsdGeom.PrimvarsAPI(m).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set(uv)
 if smooth:
  normals=[Gf.Vec3f(0) for _ in pts]
  for f in faces:
   n=Gf.Cross(Gf.Vec3f(*pts[f[1]])-Gf.Vec3f(*pts[f[0]]),Gf.Vec3f(*pts[f[2]])-Gf.Vec3f(*pts[f[0]]))
   for j in f:normals[j]+=n
  for n in normals:
   if n.GetLength():n.Normalize()
  m.CreateNormalsAttr(normals);m.SetNormalsInterpolation('vertex')
 return m
def box(stage,path,c,sz,mat):
 pts=[(c[0]+x*sz[0]/2,c[1]+y*sz[1]/2,c[2]+z*sz[2]/2) for z in [-1,1] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 return mesh(stage,path,pts,[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],mat,smooth=False)
def tube(stage,path,points,radii,mat,sides=9):
 pts=[];faces=[]
 for i,p in enumerate(points):
  a=Gf.Vec3d(*points[max(0,i-1)]);b=Gf.Vec3d(*points[min(len(points)-1,i+1)]);axis=(b-a).GetNormalized();ref=Gf.Vec3d(0,0,1) if abs(axis[2])<.9 else Gf.Vec3d(1,0,0);u=Gf.Cross(axis,ref).GetNormalized();v=Gf.Cross(axis,u)
  for j in range(sides):
   q=Gf.Vec3d(*p)+radii[i]*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides));pts.append(tuple(q))
  if i:
   for j in range(sides):faces.append([(i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j])
 return mesh(stage,path,pts,faces,mat)
def leaf_texture():
 rng=random.Random(81);im=Image.new('RGBA',(256,256),(0,0,0,0));d=ImageDraw.Draw(im)
 for j in range(12):
  cx=rng.randint(35,220);cy=rng.randint(30,225);angle=rng.uniform(0,math.tau);length=rng.uniform(25,43);width=length*.38;points=[]
  for k in range(24):
   t=k*math.tau/24;x=math.cos(t)*length;y=math.sin(t)*width*(.88+.12*math.cos(3*t));points.append((cx+x*math.cos(angle)-y*math.sin(angle),cy+x*math.sin(angle)+y*math.cos(angle)))
  g=rng.randint(75,128);d.polygon(points,fill=(int(g*.48),g,int(g*.28),255));a=(cx-length*math.cos(angle),cy-length*math.sin(angle));b=(cx+length*math.cos(angle),cy+length*math.sin(angle));d.line([a,b],fill=(88,126,43,255),width=2)
 im.save(OUT/'textures/leaf_cluster.png')
leaf_texture()
def tree(kind,seed):
 file=OUT/(kind+'.usdc');stage=Usd.Stage.CreateNew(str(file));root=UsdGeom.Xform.Define(stage,'/Asset');stage.SetDefaultPrim(root.GetPrim());UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
 bark=material(stage,'Bark',(.15,.105,.065),.95);leaves=material(stage,'Leaves',(.08,.20,.05),.95,leaf=True)
 root.GetPrim().SetCustomData({'creator':'TWIN original procedural asset','species_quality':'oak-like broadleaf' if kind!='palm' else 'palm-like illustrative','units':'meters'})
 variants=root.GetPrim().GetVariantSets().AddVariantSet('detail')
 for lod,density in [('high',2400),('medium',1100),('low',250)]:
  variants.AddVariant(lod);variants.SetVariantSelection(lod)
  with variants.GetVariantEditContext():
   rng=random.Random(seed);tube(stage,'/Asset/Geometry/Trunk',[(0,0,0),(.12,0,1.5),(.20,.08,3.1),(.08,.15,4.8),(.25,.1,6.1)],[.36,.30,.25,.17,.1],bark,12)
   pts=[];faces=[];uv=[]
   if kind=='palm':
    tube(stage,'/Asset/Geometry/UpperTrunk',[(.25,.1,6),(.33,.12,8.2)],[.15,.10],bark)
    for j in range(22):
     angle=j*math.tau/22;line=[]
     for k in range(11):
      t=k/10;line.append((.33+math.cos(angle)*4*t,.12+math.sin(angle)*4*t,8.3+1.1*math.sin(t*math.pi)-2*t*t))
     tube(stage,'/Asset/Geometry/FrondStem_'+str(j),line,[.035*(1-k/12) for k in range(11)],bark,5)
     for k in range(1,10):
      c=line[k]
      for side in [-1,1]:
       v=Gf.Vec3d(-math.sin(angle),math.cos(angle),-.3)*side*(.9*(1-k/13));u=Gf.Vec3d(math.cos(angle),math.sin(angle),0)*.065;a=Gf.Vec3d(*c);b=a+v;idx=len(pts);pts.extend([tuple(a-u),tuple(a+u),tuple(b+u*.1),tuple(b-u*.1)]);faces.append([idx,idx+1,idx+2,idx+3]);uv.extend([(0,0),(1,0),(1,1),(0,1)])
   else:
    for j in range(24):
     angle=j*2.39996;radius=rng.uniform(2.3,5);end=(math.cos(angle)*radius,math.sin(angle)*radius,rng.uniform(5.3,8.8));mid=(end[0]*.5,end[1]*.5,4.4+end[2]*.2);tube(stage,'/Asset/Geometry/Branch_'+str(j),[(.12,.1,3.2),mid,end],[.10,.055,.014],bark,7)
    for j in range(density):
     angle=rng.uniform(0,math.tau);radius=math.sqrt(rng.random());x=math.cos(angle)*radius*5.8;y=math.sin(angle)*radius*5.0;z=6.2+math.sqrt(max(0,1-radius*radius))*2.8+rng.uniform(-1.0,.8);size=rng.uniform(.27,.55);az=rng.uniform(0,math.tau);tilt=rng.uniform(-.8,.8);u=Gf.Vec3d(math.cos(az),math.sin(az),0)*size;v=Gf.Vec3d(-math.sin(az)*tilt,math.cos(az)*tilt,1)*size*.75;c=Gf.Vec3d(x,y,z);idx=len(pts);pts.extend([tuple(c-u-v),tuple(c+u-v),tuple(c+u+v),tuple(c-u+v)]);faces.append([idx,idx+1,idx+2,idx+3]);uv.extend([(0,0),(1,0),(1,1),(0,1)])
   mesh(stage,'/Asset/Geometry/Foliage',pts,faces,leaves,uv,smooth=False)
 variants.SetVariantSelection('medium');stage.GetRootLayer().Save();return file

def car():
 stage=Usd.Stage.CreateNew(str(OUT/'sedan.usdc'));root=UsdGeom.Xform.Define(stage,'/Asset');stage.SetDefaultPrim(root.GetPrim());UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
 paint=material(stage,'Paint',(.16,.24,.30),.24,.7);glass=material(stage,'Glass',(.055,.11,.14),.12,.6);rubber=material(stage,'Rubber',(.018,.019,.021),.9);chrome=material(stage,'Alloy',(.55,.59,.61),.22,.9);lamp=material(stage,'Headlight',(.8,.87,.9),.2,emit=(.3,.35,.4));red=material(stage,'Taillight',(.35,.015,.008),.25,emit=(.10,.001,.001))
 def loft(path,sections,mat,segments=20):
  pts=[];fs=[]
  for i,(x,w,zmid,h) in enumerate(sections):
   for j in range(segments):
    a=j*math.tau/segments;pts.append((x,w*math.sin(a),zmid+h*math.cos(a)))
   if i:
    for j in range(segments):fs.append([(i-1)*segments+j,i*segments+j,i*segments+(j+1)%segments,(i-1)*segments+(j+1)%segments])
  fs.extend([list(range(segments-1,-1,-1)),list(range((len(sections)-1)*segments,len(sections)*segments))]);mesh(stage,path,pts,fs,mat)
 loft('/Asset/Body',[(-2.25,.58,.66,.20),(-2.08,.85,.68,.30),(-1.6,.94,.68,.33),(-.7,.96,.69,.34),(.6,.96,.69,.34),(1.5,.91,.66,.29),(2.12,.76,.62,.24),(2.25,.54,.60,.17)],paint)
 loft('/Asset/Cabin',[(-1.28,.77,1.0,.06),(-.85,.72,1.16,.29),(.25,.70,1.18,.31),(1.22,.77,1.01,.05)],glass)
 loft('/Asset/Roof',[(-.87,.61,1.42,.03),(-.5,.66,1.48,.025),(.23,.61,1.46,.025)],paint)
 for side in [-1,1]:
  for x in [-.75,.45]:box(stage,f'/Asset/Handle_{side}_{str(x).replace(".","_").replace("-","n")}',(x,side*.965,.94),(.22,.035,.045),chrome)
  tube(stage,f'/Asset/WindowPillar_{side}',[(.04,side*.81,.96),(.04,side*.66,1.45)],[.035,.035],paint,6)
  box(stage,f'/Asset/Mirror_{side}',(.80,side*1.02,1.10),(.28,.22,.14),paint)
  box(stage,f'/Asset/Headlight_{side}',(2.11,side*.51,.77),(.16,.40,.15),lamp);box(stage,f'/Asset/Taillight_{side}',(-2.12,side*.53,.80),(.14,.36,.16),red)
  for x in [-1.4,1.4]:
   pts=[];fs=[]
   for i in range(32):
    theta=i*math.tau/32
    for j in range(10):
     phi=j*math.tau/10;r=.27+.075*math.cos(phi);pts.append((x+r*math.cos(theta),side*.93+.105*math.sin(phi),.35+r*math.sin(theta)))
   for i in range(32):
    for j in range(10):fs.append([i*10+j,((i+1)%32)*10+j,((i+1)%32)*10+(j+1)%10,i*10+(j+1)%10])
   name=f'/Asset/Wheel_{side}_{str(x).replace(".","_").replace("-","n")}';mesh(stage,name,pts,fs,rubber)
   for j in range(5):
    a=j*math.tau/5;tube(stage,name+'_Spoke_'+str(j),[(x,side*1.035,.35),(x+math.cos(a)*.22,side*1.035,.35+math.sin(a)*.22)],[.045,.028],chrome,6)
 box(stage,'/Asset/Grille',(2.21,0,.60),(.06,.65,.14),rubber);root.GetPrim().SetCustomData({'creator':'TWIN original procedural sedan','length_m':4.5,'width_m':2.26,'placement':'static illustrative vehicle; not traffic data'})
 stage.GetRootLayer().Save()

for kind,seed in [('oak_a',110),('oak_b',230),('palm',310)]:tree(kind,seed)
car()
source=Usd.Stage.Open(str(ROOT/'scene/edgewater_details.usdc'));layer=Usd.Stage.CreateNew(str(ROOT/'scene/asset_upgrade.usda'))
inst=UsdGeom.PointInstancer.Define(layer,'/World/Trees');layer.OverridePrim('/World/Trees/Prototypes').SetActive(False);targets=[]
for i,name in enumerate(['oak_a','oak_b','oak_a','oak_b','oak_a','oak_b','palm']):
 path='/World/Trees/Detailed/Tree_'+str(i);p=UsdGeom.Xform.Define(layer,path).GetPrim();p.GetReferences().AddReference('../assets/generated/'+name+'.usdc','/Asset');p.GetVariantSet('detail').SetVariantSelection('medium');targets.append(Sdf.Path(path))
inst.CreatePrototypesRel().SetTargets(targets)
car_count=0
for prim in source.GetPrimAtPath('/World/ParkedVehicles').GetChildren():
 body=UsdGeom.Mesh(prim.GetChild('Body'));pts=body.GetPointsAttr().Get();c=Gf.Vec3d(0)
 for p in pts:c+=Gf.Vec3d(p)
 c/=len(pts);direction=Gf.Vec3d(pts[1])-Gf.Vec3d(pts[0]);angle=math.degrees(math.atan2(direction[1],direction[0]))
 for child in prim.GetChildren():layer.OverridePrim(child.GetPath()).SetActive(False)
 p=UsdGeom.Xform.Define(layer,prim.GetPath().AppendChild('DetailedSedan'));p.GetPrim().GetReferences().AddReference('../assets/generated/sedan.usdc','/Asset');p.AddTranslateOp().Set(Gf.Vec3d(c[0],c[1],.08));p.AddRotateZOp().Set(angle);p.GetPrim().SetInstanceable(True);car_count+=1
layer.GetRootLayer().customLayerData={'quality':'Detailed original procedural assets; existing placements are illustrative, pending verified sidewalk/parking review'};layer.GetRootLayer().Save()
report={'original_assets':True,'external_asset_licenses_required':False,'tree_assets':['oak_a','oak_b','palm'],'tree_detail_levels':['high','medium','low'],'default_detail':'medium','replaced_static_cars':car_count,'not_verified':['species inventory','tree wells','parking legality','measured sidewalk clearances'],'units':'meters','source_generator':'tools/build_detailed_assets.py'}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
