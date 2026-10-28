"""Create a reversible visual detail layer over the geographic base.

All vegetation placement and facade designs are illustrative, not surveyed.
"""
import sys, math, json, random, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd, UsdGeom, UsdShade, UsdLux, Sdf, Gf, Vt
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union, nearest_points, linemerge, triangulate
from shapely.strtree import STRtree
from pyproj import Transformer
from PIL import Image, ImageDraw, ImageFont
import numpy as np

rng=random.Random(417)
SCENE=ROOT/'scene';ASSETS=SCENE/'textures';ASSETS.mkdir(exist_ok=True)
BASE=SCENE/'college_park.usda'
base=Usd.Stage.Open(str(BASE))
detail=Usd.Stage.CreateNew(str(SCENE/'edgewater_details.usdc'))
detail.OverridePrim('/World')
detail.GetRootLayer().customLayerData={'quality':'Illustrative streetscape, not a surveyed as-built model','scope':'Trees, storefront designs, street furniture, and road materials','reference':'City of Orlando Edgewater Drive Vision Plan Support Document, April 2009; stylistic reference only','businessSigns':'Generic illustrative shop categories; not verified tenants'}

# Original procedural texture assets. No third-party imagery is embedded.
nrng=np.random.default_rng(417)
def texture(name,base_color,noise=7,brick=False,paving=False):
    size=512
    a=np.clip(np.array(base_color)[None,None,:]+nrng.normal(0,noise,(size,size,1)),0,255).astype('uint8')
    image=Image.fromarray(a);draw=ImageDraw.Draw(image)
    if brick:
        for row in range(16):
            y=row*32;draw.line((0,y,512,y),fill=(132,124,111),width=3)
            for x in range(-64,576,128):
                x+=64*(row%2);draw.line((x,y,x,y+32),fill=(132,124,111),width=3)
    if paving:
        for i in range(0,513,128):
            draw.line((i,0,i,512),fill=(128,124,114),width=2)
            draw.line((0,i,512,i),fill=(128,124,114),width=2)
    image.save(ASSETS/(name+'.png'))
texture('asphalt',(61,64,65),10)
texture('concrete',(174,169,155),5,paving=True)
texture('brick',(150,83,54),9,brick=True)
texture('stucco',(207,196,169),6)
texture('roof',(74,78,77),12)
texture('bark',(83,66,45),18)
texture('grass',(69,89,48),9)

materials={}
def mat(name,color,rough=.8,metal=0,tex=None,emission=None):
    m=UsdShade.Material.Define(detail,'/World/DetailMaterials/'+name)
    s=UsdShade.Shader.Define(detail,m.GetPath().AppendChild('Surface'));s.CreateIdAttr('UsdPreviewSurface')
    s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough)
    s.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(metal)
    if emission:s.CreateInput('emissiveColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emission))
    if tex:
        t=UsdShade.Shader.Define(detail,m.GetPath().AppendChild('Texture'));t.CreateIdAttr('UsdUVTexture')
        t.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('textures/'+tex+'.png'))
        t.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB')
        t.CreateInput('wrapS',Sdf.ValueTypeNames.Token).Set('repeat');t.CreateInput('wrapT',Sdf.ValueTypeNames.Token).Set('repeat')
        t.CreateInput('scale',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*color,1))
        uv=UsdShade.Shader.Define(detail,m.GetPath().AppendChild('UV'));uv.CreateIdAttr('UsdPrimvarReader_float2');uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
        t.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result')
        s.GetInput('diffuseColor').ConnectToSource(t.ConnectableAPI(),'rgb')
    m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface');materials[name]=m;return m

