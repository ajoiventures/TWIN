"""Original procedural, editable 3D assets. No third-party models or photographs.

Produces leaf/branch vegetation and a curved-body sedan, replacing prototype blobs/boxes.
Placements remain illustrative until pedestrian and parking evidence is accepted.
"""
from pathlib import Path
import sys,math,random,json,os,argparse,hashlib
for _thread_key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_thread_key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf,UsdLux
from PIL import Image,ImageDraw
OUT=ROOT/'assets/generated/environment_v2'

def material(stage,name,color,rough=.7,metal=0,leaf=False,emit=None):
 m=UsdShade.Material.Define(stage,'/Asset/Materials/'+name);s=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'));s.CreateIdAttr('UsdPreviewSurface');s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough);s.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(metal)
 if emit:s.CreateInput('emissiveColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emit))
 if leaf:
  tex=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Texture'));tex.CreateIdAttr('UsdUVTexture');tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('textures/leaf_cluster.png'));tex.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB')
  uv=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('UV'));uv.CreateIdAttr('UsdPrimvarReader_float2');uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st');tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result');s.GetInput('diffuseColor').ConnectToSource(tex.ConnectableAPI(),'rgb');s.CreateInput('opacity',Sdf.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(),'a');s.CreateInput('opacityThreshold',Sdf.ValueTypeNames.Float).Set(.45)
 if name=='Paint':s.CreateInput('clearcoat',Sdf.ValueTypeNames.Float).Set(.8);s.CreateInput('clearcoatRoughness',Sdf.ValueTypeNames.Float).Set(.12)
 if name=='Glass':s.CreateInput('ior',Sdf.ValueTypeNames.Float).Set(1.52);s.CreateInput('useSpecularWorkflow',Sdf.ValueTypeNames.Int).Set(0)
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
 for j in range(28):
  cx=rng.randint(25,230);cy=rng.randint(25,230);angle=rng.uniform(0,math.tau);length=rng.uniform(13,23);width=length*.38;points=[]
  for k in range(24):
   t=k*math.tau/24;x=math.cos(t)*length;y=math.sin(t)*width*(.88+.12*math.cos(3*t));points.append((cx+x*math.cos(angle)-y*math.sin(angle),cy+x*math.sin(angle)+y*math.cos(angle)))
  g=rng.randint(75,128);d.polygon(points,fill=(int(g*.48),g,int(g*.28),255));a=(cx-length*math.cos(angle),cy-length*math.sin(angle));b=(cx+length*math.cos(angle),cy+length*math.sin(angle));d.line([a,b],fill=(88,126,43,255),width=2)
 im.save(OUT/'textures/leaf_cluster.png')
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
 paint=material(stage,'Paint',(.12,.20,.27),.28,.12);glass=material(stage,'Glass',(.025,.045,.055),.09,0);rubber=material(stage,'Rubber',(.018,.019,.021),.91);chrome=material(stage,'Alloy',(.55,.59,.61),.22,.95);lamp=material(stage,'Headlight',(.8,.87,.9),.2,emit=(.3,.35,.4));red=material(stage,'Taillight',(.35,.015,.008),.25,emit=(.10,.001,.001))
 def loft(path,sections,mat,segments=20):
  pts=[];fs=[]
  for i,(x,w,zmid,h) in enumerate(sections):
   for j in range(segments):
    a=j*math.tau/segments
    # Rounded rectangular sections produce panels/hoods rather than a cylindrical blob.
    si=math.sin(a);co=math.cos(a)
    pts.append((x,w*math.copysign(abs(si)**.6,si),zmid+h*math.copysign(abs(co)**.7,co)))
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
   # A recessed alloy rim and central hub give tires actual sidewall/rim separation.
   rim=UsdGeom.Cylinder.Define(stage,(name+'_Rim').replace('-','n'));rim.CreateAxisAttr('Y');rim.CreateRadiusAttr(.215);rim.CreateHeightAttr(.025);rim.AddTranslateOp().Set(Gf.Vec3d(x,side*1.025,.35));UsdShade.MaterialBindingAPI.Apply(rim.GetPrim()).Bind(chrome)
   for j in range(5):
    a=j*math.tau/5;tube(stage,name+'_Spoke_'+str(j),[(x,side*1.035,.35),(x+math.cos(a)*.22,side*1.035,.35+math.sin(a)*.22)],[.045,.028],chrome,6)
 box(stage,'/Asset/Grille',(2.21,0,.60),(.06,.65,.14),rubber);root.GetPrim().SetCustomData({'creator':'TWIN original procedural sedan','length_m':4.5,'width_m':2.26,'placement':'static illustrative vehicle; not traffic data'})
 colors=root.GetPrim().GetVariantSets().AddVariantSet('paintColor')
 for label,color in [('slate',(.12,.20,.27)),('silver',(.48,.50,.52)),('white',(.78,.78,.72)),('red',(.31,.025,.018))]:
  colors.AddVariant(label);colors.SetVariantSelection(label)
  with colors.GetVariantEditContext():UsdShade.Shader(stage.GetPrimAtPath('/Asset/Materials/Paint/Surface')).GetInput('diffuseColor').Set(Gf.Vec3f(*color))
 colors.SetVariantSelection('slate');stage.GetRootLayer().Save()


