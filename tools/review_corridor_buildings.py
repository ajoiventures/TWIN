"""Full-boundary cached building exception classification; no invented buildings."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,hashlib,collections,datetime,csv
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import shapely
from shapely.geometry import shape,box,mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
from pxr import Usd,UsdGeom
from constrain_scene import mesh_footprint

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic_json(path,data):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');os.replace(temporary,path)

def record_state(p,context):
    """States describe evidence, never automatically count tax rows as buildings."""
    if context['reconstructed']:return 'already_reconstructed_historical' if context.get('registered_visible',True) else 'registered_form_visibility_review'
    if context['proposal_ready']:return 'historical_source_form_ready_uncomposed'
    if context['condo_or_shared']:return 'condo_or_shared_building_record'
    if p['parcel_id']=='292223390900010':return 'construction_temporal_review'
    if context['land_only']:return 'land_record_with_geometry_conflict' if context['visible_geometry'] else 'parking_or_unimproved_land_review'
    if context['source_displaced']:return 'source_identity_spatial_conflict'
    if context['visible_geometry']:
        return 'represented_source_geometry' if context['accepted_links'] else 'identity_link_review_existing_geometry'
    if context['building_attributes']:return 'potential_physical_omission_unverified'
    return 'unresolved_building_evidence'

def build(root=ROOT):
    active=read(root/'data/processed/active.json');folder=(root/active['relative_path']).resolve()
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Invalid snapshot path')
    config=read(root/'config/study_area.json');t=Transformer.from_crs(4326,32617,always_xy=True);origin=t.transform(*config['local_origin_wgs84'])
    to_local=lambda g:shapely.transform(g,lambda x,y:(x-origin[0],y-origin[1]),interleaved=False)
    project=lambda g:shapely.transform(g,t.transform,interleaved=False)
    boundaries=read(root/'data/processed/study_boundaries.geojson')['features'];boundary={f['id']:project(shape(f['geometry'])) for f in boundaries}
    acquisition=project(box(*config['acquisition_bbox_wgs84']));coverage={};outside=[]
    for name,g in boundary.items():
        missing=g.difference(acquisition);coverage[name]={'official_area_m2':g.area,'in_extraction_m2':g.intersection(acquisition).area,
            'outside_extraction_m2':missing.area,'percent_area_in_extraction':min(100.,100*g.intersection(acquisition).area/g.area),
            'parcel_or_building_count_outside_extraction':None,'status':'complete_ground_extent_not_building_completeness' if missing.area<.01 else 'partial_source_extent_unknown_building_census'}
        if missing.area>.01:outside.append({'type':'Feature','geometry':mapping(missing),'properties':{'record_type':'outside_extraction_area','scope':name,
            'state':'outside_extraction','source_building_count':'unknown','area_m2':missing.area,'reason':'Official boundary outside current source extraction; not inferred empty land'}})
    parcels=read(folder/'parcels.json')['features'];buildings=read(folder/'buildings.json');heights=read(root/'data/heights/building_heights.json');hby={h['building_id']:h for h in heights}
    if any(h['source_snapshot']!=active['snapshot'] for h in heights):raise ValueError('Stale height table')
    audit=read(root/'data/commercial/edgewater_property_audit.json')
    if audit['source_snapshot']!=active['snapshot']:raise ValueError('Stale corridor audit')
    aby={r['parcel_feature_id']:r for r in audit['rows']};old35={r['parcel_feature_id'] for r in audit['rows'] if r['commercial_tax_family_review'] and not r['accepted_model_links']}
    old17={r['parcel_feature_id'] for r in audit['rows'] if r['commercial_tax_family_review'] and not r['spatial_footprint_candidates_not_accepted_identity']}
    registered=read(root/'data/processed/reconstructions.json');recon={r['parcel_id']:r for r in registered['records']}
    proposal_path=root/'data/heights/landmarks/proposal_manifest.json';proposal=read(proposal_path) if proposal_path.exists() else {'sites':[]}
    pending={r['parcel_id']:r for r in proposal['sites'] if r['parcel_id'] not in recon}
    stage=Usd.Stage.Open(str(root/'scene/college_park_connected.usda'))
    if not stage:raise ValueError('Cannot inspect current composed geometry')
    model=[];model_shapes=[];by_parcel=collections.defaultdict(list);by_source=collections.defaultdict(list)
    raw={str(f['properties']['OBJECTID']):f['properties'] for f in read(root/'data/buildings.geojson')['features']}
    underused_source_floors=[]
    for b in buildings:
        by_parcel[b.get('parcel_id')].append(b);by_source[b.get('source_parcel_id')].append(b)
        prim=stage.GetPrimAtPath(b['usd_path'])
        if not prim or not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        g=mesh_footprint(prim)
        if g.is_empty or g.area<.01:continue
        ids=prim.GetCustomData().get('sourceObjectIds','').split(',');floors=[int(raw[i].get('FLOOR_NUM') or 0) for i in ids if i in raw]
        source_floor=max(floors,default=0);height=hby[b['id']]
        if source_floor>height.get('floors_used',0):underused_source_floors.append({'building_id':b['id'],'source_floor':source_floor,'modeled_floors':height.get('floors_used')})
        model.append({'id':b['id'],'usd_path':b['usd_path'],'representation':'visible_legacy_or_corrected_mesh','source_parcel_id':b.get('source_parcel_id'),
            'floors_used':height.get('floors_used'),'source_maximum_floor_num':source_floor,'height_m':height['height_m'],'quality':height['quality']})
        model_shapes.append(g)
    for record in recon.values():
        prim=stage.GetPrimAtPath(record['usd_path']);pieces=[]
        if prim:
            for child in Usd.PrimRange(prim):
                if child.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(child).ComputeVisibility()!='invisible':
                    g=mesh_footprint(child)
                    if not g.is_empty and g.area>.01:pieces.append(g)
        if pieces:
            model.append({'id':record['id'],'usd_path':record['usd_path'],'representation':'registered_historical_reconstruction','source_parcel_id':None,
                'floors_used':record.get('reported_project_maximum_storeys'),'height_m':None,'quality':record.get('quality')})
            model_shapes.append(unary_union(pieces))
    tree=STRtree(model_shapes);model_index={m['id']:i for i,m in enumerate(model)}
    geometries={f['properties']['id']:project(shape(f['geometry'])) for f in parcels}
    coincidence=collections.Counter(shapely.normalize(g).wkb for g in geometries.values())
    rows=[];features=[];upper=[];queue35=[];queue17=[]
    for feature in parcels:
        p=feature['properties'];g=geometries[p['id']];scopes=[name for name,b in boundary.items() if b.intersection(g).area>1]
        if not scopes and p['id'] not in aby:continue
        local=to_local(g);candidates=[]
        for index in tree.query(local):
            area=model_shapes[index].intersection(local).area
            if area>1:candidates.append({**model[index],'parcel_overlap_m2':round(area,3),'model_footprint_overlap_ratio':round(area/model_shapes[index].area,6)})
        associated=by_parcel[p['parcel_id']];accepted=[b for b in associated if b['match_method']=='id_and_geometry'];a=aby.get(p['id'],{})
        reconstruction=recon.get(p['parcel_id']);proposal_site=pending.get(p['parcel_id'])
        registered_visible=bool(reconstruction and reconstruction['id'] in model_index)
        coincident=coincidence[shapely.normalize(g).wkb];condo=any('condominium' in flag for flag in a.get('review_flags',[])) or (coincident>1 and not accepted)
        building_attributes=bool((p.get('stories') or 0)>0 or (p.get('year_built') or 0)>0)
        land_only=not building_attributes and (not a.get('ocpa_building_use_code')) and str(p.get('property_use_code') or '') in ['0000','1000','2800','4000','8000']
        raw_candidates=[]
        for b in by_source[p['parcel_id']]:
            if b['id'] in model_index:
                index=model_index[b['id']];overlap=model_shapes[index].intersection(local).area
                raw_candidates.append({'building_id':b['id'],'parcel_overlap_ratio':overlap/max(model_shapes[index].area,.001)})
        source_displaced=bool(raw_candidates) and max(r['parcel_overlap_ratio'] for r in raw_candidates)<.05
        context={'reconstructed':bool(reconstruction),'registered_visible':registered_visible,'proposal_ready':bool(proposal_site),'condo_or_shared':condo,'land_only':land_only,
            'visible_geometry':bool(candidates),'source_displaced':source_displaced,'accepted_links':len(accepted),'building_attributes':building_attributes}
        state=record_state(p,context);flags=[]
        if reconstruction and not registered_visible:flags.append('registered_source_form_not_visible_in_current_root_not_a_new_physical_omission')
        if coincident>1:flags.append('coincident_tax_geometries_not_independent_building_count')
        if g.difference(acquisition).area>1:flags.append('parcel_extends_outside_extraction')
        if not scopes:flags.append('edgewater_address_context_outside_official_boundaries')
        if p.get('year_built',0) and p['year_built']>2019:flags.append('postdates_historical_2018_2019_lidar')
        floors=[c['floors_used'] for c in candidates if c.get('floors_used')]
        if (p.get('stories') or 0)>=2 and not reconstruction and not condo and (not floors or max(floors)<p['stories']):
            reason='parcel_maximum_storeys_vs_component_evidence_requires_review' if len(candidates)>1 else 'appraiser_story_vs_single_or_absent_model_conflict'
            item={'parcel_feature_id':p['id'],'parcel_id':p['parcel_id'],'site_address':p.get('site_address'),'reported_storeys':p['stories'],
                'visible_model_maximum_floors':max(floors,default=None),'visible_model_entities':[c['id'] for c in candidates],
                'state':reason,'automatic_height_change':False,'reason':'Parcel storeys do not establish every wing/accessory floor; no unsupported whole-footprint extrusion'}
            upper.append(item);flags.append('upper_floor_evidence_review_not_confirmed_missing_floor')
        if a.get('property_name','').strip().upper()=='VACANT' and building_attributes:flags.append('vacant_label_may_mean_unoccupied_building_not_vacant_land')
        row={'record_type':'parcel_feature','parcel_feature_id':p['id'],'parcel_id':p['parcel_id'],'site_address':p.get('site_address'),
            'scopes':scopes,'state':state,'property_use_code':p.get('property_use_code'),'appraiser_storeys':p.get('stories'),'year_built':p.get('year_built'),
            'accepted_legacy_links':len(accepted),'visible_model_candidates':candidates,'source_identity_candidates':raw_candidates,
            'registered_reconstruction':reconstruction['id'] if reconstruction else None,'registered_form_visible':registered_visible,'ready_uncomposed_form':proposal_site['site_id'] if proposal_site else None,
            'coincident_tax_geometry_records':coincident,'flags':flags,'original_35_unaccepted_queue':p['id'] in old35,'original_17_no_legacy_queue':p['id'] in old17,
            'physical_omission_confirmed':False,'current_shape_verified':False,'parcel_is_building_footprint':False}
        rows.append(row);features.append({'type':'Feature','geometry':feature['geometry'],'properties':{k:v for k,v in row.items() if k not in ['visible_model_candidates','source_identity_candidates']}})
        if p['id'] in old35:queue35.append(row)
        if p['id'] in old17:queue17.append(row)
    # The proposal contains evidence metadata only unless an independently supported
    # physical correction is ready. This run must not manufacture buildings from land records.
    stage_out=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage_out,1);UsdGeom.SetStageUpAxis(stage_out,'Z')
    root_prim=UsdGeom.Xform.Define(stage_out,'/World/CorridorBuildingReview');root_prim.GetPrim().SetCustomData({'sourceSnapshot':active['snapshot'],
        'status':'classified_source_queue_no_new_geometry_verified','correctedBuildingCount':0,'rawParcelLinksPromoted':False})
    layer=root/'scene/corridor_building_corrections_proposal.usda';temporary=layer.with_name(layer.stem+'.tmp.usda');stage_out.GetRootLayer().Export(str(temporary));os.replace(temporary,layer)
    dependencies=[root/'data/processed/active.json',folder/'parcels.json',folder/'buildings.json',root/'data/buildings.geojson',root/'data/heights/building_heights.json',
        root/'data/processed/study_boundaries.geojson',root/'config/study_area.json',root/'data/commercial/edgewater_property_audit.json',root/'data/processed/reconstructions.json',Path(__file__).resolve()]
    if proposal_path.exists():dependencies.append(proposal_path)
    dependencies += [Path(l.realPath) for l in stage.GetUsedLayers() if l.realPath and Path(l.realPath).resolve().is_relative_to(root.resolve())]
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],
        'scope':'ALL building uses in official MainStreet and CollegePark neighborhood boundaries, plus prior Edgewater-address context; current cached extraction is partial',
        'coverage':coverage,'extracted_parcel_features':len(parcels),'classified_parcel_features':len(rows),'extracted_features_outside_both_official_boundaries_and_prior_corridor_context':len(parcels)-len(rows),'classified_unique_parcel_ids':len({r['parcel_id'] for r in rows}),
        'visible_model_entities_checked':len(model),'registered_reconstructions_checked':list(recon),'ready_uncomposed_historical_sites_checked':list(pending),
        'state_counts':dict(collections.Counter(r['state'] for r in rows)),'rows':rows,'upper_floor_review':upper,
        'official_subarea_floor_underuse':underused_source_floors,'raw_official_subareas_checked':len(raw),
        'original_35_queue_state_counts':dict(collections.Counter(r['state'] for r in queue35)),
        'original_17_queue_state_counts':dict(collections.Counter(r['state'] for r in queue17)),
        'original_35_queue':queue35,'original_17_queue':queue17,'corrected_building_count':0,
        'proposal_layer':str(layer),'proposal_layer_sha256':sha(layer),'active_model_modified':False,
        'dependencies':{str(p.resolve().relative_to(root.resolve())).replace('\\','/'):sha(p) for p in set(dependencies)},
        'limits':['Parcel-feature states are not a census of physical buildings or occupied storeys.',
            'Outside-extraction building/parcel counts remain unknown; geographic extent coverage is not feature completeness.',
            'Fresh audit attributes and historical geometry have different observation dates; current geometry is not verified.',
            'Potential omissions require independent footprints/sketches/dated imagery or complete local LiDAR before geometry correction.',
            'No new acquisition, no parcel-envelope extrusion, no parking/vacant/condo record promoted to a building.']}
    out=root/'data/processed/corridor_building_review.json'
    to_wgs=Transformer.from_crs(32617,4326,always_xy=True)
    for f in outside:f['geometry']=mapping(shapely.transform(shape(f['geometry']),to_wgs.transform,interleaved=False))
    geo_path=root/'data/processed/corridor_building_review.geojson'
    atomic_json(geo_path,{'type':'FeatureCollection','features':features+outside})
    report['geometry_geojson_relative_path']='data/processed/corridor_building_review.geojson'
    report['geometry_geojson_sha256']=sha(geo_path)
    atomic_json(out,report)
    print(json.dumps({k:report[k] for k in ['classified_parcel_features','classified_unique_parcel_ids','visible_model_entities_checked','state_counts','original_35_queue_state_counts','original_17_queue_state_counts','corrected_building_count']},indent=2))
    print('coverage',json.dumps(coverage));print('upper_floor_review',len(upper),'official_floor_underuse',len(underused_source_floors));return report

if __name__=='__main__':build()