mat('Asphalt',(1,1,1),.96,tex='asphalt');mat('Concrete',(1,1,1),.92,tex='concrete')
mat('Brick',(1,1,1),.9,tex='brick');mat('Stucco',(1,1,1),.85,tex='stucco');mat('Roof',(1,1,1),.9,tex='roof')
mat('Grass',(1,1,1),.96,tex='grass');mat('Bark',(1,1,1),.95,tex='bark')
mat('Glass',(.045,.105,.13),.14,.55);mat('WindowFrame',(.065,.075,.07),.35,.7)
mat('CreamTrim',(.66,.60,.45));mat('WhitePaint',(.82,.80,.71));mat('BlackMetal',(.028,.036,.033),.4,.75)
mat('Wood',(.22,.105,.044),.8);mat('Soil',(.085,.055,.028));mat('Yellow',(.64,.45,.08));mat('Tire',(.018,.02,.023))
mat('LampGlass',(.85,.73,.42),.3,emission=(1,.7,.32))
for i,c in enumerate([(.035,.12,.025),(.06,.17,.035),(.095,.21,.045),(.12,.24,.065),(.07,.15,.045),(.14,.23,.075)]):mat('Leaves'+str(i),c,.95)
for i,c in enumerate([(.075,.19,.16),(.38,.13,.055),(.15,.17,.21),(.48,.39,.23),(.22,.08,.075)]):mat('Awning'+str(i),c,.9)
for i,c in enumerate([(.60,.54,.40),(.72,.67,.55),(.42,.49,.43),(.62,.47,.34),(.55,.58,.56),(.73,.71,.64)]):mat('Facade'+str(i),c,.9)
for i,c in enumerate([(.08,.12,.16),(.5,.50,.46),(.32,.055,.035),(.055,.14,.12),(.69,.66,.53)]):mat('Car'+str(i),c,.3,.6)

def bind(prim,name):UsdShade.MaterialBindingAPI.Apply(prim).Bind(materials[name])
def raw_mesh(path,points,faces,name,uv=None,smooth=False):
    m=UsdGeom.Mesh.Define(detail,path);m.CreatePointsAttr(points);m.CreateFaceVertexCountsAttr([len(f) for f in faces]);m.CreateFaceVertexIndicesAttr([i for f in faces for i in f]);m.CreateSubdivisionSchemeAttr('none');m.CreateDoubleSidedAttr(True)
    bind(m.GetPrim(),name)
    if uv:UsdGeom.PrimvarsAPI(m).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set(uv)
    return m.GetPrim()

def cuboid(path,c,size,name,t=(1,0)):
    # Local x follows facade, local y points outward. Symmetric box is insensitive to handedness.
    tx,ty=t;nx,ny=-ty,tx
    pts=[]
    for z in [-.5,.5]:
        for x,y in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]:
            pts.append((c[0]+x*size[0]*tx+y*size[1]*nx,c[1]+x*size[0]*ty+y*size[1]*ny,c[2]+z*size[2]))
    fs=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
    uv=[]
    for j,f in enumerate(fs):
        w=size[0] if j in [0,1,2,4] else size[1];h=size[1] if j<2 else size[2]
        uv.extend([(0,0),(w,0),(w,h),(0,h)])
    return raw_mesh(path,pts,fs,name,uv)

def cylinder(path,c,r,h,name):
    p=UsdGeom.Cylinder.Define(detail,path);p.CreateRadiusAttr(r);p.CreateHeightAttr(h);p.CreateAxisAttr('Z');p.AddTranslateOp().Set(Gf.Vec3d(*c));bind(p.GetPrim(),name);return p

def flat(path,geom,z,name):
    ps=[];fs=[]
    geoms=[geom] if geom.geom_type=='Polygon' else list(getattr(geom,'geoms',[]))
    for g in geoms:
        if g.geom_type!='Polygon':continue
        for tri in triangulate(g):
            if not g.covers(tri):continue
            coords=list(tri.exterior.coords)[:3];k=len(ps);ps.extend([(x,y,z) for x,y in coords]);fs.append([k,k+1,k+2])
    if ps:return raw_mesh(path,ps,fs,name,[(x/4,y/4) for f in fs for x,y,_ in [ps[i] for i in f]])