def revised_tree(kind,seed):
 """Layered, branch-supported crown; batched cards and opaque palm leaflets."""
 file=OUT/(kind+'.usdc');stage=Usd.Stage.CreateNew(str(file));root=UsdGeom.Xform.Define(stage,'/Asset');stage.SetDefaultPrim(root.GetPrim());UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
 bark=material(stage,'Bark',(.17,.12,.075),.96)
 leafmats=[material(stage,'LeafTone'+str(i),(.08,.18,.04),.8+i*.035,leaf=True) for i in range(3)]
 # Texture variation is multiplicative; original RGBA cluster supplies cutout silhouettes.
 for i in range(3):
  tex=UsdShade.Shader(stage.GetPrimAtPath('/Asset/Materials/LeafTone'+str(i)+'/Texture'))
  tex.CreateInput('scale',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(.82+i*.12,.88+i*.09,.78+i*.12,1))
 variants=root.GetPrim().GetVariantSets().AddVariantSet('detail')
 for lod,density in [('high',2200),('medium',1450),('low',350)]:
  variants.AddVariant(lod);variants.SetVariantSelection(lod)
  with variants.GetVariantEditContext():
   rng=random.Random(seed);batches=[([],[],[]) for _ in range(3)]
   if kind=='palm':
    tube(stage,'/Asset/Geometry/Trunk',[(0,0,0),(.08,.02,2),(.18,.06,4),(.29,.10,6),(.33,.12,8.15)],[.23,.20,.17,.14,.11],bark,12)
    palmleaf=material(stage,'PalmLeaf',(.12,.25,.065),.78)
    # Narrow physical leaflets require no cluster alpha; each has a tapered folded ridge.
    pts=[];faces=[]
    for j in range(27):
     angle=j*2.399963+seed*.01;length=(2.0 if j<6 else 3.1)+rng.random()*1.0;tilt=rng.uniform(-.4,.4)
     # New upright central fronds and mature arching outer fronds form a crown.
     lift=2.2 if j<6 else 1.3;droop=.45 if j<6 else 2.0
     line=[]
     for k in range(13):
      t=k/12;line.append((.33+math.cos(angle)*length*t,.12+math.sin(angle)*length*t,8.25+lift*math.sin(t*math.pi*.8)+tilt*t-droop*t*t))
     tube(stage,'/Asset/Geometry/Frond_'+str(j),line,[max(.004,.032*(1-k/13)) for k in range(13)],bark,5)
     for k in range(1,24):
      for side in [-1,1]:
       t=k/24;segment=t*12;index=int(segment)
       c=Gf.Vec3d(*line[index])*(1-(segment-index))+Gf.Vec3d(*line[index+1])*(segment-index);across=Gf.Vec3d(-math.sin(angle),math.cos(angle),0)*side
       direction=Gf.Vec3d(math.cos(angle),math.sin(angle),0)
       reach=(.8*math.sin(t*math.pi)+.12)*rng.uniform(.88,1.1)*(length/3.6)
       tip=c+across*reach+direction*.19+Gf.Vec3d(0,0,-.2*reach)
       half=direction*.045;mid=(c+tip)*.5+Gf.Vec3d(0,0,.045)
       base=len(pts);pts.extend([tuple(c-half),tuple(c+half),tuple(mid+half*.65),tuple(tip),tuple(mid-half*.65)])
       faces.extend([[base,base+1,base+2],[base,base+2,base+4],[base+2,base+3,base+4]])
    mesh(stage,'/Asset/Geometry/Foliage',pts,faces,palmleaf,smooth=False)
   else:
    tube(stage,'/Asset/Geometry/Trunk',[(0,0,0),(.08,.02,1.4),(.16,.05,2.7),(.12,.12,4.2)],[.40,.34,.29,.22],bark,12)
    lobes=[]
    for j in range(9):
     angle=j*2.399963+seed*.04;radius=rng.uniform(3.2,4.8);end=Gf.Vec3d(math.cos(angle)*radius,math.sin(angle)*radius,rng.uniform(5.3,7.4))
     start=Gf.Vec3d(.12,.1,rng.uniform(2.7,3.6));elbow=Gf.Vec3d(end[0]*.45,end[1]*.45,4.1+rng.random()*.7)
     tube(stage,'/Asset/Geometry/Scaffold_'+str(j),[tuple(start),tuple(elbow),tuple(end)],[.20,.12,.033],bark,8)
     for k in range(3):
      a=angle+(k-1)*.58;tip=end+Gf.Vec3d(math.cos(a)*rng.uniform(.4,1.3),math.sin(a)*rng.uniform(.4,1.3),rng.uniform(.2,1.4))
      tube(stage,'/Asset/Geometry/Twig_'+str(j)+'_'+str(k),[tuple(elbow*.25+end*.75),tuple(end),tuple(tip)],[.06,.033,.009],bark,6);lobes.append(tip)
    lobes.extend([Gf.Vec3d(0,0,7.4),Gf.Vec3d(1,-.5,8.0)])
    for j in range(density):
     center=lobes[j%len(lobes)];c=center+Gf.Vec3d(rng.gauss(0,.68),rng.gauss(0,.68),rng.gauss(0,.56))
     size=rng.uniform(.35,.54);az=rng.uniform(0,math.tau);tilt=rng.uniform(.2,1.1)
     u=Gf.Vec3d(math.cos(az),math.sin(az),rng.uniform(-.3,.3))*size
     v=Gf.Vec3d(-math.sin(az)*math.cos(tilt),math.cos(az)*math.cos(tilt),math.sin(tilt))*size
     pts,faces,uv=batches[j%3];base=len(pts);pts.extend([tuple(c-u-v),tuple(c+u-v),tuple(c+u+v),tuple(c-u+v)]);faces.append([base,base+1,base+2,base+3]);uv.extend([(0,0),(1,0),(1,1),(0,1)])
    for i,(pts,faces,uv) in enumerate(batches):mesh(stage,'/Asset/Geometry/FoliageTone'+str(i),pts,faces,leafmats[i],uv,smooth=False)
 root.GetPrim().SetCustomData({'creator':'TWIN original procedural vegetation revision 2','placement':'existing illustrative positions retained','species_quality':'palm-like' if kind=='palm' else 'oak-like; not surveyed species','leaf_cluster_card_width_m':'0.70-1.08; each texture contains multiple physical leaves'})
 variants.SetVariantSelection('medium');stage.GetRootLayer().Save();return file


