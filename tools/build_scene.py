"""Download real map geometry and build the College Park prototype (meters, Z up)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import json, math, urllib.request, urllib.parse, datetime, time
from pyproj import Transformer
from shapely.geometry import shape, Polygon, LineString, box
from shapely.ops import transform, unary_union, triangulate
from pxr import Usd, UsdGeom, UsdLux, UsdShade, Sdf, Gf

BBOX = [-81.398, 28.5605, -81.379, 28.5845]
ORIGIN = [-81.389, 28.572]
DATA = ROOT / 'data'
DATA.mkdir(parents=True,exist_ok=True)
(ROOT/'scene').mkdir(parents=True,exist_ok=True)
SERVICE = 'https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28'

def get_json(url, params=None):
    if params: url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'CollegeParkTwinPrototype/0.1 (public map geometry research)'})
    with urllib.request.urlopen(req, timeout=180) as response: result = json.load(response)
    if 'error' in result: raise RuntimeError(result['error'])
    return result

def download():
    path = DATA / 'buildings.geojson'
    if not path.exists():
        params = dict(f='json', where='1=1', geometry=','.join(map(str,BBOX)), geometryType='esriGeometryEnvelope', inSR=4326, spatialRel='esriSpatialRelIntersects', returnIdsOnly='true')
        ids = get_json(SERVICE+'/query', params)['objectIds']
        features = []
        print('Fetching',len(ids),'building subareas',flush=True)
        for i in range(0,len(ids),50):
            cache=DATA/f'county_batch_{i:05d}.json'
            if cache.exists():page=json.loads(cache.read_text(encoding='utf-8'))
            else:
                page = get_json(SERVICE+'/query', dict(f='geojson',objectIds=','.join(map(str,ids[i:i+50])),outFields='OBJECTID,SUBTYPE,TYPE_CODE,PID,BLDG_NUM,FLOOR_NUM,SUB_DESC,BLDG_TYPE',outSR=4326,returnGeometry='true'))
                cache.write_text(json.dumps(page))
            features.extend(page['features'])
            print('Buildings:',len(features),'/',len(ids),flush=True)
        path.write_text(json.dumps(dict(type='FeatureCollection',features=features)),encoding='utf-8')
        print('Downloaded',len(features),'county building polygons',flush=True)
    path = DATA / 'openstreetmap.json'
    if not path.exists():
        w,s,e,n = BBOX
        query = f'[out:json][timeout:120];(way[highway]({s},{w},{n},{e});way[natural=water]({s},{w},{n},{e});way[waterway]({s},{w},{n},{e});way[leisure=park]({s},{w},{n},{e}););out geom;'
        failures=[]
        for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
            try:
                osm = get_json(endpoint, {'data':query})
                if osm.get('remark'): raise RuntimeError(osm['remark'])
                path.write_text(json.dumps(osm),encoding='utf-8'); break
            except Exception as exc: failures.append(str(exc))
        else: raise RuntimeError(f'OSM download failed: {failures}')
        print('Downloaded',len(osm['elements']),'OSM ways',flush=True)

download()
projection = Transformer.from_crs(4326,32617,always_xy=True)
ox,oy = projection.transform(*ORIGIN)
def project(x,y,z=None):
    xx,yy=projection.transform(x,y)
    return xx-ox,yy-oy
def local_geom(g): return transform(project,g)
boundary = local_geom(box(*BBOX))
stage = Usd.Stage.CreateNew(str(ROOT/'scene'/'college_park.usda'))
UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage,1)
world=UsdGeom.Xform.Define(stage,'/World');stage.SetDefaultPrim(world.GetPrim())
stage.GetRootLayer().customLayerData = {'project':'College Park, Orlando — Edgewater corridor prototype','originLongitude':ORIGIN[0],'originLatitude':ORIGIN[1],'projectedCRS':'EPSG:32617; local origin subtracted','verticalDatum':'Flat prototype ground at z=0; no surveyed elevations','attribution':'Buildings: Orange County Property Appraiser. Streets/water/parks: OpenStreetMap contributors, ODbL.','limitations':'Estimated heights, flat terrain, no live feeds. Map coverage is a rectangle, not an official district boundary.'}
materials={}
def material(name,color,roughness=.85,metallic=0):
    mat=UsdShade.Material.Define(stage,'/World/Materials/'+name)
    shader=UsdShade.Shader.Define(stage,mat.GetPath().AppendChild('Surface'));shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(metallic)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    materials[name]=mat
material('Ground',(.32,.40,.30));material('Park',(.20,.35,.18));material('Water',(.10,.28,.34),.25)
material('Road',(.16,.18,.20));material('Edgewater',(.22,.25,.29));material('Sidewalk',(.58,.56,.50))
material('Residential',(.72,.68,.57));material('Commercial',(.64,.72,.74));material('Roof',(.37,.40,.42))
material('Marking',(.86,.72,.25));material('Backdrop',(.18,.24,.21))

counts={'buildingMeshes':0,'roadSegments':0,'parks':0,'waterBodies':0}
def polys(geom):
    if geom.is_empty:return []
    if geom.geom_type=='Polygon':return [geom]
    if hasattr(geom,'geoms'):return [p for g in geom.geoms for p in polys(g)]
    return []
def mesh(path,geom,z,mat,height=0):
    points=[];indices=[];faces=[]
    for poly in polys(geom):
        for triangle in triangulate(poly):
            if not poly.covers(triangle):continue
            coords=list(triangle.exterior.coords)[:3]
            # Positive normal for top faces.
            if (coords[1][0]-coords[0][0])*(coords[2][1]-coords[0][1])-(coords[1][1]-coords[0][1])*(coords[2][0]-coords[0][0])<0:coords.reverse()
            base=len(points);points.extend([(x,y,z+height) for x,y in coords]);indices.extend([base,base+1,base+2]);faces.append(3)
        if height:
            for ring in [poly.exterior,*poly.interiors]:
                coords=list(ring.coords)
                for a,b in zip(coords,coords[1:]):
                    base=len(points);points.extend([(a[0],a[1],z),(b[0],b[1],z),(b[0],b[1],z+height),(a[0],a[1],z+height)])
                    indices.extend(range(base,base+4));faces.append(4)
    if not points:return None
    m=UsdGeom.Mesh.Define(stage,path);m.CreatePointsAttr(points);m.CreateFaceVertexCountsAttr(faces);m.CreateFaceVertexIndicesAttr(indices)
    m.CreateSubdivisionSchemeAttr('none');m.CreateDoubleSidedAttr(True)
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(materials[mat])
    m.CreateExtentAttr([Gf.Vec3f(*(min(p[i] for p in points) for i in range(3))),Gf.Vec3f(*(max(p[i] for p in points) for i in range(3)))])
    return m.GetPrim()

mesh('/World/Context/SurroundingGround',boundary.buffer(600),-.08,'Backdrop')
mesh('/World/Ground',boundary,0,'Ground')
osm=json.loads((DATA/'openstreetmap.json').read_text(encoding='utf-8'))
roads=[];named_roads=set()
for way in osm['elements']:
    coords=[project(p['lon'],p['lat']) for p in way.get('geometry',[]) if 'lat' in p]
    if len(coords)<2:continue
    tags=way.get('tags',{});wid=way['id']
    if tags.get('natural')=='water' and len(coords)>=4 and coords[0]==coords[-1]:
        geom=Polygon(coords).buffer(0).intersection(boundary)
        if mesh(f'/World/Water/OSM_{wid}',geom,.025,'Water'):counts['waterBodies']+=1
    if tags.get('leisure')=='park' and len(coords)>=4 and coords[0]==coords[-1]:
        geom=Polygon(coords).buffer(0).intersection(boundary)
        if mesh(f'/World/Parks/OSM_{wid}',geom,.015,'Park'):counts['parks']+=1
    kind=tags.get('highway')
    if not kind or kind in ['proposed','construction']:continue
    width={'motorway':18,'trunk':15,'primary':13,'secondary':11,'tertiary':10,'residential':7,'service':4,'footway':1.8,'path':1.6,'cycleway':2.5,'steps':1.5}.get(kind,7)
    try: width=float(tags.get('width',width))
    except (ValueError,TypeError):pass
    line=LineString(coords);geom=line.buffer(width/2,cap_style=2,join_style=2).intersection(boundary)
    edge='Edgewater' in tags.get('name','')
    if kind not in ['footway','path','cycleway','steps','service','motorway','motorway_link']:
        mesh(f'/World/Streets/Shoulders_{wid}',line.buffer(width/2+2,cap_style=2,join_style=2).intersection(boundary),.035,'Sidewalk')
    prim=mesh(f'/World/Streets/Road_{wid}',geom,.065,'Edgewater' if edge else 'Road')
    if prim:
        prim.SetCustomDataByKey('source','OpenStreetMap');prim.SetCustomDataByKey('osmId',str(wid));prim.SetCustomDataByKey('roadName',tags.get('name','Unnamed'));counts['roadSegments']+=1
        roads.append(geom)
    if edge:mesh(f'/World/Streets/Centerline_{wid}',line.buffer(.09,cap_style=2).intersection(boundary),.07,'Marking')
    if tags.get('name'):named_roads.add(tags['name'])

# County polygons can be individual property-appraiser subareas. Dissolve by parcel + building number.
features=json.loads((DATA/'buildings.geojson').read_text(encoding='utf-8'))['features']
groups={}
for feature in features:
    prop=feature['properties'];geo=local_geom(shape(feature['geometry'])).buffer(0).intersection(boundary)
    if geo.is_empty:continue
    key=(prop.get('PID') or str(prop.get('OBJECTID')),prop.get('BLDG_NUM') or '0')
    groups.setdefault(key,[]).append((geo,prop))
for i,(key,parts) in enumerate(groups.items()):
    geom=unary_union([p[0] for p in parts]);prop=parts[0][1]
    commercial=any(p[1].get('SUBTYPE')==1 for p in parts)
    height=6.5 if commercial else 4.2
    prim=mesh(f'/World/Buildings/Building_{i:04d}',geom,.10,'Commercial' if commercial else 'Residential',height)
    if not prim:continue
    prim.SetCustomData({'source':'Orange County Property Appraiser / Building_FootPrints','parcelId':str(key[0]),'buildingNumber':str(key[1]),'heightMeters':height,'heightQuality':'ESTIMATED — not surveyed','classification':'Commercial' if commercial else 'Residential','sourceObjectIds':','.join(str(p[1].get('OBJECTID')) for p in parts)})
    mesh(f'/World/Roofs/Roof_{i:04d}',geom,.10+height+.02,'Roof')
    counts['buildingMeshes']+=1

sun=UsdLux.DistantLight.Define(stage,'/World/Lighting/Sun');sun.CreateIntensityAttr(1500);sun.CreateAngleAttr(.7);UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(25,-30,-25))
sky=UsdLux.DomeLight.Define(stage,'/World/Lighting/Sky');sky.CreateIntensityAttr(200);sky.CreateColorAttr(Gf.Vec3f(.80,.88,1))
def camera(name,eye,target,focal=35):
    cam=UsdGeom.Camera.Define(stage,'/World/Cameras/'+name);cam.CreateFocalLengthAttr(focal);cam.CreateClippingRangeAttr(Gf.Vec2f(.2,20000))
    matrix=Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse()
    UsdGeom.Xformable(cam).AddTransformOp().Set(matrix)
camera('DistrictOverview',(1700,-2350,2200),(0,100,0),35)
camera('EdgewaterCorridor',(470,-820,750),(-60,230,0),32)
camera('StreetScale',(80,-100,70),(-70,130,0),28)
stage.GetRootLayer().Save()
manifest={'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boundsWGS84':BBOX,'localOriginWGS84':ORIGIN,'coordinateSystem':'UTM 17N EPSG:32617, local origin, Z up, meters','counts':counts,'sourceBuildingFeatures':len(features),'streetNames':sorted(named_roads),'sources':[{'name':'Orange County Property Appraiser building footprints','url':SERVICE,'cache':'data/buildings.geojson'},{'name':'OpenStreetMap contributors','url':'https://www.openstreetmap.org/copyright','license':'ODbL','cache':'data/openstreetmap.json'}],'limitations':['Prototype flat ground, not surveyed terrain.','All building heights estimated: residential 4.2 m, commercial 6.5 m.','Simplified flat roofs; no facades or live data.','Road widths inferred from road type unless OSM width exists. Shoulders are schematic.','Rectangular study area; not an official College Park boundary.']}
(ROOT/'data'/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(counts),flush=True)
print('Saved',ROOT/'scene'/'college_park.usda',flush=True)
