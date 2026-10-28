"""City reference outlines and Main Street view in the existing local USD frame."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Gf
from pyproj import Transformer
from shapely.geometry import shape,LineString
from shapely.ops import transform
from constrain_scene import ground_footprint

def compose():
    collection=json.loads((ROOT/'data/processed/study_boundaries.geojson').read_text(encoding='utf-8'));source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'));ground=ground_footprint(source)
    projection=Transformer.from_crs(4326,32617,always_xy=True);origin=projection.transform(-81.389,28.572)
    def xy(x,y,z=None):
        a,b=projection.transform(x,y)
        try:return [v-origin[0] for v in a],[v-origin[1] for v in b]
        except TypeError:return a-origin[0],b-origin[1]
    stage=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(stage,'/World/StudyBoundaries')
    for feature in collection['features']:
        geometry=transform(xy,shape(feature['geometry']));lines=geometry.boundary.intersection(ground);lines=[lines] if lines.geom_type=='LineString' else list(lines.geoms) if hasattr(lines,'geoms') else []
        pts=[];counts=[]
        for line in lines:
            if line.geom_type!='LineString':continue
            coords=list(line.coords);counts.append(len(coords));pts.extend((float(x),float(y),.22) for x,y in coords)
        name='MainStreet' if feature['id']=='main_street' else 'Neighborhood';curve=UsdGeom.BasisCurves.Define(stage,'/World/StudyBoundaries/'+name);curve.CreateTypeAttr('linear');curve.CreateCurveVertexCountsAttr(counts);curve.CreatePointsAttr(pts);curve.CreateWidthsAttr([1.2 if name=='MainStreet' else .6]);curve.SetWidthsInterpolation('constant');curve.CreateDisplayColorAttr([Gf.Vec3f(1,.66,.12) if name=='MainStreet' else Gf.Vec3f(.2,.75,.35)])
        curve.GetPrim().SetCustomDataByKey('reference',{'source':feature['properties']['source_url'],'scope':feature['id'],'display':'official boundary line clipped to current ground coverage; no invented closing edge'})
        if name=='Neighborhood':curve.CreateVisibilityAttr('invisible')
        if name=='MainStreet':
            center=geometry.centroid;cam=UsdGeom.Camera.Define(stage,'/World/Cameras/MainStreetOverview');cam.CreateFocalLengthAttr(35);cam.CreateClippingRangeAttr(Gf.Vec2f(.2,20000));matrix=Gf.Matrix4d().SetLookAt(Gf.Vec3d(center.x+850,center.y-1700,1900),Gf.Vec3d(center.x,center.y,0),Gf.Vec3d(0,0,1)).GetInverse();UsdGeom.Xformable(cam).AddTransformOp().Set(matrix)
    stage.GetRootLayer().customLayerData={'primaryFocus':'College Park Main Street','context':'College Park neighborhood','quality':'City reference boundaries; see study_scope_quality.json for verified extraction coverage'};stage.GetRootLayer().Export(str(ROOT/'scene/study_scope.usda'))
    print('Added separate City Main Street/neighborhood outlines and MainStreetOverview camera')

if __name__=='__main__':compose()