def planar_uv(prim,period=3):
    source=UsdGeom.Mesh(prim);points=source.GetPointsAttr().Get();sizes=source.GetFaceVertexCountsAttr().Get();ids=source.GetFaceVertexIndicesAttr().Get();uv=[];k=0
    for size in sizes:
        p=[Gf.Vec3d(points[i]) for i in ids[k:k+size]];k+=size
        normal=Gf.Cross(p[1]-p[0],p[2]-p[0]);axis=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=axis]
        uv.extend([(v[axes[0]]/period,v[axes[1]]/period) for v in p])
    override=detail.OverridePrim(prim.GetPath())
    UsdGeom.PrimvarsAPI(override).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set(uv)
    return override

# Read base geometry without rewriting it or discarding manual edits.
buildings=[]
for prim in base.GetPrimAtPath('/World/Buildings').GetChildren():
    m=UsdGeom.Mesh(prim);points=m.GetPointsAttr().Get();ids=m.GetFaceVertexIndicesAttr().Get();sizes=m.GetFaceVertexCountsAttr().Get();triangles=[];k=0
    for size in sizes:
        if size==3:triangles.append(Polygon([(points[i][0],points[i][1]) for i in ids[k:k+3]]))
        k+=size
    footprint=unary_union(triangles).buffer(0)
    if not footprint.is_empty:buildings.append((prim,footprint))
building_geoms=[g for _,g in buildings];building_index=STRtree(building_geoms)
water=[];streets=[]
for parent,collection in [('/World/Water',water),('/World/Streets',streets)]:
    for prim in base.GetPrimAtPath(parent).GetChildren():
        if parent.endswith('Streets') and not prim.GetName().startswith('Road_'):continue
        m=UsdGeom.Mesh(prim)
        if not m:continue
        pts=m.GetPointsAttr().Get();ids=m.GetFaceVertexIndicesAttr().Get();ss=m.GetFaceVertexCountsAttr().Get();k=0;ts=[]
        for size in ss:
            if size==3:ts.append(Polygon([(pts[i][0],pts[i][1]) for i in ids[k:k+3]]))
            k+=size
        if ts:collection.append(unary_union(ts))
wet=unary_union(water);street_union=unary_union(streets)
proj=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=proj.transform(-81.389,28.572)
def project(lon,lat):
    x,y=proj.transform(lon,lat);return x-ox,y-oy
osm=json.loads((ROOT/'data'/'openstreetmap.json').read_text())
edge_lines=[];other_lines=[]
for way in osm['elements']:
    tags=way.get('tags',{});geo=way.get('geometry',[])
    if not tags.get('highway') or len(geo)<2:continue
    line=LineString([project(p['lon'],p['lat']) for p in geo if 'lat' in p])
    if tags.get('name')=='Edgewater Drive':edge_lines.append(line)
    elif tags.get('highway') in ['residential','tertiary','secondary']:other_lines.append(line)
edge=unary_union(edge_lines)
print('Loaded base buildings',len(buildings),'Edgewater centerlines',len(edge_lines),flush=True)

# Texture and color variation across the base removes the uniform white-block look.
for prim,g in buildings:
    bind(planar_uv(prim,3),'Facade'+str(rng.randrange(6)))
for prim in base.GetPrimAtPath('/World/Roofs').GetChildren():bind(planar_uv(prim,5),'Roof')
for prim in base.GetPrimAtPath('/World/Streets').GetChildren():
    name=prim.GetName()
    if name.startswith('Road_'):bind(planar_uv(prim,4),'Asphalt')
    elif name.startswith('Shoulders_'):bind(planar_uv(prim,4),'Concrete')
bind(planar_uv(base.GetPrimAtPath('/World/Ground'),10),'Grass')

counts={'trees':0,'storefrontBuildings':0,'storefrontBays':0,'benches':0,'lamps':0,'parkedCars':0}
decor=UsdGeom.Xform.Define(detail,'/World/Storefronts')
decor.GetPrim().SetCustomData({'quality':'Illustrative facades on public footprint geometry','signs':'Generic shop categories, not verified business identities'})
frontages=[]
fontpath='C:/Windows/Fonts/arialbd.ttf'
font=ImageFont.truetype(fontpath,58)
labels=['CAFE','MARKET','STUDIO','LOCAL GOODS','COFFEE','KITCHEN','SHOP','BAKERY']
for i,label in enumerate(labels):
    image=Image.new('RGB',(512,128),[(24,51,44),(83,39,25),(29,40,48),(74,64,44)][i%4]);d=ImageDraw.Draw(image)
    bounds=d.textbbox((0,0),label,font=font);x=(512-(bounds[2]-bounds[0]))/2
    d.text((x,30),label,font=font,fill=(232,224,202));image.save(ASSETS/f'sign_{i}.png')
    mat('Sign'+str(i),(1,1,1),.7,tex='sign_'+str(i))

