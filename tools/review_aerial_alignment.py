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
    controls=[];marks=[]
    for p in pilot['endpoints']:
        x,y=pixel(*project.transform(*p['coordinates']),extent,width,height)
        controls.append({'name':p['street'],'source':'City centerline intersection; comparison feature, not independent survey control','pixel_x':x,'pixel_y':y})
        marks.append(f'<g><circle cx="{x}" cy="{y}" r="9"/><text x="{x+14}" y="{y-12}">{html.escape(p["street"])}</text></g>')
    requested=manifest['preview_bbox_epsg2236'];requested_width=requested[2]-requested[0];actual_width=extent['xmax']-extent['xmin']
    report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'image_sha256':digest,'image_acquisition':ref['acquisition'],'reference_manifest_snapshot':manifest['source_snapshot'],'returned_extent':extent,'image_size':[width,height],'export_sampling_m':actual_width/width*1200/3937,'requested_width_usft':requested_width,'returned_width_usft':actual_width,'width_adjustment_percent':100*(actual_width/requested_width-1),'comparison_features':controls,'preview_accepted_for_modeling':False,'survey_control_residuals_m':None,'limits':['Frame arithmetic and source overlay only; independent ground-control residuals are not measured.','Sampling resolution does not establish native GSD or positional accuracy.','City centerlines do not establish curb, sidewalk, parking or roof edges.','Historical image reference and active GIS snapshot describe different observation dates.']}
    out=root/'data/imagery/aerial_alignment_review.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Edgewater aerial alignment</title><style>body{font:16px/1.5 system-ui;max-width:1000px;margin:24px auto;padding:0 18px;background:#f3f5f0;color:#163e31}svg{width:100%;height:auto;background:#ddd}polyline{fill:none;stroke:#00efff;stroke-width:1.5;stroke-opacity:.8}circle{fill:none;stroke:#ff3434;stroke-width:3}text{fill:#fff;stroke:#222;stroke-width:3;paint-order:stroke;font-size:17px}label{display:block;padding:10px}a{color:#245f48}</style><a href="/road-review">Road reference review</a><h1>Edgewater aerial registration check</h1><p>January 2025 OCPA aerial with current City street centerlines (cyan) and pilot intersections (red). These are reference comparisons, not surveyed controls. No curb or parking geometry has been accepted from this overlay.</p><p>Use the actual returned export extent: the server widened the requested image frame by __ADJUST__%. Using the requested box would stretch/shift horizontal placement. Export sampling is approximately 0.178 m/pixel; positional accuracy remains unknown.</p><label><input type="checkbox" checked id="show"> Show City reference geometry</label><svg viewBox="0 0 __W__ __H__" role="img" aria-label="Dated aerial with City street centerline overlay"><defs><clipPath id="frame"><rect width="__W__" height="__H__"/></clipPath></defs><image href="/road-reference/aerial2025" width="__W__" height="__H__"/><g id="overlay" clip-path="url(#frame)">__LINES____MARKS__</g></svg><p>Local review only. Roof lean, tree cover, shadows and historical changes require separate interpretation. Source imagery is not a road texture.</p><script>document.getElementById('show').addEventListener('change',e=>document.getElementById('overlay').style.display=e.target.checked?'':'none')</script></html>'''
    for key,value in {'__ADJUST__':f'{report["width_adjustment_percent"]:.2f}','__W__':str(width),'__H__':str(height),'__LINES__':''.join(lines),'__MARKS__':''.join(marks)}.items():page=page.replace(key,value)
    (root/'data/imagery/aerial_alignment_review.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':build()
