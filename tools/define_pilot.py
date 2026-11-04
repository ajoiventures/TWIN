"""Freeze a bounded review area using named official street intersections.

The 60 m context buffer is an extraction rule, never a right-of-way boundary.
"""
from pathlib import Path
import sys,json,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from shapely.geometry import shape,mapping,box
from shapely.ops import unary_union,transform
from pyproj import Transformer
from data_pipeline import atomic_json

def select_intersection(edge,cross,choice):
    result=edge.intersection(cross)
    points=[result] if result.geom_type=='Point' else list(result.geoms) if result.geom_type=='MultiPoint' else []
    if not points:raise ValueError('No unambiguous point intersection')
    return sorted(points,key=lambda p:p.y)[0 if choice=='south' else -1],len(points)

def build():
    active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'));folder=ROOT/active['relative_path']
    streets=json.loads((folder/'streets.json').read_text(encoding='utf-8'))['features'];parcels=json.loads((folder/'parcels.json').read_text(encoding='utf-8'))['features'];buildings=json.loads((folder/'buildings.json').read_text(encoding='utf-8'))
    named=lambda name:unary_union([shape(f['geometry']) for f in streets if f['properties']['FullStreetName']==name])
    edge=named('EDGEWATER DR');south,_=select_intersection(edge,named('W PRINCETON ST'),'south');north,count=select_intersection(edge,named('W SMITH ST'),'south')
    clipped=edge.intersection(box(-81.398,south.y,-81.379,north.y));to_m=Transformer.from_crs(4326,32617,always_xy=True).transform;to_ll=Transformer.from_crs(32617,4326,always_xy=True).transform
    route=transform(to_m,clipped);context=route.buffer(60);extent=transform(to_ll,context)
    selected=[f for f in parcels if shape(f['geometry']).intersects(extent)];pins={f['properties']['parcel_id'] for f in selected}
    selected_buildings=[b for b in buildings if b.get('parcel_id') in pins]
    ids=[f['properties']['OBJECTID'] for f in streets if f['properties']['FullStreetName']=='EDGEWATER DR' and shape(f['geometry']).intersection(clipped).length>1e-7]
    data={'pilot_id':'edgewater-princeton-smith-south-v1','name':'Edgewater Drive: W Princeton Street to southern W Smith Street junction','source_snapshot':active['snapshot'],'configured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reference_date':'2026-10-28','reference_date_meaning':'model review baseline date; not assertion of current surveyed conditions','endpoints':[{'street':'W PRINCETON ST','coordinates':list(south.coords)[0]},{'street':'W SMITH ST','choice':'southern intersection','source_intersection_count':count,'coordinates':list(north.coords)[0]}],'city_centerline_object_ids':ids,'centerline':mapping(clipped),'centerline_length_m':round(route.length,2),'context_buffer_m':60,'context_geometry':mapping(extent),'context_role':'review extraction only; not surveyed ROW, district boundary or sidewalk edge','parcel_feature_ids':[f['properties']['id'] for f in selected],'parcel_ids':sorted(pins),'building_ids':[b['id'] for b in selected_buildings],'building_match_methods':{name:sum(b['match_method']==name for b in selected_buildings) for name in sorted({b['match_method'] for b in selected_buildings})},'limitations':['Official centerline intersection defines endpoints only; street/sidewalk widths remain unverified.','Cross-street junction geometry can be staggered; southern Smith junction explicitly selected.','Parcel context includes adjacent properties beyond immediate storefront frontage.']}
    atomic_json(ROOT/'data/processed/pilot.json',data);print(json.dumps({k:v for k,v in data.items() if k not in ['centerline','context_geometry','parcel_ids','parcel_feature_ids','building_ids']},indent=2));return data

if __name__=='__main__':build()