for prim,g in buildings:
    if g.distance(edge)>38 or prim.GetCustomData().get('classification')!='Commercial':continue
    pieces=[g] if g.geom_type=='Polygon' else list(g.geoms)
    candidates=[]
    for poly in pieces:
        coords=list(poly.exterior.coords)
        for a,b in zip(coords,coords[1:]):
            segment=LineString([a,b]);length=segment.length
            if length<4.5:continue
            mid=segment.interpolate(.5,normalized=True);roadpoint=nearest_points(mid,edge)[1];distance=mid.distance(roadpoint)
            if distance<5 or distance>42:continue
            tx=(b[0]-a[0])/length;ty=(b[1]-a[1])/length;nx=-ty;ny=tx
            if poly.contains(Point(mid.x+nx*.3,mid.y+ny*.3)):nx=-nx;ny=-ny
            dx=roadpoint.x-mid.x;dy=roadpoint.y-mid.y
            if (nx*dx+ny*dy)/distance<.78:continue
            # Front is visible from the road rather than behind another part of its building.
            if LineString([(mid.x+nx*.25,mid.y+ny*.25),(roadpoint.x,roadpoint.y)]).intersection(g).length>.5:continue
            candidates.append((length,a,b,(tx,ty),(nx,ny),distance))
    if not candidates:continue
    # One or two front-facing surfaces per structure, not every tiny footprint edge.
    candidates=sorted(candidates,reverse=True,key=lambda x:x[0])[:2]
    bid=prim.GetName();root='/World/Storefronts/'+bid;UsdGeom.Xform.Define(detail,root)
    height=float(prim.GetCustomData().get('heightMeters',6.5))
    for fi,(length,a,b,t,n,distance) in enumerate(candidates):
        tx,ty=t;nx,ny=n
        def at(u,v,z):return (a[0]+tx*u+nx*v,a[1]+ty*u+ny*v,z)
        fp=root+'/Front_'+str(fi)
        UsdGeom.Xform.Define(detail,fp)
        # Masonry plinth, cornice and parapet cap give facades depth.
        cuboid(fp+'/Plinth',at(length/2,.08,.38),(length,.20,.55),'Brick',t)
        cuboid(fp+'/Cornice',at(length/2,.12,4.05),(length+.20,.34,.22),'CreamTrim',t)
        cuboid(fp+'/Parapet',at(length/2,.06,height-.12),(length+.1,.25,.22),'CreamTrim',t)
        bays=max(1,int(length/4.8));step=length/bays
        for bi in range(bays):
            center=(bi+.5)*step;w=step-.65;bp=fp+f'/Bay_{bi:02d}'
            UsdGeom.Xform.Define(detail,bp)
            cuboid(bp+'/Glass',at(center,.10,1.72),(w,.12,2.40),'Glass',t)
            for u in [center-w/2,center+w/2,center]:cuboid(bp+'/Mullion_'+str(round(u,3)).replace('.','_'),at(u,.19,1.72),(.065,.10,2.48),'WindowFrame',t)
            for z in [.52,2.92]:cuboid(bp+'/Rail_'+str(z).replace('.','_'),at(center,.19,z),(w+.12,.10,.075),'WindowFrame',t)
            # Opaque dark glazing intentionally avoids pretending to model unobserved shop interiors.
            cuboid(bp+'/DoorFrame',at(center,.23,1.35),(1.02,.14,2.5),'WindowFrame',t)
            cuboid(bp+'/DoorGlass',at(center,.32,1.38),(.84,.06,2.22),'Glass',t)
            cuboid(bp+'/Handle',at(center+.29,.39,1.24),(.035,.04,.43),'CreamTrim',t)
            awning='Awning'+str((bi+counts['storefrontBuildings'])%5)
            pts=[at(center-w/2-.15,.15,3.40),at(center+w/2+.15,.15,3.40),at(center+w/2+.15,1.65,3.05),at(center-w/2-.15,1.65,3.05)]
            raw_mesh(bp+'/Awning',pts,[[0,1,2,3]],awning,[(0,0),(1,0),(1,1),(0,1)])
            cuboid(bp+'/Valance',at(center,1.65,2.96),(w+.30,.09,.20),awning,t)
            # Textured sign quad, with orientation explicitly defined in the facade basis.
            sw=min(w,3.6);pts=[at(center-sw/2,.29,3.67),at(center+sw/2,.29,3.67),at(center+sw/2,.29,3.99),at(center-sw/2,.29,3.99)]
            sign_uv=[(1,0),(0,0),(0,1),(1,1)] if (-ty*nx+tx*ny)>0 else [(0,0),(1,0),(1,1),(0,1)]
            raw_mesh(bp+'/IllustrativeSign',pts,[[0,1,2,3]],'Sign'+str((bi+counts['storefrontBuildings'])%len(labels)),sign_uv)
            counts['storefrontBays']+=1
        # Front apron extends toward the road without covering the mapped carriageway.
        strip=LineString([a,b]).buffer(min(2.2,max(.7,distance-6)),cap_style=2).difference(g).difference(street_union)
        flat(fp+'/EntryPaving',strip,.09,'Concrete')
        frontages.append((a,b,t,n))
    counts['storefrontBuildings']+=1

