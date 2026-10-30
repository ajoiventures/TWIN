"""Prepare isolated tree/car visual candidates; never activate or relocate objects.

Contract (#9/#10): reuse original TWIN procedural assets; improve crown density,
leaf shading and sedan body/window geometry. Outputs live in a new diagnostic
directory and scene review wrappers. Existing source/manual files are hash-guarded.
Run: python tools/build_environment_candidate.py --output data/diagnostics/environment_v3
No downloads, third-party imagery, parking validation or traffic claims.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import argparse, hashlib, json, math, random
from pathlib import Path
import build_detailed_assets as base
from pxr import Usd, UsdGeom, UsdShade, UsdLux, Sdf, Gf
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, Point
from shapely.ops import triangulate

ROOT=base.ROOT
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path, anchor): return os.path.relpath(path,anchor).replace('\\','/')

def leaf_texture(out):
    """Original painted foliage: individual tapered leaves, tonal edge and midrib."""
    im=Image.new('RGBA',(512,512)); d=ImageDraw.Draw(im); rng=random.Random(903)
    for _ in range(50):
        cx,cy=rng.uniform(48,464),rng.uniform(48,464); angle=rng.random()*math.tau
        length=rng.uniform(20,34); width=length*rng.uniform(.29,.40)
        green=rng.randint(68,130)
        def shape(scale):
            return [(cx+math.cos(angle)*math.cos(t)*length*scale-math.sin(angle)*math.sin(t)*width*scale,
                     cy+math.sin(angle)*math.cos(t)*length*scale+math.cos(angle)*math.sin(t)*width*scale)
                    for t in [i*math.tau/32 for i in range(32)]]
        d.polygon(shape(1),fill=(int(green*.45),green,int(green*.29),255))
        d.polygon(shape(.75),fill=(int(green*.51),min(150,green+12),int(green*.31),255))
        d.line([(cx-math.cos(angle)*length*.85,cy-math.sin(angle)*length*.85),
                (cx+math.cos(angle)*length*.85,cy+math.sin(angle)*length*.85)],fill=(76,105,39,255),width=1)
    im.save(out/'textures/leaf_cluster.png')

def refine_tree(path,kind):
    stage=Usd.Stage.Open(str(path)); variants=stage.GetDefaultPrim().GetVariantSet('detail')
    # Keep alpha-cutout batches and existing branch hierarchy; offset second crown
    # layer into the sparse lobe interiors instead of enlarging surveyed envelopes.
    for lod in ('high','medium','low'):
        variants.SetVariantSelection(lod)
        with variants.GetVariantEditContext():
            if kind!='palm':
                for i in range(3):
                    m=UsdGeom.Mesh(stage.GetPrimAtPath('/Asset/Geometry/FoliageTone'+str(i)))
                    points=list(m.GetPointsAttr().Get()); counts=list(m.GetFaceVertexCountsAttr().Get()); indices=list(m.GetFaceVertexIndicesAttr().Get())
                    st=UsdGeom.PrimvarsAPI(m).GetPrimvar('st'); uv=list(st.Get())
                    # One added card per original, rotated about its own center and
                    # moved inward; leaves stay batched (no per-leaf prim overhead).
                    extra=[]
                    for start in range(0,len(points),4):
                        center=sum((Gf.Vec3f(p) for p in points[start:start+4]),Gf.Vec3f(0))/4
                        for p in points[start:start+4]:
                            delta=Gf.Vec3f(p)-center
                            extra.append(center+Gf.Vec3f(-delta[1],delta[0],delta[2])*.82+Gf.Vec3f(-center[0]*.05,-center[1]*.05,-.22))
                    offset=len(points); m.GetPointsAttr().Set(points+extra);m.GetFaceVertexCountsAttr().Set(counts+counts);m.GetFaceVertexIndicesAttr().Set(indices+[n+offset for n in indices]);st.Set(uv+uv)
            else:
                foliage=stage.GetPrimAtPath('/Asset/Materials/PalmLeaf/Surface')
                UsdShade.Shader(foliage).GetInput('diffuseColor').Set(Gf.Vec3f(.075,.20,.035))
    variants.SetVariantSelection('medium');stage.GetRootLayer().Save()

def refine_car(path):
    """Explicit sedan panels and wheel arches replace the old rounded loft shell."""
    stage=Usd.Stage.Open(str(path)); mats={n:UsdShade.Material(stage.GetPrimAtPath('/Asset/Materials/'+n)) for n in ('Paint','Glass','Rubber','Alloy')}
    for name in ('Body','Cabin','Roof'): stage.RemovePrim('/Asset/'+name)
    profile=Polygon([(-2.23,.34),(2.23,.34),(2.23,.68),(2.03,.82),(1.05,.94),(-1.18,.94),(-2.05,.80),(-2.23,.64)])
    for x in (-1.4,1.4): profile=profile.difference(Point(x,.35).buffer(.386,quad_segs=16))
    pts=[];fs=[];lookup={}
    def vertex(x,side,z):
        # Taper both ends and roll upper shoulder inward without altering wheelbase.
        width=.91-.19*max(0,(abs(x)-1.65)/.58)-.035*max(0,(z-.76)/.18)
        key=(round(x,8),side,round(z,8))
        if key not in lookup:lookup[key]=len(pts);pts.append((x,side*width,z))
        return lookup[key]
    for side in (-1,1):
        for triangle in triangulate(profile):
            if not profile.covers(triangle): continue
            ids=[vertex(x,side,z) for x,z in list(triangle.exterior.coords)[:-1]]
            fs.append(ids if side<0 else ids[::-1])
    ring=list(profile.exterior.coords)
    for a,b in zip(ring,ring[1:]):
        fs.append([vertex(*a[:1],-1,a[1]),vertex(*b[:1],-1,b[1]),vertex(*b[:1],1,b[1]),vertex(*a[:1],1,a[1])])
    base.mesh(stage,'/Asset/Body',pts,fs,mats['Paint'],smooth=True)
    base.box(stage,'/Asset/Roof',(-.08,0,1.46),(1.02,1.34,.065),mats['Paint'])
    # Side panes are separated by a genuine B-pillar and dark rubber seals.
    for side in (-1,1):
        for label,corners in [('Rear',[(-1.12,.98),(-.64,1.43),(-.13,1.43),(-.13,.98)]),('Front',[(-.04,.98),(-.04,1.43),(.43,1.43),(1.08,.98)])]:
            p=[(x,side*(.855-(z-.98)*.43),z) for x,z in corners]
            base.mesh(stage,f'/Asset/{label}Window_{side}',p,[[0,1,2,3]],mats['Glass'],smooth=False)
            base.tube(stage,f'/Asset/{label}WindowSeal_{side}',p+[p[0]],[.018]*5,mats['Rubber'],6)
        for label,a,b in [('A',(.43,1.46),(1.13,.96)),('B',(-.085,1.46),(-.085,.96)),('C',(-.66,1.46),(-1.17,.96))]:
            base.tube(stage,f'/Asset/{label}Pillar_{side}',[(a[0],side*.66,a[1]),(b[0],side*.86,b[1])],[.035,.043],mats['Paint'],8)
    for label,pts in [('Windshield',[(.46,-.66,1.43),(.46,.66,1.43),(1.10,.85,.98),(1.10,-.85,.98)]),('RearGlass',[(-1.14,-.85,.98),(-1.14,.85,.98),(-.67,.66,1.43),(-.67,-.66,1.43)])]:
        base.mesh(stage,'/Asset/'+label,pts,[[0,1,2,3]],mats['Glass'],smooth=False)
    for j in range(7):base.box(stage,'/Asset/GrilleSlat_'+str(j),(2.25,(j-3)*.08,.61),(.02,.025,.11),mats['Alloy'])
    # Lamps sit on the actual end panels, not on the removed loft's upper corners.
    for side in (-1,1):
        for label,x,matname in [('Headlight',2.232,'Headlight'),('Taillight',-2.232,'Taillight')]:
            path=f'/Asset/{label}_{side}'.replace('-','n');stage.RemovePrim(path)
            mat=UsdShade.Material(stage.GetPrimAtPath('/Asset/Materials/'+matname))
            base.box(stage,path,(x,side*.48,.66),(.025,.30,.10),mat)
        for p in stage.GetDefaultPrim().GetChildren():
            if p.GetName().startswith('Handle_'+str(side).replace('-','n')):
                xf=UsdGeom.Xformable(p)
                # Handles are mesh-authored in the original helper; translate only Z.
                xf.AddTranslateOp(opSuffix='panelFit').Set(Gf.Vec3d(0,-side*.07,-.10))
    # Existing vehicle has oversized handles outside its new side body.
    for p in list(stage.GetDefaultPrim().GetChildren()):
        if p.GetName().startswith('WindowPillar'): stage.RemovePrim(p.GetPath())
    stage.GetDefaultPrim().SetCustomDataByKey('quality','Original procedural static sedan; model detail only; placement unverified')
    stage.GetRootLayer().Save()

def build(output):
    output=output.resolve()
    if output.exists(): raise ValueError('Use a new output directory; existing candidate preserved')
    if not output.is_relative_to(ROOT/'data/diagnostics'):raise ValueError('Candidate output must be under data/diagnostics')
    protected={str(p):sha(p) for folder in (ROOT/'scene',ROOT/'assets/generated') for p in folder.rglob('*') if p.is_file()}
    output.mkdir(parents=True);(output/'textures').mkdir();base.OUT=output
    leaf_texture(output)
    for kind,seed in [('oak_a',110),('oak_b',230),('palm',310)]: refine_tree(base.revised_tree(kind,seed),kind)
    base.car();refine_car(output/'sedan.usdc')
    source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'))
    candidate=Usd.Stage.CreateNew(str(output/'asset_candidate.usda'));inst=UsdGeom.PointInstancer.Define(candidate,'/World/Trees');targets=[]
    for i,kind in enumerate(('oak_a','oak_b','oak_a','oak_b','oak_a','oak_b','palm')):
        p=candidate.OverridePrim('/World/Trees/Detailed/Tree_'+str(i));p.GetReferences().SetReferences([Sdf.Reference(kind+'.usdc','/Asset')]);p.GetVariantSets().AddVariantSet('detail').SetVariantSelection('medium');targets.append(p.GetPath())
    inst.CreatePrototypesRel().SetTargets(targets);cars=[]
    for parent in source.GetPrimAtPath('/World/ParkedVehicles').GetChildren():
        old=parent.GetChild('DetailedSedan')
        if old:
            p=candidate.OverridePrim(old.GetPath());p.GetReferences().SetReferences([Sdf.Reference('sedan.usdc','/Asset')]);p.SetInstanceable(True);cars.append(str(old.GetPath()))
    candidate.GetRootLayer().customLayerData={'proposalOnly':True,'placementQuality':'Existing illustrative arrays/transforms retained; no parking, inventory or clearance acceptance'};candidate.GetRootLayer().Save()
    work=Sdf.Layer.CreateNew(str(output/'district_workview.usda'));work.subLayerPaths=['asset_candidate.usda',rel(ROOT/'scene/college_park_connected.usda',output)];work.Save()
    compare=Usd.Stage.CreateNew(str(output/'compare.usda'));UsdGeom.SetStageMetersPerUnit(compare,1);UsdGeom.SetStageUpAxis(compare,'Z')
    for side,x in [('Current',-8),('Candidate',8)]:
        for kind,y,target in [('oak_a',6,'/World/Trees/Detailed/Tree_0'),('palm',-6,'/World/Trees/Detailed/Tree_6'),('sedan',-15,cars[0])]:
            xf=UsdGeom.Xform.Define(compare,'/World/'+side+'/'+kind)
            xf.GetPrim().GetReferences().AddReference(rel(ROOT/'scene/college_park_connected.usda',output) if side=='Current' else kind+'.usdc',target if side=='Current' else '/Asset')
            xf.GetPrim().SetInstanceable(False);xf.SetXformOpOrder([],resetXformStack=True);xf.AddTranslateOp(opSuffix='review').Set(Gf.Vec3d(x,y,0))
    sun=UsdLux.DistantLight.Define(compare,'/World/Sun');sun.CreateIntensityAttr(2200);sun.CreateAngleAttr(.7);UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(25,-30,-30));UsdLux.DomeLight.Define(compare,'/World/Sky').CreateIntensityAttr(500)
    cam=UsdGeom.Camera.Define(compare,'/World/CompareCamera');cam.CreateFocalLengthAttr(35);cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(20.25);cam.CreateClippingRangeAttr(Gf.Vec2f(.1,1000));cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(32,-47,27),Gf.Vec3d(0,-3,4),Gf.Vec3d(0,0,1)).GetInverse())
    for name,eye,target in [('CarDetail',(14,-20,3),(8,-15,.8)),('TreeDetail',(19,-4,8),(8,6,5))]:
        c=UsdGeom.Camera.Define(compare,'/World/'+name);c.CreateFocalLengthAttr(45);c.CreateHorizontalApertureAttr(36);c.CreateVerticalApertureAttr(20.25);c.CreateClippingRangeAttr(Gf.Vec2f(.1,1000));c.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
    mat=base.material(compare,'CompareGround',(.26,.28,.25),.95);base.box(compare,'/World/Ground',(0,-5,-.12),(45,50,.2),mat);compare.GetRootLayer().Save()
    changed=[p for p,d in protected.items() if sha(p)!=d]
    if changed:raise ValueError('Protected inputs changed: '+str(changed))
    composed=Usd.Stage.Open(str(output/'district_workview.usda'))
    if composed.GetCompositionErrors():raise ValueError('Candidate has composition errors')
    for attr in ('positions','orientations','scales','protoIndices','invisibleIds'):
        a=source.GetPrimAtPath('/World/Trees').GetAttribute(attr).Get();b=composed.GetPrimAtPath('/World/Trees').GetAttribute(attr).Get()
        if a!=b:raise ValueError('Tree instance array changed: '+attr)
    for path in cars:
        if UsdGeom.Xformable(source.GetPrimAtPath(path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())!=UsdGeom.Xformable(composed.GetPrimAtPath(path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default()):raise ValueError('Car world transform changed: '+path)
    geometry={}
    for name in ('oak_a','oak_b','palm','sedan'):
        asset=Usd.Stage.Open(str(output/(name+'.usdc')));vertices=faces=0
        for p in asset.Traverse():
            if p.IsA(UsdGeom.Mesh):
                m=UsdGeom.Mesh(p);points=m.GetPointsAttr().Get();counts=m.GetFaceVertexCountsAttr().Get();ids=m.GetFaceVertexIndicesAttr().Get()
                if not all(math.isfinite(float(v)) for xyz in points for v in xyz):raise ValueError('Nonfinite geometry')
                if sum(counts)!=len(ids) or min(ids,default=0)<0 or max(ids,default=0)>=len(points):raise ValueError('Invalid mesh topology')
                vertices+=len(points);faces+=len(counts)
            for attr in p.GetAttributes():
                if attr.GetTypeName()==Sdf.ValueTypeNames.Asset:
                    value=attr.Get()
                    if value and value.path and not value.resolvedPath:raise ValueError('Unresolved asset: '+value.path)
        geometry[name]={'vertices':vertices,'faces':faces,'bytes':(output/(name+'.usdc')).stat().st_size}
    report={'proposal_only':True,'protected_files_unchanged':len(protected),'source_root_sha256':sha(ROOT/'scene/college_park_connected.usda'),'placement_quality':'illustrative; no new placement or clearance accuracy','tree_instances':len(UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees')).GetPositionsAttr().Get()),'car_instances':len(cars),'exact_instance_arrays_and_car_world_transforms':True,'prototype_geometry':geometry,'original_assets_only':True,'files':{p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()},'render_status':'not_run','camera':'/World/CompareCamera','detail_cameras':['/World/CarDetail','/World/TreeDetail']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();build(args.output)