def build(proposal=True,output=None):
 global OUT
 if not proposal:raise ValueError('Only non-active proposal output is supported')
 OUT=Path(output).resolve() if output else ROOT/'assets/generated/environment_v2'
 if OUT==ROOT/'assets/generated':raise ValueError('Do not overwrite original assets')
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'textures').mkdir(exist_ok=True)
 leaf_texture()
 for kind,seed in [('oak_a',110),('oak_b',230),('palm',310)]:revised_tree(kind,seed)
 car()
 source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'))
 source_inst=UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees'))
 layer=Usd.Stage.CreateNew(str(ROOT/'scene/asset_upgrade_proposal.usda'));inst=UsdGeom.PointInstancer.Define(layer,'/World/Trees');targets=[]
 def relative(path):return os.path.relpath(path,ROOT/'scene').replace('\\','/')
 for i,name in enumerate(['oak_a','oak_b','oak_a','oak_b','oak_a','oak_b','palm']):
  path='/World/Trees/Detailed/Tree_'+str(i);p=UsdGeom.Xform.Define(layer,path).GetPrim()
  # Replace rather than prepend, avoiding a composition of old and new asset geometry.
  p.GetReferences().SetReferences([Sdf.Reference(relative(OUT/(name+'.usdc')),'/Asset')]);p.GetVariantSet('detail').SetVariantSelection('medium');targets.append(Sdf.Path(path))
 inst.CreatePrototypesRel().SetTargets(targets)
 cars=0
 for parent in source.GetPrimAtPath('/World/ParkedVehicles').GetChildren():
  old=parent.GetChild('DetailedSedan')
  if not old:continue
  p=layer.OverridePrim(old.GetPath());p.GetReferences().SetReferences([Sdf.Reference(relative(OUT/'sedan.usdc'),'/Asset')]);p.GetVariantSets().AddVariantSet('paintColor').SetVariantSelection(['slate','silver','white','red'][cars%4]);p.SetInstanceable(True);cars+=1
 layer.GetRootLayer().customLayerData={'quality':'Original environment revision 2; preserves existing arrays/transforms; placement not surveyed','proposalOnly':True}
 path=ROOT/'scene/asset_upgrade_proposal.usda';layer.GetRootLayer().Export(str(path))
 # Standalone comparison: original on left, revised on right, with useful cameras/light.
 compare=Usd.Stage.CreateNew(str(ROOT/'scene/environment_compare_proposal.usda'));UsdGeom.SetStageUpAxis(compare,'Z');UsdGeom.SetStageMetersPerUnit(compare,1)
 for side,x in [('Original',-8),('Revised',8)]:
  folder=ROOT/'assets/generated' if side=='Original' else OUT
  for name,y in [('oak_a',6),('palm',-6),('sedan',-15)]:
   xf=UsdGeom.Xform.Define(compare,'/World/'+side+'/'+name)
   if side=='Original':
    # Reference the actual composed subtree, retaining presentation material opinions.
    current={'oak_a':'/World/Trees/Detailed/Tree_0','palm':'/World/Trees/Detailed/Tree_6','sedan':'/World/ParkedVehicles/Car_000/DetailedSedan'}[name]
    xf.GetPrim().GetReferences().AddReference('college_park_connected.usda',current)
    xf.GetPrim().SetInstanceable(False)
    xf.SetXformOpOrder([],resetXformStack=True)
    xf.AddTranslateOp(opSuffix='comparisonPlacement').Set(Gf.Vec3d(x,y,0))
   else:
    xf.GetPrim().GetReferences().AddReference(relative(folder/(name+'.usdc')),'/Asset');xf.AddTranslateOp().Set(Gf.Vec3d(x,y,0))
 sun=UsdLux.DistantLight.Define(compare,'/World/Sun');sun.CreateIntensityAttr(2200);sun.CreateAngleAttr(.7);UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(25,-30,-30));UsdLux.DomeLight.Define(compare,'/World/Sky').CreateIntensityAttr(500)
 cam=UsdGeom.Camera.Define(compare,'/World/CompareCamera');cam.CreateFocalLengthAttr(35);cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(20.25);cam.CreateClippingRangeAttr(Gf.Vec2f(.1,1000));cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(32,-47,27),Gf.Vec3d(0,-3,4),Gf.Vec3d(0,0,1)).GetInverse())
 ground=material(compare,'CompareGround',(.26,.28,.25),.95);box(compare,'/World/Ground',(0,-5,-.12),(45,50,.2),ground)
 compare_path=ROOT/'scene/environment_compare_proposal.usda';compare.GetRootLayer().Export(str(compare_path))
 work=Sdf.Layer.CreateAnonymous();work.subLayerPaths=['asset_upgrade_proposal.usda','college_park_connected.usda'];work.Export(str(ROOT/'scene/environment_workview_proposal.usda'))
 counts={}
 for name in ['oak_a','oak_b','palm','sedan']:
  s=Usd.Stage.Open(str(OUT/(name+'.usdc')));counts[name]={'mesh_count':0,'vertices':0,'faces':0}
  for p in s.Traverse():
   if p.IsA(UsdGeom.Mesh):
    m=UsdGeom.Mesh(p);counts[name]['mesh_count']+=1;counts[name]['vertices']+=len(m.GetPointsAttr().Get());counts[name]['faces']+=len(m.GetFaceVertexCountsAttr().Get())
 report={'original_assets':True,'proposal_only':True,'external_assets':False,'tree_instances':len(source_inst.GetPositionsAttr().Get()),'replaced_cars':cars,'prototype_geometry_counts_medium':counts,'instance_arrays_authored':False,'car_transforms_authored':False,'placement_quality':'illustrative existing positions retained; no inventory, parking or clearance accuracy claim','compare_layer':str(compare_path),'workview_layer':str(ROOT/'scene/environment_workview_proposal.usda')}
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report