print('Storefront buildings',counts['storefrontBuildings'],'bays',counts['storefrontBays'],flush=True)

# Reusable oak and palm prototypes, instanced for modest GPU and file cost.
inst=UsdGeom.PointInstancer.Define(detail,'/World/Trees')
inst.GetPrim().SetCustomData({'placement':'Illustrative procedural placement; not an inventory of existing trees','species':'Stylized broadleaf shade trees and palms'})
proto_paths=[]
def branch(path,a,b,r):
    va=Gf.Vec3d(*a);vb=Gf.Vec3d(*b);direction=vb-va
    c=UsdGeom.Cylinder.Define(detail,path);c.CreateRadiusAttr(r);c.CreateHeightAttr(direction.GetLength());c.CreateAxisAttr('Z');c.AddTranslateOp().Set((va+vb)/2)
    rotation=Gf.Rotation(Gf.Vec3d(0,0,1),direction.GetNormalized());c.AddOrientOp().Set(Gf.Quatf(rotation.GetQuat()));bind(c.GetPrim(),'Bark')

def crown(path,c,scale,seed,matname):
    local=random.Random(seed);pts=[];uv=[];rings=9;segments=16
    jitter=[[local.uniform(.86,1.16) for j in range(segments)] for i in range(rings+1)]
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(segments):
            theta=2*math.pi*j/segments;r=jitter[i][j]
            pts.append((c[0]+math.sin(phi)*math.cos(theta)*scale[0]*r,c[1]+math.sin(phi)*math.sin(theta)*scale[1]*r,c[2]+math.cos(phi)*scale[2]*r))
    fs=[]
    for i in range(rings):
        for j in range(segments):fs.append([i*segments+j,i*segments+(j+1)%segments,(i+1)*segments+(j+1)%segments,(i+1)*segments+j])
    prim=raw_mesh(path,pts,fs,matname)
    normals=[]
    for p in pts:
        normal=Gf.Vec3f(*((p[i]-c[i])/(scale[i]*scale[i]) for i in range(3)))
        if normal.GetLength()>0:normal.Normalize()
        normals.append(normal)
    m=UsdGeom.Mesh(prim);m.CreateNormalsAttr(normals);m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)

