"""Local ephemeral feature-ID selection exchange; never writes scene/source data."""
from pathlib import Path
from contextlib import contextmanager
import datetime,ipaddress,json,os,tempfile,threading,uuid
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
MAX_BODY=2048
_lock=threading.RLock()
_contexts={}

class SelectionError(ValueError):
    def __init__(self,message,status=400):super().__init__(message);self.status=status

def valid_origin(origin,host,port,client):
    try:
        if not ipaddress.ip_address(client).is_loopback:return False
        expected=urlparse('http://'+host);actual=urlparse(origin)
        return (expected.hostname in ('localhost','127.0.0.1','::1') and expected.port==port
                and actual.scheme=='http' and actual.netloc==expected.netloc
                and not actual.path and not actual.query and not actual.fragment
                and not actual.username and not actual.password)
    except (ValueError,TypeError):return False

def validate_payload(payload):
    allowed={'epoch','snapshot','expected_revision','sender','feature_id','entity_id'}
    if not isinstance(payload,dict) or set(payload)-allowed:raise SelectionError('Invalid selection fields')
    for key in ('epoch','snapshot','sender'):
        if not isinstance(payload.get(key),str) or not 0<len(payload[key])<=128:raise SelectionError('Invalid '+key)
    revision=payload.get('expected_revision')
    if type(revision) is not int or revision<0:raise SelectionError('Invalid selection revision')
    if payload['sender'] not in ('map','kit'):raise SelectionError('Invalid selection sender')
    for key in ('feature_id','entity_id'):
        if key in payload and (not isinstance(payload[key],str) or len(payload[key])>256):raise SelectionError('Invalid '+key)
    if payload.get('feature_id') and payload.get('entity_id'):raise SelectionError('Choose one identity')
    if payload['sender']=='map' and 'entity_id' in payload:raise SelectionError('Map selection requires feature identity')
    return payload

def load_context(root=ROOT):
    root=Path(root).resolve();pointer=root/'data/processed/active.json'
    active=json.loads(pointer.read_text(encoding='utf-8'));folder=(root/active['relative_path']).resolve()
    if not folder.is_relative_to(root/'data/snapshots'):raise SelectionError('Invalid snapshot path')
    registry_path=root/'data/processed/asset_registry.json';parcel_path=folder/'parcels.json'
    signature=(active['snapshot'],pointer.stat().st_mtime_ns,registry_path.stat().st_mtime_ns,parcel_path.stat().st_mtime_ns)
    cached=_contexts.get(str(root))
    if cached and cached[0]==signature:return cached[1]
    registry=json.loads(registry_path.read_text(encoding='utf-8'))
    if registry.get('source_snapshot')!=active['snapshot']:raise SelectionError('Selection registry is stale',409)
    parcels=json.loads(parcel_path.read_text(encoding='utf-8'))
    features={}
    for feature in parcels['features']:
        key=str(feature.get('id') or feature.get('properties',{}).get('id') or '')
        if not key or key in features:raise SelectionError('Parcel feature identity is missing or duplicated',409)
        features[key]=feature
    context={'snapshot':active['snapshot'],'features':features,'records':registry['records']}
    _contexts[str(root)]=(signature,context);return context

def resolve_selection(context,feature_id='',entity_id=''):
    records=context['records'];snapshot=context['snapshot']
    if entity_id:
        matches=[r for r in records if r.get('entity_id')==entity_id and r.get('source_snapshot')==snapshot]
        if len(matches)!=1:return {'status':'unmatched','feature_id':None,'paths':[],'entity_ids':[],'reason':'Selected 3D entity has no unique current registry identity.'}
        row=matches[0]
        if row.get('parcel_link_accepted') is not True:
            return {'status':'unmatched','feature_id':None,'paths':[],'entity_ids':[entity_id],'reason':'3D parcel association is not accepted.'}
        feature_id=row.get('parcel_feature_id') or ''
    if not feature_id:return {'status':'cleared','feature_id':None,'paths':[],'entity_ids':[],'reason':'Selection cleared.'}
    if feature_id not in context['features']:raise SelectionError('Parcel feature is not in the current snapshot',409)
    accepted=[r for r in records if r.get('source_snapshot')==snapshot and r.get('parcel_feature_id')==feature_id and r.get('parcel_link_accepted') is True and isinstance(r.get('usd_path'),str) and r['usd_path'].startswith('/World/Buildings/')]
    paths=sorted({r['usd_path'] for r in accepted})
    return {'status':'matched' if paths else 'unmatched','feature_id':feature_id,'paths':paths,
            'entity_ids':sorted({r['entity_id'] for r in accepted}),
            'reason':f'{len(paths)} accepted 3D building counterpart(s).' if paths else 'No accepted 3D building counterpart for this exact parcel feature. Parcel context is not a storefront.'}

