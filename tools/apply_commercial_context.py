"""Attach reviewed broker facts and explicitly unknown current status to model entities."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd
from data_pipeline import atomic_json

def apply():
    evidence=json.loads((ROOT/'data/commercial/commercial_evidence.json').read_text(encoding='utf-8'));active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'))
    if evidence['source_snapshot']!=active['snapshot']:raise ValueError('Commercial evidence snapshot is stale')
    folder=ROOT/active['relative_path'];parcels=json.loads((folder/'parcels.json').read_text(encoding='utf-8'))['features'];pby={f['properties']['parcel_id']:f['properties'] for f in parcels}
    stage=Usd.Stage.CreateInMemory();applied=[]
    for review in evidence['entity_link_review']:
        facts=review.get('accepted_physical_metadata',[])
        for link in review.get('accepted_entity_links',[]):
            path='/World/Buildings/'+link['building_id'];row={'claim_id':review['claim_id'],'scope':link['scope'],'current_verified_status':'unknown','status_update_activated':False,'physical_facts':facts,'source_url':link['evidence_url'],'source_snapshot':active['snapshot']}
            stage.OverridePrim(path).SetCustomDataByKey('commercialEvidence',json.dumps(row));applied.append({'path':path,**row})
        for context in review.get('accepted_property_context',[]):
            p=pby[context['parcel_id']];path='/World/ParcelBoundaries/Parcel_'+str(p['source_object_id']);row={**context,'current_verified_status':'unknown','source_snapshot':active['snapshot']}
            stage.OverridePrim(path).SetCustomDataByKey('commercialEvidence',json.dumps(row));applied.append({'path':path,**row})
    stage.GetRootLayer().customLayerData={'purpose':'Reviewed commercial reference context, separate from physical geometry','current_verified_status':'unknown; broker reports are not current occupancy verification'};stage.GetRootLayer().Export(str(ROOT/'scene/commercial_context.usda'))
    report={'source_snapshot':active['snapshot'],'model_annotations':applied,'active_market_status_changes':0,'geometry_resized':False};atomic_json(ROOT/'data/commercial/model_context_quality.json',report);print('Applied',len(applied),'reviewed model annotations; active market-status changes: 0');return report

if __name__=='__main__':apply()