for variant in range(6):
    path=f'/World/Trees/Prototypes/Oak_{variant}';UsdGeom.Xform.Define(detail,path);proto_paths.append(Sdf.Path(path))
    branch(path+'/Trunk',(0,0,0),(.15,-.1,4.9),.24)
    local=random.Random(variant+40)
    for j in range(8):
        angle=j*math.tau/8+local.uniform(-.2,.2);r=local.uniform(1.9,3.2);end=(math.cos(angle)*r,math.sin(angle)*r,local.uniform(5.0,6.5))
        branch(path+f'/Branch_{j}',(.1,0,3.1),end,.075)
        crown(path+f'/Crown_{j}',end,(2.05,2.05,1.65),variant*20+j,'Leaves'+str((variant+j)%6))
    crown(path+'/Top',(.1,0,6.3),(2.7,2.7,1.9),variant+300,'Leaves'+str(variant))
path='/World/Trees/Prototypes/Palm';UsdGeom.Xform.Define(detail,path);proto_paths.append(Sdf.Path(path));branch(path+'/Trunk',(0,0,0),(.18,0,7.1),.19)
for j in range(14):
    angle=j*math.tau/14;pts=[];fs=[]
    for k in range(9):
        u=k/8;length=3.7*u;z=7.4+1.25*math.sin(math.pi*u)-1.6*u*u;cx=.18+math.cos(angle)*length;cy=math.sin(angle)*length
        width=.32*math.sin(math.pi*u)+.025
        pts.extend([(cx-math.sin(angle)*width,cy+math.cos(angle)*width,z),(cx+math.sin(angle)*width,cy-math.cos(angle)*width,z)])
        if k:fs.append([2*k-2,2*k-1,2*k+1,2*k])
    raw_mesh(path+f'/Frond_{j}',pts,fs,'Leaves'+str(j%6))
inst.CreatePrototypesRel().SetTargets(proto_paths)

positions=[];indices=[];scales=[];orientations=[];occupied=set()
def available(p,clearance=2):
    if wet.distance(p)<2 or street_union.distance(p)<1.15:return False
    for idx in building_index.query(p.buffer(clearance)):
        if building_geoms[int(idx)].distance(p)<clearance:return False
    cell=(round(p.x/5),round(p.y/5))
    if cell in occupied:return False
    occupied.add(cell);return True
def add_tree(p,priority=False):
    if not available(p,2.2):return
    variant=6 if priority and rng.random()<.22 else rng.randrange(6)
    scale=rng.uniform(.75,1.23) if priority else rng.uniform(.8,1.45)
    positions.append((p.x,p.y,.10));indices.append(variant);scales.append(Gf.Vec3f(scale,scale,scale*rng.uniform(.9,1.08)))
    orientations.append(Gf.Quath(Gf.Rotation(Gf.Vec3d(0,0,1),rng.uniform(0,360)).GetQuat()))

for line in edge_lines:
    for distance in np.arange(6,line.length,17):
        p=line.interpolate(float(distance));p0=line.interpolate(max(0,float(distance)-.5));p1=line.interpolate(min(line.length,float(distance)+.5));dx=p1.x-p0.x;dy=p1.y-p0.y;length=math.hypot(dx,dy)
        if length<.01:continue
        for sign in [-1,1]:
            offset=rng.uniform(8.5,10.6)
            add_tree(Point(p.x-sign*dy/length*offset,p.y+sign*dx/length*offset),True)
for line in other_lines:
    for distance in np.arange(10,line.length,37):
        if rng.random()<.22:continue
        p=line.interpolate(float(distance))
        if p.distance(edge)>330:continue
        p0=line.interpolate(max(0,float(distance)-1));p1=line.interpolate(min(line.length,float(distance)+1));dx=p1.x-p0.x;dy=p1.y-p0.y;length=math.hypot(dx,dy)
        if length<.01:continue
        sign=rng.choice([-1,1]);offset=rng.uniform(7,12)
        add_tree(Point(p.x-sign*dy/length*offset,p.y+sign*dx/length*offset))