@contextmanager
def state_lock(root):
    directory=Path(root)/'data/processed';directory.mkdir(parents=True,exist_ok=True)
    with _lock, (directory/'selection_bridge.lock').open('a+b') as stream:
        if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

def write_state(root,state):
    directory=Path(root)/'data/processed'
    fd,path=tempfile.mkstemp(prefix='selection-',suffix='.tmp',dir=directory)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(state,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(path,directory/'selection_bridge.json')
    finally:
        if os.path.exists(path):os.unlink(path)

def _read(root,context,reset=False):
    path=Path(root)/'data/processed/selection_bridge.json'
    try:state=json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError,ValueError):state={}
    if (not isinstance(state,dict) or reset or state.get('snapshot')!=context['snapshot']
            or not isinstance(state.get('epoch'),str) or type(state.get('revision')) is not int
            or state.get('revision',-1)<0 or not isinstance(state.get('selection'),dict)):
        state={'epoch':str(uuid.uuid4()),'snapshot':context['snapshot'],'revision':0,'sender':'none',
               'selection':resolve_selection(context),'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        write_state(root,state)
    return state

def read_state(root=ROOT,reset=False):
    with state_lock(root):return _read(root,load_context(root),reset)

def publish(payload,root=ROOT):
    validate_payload(payload)
    with state_lock(root):
        context=load_context(root);state=_read(root,context)
        if payload['snapshot']!=context['snapshot'] or payload['epoch']!=state['epoch']:raise SelectionError('Selection epoch or snapshot changed; reload selection state',409)
        if payload['expected_revision']!=state['revision']:raise SelectionError('A newer selection exists; refresh before retrying',409)
        selection=resolve_selection(context,payload.get('feature_id',''),payload.get('entity_id',''))
        state.update(revision=state['revision']+1,sender=payload['sender'],selection=selection,
                     delivery={'status':'pending' if payload['sender']=='map' else 'selected-in-editor'},
                     updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write_state(root,state);return state

def acknowledge(packet,status,reason,root=ROOT):
    with state_lock(root):
        current=_read(root,load_context(root))
        if any(current.get(key)!=packet.get(key) for key in ('epoch','snapshot','revision')):raise SelectionError('New selection superseded delivery',409)
        current['delivery']={'status':status,'reason':reason}
        write_state(root,current);return current

def counterpart_paths(stage,packet,context):
    if packet.get('snapshot')!=context['snapshot']:raise SelectionError('Editor selection snapshot is stale',409)
    selection=packet.get('selection',{})
    if not selection.get('feature_id'):return []
    canonical=resolve_selection(context,selection['feature_id'])
    result=[]
    for path in canonical['paths']:
        prim=stage.GetPrimAtPath(path)
        if not prim:continue
        data=prim.GetCustomData();twin=data.get('twin',{})
        if twin.get('sourceSnapshot')==context['snapshot'] and twin.get('entityId') in canonical['entity_ids']:result.append(path)
    return result

def selection_identity(prim,context):
    """Only registry entity identity or exact official parcel feature, never PIN."""
    while prim and not prim.IsPseudoRoot():
        data=prim.GetCustomData();entity=data.get('twin',{}).get('entityId')
        if entity:return {'entity_id':entity}
        official=data.get('official',{})
        feature=official.get('id')
        if feature in context['features'] and str(prim.GetPath()).startswith('/World/ParcelBoundaries/'):
            return {'feature_id':feature}
        prim=prim.GetParent()
    # Explicit unknown entity yields unmatched rather than guessing a parcel.
    return {'entity_id':'unregistered-selection'}
