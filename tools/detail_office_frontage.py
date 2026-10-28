"""Original photo-interpreted public frontage proposal; never activates scene layers."""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build(root=ROOT):
    manifest=json.loads((root/'data/heights/landmarks/proposal_manifest.json').read_text())
    source_path=root/'scene/landmark_building_proposal.usda'
    if sha(source_path)!=manifest['layer_sha256']:raise ValueError('Source proposal hash changed')
    office=next(s for s in manifest['sites'] if s['site_id']=='andersen_office_1615')
    source=Usd.Stage.Open(str(source_path));stage=Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    world=UsdGeom.Xform.Define(stage,'/World');stage.SetDefaultPrim(world.GetPrim())
    base='/World/OfficeFrontageProposal'
    UsdGeom.Xform.Define(stage,base)
    def material(name,color,rough=.8):
        m=UsdShade.Material.Define(stage,base+'/Materials/'+name)
        s=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'));s.CreateIdAttr('UsdPreviewSurface')
        s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough)
        m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface');return m
    brick=material('Brick',(.39,.115,.065));white=material('PaintedTrim',(.84,.83,.74))
    glass=material('Glazing',(.085,.16,.18),.22);dark=material('ClockAndRecess',(.025,.035,.035))
    def bind(obj,mat):UsdShade.MaterialBindingAPI.Apply(obj.GetPrim()).Bind(mat);return obj
    def box(name,center,size,mat):
        b=UsdGeom.Cube.Define(stage,base+'/'+name);b.CreateSizeAttr(1)
        b.AddTranslateOp().Set(Gf.Vec3d(*center));b.AddScaleOp().Set(Gf.Vec3f(*size));return bind(b,mat)
    points=[];faces=[];roofpolys=[];frontfaces=[]
    for component in office['components']:
        m=UsdGeom.Mesh(source.GetPrimAtPath(component['prim_path']))
        pts=m.GetPointsAttr().Get();ids=m.GetFaceVertexIndicesAttr().Get();offset=0
        for n in m.GetFaceVertexCountsAttr().Get():
            q=[Gf.Vec3d(pts[i]) for i in ids[offset:offset+n]];offset+=n
            projected=Polygon([(v[0],v[1]) for v in q])
            if projected.is_valid and projected.area>.001:roofpolys.append(projected)
            normal=Gf.Cross(q[1]-q[0],q[2]-q[0]).GetNormalized()
            if normal[0]<-.7 and abs(normal[2])<.15:
                start=len(points);points.extend([(v[0]-.025,v[1],v[2]) for v in q]);faces.append(list(range(start,start+n)));frontfaces.append(q)
    footprint=unary_union(roofpolys)
    xmin,ymin,xmax,ymax=footprint.bounds
    if not frontfaces:raise ValueError('No west-facing wall faces in proposal')
    skin=UsdGeom.Mesh.Define(stage,base+'/BrickFrontSkin');skin.CreatePointsAttr(points)
    skin.CreateFaceVertexCountsAttr([len(f) for f in faces]);skin.CreateFaceVertexIndicesAttr([i for f in faces for i in f]);skin.CreateSubdivisionSchemeAttr('none');bind(skin,brick)
    def front(y):
        hit=footprint.intersection(LineString([(xmin-5,y),(xmax+5,y)]))
        if hit.is_empty:raise ValueError('Frontage station outside actual footprint')
        return hit.bounds[0]
    center=(ymin+ymax)/2
    window_count=0;fit_errors=[]
    # Individual bays follow west envelope, including its genuine recesses.
    for index in range(17):
        y=ymin+2.5+index*(ymax-ymin-5)/16
        if abs(y-center)<5.4:continue
        xs=[front(y+dy) for dy in (-.85,0,.85)]
        if max(xs)-min(xs)>.2:continue
        x=min(xs)-.13
        for floor,z in enumerate((2.0,5.6)):
            name=f'Windows/Bay{index}_Floor{floor}'
            box(name+'/Frame',(x,y,z),(.16,1.65,2.0),white)
            box(name+'/Pane',(x-.10,y,z),(.08,1.42,1.78),glass)
            box(name+'/Mullion',(x-.16,y,z),(.05,.055,1.8),white)
            for dz in (-.45,.15):box(name+f'/Rail{int((dz+1)*100)}',(x-.16,y,z+dz),(.05,1.42,.045),white)
            window_count+=1
        if abs(x-front(y))>.3:fit_errors.append(index)
    # Four-column portico inferred from public-front photograph, not survey dimensions.
    fx=front(center);width=9.2;column_x=fx-1.05
    box('Entrance/GlazedRecess',(fx-.08,center,4.0),(.12,8.9,7.8),glass)
    for dy in (-3.65,-2.15,2.15,3.65):
        name=f'Entrance/Column{int((dy+5)*100)}'
        column=UsdGeom.Cylinder.Define(stage,base+'/'+name+'/Shaft')
        column.CreateRadiusAttr(.19);column.CreateHeightAttr(6.65)
        column.AddTranslateOp().Set(Gf.Vec3d(column_x,center+dy,3.75));bind(column,white)
        box(name+'/Base',(column_x,center+dy,.42),(.6,.6,.35),white)
        box(name+'/Capital',(column_x,center+dy,7.17),(.62,.62,.28),white)
    box('Entrance/Entablature',(column_x,center,7.6),(1.55,width,.65),white)
    for dy in (-3,-1.5,0,1.5,3):box('Entrance/GlassVertical'+str(int((dy+4)*100)),(fx-.18,center+dy,4),(.06,.06,7.3),dark)
    box('Entrance/GlassFloorRail',(fx-.18,center,3.85),(.06,8.8,.13),dark)
    # Triangular pediment in the Y/Z plane; real geometry, no photograph/logo texture.
    p=[]
    for x in (column_x-.83,column_x+.55):
        p.extend([(x,center-width/2,7.95),(x,center+width/2,7.95),(x,center,10.45)])
    ped=UsdGeom.Mesh.Define(stage,base+'/Entrance/Pediment')
    ped.CreatePointsAttr(p);ped.CreateFaceVertexCountsAttr([3,3,4,4,4])
    ped.CreateFaceVertexIndicesAttr([0,2,1,3,4,5,0,1,4,3,1,2,5,4,2,0,3,5]);ped.CreateSubdivisionSchemeAttr('none');bind(ped,white)
    clock=UsdGeom.Cylinder.Define(stage,base+'/Entrance/ClockFace');clock.CreateAxisAttr('X')
    clock.CreateRadiusAttr(.38);clock.CreateHeightAttr(.055);clock.AddTranslateOp().Set(Gf.Vec3d(column_x-.88,center,8.85));bind(clock,dark)
    face=UsdGeom.Cylinder.Define(stage,base+'/Entrance/ClockDial');face.CreateAxisAttr('X')
    face.CreateRadiusAttr(.32);face.CreateHeightAttr(.06);face.AddTranslateOp().Set(Gf.Vec3d(column_x-.92,center,8.85));bind(face,white)
    box('Entrance/ClockHandVertical',(column_x-.97,center,8.98),(.03,.035,.28),dark)
    box('Entrance/ClockHandSide',(column_x-.97,center+.12,8.85),(.03,.25,.035),dark)
    if fit_errors:raise ValueError('Window envelope checks failed')
    photos={f'1615_exterior_page_{n}.png':sha(root/f'data/imagery/landmark_reference/1615_exterior_page_{n}.png') for n in (3,4,9)}
    stage.GetRootLayer().customLayerData={
        'purpose':'Inactive public-front architectural proposal; photo-interpreted approximate dimensions and placement.',
        'photoDate':'Unknown; broker brochure exterior pages3/9 front, page4 rear used for contextual material review only.',
        'sourceSnapshot':manifest['source_snapshot'],'geometryProposalSha256':manifest['layer_sha256'],
        'photoHashesJson':json.dumps(photos,sort_keys=True),
        'sourcePrim':office['components'][0]['prim_path'],
        'limitations':'No measured facade dimensions; window count/spacing/entrance alignment interpreted. No speculative rear details. Roof dormers/chimneys remain source roof proposal responsibility. No textures/logos/source pixels.',
        'activation':'Parent review required. Detail-only; no sublayers and no source geometry changed.',
        'fitReportJson':json.dumps({'front_axis':'-X','actual_footprint_bounds':list(footprint.bounds),'center_y':center,'portico_wall_x':fx,'window_count':window_count,'west_wall_faces':len(faces),'window_max_wall_offset_m':.13,'portico_projection_m':1.88,'fit_errors':fit_errors})}
    output=root/'scene/office_frontage_proposal.usda';stage.GetRootLayer().Export(str(output))
    return {'output':str(output),'sha256':sha(output),'window_count':window_count,'west_wall_faces':len(faces),'footprint_bounds':list(footprint.bounds),'source_sha256':manifest['layer_sha256'],'activated':False}

if __name__=='__main__':print(json.dumps(build(),indent=2))