inst.CreatePositionsAttr(positions);inst.CreateProtoIndicesAttr(indices);inst.CreateScalesAttr(scales);inst.CreateOrientationsAttr(orientations)
counts['trees']=len(positions)

# Small streetscape objects, all illustrative. Keep them outside mapped traffic surfaces.
UsdGeom.Xform.Define(detail,'/World/StreetFurniture')
for i,(a,b,t,n) in enumerate(frontages):
    if i%3:continue
    length=math.dist(a,b);nx,ny=n;tx,ty=t;p=Point((a[0]+b[0])/2+nx*2.3,(a[1]+b[1])/2+ny*2.3)
    if street_union.distance(p)<1 or wet.distance(p)<1:continue
    root=f'/World/StreetFurniture/Frontage_{i}';UsdGeom.Xform.Define(detail,root)
    cuboid(root+'/BenchSeat',(p.x,p.y,.57),(1.8,.46,.12),'Wood',t)
    cuboid(root+'/BenchBack',(p.x-nx*.24,p.y-ny*.24,.92),(1.8,.09,.58),'Wood',t)
    for k in [-.65,.65]:cuboid(root+'/Leg_'+str(k).replace('.','_').replace('-','n'),(p.x+tx*k,p.y+ty*k,.30),(.09,.40,.5),'BlackMetal',t)
    counts['benches']+=1
    for k in [-1,1]:
        x=p.x+tx*k*1.75;y=p.y+ty*k*1.75
        cylinder(root+'/Planter_'+str(k).replace('-','n'),(x,y,.4),.38,.65,'Brick')
        crown(root+'/Shrub_'+str(k).replace('-','n'),(x,y,.96),(.55,.55,.55),i*10+k,'Leaves2')

for line in edge_lines:
    for d in np.arange(15,line.length,47):
        p=line.interpolate(float(d));q0=line.interpolate(max(0,float(d)-1));q1=line.interpolate(min(line.length,float(d)+1));dx=q1.x-q0.x;dy=q1.y-q0.y;length=math.hypot(dx,dy)
        if length<.01:continue
        p=Point(p.x-dy/length*8,p.y+dx/length*8)
        if not available(p,.8):continue
        root=f'/World/StreetFurniture/Lamp_{counts["lamps"]:03d}';UsdGeom.Xform.Define(detail,root)
        cylinder(root+'/Post',(p.x,p.y,2.25),.065,4.4,'BlackMetal');cylinder(root+'/Base',(p.x,p.y,.28),.16,.5,'BlackMetal')
        cuboid(root+'/Lantern',(p.x,p.y,4.57),(.36,.36,.48),'LampGlass');cuboid(root+'/Cap',(p.x,p.y,4.85),(.49,.49,.09),'BlackMetal')
        counts['lamps']+=1

# A few schematic parked vehicles add scale without pretending to simulate traffic.
UsdGeom.Xform.Define(detail,'/World/ParkedVehicles')
for line in edge_lines:
    for d in np.arange(20,line.length,29):
        p=line.interpolate(float(d));q0=line.interpolate(max(0,float(d)-1));q1=line.interpolate(min(line.length,float(d)+1));dx=q1.x-q0.x;dy=q1.y-q0.y;length=math.hypot(dx,dy)
        if length<.01 or rng.random()<.32:continue
        t=(dx/length,dy/length);n=(-t[1],t[0]);side=rng.choice([-1,1]);p=Point(p.x+n[0]*side*4.1,p.y+n[1]*side*4.1)
        # Reject junctions (another road within the vehicle's swept envelope).
        rectangle=LineString([(p.x-t[0]*2.3,p.y-t[1]*2.3),(p.x+t[0]*2.3,p.y+t[1]*2.3)]).buffer(.95,cap_style=2)
        if any(building_geoms[int(idx)].intersects(rectangle) for idx in building_index.query(rectangle)):continue
        root=f'/World/ParkedVehicles/Car_{counts["parkedCars"]:03d}';UsdGeom.Xform.Define(detail,root)
        color='Car'+str(rng.randrange(5))
        cuboid(root+'/Body',(p.x,p.y,.65),(4.3,1.8,1.05),color,t)
        cuboid(root+'/Cabin',(p.x-t[0]*.1,p.y-t[1]*.1,1.25),(2.2,1.60,.72),'Glass',t)
        cuboid(root+'/Roof',(p.x-t[0]*.1,p.y-t[1]*.1,1.63),(1.6,1.63,.08),color,t)
        for x in [-1.35,1.35]:
            for y in [-.88,.88]:
                c=(p.x+t[0]*x+n[0]*y,p.y+t[1]*x+n[1]*y,.42)
                wheel=UsdGeom.Cylinder.Define(detail,root+'/Wheel_'+str(x).replace('-','n').replace('.','_')+'_'+str(y).replace('-','n').replace('.','_'));wheel.CreateRadiusAttr(.32);wheel.CreateHeightAttr(.18);wheel.CreateAxisAttr('Y');wheel.AddTranslateOp().Set(Gf.Vec3d(*c));wheel.AddRotateZOp().Set(math.degrees(math.atan2(t[1],t[0])));bind(wheel.GetPrim(),'Tire')
        counts['parkedCars']+=1