def repair_comparison_only():
 """Re-reference only comparison originals; never regenerate district assets."""
 path=ROOT/'scene/environment_compare_proposal.usda';stage=Usd.Stage.Open(str(path))
 for name,y in [('oak_a',6),('palm',-6),('sedan',-15)]:
  xf=UsdGeom.Xformable(stage.GetPrimAtPath('/World/Original/'+name))
  target={'oak_a':'/World/Trees/Detailed/Tree_0','palm':'/World/Trees/Detailed/Tree_6','sedan':'/World/ParkedVehicles/Car_000/DetailedSedan'}[name]
  xf.GetPrim().GetReferences().SetReferences([Sdf.Reference('college_park_connected.usda',target)])
  xf.GetPrim().SetInstanceable(False);xf.SetXformOpOrder([],resetXformStack=True)
  op=next((op for op in xf.GetOrderedXformOps() if op.GetOpName()=='xformOp:translate:comparisonPlacement'),None)
  attr=xf.GetPrim().GetAttribute('xformOp:translate:comparisonPlacement')
  if attr and attr.HasAuthoredValueOpinion():
   attr.Set(Gf.Vec3d(-8,y,0));xf.GetXformOpOrderAttr().Set(['!resetXformStack!','xformOp:translate:comparisonPlacement'])
  else:xf.AddTranslateOp(opSuffix='comparisonPlacement').Set(Gf.Vec3d(-8,y,0))
  xf.GetPrim().SetCustomDataByKey('comparisonLabel','CURRENT COMPOSED APPEARANCE (left)')
 stage.GetPrimAtPath('/World/Revised').SetCustomDataByKey('comparisonLabel','PROPOSED ORIGINAL ASSETS (right)')
 stage.GetRootLayer().Save();print(str(path))


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--proposal',action='store_true',default=True);parser.add_argument('--output',type=Path);parser.add_argument('--comparison-only',action='store_true');args=parser.parse_args()
 if args.comparison_only:repair_comparison_only()
 else:build(args.proposal,args.output)
