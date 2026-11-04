"""Compare rendered-road source centerlines with City references; no geometry writes."""
from pathlib import Path
import sys,json,math,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from shapely.geometry import shape,LineString,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
from data_pipeline import atomic_json

def distances(line,reference,spacing=2):
    parts=list(line.geoms) if hasattr(line,'geoms') else [line]
    values=[]
    for part in parts:
        if part.is_empty or part.length==0:continue
        n=max(1,math.ceil(part.length/spacing))
        values.extend(part.interpolate(i/n,normalized=True).distance(reference) for i in range(n+1))
    ordered=sorted(values)
    return {'samples':len(values),'spacing_max_m':spacing,'median_m':ordered[len(ordered)//2] if values else None,'p95_m':ordered[min(len(ordered)-1,math.ceil(.95*len(ordered))-1)] if values else None,'max_m':max(values) if values else None}

def build():
    active=json.loads((ROOT/'data/processed/active.json').read_text());folder=ROOT/active['relative_path']
    streets=json.loads((folder/'streets.json').read_text())['features']
    osm=json.loads((ROOT/'data/openstreetmap.json').read_text())['elements']
    project=Transformer.from_crs(4326,32617,always_xy=True).transform
    city=lambda name:unary_union([transform(project,shape(f['geometry'])) for f in streets if f['properties']['FullStreetName']==name])
    junction=city('EDGEWATER DR').intersection(city('W PRINCETON ST'))
    if junction.geom_type!='Point':raise ValueError('Princeton junction needs explicit review')
    area=junction.buffer(160)
    comparisons=[]
    for official,names in [('EDGEWATER DR',['Edgewater Drive']),('W PRINCETON ST',['West Princeton Street','Princeton Street'])]:
        reference=city(official).intersection(area);ways=[];lines=[]
        for way in osm:
            tags=way.get('tags',{})
            if tags.get('name') not in names or not tags.get('highway'):continue
            points=[project(p['lon'],p['lat']) for p in way.get('geometry',[]) if 'lat' in p]
            if len(points)<2:continue
            line=LineString(points).intersection(area)
            if line.is_empty:continue
            lines.append(line);kind=tags['highway'];fallback={'motorway':18,'trunk':15,'primary':13,'secondary':11,'tertiary':10,'residential':7,'service':4}.get(kind,7)
            try:width=float(tags.get('width',fallback));basis='OSM width tag' if 'width' in tags else 'highway-class fallback'
            except (ValueError,TypeError):width=fallback;basis='invalid width tag; fallback'
            ways.append({'osm_way':way['id'],'name':tags['name'],'highway':kind,'width_tag':tags.get('width'),'lanes_tag':tags.get('lanes'),'modeled_width_m':width,'width_basis':basis,'sidewalk_model':'uniform 2 m buffer outside road, unverified','lane_markings_model':'single centerline on Edgewater, no verified lane boundaries'})
        network=unary_union(lines)
        comparisons.append({'city_street':official,'osm_ways':ways,'city_length_within_review_m':reference.length,'city_to_osm':distances(reference,network) if lines else None,'osm_to_city':distances(network,reference) if lines else None})
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'focus':'Princeton Street / Edgewater Drive','review_radius_m':160,'junction_utm17_m':list(junction.coords)[0],'comparisons':comparisons,'acceptance':'NOT conference-accuracy accepted','limits':['Distances compare two reference centerline sources, not independently surveyed road edges.','Widths, corner radii, crosswalk placement, turn pockets, bicycle lanes and parking are not verified by centerline agreement.','January 2025 aerial is local visual review only; not activated as scene geometry or redistributed.','Proposed Complete Street dimensions must not replace existing conditions.']}
    atomic_json(ROOT/'data/transport/princeton_road_review.json',report)
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':build()