# Warm Florida daylight, with useful low views selected from an actual detailed frontage.
sun=UsdLux.DistantLight.Define(detail,'/World/Lighting/Sun');sun.CreateIntensityAttr(1500);sun.CreateColorAttr(Gf.Vec3f(1,.94,.84));sun.CreateAngleAttr(1.2)
sky=UsdLux.DomeLight.Define(detail,'/World/Lighting/Sky');sky.CreateIntensityAttr(550);sky.CreateColorAttr(Gf.Vec3f(.78,.86,1))
def camera(name,eye,target,focal=32):
    c=UsdGeom.Camera.Define(detail,'/World/Cameras/'+name);c.CreateFocalLengthAttr(focal);c.CreateClippingRangeAttr(Gf.Vec2f(.1,10000));c.CreateHorizontalApertureAttr(36)
    matrix=Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse();UsdGeom.Xformable(c).AddTransformOp().Set(matrix)
if frontages:
    # Choose the most central facade for a repeatable detailed street-level view.
    a,b,t,n=min(frontages,key=lambda f:math.hypot((f[0][0]+f[1][0])/2,(f[0][1]+f[1][1])/2))
    mx=(a[0]+b[0])/2;my=(a[1]+b[1])/2
    camera('StorefrontWalk',(mx+n[0]*21-t[0]*16,my+n[1]*21-t[1]*16,3.2),(mx,my,2.4),32)
    camera('TreeLinedEdgewater',(mx+n[0]*42-t[0]*55,my+n[1]*42-t[1]*55,19),(mx,my,2.5),32)
detail.GetRootLayer().Save()
assembly=Usd.Stage.CreateNew(str(SCENE/'college_park_realistic.usda'))
assembly.GetRootLayer().subLayerPaths=['edgewater_details.usdc','college_park.usda']
UsdGeom.SetStageMetersPerUnit(assembly,1);UsdGeom.SetStageUpAxis(assembly,'Z');assembly.SetDefaultPrim(assembly.GetPrimAtPath('/World'))
assembly.GetRootLayer().customLayerData={'project':'College Park, Orlando — Prototype 02 streetscape','quality':'Public map geometry with illustrative vegetation and storefront detailing; not surveyed or photogrammetric'}
assembly.GetRootLayer().Save()
report={'version':2,'counts':counts,'scene':'scene/college_park_realistic.usda','baseSceneUnmodified':True,'limitations':['All tree placements and species illustrative, not surveyed.','Storefront windows, doors, awnings, signs, and furniture are generic visual approximations.','Generic shop-category signs do not identify actual tenants.','Vehicles static and schematic, not live traffic.','Original estimated heights and flat-terrain limitations still apply.'],'referenceSources':['https://www.orlando.gov/files/sharedassets/public/v/1/documents/city-and-district-plans/edgewater_support_document_v1-4.pdf','https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project'],'textures':'Original procedural texture assets created locally; no downloaded imagery.'}
(ROOT/'data'/'detail_manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
