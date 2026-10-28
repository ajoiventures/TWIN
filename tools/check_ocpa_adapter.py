"""Produce usable corrected OCPA tables from cache without activating a snapshot."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):os.environ[key]='1'
import collections,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from data_pipeline import Client,SOURCES,arcgis,normalize_parcels,building_joins,atomic_json

def build(root=ROOT):
    client=Client(root/'data/cache/official',offline=True)
    raw,metadata=arcgis(client,SOURCES['parcels'])
    parcels,rejects=normalize_parcels(raw)
    buildings=building_joins(parcels,root/'scene/college_park.usda')
    active=json.loads((root/'data/processed/active.json').read_text());old=json.loads((root/active['relative_path']/'buildings.json').read_text());old_index={r['id']:r for r in old}
    changes=[{'id':r['id'],'old_method':old_index.get(r['id'],{}).get('match_method'),'new_method':r['match_method'],'old_feature_id':old_index.get(r['id'],{}).get('parcel_feature_id'),'new_feature_id':r['parcel_feature_id'],'candidate_features':r['candidate_parcel_features']} for r in buildings if r['match_method']!=old_index.get(r['id'],{}).get('match_method') or r['parcel_feature_id']!=old_index.get(r['id'],{}).get('parcel_feature_id')]
    out=root/'data/processed/ocpa_adapter_preview';out.mkdir(parents=True,exist_ok=True)
    report={'mode':'offline_candidate_tables_not_active_snapshot','basis_snapshot':active['snapshot'],'parcel_features':len(parcels['features']),'unique_parcel_ids':len({r['properties']['parcel_id'] for r in parcels['features']}),
      'building_groups':len(buildings),'join_states':dict(collections.Counter(r['join_state'] for r in buildings)),'normalization_rejects':rejects,'link_changes_requiring_review':changes,
      'source_schema_fields':[{'name':f['name'],'type':f.get('type'),'alias':f.get('alias')} for f in metadata['fields']],
      'source_url':SOURCES['parcels']['url'],'requests':client.accesses,'private_booms_imported':False,'active_snapshot_modified':False,
      'coverage':'Full configured extraction including official Main Street; neighborhood/context gaps and full-project property verification remain separate.'}
    atomic_json(out/'parcels.json',parcels);atomic_json(out/'buildings.json',buildings);atomic_json(out/'quality.json',report)
    atomic_json(out/'first_five.json',{'parcel_fields':list(parcels['features'][0]['properties']) if parcels['features'] else [],'parcels':[f['properties'] for f in parcels['features'][:5]],'building_fields':list(buildings[0]) if buildings else [],'buildings':buildings[:5]})
    print(json.dumps({k:v for k,v in report.items() if k not in ('requests','source_schema_fields','link_changes_requiring_review')},indent=2));print('Review link changes:',len(changes));return report

if __name__=='__main__':build()
