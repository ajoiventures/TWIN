"""Dated official OCPA pilot references; no inferred roof accuracy or rights grant."""
from pathlib import Path
import argparse, datetime, hashlib, html, io, json, math, os, re, sys
import urllib.parse, urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(temp,path)
def check_url(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.hostname!='vgispublic.ocpafl.org':raise ValueError('Only the official public OCPA HTTPS host is permitted')

class Client:
    def __init__(self,folder,offline=False,refresh=False):self.folder,self.offline,self.refresh=folder,offline,refresh
    def json(self,url,params=None,force_live=False):
        check_url(url);target=url+('?' + urllib.parse.urlencode(params) if params else '')
        path=self.folder/(hashlib.sha256(target.encode()).hexdigest()+'.json')
        if path.exists() and (self.offline or (not self.refresh and not force_live)):return read_json(path)
        if self.offline:raise RuntimeError('Offline imagery metadata cache miss')
        req=urllib.request.Request(target,headers={'User-Agent':'TWIN-pilot-imagery-reference/1.0'})
        with urllib.request.urlopen(req,timeout=25) as response:
            check_url(response.geturl());raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('Metadata response too large')
        data=json.loads(raw)
        if isinstance(data,dict) and data.get('error'):raise ValueError('ArcGIS error: '+json.dumps(data['error']))
        envelope={'url':target,'retrieved_utc':stamp(),'sha256':hashlib.sha256(raw).hexdigest(),'data':data}
        write_json(path,envelope);return envelope
    def image(self,url,path):
        check_url(url)
        req=urllib.request.Request(url,headers={'User-Agent':'TWIN-pilot-imagery-reference/1.0'})
        with urllib.request.urlopen(req,timeout=25) as response:
            check_url(response.geturl());raw=response.read(6*1024*1024+1);kind=response.headers.get('Content-Type')
        if len(raw)>6*1024*1024:raise ValueError('Preview image too large')
        stats=image_statistics(raw)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return {'url':url,'retrieved_utc':stamp(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'content_type':kind,**stats}

def acquisition_month(item,service):
    """A month is asserted only when descriptive metadata states it, never from service year."""
    texts=[item.get('snippet',''),item.get('summary',''),item.get('description',''),service.get('serviceDescription','')]
    for text in texts:
        match=re.search(r'\b(January|Jan)\s+(20\d{2})\b',text,re.I)
        if match:return {'month':match.group(2)+'-01','precision':'month','evidence':text,'exact_capture_date':None}
        match=re.search(r'\b(20\d{2})\b.*?\bflown\s+Jan(?:uary)?\b',text,re.I)
        if match:return {'month':match.group(1)+'-01','precision':'month','evidence':text,'exact_capture_date':None}
    return {'month':None,'precision':'unresolved','evidence':None,'exact_capture_date':None}

def image_statistics(raw):
    from PIL import Image,ImageStat
    image=Image.open(io.BytesIO(raw));image.load()
    if image.format not in ['JPEG','PNG']:raise ValueError('Unsupported/non-image preview response')
    stats=ImageStat.Stat(image.convert('RGB'));variation=max(stats.stddev)
    if variation<2:raise ValueError('Preview appears blank or uniform; do not claim imagery coverage')
    return {'width':image.width,'height':image.height,'format':image.format,'channel_stddev':stats.stddev,
            'coverage_evidence':'Nonuniform reference image returned; manual inspection still required, not an accuracy test'}

def projected_context(pilot,crs):
    from pyproj import Transformer
    if pilot.get('context_geometry',{}).get('type')!='Polygon':raise ValueError('Pilot context must be a Polygon')
    ring=pilot['context_geometry']['coordinates'][0]
    if len(ring)<4:raise ValueError('Pilot context ring is incomplete')
    to=Transformer.from_crs(4326,crs,always_xy=True);points=[to.transform(p[0],p[1]) for p in ring]
    if not all(math.isfinite(n) for p in points for n in p):raise ValueError('Invalid projected pilot coordinates')
    return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]

def pixel_resolution(export):
    e=export['extent'];sr=e.get('spatialReference',{}).get('latestWkid',e.get('spatialReference',{}).get('wkid'))
    if sr not in [2236,102658]:raise ValueError('Unexpected export CRS; units must not be guessed')
    x=(e['xmax']-e['xmin'])/export['width'];y=(e['ymax']-e['ymin'])/export['height']
    return {'x_us_survey_feet':x,'y_us_survey_feet':y,'x_m':x*1200/3937,'y_m':y*1200/3937,
            'meaning':'Export sampling resolution; not native acquisition GSD or surveyed positional accuracy'}

def review_queue(pilot,buildings):
    by={b['id']:b for b in buildings};rows=[]
    for identifier in pilot['building_ids']:
        b=by.get(identifier)
        if not b:raise ValueError('Pilot building missing from matching source snapshot: '+identifier)
        rows.append({'building_id':identifier,'parcel_id':b.get('parcel_id'),'site_address':b.get('site_address'),
          'match_method':b.get('match_method'),'link_accepted':b.get('match_method')=='id_and_geometry',
          'review_status':'unreviewed','review_topics':{'roof_outline':'unresolved','addition_change':'unresolved',
             'parking_stripes_driveways':'unresolved','canopy_occlusion':'unresolved','curb_frontage':'unresolved'},
          'note':'Aerial evidence cannot establish facade identity, measured height, curb grade or current occupancy.'})
    return rows

def reference_html(manifest):
    cards=[]
    for r in manifest['references']:
        if r.get('image_path'):
            cards.append('<section><h2>'+html.escape(r['service_name'])+' · '+html.escape(r['acquisition']['month'] or 'date unresolved')+'</h2>'
              +'<p>'+html.escape(r['acquisition']['evidence'] or 'No capture date verified')+'</p>'
              +'<img src="'+html.escape(Path(r['image_path']).name)+'" alt="Historical OCPA aerial of frozen Edgewater pilot context">'
              +'<p>Export sampling '+str(round(r['export_resolution']['x_m'],3))+' m/pixel; acquisition GSD/accuracy unknown. Source: '
              +'<a href="'+html.escape(r['service_url'])+'">OCPA public service</a>.</p></section>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Pilot historical aerial references</title><style>body{font:16px system-ui;max-width:1400px;margin:25px auto;padding:15px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}img{width:100%;height:auto}section{border:1px solid #bbb;padding:12px}</style><h1>'+html.escape(manifest['pilot_name'])+'</h1><p>Local historical reference review only. Capture dates have month precision. Not a survey, current-condition verification, redistribution license or AI-use approval.</p><main>'+''.join(cards)+'</main></html>'

def build(root=ROOT,offline=False,refresh=False):
    config=read_json(root/'config/imagery_sources.json');pilot=read_json(root/'data/processed/pilot.json')
    pointer=read_json(root/'data/processed/active.json')
    if pointer['snapshot']!=pilot['source_snapshot']:raise ValueError('Pilot/snapshot mismatch; refreeze or rebuild pilot before review')
    folder=(root/pointer['relative_path']).resolve()
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Snapshot escaped allowed directory')
    out=root/'data/imagery';client=Client(out/'cache',offline,refresh)
    catalog=client.json(config['catalog_url'],{'f':'json'});public=client.json(config['catalog_url']+'/'+config['public_folder'],{'f':'json'})
    names={s['name'] for s in public['data'].get('services',[]) if s['type']=='MapServer'}
    bbox=projected_context(pilot,config['preview_crs']);references=[]
    previous_path=out/'pilot_imagery_manifest.json';previous=read_json(previous_path) if previous_path.exists() else {}
    for name in config['selected_service_names']:
        row={'service_name':name,'service_url':config['catalog_url']+'/'+name+'/MapServer','preview_accepted_for_modeling':False,
             'reuse_status':'unresolved; local review reference only','native_acquisition_gsd_m':None,'positional_accuracy_m':None}
        try:
            if name not in names:raise ValueError('Selected service absent from observed public catalog')
            meta=client.json(row['service_url'],{'f':'json'});item=client.json(row['service_url']+'/info/iteminfo',{'f':'json'})
            row.update(acquisition=acquisition_month(item['data'],meta['data']),
               metadata={k:meta['data'].get(k) for k in ['serviceDescription','copyrightText','spatialReference','fullExtent','maxScale','minScale','tileInfo']},
               item_metadata={k:item['data'].get(k) for k in ['title','snippet','summary','licenseInfo','accessInformation']},
               metadata_fetch={k:meta[k] for k in ['retrieved_utc','sha256','url']},
               item_metadata_fetch={k:item[k] for k in ['retrieved_utc','sha256','url']})
            image_name=name.replace('/','_')+'_'+pilot['pilot_id']+'.jpg';image_path=out/image_name
            if offline:
                old=next((r for r in previous.get('references',[]) if r['service_name']==name),None)
                if not old or not image_path.exists():raise RuntimeError('Offline preview or manifest missing')
                if previous.get('pilot_sha256')!=hashlib.sha256((root/'data/processed/pilot.json').read_bytes()).hexdigest():raise ValueError('Cached image belongs to a different pilot definition')
                if hashlib.sha256(image_path.read_bytes()).hexdigest()!=old['image_fetch']['sha256']:raise ValueError('Cached preview checksum mismatch')
                row.update({k:old[k] for k in ['image_fetch','export_extent','export_resolution','export_request_url']})
            else:
                params={'f':'json','bbox':','.join(map(str,bbox)),'bboxSR':config['preview_crs'],'imageSR':config['preview_crs'],
                    'size':','.join(map(str,config['preview_size'])),'format':config['preview_format'],'transparent':'false'}
                export=client.json(row['service_url']+'/export',params,force_live=True)
                row.update(image_fetch=client.image(export['data']['href'],image_path),export_extent=export['data']['extent'],
                           export_resolution=pixel_resolution(export['data']),export_request_url=export['url'])
            row.update(image_path=image_path.relative_to(root).as_posix(),access_status='public_export_observed',
                       capture_date_status='descriptive_metadata_month_only' if row['acquisition']['month'] else 'unresolved')
        except Exception as exc:row.update(access_status='unresolved',error=str(exc))
        references.append(row)
    manifest={'created_utc':stamp(),'offline_replay':offline,'pilot_id':pilot['pilot_id'],'pilot_name':pilot['name'],
      'source_snapshot':pointer['snapshot'],'pilot_sha256':hashlib.sha256((root/'data/processed/pilot.json').read_bytes()).hexdigest(),
      'pilot_reference_date':pilot['reference_date'],'pilot_reference_date_note':pilot['reference_date_meaning'],
      'catalog_url':config['catalog_url'],'observed_public_aerial_services':sorted(n for n in names if 'aerial' in n.lower()),
      'catalog_fetch':{k:catalog[k] for k in ['url','retrieved_utc','sha256']},
      'folder_fetch':{k:public[k] for k in ['url','retrieved_utc','sha256']},
      'configuration_sha256':hashlib.sha256((root/'config/imagery_sources.json').read_bytes()).hexdigest(),
      'preview_bbox_epsg2236':bbox,'references':references,'reuse_policy':config['reuse_policy'],
      'unresolved':['Exact flight day and native acquisition GSD/positional accuracy','Reuse/redistribution and AI eligibility',
                    'Building-by-building roof/addition alignment','Parking, driveway and canopy/curb review','Current conditions after historical capture']}
    suffix='_offline' if offline else ''
    write_json(out/('pilot_imagery_manifest'+suffix+'.json'),manifest)
    write_json(out/('pilot_aerial_review_queue'+suffix+'.json'),review_queue(pilot,read_json(folder/'buildings.json')))
    (out/('pilot_imagery_reference'+suffix+'.html')).write_text(reference_html(manifest),encoding='utf-8')
    print(json.dumps({'pilot':pilot['pilot_id'],'references':[{k:r.get(k) for k in ['service_name','access_status','acquisition','error']} for r in references]},indent=2));return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--refresh',action='store_true');a=parser.parse_args()
    build(offline=a.offline,refresh=a.refresh)
