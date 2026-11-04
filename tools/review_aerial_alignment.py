"""Coordinate registration diagnostic; never promotes imagery to accepted geometry."""
from pathlib import Path
import datetime,hashlib,html,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pyproj import Transformer
from PIL import Image

def pixel(x,y,extent,width,height):
    if width<=0 or height<=0 or extent['xmax']<=extent['xmin'] or extent['ymax']<=extent['ymin']:raise ValueError('Invalid image frame')
    return ((x-extent['xmin'])/(extent['xmax']-extent['xmin'])*width,(extent['ymax']-y)/(extent['ymax']-extent['ymin'])*height)

def build(root=ROOT):
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    manifest_path=root/'data/imagery/pilot_imagery_manifest.json';manifest=read(manifest_path)
    ref=next(r for r in manifest['references'] if r['service_name']=='OCPA/Aerials2025');image=root/ref['image_path']
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    if digest!=ref['image_fetch']['sha256']:raise ValueError('Aerial image checksum changed')
    with Image.open(image) as im:width,height=im.size
    if (width,height)!=(ref['image_fetch']['width'],ref['image_fetch']['height']):raise ValueError('Image dimensions changed')
    extent=ref['export_extent'];crs=extent['spatialReference'].get('latestWkid',extent['spatialReference']['wkid'])
    if crs!=2236:raise ValueError('Review requires verified EPSG:2236 export frame')
    project=Transformer.from_crs(4326,2236,always_xy=True)
    active=read(root/'data/processed/active.json');pilot=read(root/'data/processed/pilot.json')
    if pilot['source_snapshot']!=active['snapshot']:raise ValueError('Pilot is stale')
    folder=root/active['relative_path'];streets=read(folder/'streets.json')['features'];lines=[]
    for feature in streets:
        geometry=feature['geometry'];parts=geometry['coordinates'] if geometry['type']=='MultiLineString' else [geometry['coordinates']] if geometry['type']=='LineString' else []
        for part in parts:
            pixels=[pixel(*project.transform(*p[:2]),extent,width,height) for p in part]
            if not any(-100<x<width+100 and -100<y<height+100 for x,y in pixels):continue
            lines.append('<polyline points="'+ ' '.join(f'{x:.2f},{y:.2f}' for x,y in pixels)+'"/>')
    controls=[];marks=[];crossings=[];crossing_endpoints=[]
    crossing_path=root/'data/processed/pedestrian_source_evidence/candidate_crossings.geojson'
    crossing_sites={
        630:'Smith east approach',631:'Smith west approach',
        3731:'Smith north traverse',3870:'Smith south traverse',
        3869:'Princeton north leg',3871:'Princeton east leg',
        3872:'Princeton south leg',3873:'Princeton west leg',
    }
    if crossing_path.exists():
        pilot_crossings={
            'metroplan_crossings':{6993,6994,6995,6996,6999,7000,7001,7002},
            'orlando_task_force':crossing_sites,
        }
        for feature in read(crossing_path)['features']:
            props=feature['properties'];source=props['source_id'];oid=props['source_object_id']
            if oid not in pilot_crossings.get(source,set()):continue
            geometry=feature['geometry'];coords=geometry['coordinates']
            if source=='metroplan_crossings' and geometry['type']=='Point' and props['source_attributes']['EDGEDUP']==0:
                x,y=pixel(*project.transform(*coords[:2]),extent,width,height)
                crossings.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" style="fill:#ff4dde;stroke:#222;stroke-width:1"><title>MetroPlan reference point {oid}</title></circle>')
            elif source=='orlando_task_force' and geometry['type']=='LineString':
                points=' '.join(f'{x:.2f},{y:.2f}' for x,y in (pixel(*project.transform(*p[:2]),extent,width,height) for p in coords))
                crossings.append(f'<polyline points="{points}" style="stroke:#fff657;stroke-width:3;stroke-dasharray:6 3"><title>City draft line {oid}</title></polyline>')
                for end,(lon,lat,*_) in zip(('A','B'),(coords[0],coords[-1])):
                    crossing_endpoints.append({
                        'id':f'{oid}-{end}','location':crossing_sites[oid],'draft_object_id':oid,
                        'reference_coordinates_wgs84':[lon,lat],
                        'ramp_location_verified':False,'clear_width_m':None,'running_grade_pct':None,
                        'cross_slope_pct':None,'current_condition':None,
                    })
    samples_path=root/'config/rear_parking_samples.json'
    if samples_path.exists():
        for sample in read(samples_path)['samples']:
            points=' '.join(f'{float(x):.2f},{float(y):.2f}' for x,y in sample['pixels'])
            marks.append(f'<polygon points="{points}" fill="#ffbd24" fill-opacity=".18" stroke="#ffbd24" stroke-width="2"><title>{html.escape(sample["id"])}: interpreted asphalt interior, not full lot boundary</title></polygon>')
            for segment in sample.get('visible_stripe_segments_px',[]):
                stripe=' '.join(f'{float(x):.2f},{float(y):.2f}' for x,y in segment)
                marks.append(f'<polyline points="{stripe}" style="stroke:white;stroke-width:1.5;stroke-opacity:1"><title>Visible parking stripe fragment, January 2025</title></polyline>')
    for p in pilot['endpoints']:
        x,y=pixel(*project.transform(*p['coordinates']),extent,width,height)
        controls.append({'name':p['street'],'source':'City centerline intersection; comparison feature, not independent survey control','pixel_x':x,'pixel_y':y})
        marks.append(f'<g><circle cx="{x}" cy="{y}" r="9"/><text x="{x+14}" y="{y-12}">{html.escape(p["street"])}</text></g>')
    requested=manifest['preview_bbox_epsg2236'];requested_width=requested[2]-requested[0];actual_width=extent['xmax']-extent['xmin']
    report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'image_sha256':digest,'image_acquisition':ref['acquisition'],'reference_manifest_snapshot':manifest['source_snapshot'],'returned_extent':extent,'image_size':[width,height],'export_sampling_m':actual_width/width*1200/3937,'requested_width_usft':requested_width,'returned_width_usft':actual_width,'width_adjustment_percent':100*(actual_width/requested_width-1),'comparison_features':controls,'preview_accepted_for_modeling':False,'survey_control_residuals_m':None,'limits':['Frame arithmetic and source overlay only; independent ground-control residuals are not measured.','Sampling resolution does not establish native GSD or positional accuracy.','City centerlines do not establish curb, sidewalk, parking or roof edges.','Historical image reference and active GIS snapshot describe different observation dates.']}
    report['crossing_endpoint_review']=sorted(crossing_endpoints,key=lambda row:row['id'])
    out=root/'data/imagery/aerial_alignment_review.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Edgewater aerial alignment</title><style>body{font:16px/1.5 system-ui;max-width:1000px;margin:24px auto;padding:0 18px;background:#f3f5f0;color:#163e31}svg{width:100%;height:auto;background:#ddd}polyline{fill:none;stroke:#00efff;stroke-width:1.5;stroke-opacity:.8}circle{fill:none;stroke:#ff3434;stroke-width:3}text{fill:#fff;stroke:#222;stroke-width:3;paint-order:stroke;font-size:17px}label{display:block;padding:10px}a{color:#245f48}</style><a href="/road-review">Road reference review</a><h1>Edgewater aerial registration check</h1><p>January 2025 OCPA aerial with current City street centerlines (cyan) and pilot intersections (red). These are reference comparisons, not surveyed controls. No curb or parking geometry has been accepted from this overlay.</p><p>Use the actual returned export extent: the server widened the requested image frame by __ADJUST__%. Using the requested box would stretch/shift horizontal placement. Export sampling is approximately 0.178 m/pixel; positional accuracy remains unknown.</p><label><input type="checkbox" checked id="show"> Show City reference geometry</label><svg viewBox="0 0 __W__ __H__" role="img" aria-label="Dated aerial with City street centerline overlay"><defs><clipPath id="frame"><rect width="__W__" height="__H__"/></clipPath></defs><image href="/road-reference/aerial2025" width="__W__" height="__H__"/><g id="overlay" clip-path="url(#frame)">__LINES____MARKS__</g></svg><p>Local review only. Roof lean, tree cover, shadows and historical changes require separate interpretation. Source imagery is not a road texture.</p><script>document.getElementById('show').addEventListener('change',e=>document.getElementById('overlay').style.display=e.target.checked?'':'none')</script></html>'''
    if crossings:
        page=page.replace('<svg viewBox=', '<label><input type="checkbox" id="showCrossings"> Show Princeton and Smith crossing references (yellow draft lines and magenta MetroPlan points). Review only.</label><svg viewBox=',1)
        page=page.replace('</svg>', '<g id="crossingOverlay" style="display:none" clip-path="url(#frame)">'+''.join(crossings)+'</g></svg>',1)
        page=page.replace('</script>',";document.getElementById('showCrossings').addEventListener('change',e=>document.getElementById('crossingOverlay').style.display=e.target.checked?'':'none')</script>",1)
    if crossing_endpoints:
        rows=[]
        for row in report['crossing_endpoint_review']:
            lon,lat=row['reference_coordinates_wgs84']
            rows.append(f'<tr><td>{row["location"]}</td><td>{row["id"]}</td><td>{lat:.6f}, {lon:.6f}</td></tr>')
        checklist='<details><summary>Crossing endpoint field checklist</summary><p>Coordinates locate draft line ends. At each end, verify ramp location, clear width, running grade, cross slope, and current condition.</p><table><thead><tr><th>Location</th><th>Draft end</th><th>Reference latitude, longitude</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></details>'
        page=page.replace('</svg>','</svg>'+checklist,1)
    schedule_path=root/'data/processed/lynx_gtfs_reference/packet.json'
    if schedule_path.exists():
        from lynx_gtfs_reference import validate as validate_schedule
        schedule=validate_schedule(root)
        if schedule['source_snapshot']==active['snapshot']:
            stops=[]
            for stop in schedule['tables']['stops']:
                x,y=pixel(*project.transform(float(stop['stop_lon']),float(stop['stop_lat'])),extent,width,height)
                if 0<=x<=width and 0<=y<=height:
                    label=html.escape(stop['stop_id'].strip())
                    stops.append(f'<g><circle cx="{x:.2f}" cy="{y:.2f}" r="6" style="stroke:#fff;fill:#3155dd;stroke-width:2"/><text x="{x-11:.2f}" y="{y+22:.2f}" text-anchor="end">LYNX {label}</text></g>')
            if stops:
                page=page.replace('<svg viewBox=', '<label><input type="checkbox" id="showStops"> Show published LYNX stop references. Boarding areas remain unverified.</label><svg viewBox=',1)
                page=page.replace('</svg>', '<g id="stopOverlay" style="display:none" clip-path="url(#frame)">'+''.join(stops)+'</g></svg>',1)
                page=page.replace('</script>',";document.getElementById('showStops').addEventListener('change',e=>document.getElementById('stopOverlay').style.display=e.target.checked?'':'none')</script>",1)
    paint_receipt=root/'data/diagnostics/smith_north_paint_20261104/audit.json'
    if paint_receipt.exists():
        receipt=read(paint_receipt)
        if receipt['aerial_sha256']!=digest:raise ValueError('Smith north paint receipt refers to another image')
        paint=[]
        for mark in receipt['marks']:
            points=mark['pixel_polygon']
            if not all(0<=x<=width and 0<=y<=height for x,y in points):
                raise ValueError('Smith north paint trace falls outside the verified frame')
            coordinates=' '.join(f'{x:.3f},{y:.3f}' for x,y in points)
            paint.append(f'<polygon points="{coordinates}" fill="#41f99e" fill-opacity=".45" stroke="#14613e" stroke-width=".65"/>')
        page=page.replace('<svg viewBox=', '<label><input type="checkbox" id="showSmithPaint"> Show Smith north paint trace (green). January 2025 interpretation.</label><svg viewBox=',1)
        page=page.replace('</svg>','<g id="smithPaintOverlay" style="display:none" clip-path="url(#frame)">'+''.join(paint)+'</g></svg>',1)
        page=page.replace('</script>',";document.getElementById('showSmithPaint').addEventListener('change',e=>document.getElementById('smithPaintOverlay').style.display=e.target.checked?'':'none')</script>",1)
    canopy_path=root/'config/pilot_canopy_traces.json'
    if canopy_path.exists():
        canopy=read(canopy_path)
        if canopy['aerial_sha256']!=digest:raise ValueError('Canopy traces refer to another image')
        crowns=[]
        for trace in canopy['traces']:
            points=trace['pixels']
            if len(points)<3 or not all(0<=x<=width and 0<=y<=height for x,y in points):
                raise ValueError('Invalid canopy trace in the verified image frame')
            coordinates=' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
            crowns.append(f'<polygon points="{coordinates}" fill="#47e59d" fill-opacity=".2" stroke="#47e59d" stroke-width="2"><title>{html.escape(trace["id"])}</title></polygon>')
        page=page.replace('<svg viewBox=', '<label><input type="checkbox" id="showCanopy"> Show January 2025 visible canopy traces. Trunk locations remain unverified.</label><svg viewBox=',1)
        page=page.replace('</svg>', '<g id="canopyOverlay" style="display:none" clip-path="url(#frame)">'+''.join(crowns)+'</g></svg>',1)
        page=page.replace('</script>',";document.getElementById('showCanopy').addEventListener('change',e=>document.getElementById('canopyOverlay').style.display=e.target.checked?'':'none')</script>",1)
    for key,value in {'__ADJUST__':f'{report["width_adjustment_percent"]:.2f}','__W__':str(width),'__H__':str(height),'__LINES__':''.join(lines),'__MARKS__':''.join(marks)}.items():page=page.replace(key,value)
    (root/'data/imagery/aerial_alignment_review.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':build()
