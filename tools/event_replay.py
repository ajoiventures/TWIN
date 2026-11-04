"""Deterministic, offline replay. No sensor connection or inference is implied."""
from pathlib import Path
import argparse,datetime,hashlib,json,math

ROOT=Path(__file__).resolve().parents[1]
MODES={'observed','simulated','synthetic'}

def instant(value):
    if not isinstance(value,str):raise ValueError('Timestamp must be text')
    try:result=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise ValueError('Invalid timestamp') from None
    if result.tzinfo is None or result.utcoffset() is None:raise ValueError('Timezone is required')
    return result.astimezone(datetime.timezone.utc)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

def validate(events,registry):
    entities={r['entity_id'] for r in registry['records']};unique={}
    for event in events:
        required=['event_id','entity_id','source_snapshot','mode','source_id','event_time','ingested_time','metric','value','unit','confidence','evidence_ref']
        if any(key not in event for key in required):raise ValueError('Missing event field')
        for key in ['event_id','entity_id','source_id','metric','unit','evidence_ref']:
            if not isinstance(event[key],str) or not event[key].strip():raise ValueError('Empty identifier or evidence: '+key)
        if event['entity_id'] not in entities:raise ValueError('Unknown registry entity')
        if event['source_snapshot']!=registry['source_snapshot']:raise ValueError('Snapshot mismatch')
        if event['mode'] not in MODES:raise ValueError('Unknown observation mode')
        if event['mode']!='observed' and not event.get('run_id'):raise ValueError('Simulation/synthetic event requires run_id')
        if event['mode']=='observed' and not event.get('sensor_id'):raise ValueError('Observed event requires sensor_id')
        occurred=instant(event['event_time']);ingested=instant(event['ingested_time'])
        if ingested<occurred:raise ValueError('Ingestion precedes event time')
        for key in ['value','confidence']:
            value=event[key]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Invalid numeric '+key)
        if not 0<=event['confidence']<=1:raise ValueError('Confidence outside [0,1]')
        # Event IDs are global within this versioned input. Exact retransmits
        # are idempotent; conflicting reuse is an error, never last-write-wins.
        encoded=canonical(event);previous=unique.get(event['event_id'])
        if previous and previous!=encoded:raise ValueError('Conflicting duplicate event ID')
        unique[event['event_id']]=encoded
    return sorted((json.loads(v) for v in unique.values()),key=lambda e:(instant(e['event_time']),e['event_id']))

def replay(events,registry,at,mode,stale_after_seconds=300,known_at=None):
    if mode not in MODES:raise ValueError('Explicit single mode required')
    if isinstance(stale_after_seconds,bool) or not isinstance(stale_after_seconds,(int,float)) or not math.isfinite(stale_after_seconds) or stale_after_seconds<0:raise ValueError('Invalid stale threshold')
    cutoff=instant(at);knowledge=instant(known_at or at)
    accepted=validate(events,registry);states={};included=[]
    for event in accepted:
        if event['mode']!=mode or instant(event['event_time'])>cutoff or instant(event['ingested_time'])>knowledge:continue
        # Separate sensors/sources and runs; do not fuse inconsistent claims.
        key=(event['entity_id'],event['source_id'],event.get('sensor_id',''),event.get('run_id',''),event['metric'],event['unit'])
        states[key]=event;included.append(event['event_id'])
    rows=[]
    for key,event in sorted(states.items()):
        age=(cutoff-instant(event['event_time'])).total_seconds()
        rows.append({**event,'age_seconds':age,'stale':age>stale_after_seconds})
    return {'schema':'twin.replay/1.0','source_snapshot':registry['source_snapshot'],'mode':mode,'at':cutoff.isoformat(),'known_at':knowledge.isoformat(),'stale_after_seconds':stale_after_seconds,'input_sha256':hashlib.sha256(canonical(accepted).encode()).hexdigest(),'registry_sha256':hashlib.sha256(canonical(registry).encode()).hexdigest(),'included_event_ids':included,'rows':rows,'limits':['No sensor connection, geographic calibration or measurement validation is established by replay.','Confidence is source-reported, not calibrated accuracy. Empty state means no eligible evidence, not zero occupancy.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('events',type=Path);p.add_argument('--at',required=True);p.add_argument('--known-at');p.add_argument('--mode',required=True,choices=sorted(MODES));p.add_argument('--stale-after',type=float,default=300);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    registry=json.loads((ROOT/'data/processed/asset_registry.json').read_text(encoding='utf-8'))
    active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'))
    if registry['source_snapshot']!=active['snapshot']:raise ValueError('Rebuild stale registry before replay')
    report=replay(json.loads(a.events.read_text(encoding='utf-8')),registry,a.at,a.mode,a.stale_after,a.known_at)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print('Replayed',len(report['included_event_ids']),'events;',len(report['rows']),'separate source states')
