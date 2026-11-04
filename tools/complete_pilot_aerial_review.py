"""Completed frozen-pilot dated aerial observation ledger, not geometry promotion."""
from pathlib import Path
import os,sys,json,hashlib,datetime,html,shutil
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import shapely
from shapely.geometry import shape,mapping,box,LineString
from shapely.ops import substring
from pyproj import Transformer
from pxr import Usd,UsdGeom,Gf
from PIL import Image
from verify_retail_block import read,save,sha,inside
from review_aerial_alignment import pixel
from imagery_reference import projected_context
from constrain_scene import mesh_footprint
OUT='data/imagery/pilot_complete'
def build():
 active=read(ROOT/'data/processed/active.json');pilot=read(ROOT/'data/processed/pilot.json');observations=read(ROOT/'config/pilot_aerial_observations.json');manifest=read(ROOT/'data/imagery/pilot_imagery_manifest.json');alignment=read(ROOT/'data/imagery/aerial_alignment_review.json')
 if pilot['source_snapshot']!=active['snapshot'] or pilot['pilot_id']!=observations['pilot_id'] or manifest['pilot_id']!=pilot['pilot_id']:raise ValueError('Pilot identity/snapshot changed')
 if max(abs(x-y) for x,y in zip(projected_context(pilot,2236),manifest['preview_bbox_epsg2236']))>1e-5:raise ValueError('Cached imagery belongs to different geographic pilot context')
 refs=sorted(manifest['references'],key=lambda r:r['service_name']);references=[];dependencies={}
 for ref in refs:
  path=inside(ROOT,ref['image_path']);extent=ref['export_extent'];crs=extent['spatialReference'].get('latestWkid',extent['spatialReference']['wkid'])
  if crs!=2236 or sha(path)!=ref['image_fetch']['sha256']:raise ValueError('Reference checksum/CRS mismatch')
  with Image.open(path) as image:
   width,height=image.size
   if (width,height)!=(ref['image_fetch']['width'],ref['image_fetch']['height']):raise ValueError('Reference dimensions changed')
   image.verify()
  original_metadata={}
  for field,datafield in [('metadata_fetch','metadata'),('item_metadata_fetch','item_metadata')]:
   receipt=ref[field];cache=ROOT/'data/imagery/cache'/(hashlib.sha256(receipt['url'].encode()).hexdigest()+'.json');envelope=read(cache)
   if any(envelope['data'].get(k)!=v for k,v in ref[datafield].items()) or envelope['sha256']!=receipt['sha256']:raise ValueError('Original imagery metadata cache differs')
   dependencies[str(cache.relative_to(ROOT)).replace('\\','/')]=sha(cache);original_metadata[datafield]=envelope['data']
  references.append({'source_id':ref['service_name'],'publisher':'Orange County Property Appraiser','source_url':ref['service_url'],'acquisition':ref['acquisition'],'effective_date':None,'native_gsd_m':ref.get('native_acquisition_gsd_m'),'positional_accuracy_m':ref.get('positional_accuracy_m'),'source_crs':'EPSG2236 NAD83 Florida East US survey feet','vertical_datum':'not applicable to2Dreference; no height inference','returned_extent':extent,'width':width,'height':height,'export_sampling_m':[(extent['xmax']-extent['xmin'])/width*1200/3937,(extent['ymax']-extent['ymin'])/height*1200/3937],'metadata_fetch':ref.get('metadata_fetch'),'item_metadata_fetch':ref.get('item_metadata_fetch'),'service_item_id':original_metadata['metadata'].get('serviceItemId'),'export_request_url':ref.get('export_request_url'),'service_capabilities':original_metadata['metadata'].get('capabilities'),'export_tiles_allowed':original_metadata['metadata'].get('exportTilesAllowed'),'download_access':'Bounded public export observed; dataset/native download license and redistribution not established','original_copyright_text':ref['metadata'].get('copyrightText'),'original_license_info':ref['item_metadata'].get('licenseInfo'),'image_fetch':ref['image_fetch'],'image_path':ref['image_path'],'reuse':'local qualitative review only; empty source licenseInfo does not establish redistribution/AI/modeling permission','preview_accepted_for_modeling':False});dependencies[ref['image_path']]=sha(path)
 if {r['acquisition']['month'] for r in references}!={'2022-01','2024-01','2025-01'}:raise ValueError('Three reviewed dates required')
 if any(r['returned_extent']!=references[-1]['returned_extent'] or r['width']!=references[-1]['width'] or r['height']!=references[-1]['height'] for r in references):raise ValueError('Reference sheet requires matched actual returned frames')
 extent=references[-1]['returned_extent'];width=references[-1]['width'];height=references[-1]['height'];frame=box(extent['xmin'],extent['ymin'],extent['xmax'],extent['ymax']);to_state=Transformer.from_crs(32617,2236,always_xy=True);to_wgs=Transformer.from_crs(2236,4326,always_xy=True);project=Transformer.from_crs(4326,32617,always_xy=True);origin=project.transform(*read(ROOT/'config/study_area.json')['local_origin_wgs84']);state=lambda x,y:to_state.transform(x+origin[0],y+origin[1]);wgs=lambda g:shapely.transform(g,to_wgs.transform,interleaved=False)
 stage=Usd.Stage.Open(str(ROOT/'scene/college_park.usda'));folder=(ROOT/active['relative_path']).resolve()
 if not folder.is_relative_to((ROOT/'data/snapshots').resolve()):raise ValueError('Escaping snapshot')
 buildings={b['id']:b for b in read(folder/'buildings.json')};rows=[];features=[];svg=[];locators=[];source_keys=[]
 if set(pilot['building_ids'])|set(observations.get('supplemental_context_buildings',[]))!={r['building_id'] for r in observations['building_observations']}:raise ValueError('Pilot building review census mismatch')
 for number,note in enumerate(observations['building_observations'],1):
  b=buildings[note['building_id']];prim=stage.GetPrimAtPath(b['usd_path']);custom=prim.GetCustomData();ids=custom['sourceObjectIds'].split(',');key=custom['parcelId']+':'+custom['buildingNumber']
  if custom['parcelId']!=note['source_parcel_id'] or custom['buildingNumber']!=note['source_building_number'] or set(ids)!=set(note['source_object_ids']):raise ValueError('Source group geometry identity changed')
  g=shapely.transform(mesh_footprint(prim),state,interleaved=False);coverage=g.intersection(frame).area/g.area;actual='outside_frame' if coverage<1e-6 else 'partial_frame' if coverage<.999 else 'in_frame'
  if actual!=note['frame_disposition']:raise ValueError('Observed source-frame disposition inconsistent '+b['id']+' '+actual)
  center=pixel(g.centroid.x,g.centroid.y,extent,width,height);pixels=[]
  for polygon in getattr(g,'geoms',[g]):
   for ring in [polygon.exterior,*polygon.interiors]:pixels.append([pixel(x,y,extent,width,height) for x,y in ring.coords])
  row={**note,'review_id':'pilot-building:'+key,'review_number':number,'source_building_key':key,'source_snapshot':active['snapshot'],'current_building_alias':b['id'],'review_census_membership':'frozen_parcel_linked_candidate' if b['id'] in pilot['building_ids'] else 'supplemental_physical_context_group_omitted_by_parcel_queue','parcel_id':b['parcel_id'],'parcel_feature_id':b.get('parcel_feature_id'),'site_address':b['site_address'],'stored_link_accepted':b['match_method']=='id_and_geometry','source_link_promoted':False,'current_match_method':b['match_method'],'review_status':'reviewed_with_explicit_limits' if actual!='outside_frame' else 'reviewed_frame_exception_no_visual_conclusion','geometry_role':'OCPA source footprint review locator; not aerial-traced ground wall','dated_reference_ids':[r['source_id'] for r in references],'source_footprint_frame_fraction':coverage,'reference_centroid_pixel':list(center),'pixel_outline':pixels,'change_disposition':'roof_surface_change_candidate_not_addition' if any(s in note['roof_observation'] for s in ['bright','lighter','lighten']) else 'no_unambiguous_addition_established' if actual=='in_frame' else 'unresolved_frame_or_occlusion','roof_height_facade_inference':False,'curb_frontage':'Separate continuous frontage sectors; do not assign overhead roof to ground curb','current_conditions_verified':False}
  rows.append(row);source_keys.append(key);features.append({'type':'Feature','id':row['review_id'],'geometry':mapping(wgs(g)),'properties':{k:v for k,v in row.items() if k!='pixel_outline'}});locators.append((row['review_id'],g,row['review_number'],actual))
 # Independent source-geometry census catches unmatched/condominium groups omitted by parcel linking.
 context=shapely.transform(shape(pilot['context_geometry']),Transformer.from_crs(4326,2236,always_xy=True).transform,interleaved=False);physical_context_ids=[]
 for source_prim in stage.GetPrimAtPath('/World/Buildings').GetChildren():
  source_g=shapely.transform(mesh_footprint(source_prim),state,interleaved=False)
  if source_g.intersection(context).area>.01:physical_context_ids.append(source_prim.GetName())
 unreviewed=set(physical_context_ids)-{r['current_building_alias'] for r in rows}
 if unreviewed:raise ValueError('Unreviewed physical context source groups: '+str(sorted(unreviewed)))
 # Eight review sectors cover both sides of the entire frozen85.44mcenterline.
 centerline=shapely.transform(shape(pilot['centerline']),Transformer.from_crs(4326,2236,always_xy=True).transform,interleaved=False);frontages=[]
 for side in ['west','east']:
  for index in range(4):
   piece=substring(centerline,centerline.length*index/4,centerline.length*(index+1)/4);middle=piece.interpolate(.5,normalized=True);offset=LineString([(x+(-20 if side=='west' else 20),y) for x,y in piece.coords]);name=side+'_'+str(4-index);note=observations['frontage_observations'][name];id='pilot-frontage:'+name
   row={'review_id':id,'side':side,'sector':4-index,'start_fraction':index/4,'end_fraction':(index+1)/4,'reference_pixel_line':[list(pixel(x,y,extent,width,height)) for x,y in offset.coords],'review_locator_offset_usft':-20 if side=='west' else 20,'geometry_role':'centerline-offset review locator, not surveyed/observed curb or right-of-way','observation':note,'dates_reviewed':[r['acquisition']['month'] for r in references],'review_status':'reviewed_visible_and_occluded_parts','occluded_segments':'unresolved; never completed by interpolation','curb_grade_width_or_ADA_verified':False};frontages.append(row);features.append({'type':'Feature','id':id,'geometry':mapping(wgs(offset)),'properties':row});locators.append((id,offset,None,'frontage'))
 if abs(sum(r['end_fraction']-r['start_fraction'] for r in frontages)-2)>1e-9:raise ValueError('Continuous two-side frontage coverage incomplete')
 out=ROOT/OUT;out.mkdir(parents=True,exist_ok=True);packet_path=out/'review.json';receipt_path=out/'receipt.json';previous=read(receipt_path) if receipt_path.exists() else None
 artifact_paths=[ROOT/'scene/pilot_aerial_review.usda',out/'review.geojson',out/'references.html',out/'coverage.html']
 if previous:
  for relative,digest in {**previous['artifacts'],str(packet_path.relative_to(ROOT)).replace('\\','/'):previous['packet_sha256']}.items():
   if sha(inside(ROOT,relative))!=digest:raise ValueError('Preserve manual aerial-review output edits: '+relative)
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for path in artifact_paths+[packet_path,receipt_path]:shutil.copy2(path,backup/path.name)
 elif any(p.exists() for p in artifact_paths):raise ValueError('Untracked aerial review artifacts exist')
 save(out/'review.geojson',{'type':'FeatureCollection','source_snapshot':active['snapshot'],'features':features})
 # Dated reference sheets link original LOCAL JPEGs; no modified/copied pixels.
 cards=[]
 for reference in references:
  shapes=[]
  for row in rows:
   if row['frame_disposition']=='outside_frame':continue
   for ring in row['pixel_outline']:shapes.append('<polyline fill="none" stroke="#00e4e8" stroke-width="1.3" points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in ring)+'"/>')
   x,y=row['reference_centroid_pixel'];shapes.append(f'<text x="{min(width-15,max(10,x)):.1f}" y="{min(height-10,max(15,y)):.1f}" fill="white" stroke="black" paint-order="stroke" font-size="17">{row["review_number"]}</text>')
  for row in frontages:
   f=next(f for f in features if f['id']==row['review_id']);g=shapely.transform(shape(f['geometry']),Transformer.from_crs(4326,2236,always_xy=True).transform,interleaved=False);xy=[pixel(x,y,extent,width,height) for x,y in g.coords];shapes.append('<polyline fill="none" stroke="#f7a123" stroke-width="3" points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in xy)+'"/>')
  cards.append('<section><h2>'+reference['acquisition']['month']+'</h2><p>Original OCPA export; cyan source footprints, orange review locators are not measured curbs.</p><svg viewBox="0 0 768 1152"><image href="../'+Path(reference['image_path']).name+'" width="768" height="1152"/>'+''.join(shapes)+'</svg></section>')
 headers='<!doctype html><meta charset="utf-8"><title>Frozen pilot dated aerial review</title><style>body{font:15px system-ui;padding:20px}main{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}svg{width:100%}td{border-bottom:1px solid #aaa;padding:8px;vertical-align:top}</style><h1>Frozen Edgewater pilot dated aerial review</h1><p>LOCAL REVIEW ONLY. No source pixels redistributed. All observations are historical, qualitative and not surveyed geometry. Row labels refer to current snapshot aliases and stable source keys.</p>'
 table='<table><tr><th># / source key</th><th>Roof/addition review</th><th>Parking/access review</th><th>Limits</th></tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(value))+'</td>' for value in [str(r['review_number'])+' / '+r['source_building_key'],r['roof_observation'],r['parking_driveway_observation'],r['occlusion_identity_observation']])+'</tr>' for r in rows)+'</table>'
 (out/'references.html').write_text(headers+'<main>'+''.join(cards)+'</main>'+table,encoding='utf-8')
 # Pixel-free coverage map explicitly exposes out-of-frame source groups.
 allg=shapely.union_all([frame]+[g for _,g,_,_ in locators]);x0,y0,x1,y1=allg.bounds;scale=min(950/(x1-x0),850/(y1-y0));parts=[]
 for id,g,num,status in locators:
  lines=[g] if g.geom_type=='LineString' else [ring for p in getattr(g,'geoms',[g]) for ring in [p.exterior,*p.interiors]]
  for line in lines:parts.append('<polyline fill="none" stroke="'+('#b44c38' if status=='outside_frame' else '#28758d')+'" points="'+' '.join(f'{(x-x0)*scale+10:.2f},{(y1-y)*scale+10:.2f}' for x,y in line.coords)+'"><title>'+html.escape(id+' '+status)+'</title></polyline>')
 parts.append('<polygon fill="none" stroke="#111" stroke-width="3" points="'+' '.join(f'{(x-x0)*scale+10:.2f},{(y1-y)*scale+10:.2f}' for x,y in frame.exterior.coords)+'"/>');(out/'coverage.html').write_text('<!doctype html><meta charset="utf-8"><h1>Review coverage and source-frame exceptions</h1><p>Black frame: all three returned image extents. Red: linked source groups outside frame. Blue: source footprint/review locators. No aerial pixels.</p><svg viewBox="0 0 1000 900">'+''.join(parts)+'</svg>',encoding='utf-8')
 review=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(review,'Z');review.SetMetadata('metersPerUnit',1.);root=UsdGeom.Xform.Define(review,'/World/Information/PilotAerialReview');root.CreateVisibilityAttr('invisible');root.GetPrim().SetCustomData({'sourceSnapshot':active['snapshot'],'quality':'historical_qualitative_review_locators_not_accepted_geometry','sourceContext':{'publisher':'OCPA','acquisitionStart':'2022-01','acquisitionEnd':'2025-01','effectiveDate':'unknown','sourceSnapshot':active['snapshot'],'quality':'dated aerial review; unknown positional accuracy; no facade/height inference'}})
 from_state=Transformer.from_crs(2236,32617,always_xy=True)
 for i,(id,g,num,status) in enumerate(locators):
  lines=[g] if g.geom_type=='LineString' else [ring for p in getattr(g,'geoms',[g]) for ring in [p.exterior,*p.interiors]];points=[];counts=[]
  for line in lines:
   coords=list(line.coords);counts.append(len(coords));points.extend([(from_state.transform(x,y)[0]-origin[0],from_state.transform(x,y)[1]-origin[1],.06) for x,y in coords])
  curve=UsdGeom.BasisCurves.Define(review,str(root.GetPath())+'/Review'+str(i));curve.CreateTypeAttr('linear');curve.CreateCurveVertexCountsAttr(counts);curve.CreatePointsAttr(points);curve.CreateWidthsAttr([.16]);curve.SetWidthsInterpolation('constant');curve.CreateDisplayColorAttr([Gf.Vec3f(*((.8,.25,.16) if status=='outside_frame' else (.1,.7,.8)))]);curve.GetPrim().SetCustomData({'reviewId':id,'geometryRole':'review locator only, not current surveyed geometry','frameStatus':status})
  row=next((r for r in rows if r['review_id']==id),None);source_context={'publisher':'Orange County Property Appraiser','sourceURL':'https://vgispublic.ocpafl.org/server/rest/services/OCPA','sourceSnapshot':active['snapshot'],'acquisitionStart':'2022-01','acquisitionEnd':'2025-01','acquisitionDates':'2022-01,2024-01,2025-01','effectiveDate':'unknown','retrievedUTC':max(r['image_fetch']['retrieved_utc'] for r in references),'quality':'historical_qualitative_review_locator_not_surveyed_geometry','reviewId':id,'frameStatus':status}
  if row:source_context.update({'sourceBuildingKey':row['source_building_key'],'sourceParcelId':row['source_parcel_id'],'assignedParcelId':row['parcel_id'] or 'unknown','sourceObjectIds':','.join(row['source_object_ids']),'localBuildingAlias':row['current_building_alias'],'sourceLinkPromoted':False,'reviewObservationJSON':json.dumps({k:row[k] for k in ['roof_observation','parking_driveway_observation','occlusion_identity_observation','review_status']})})
  else:source_context.update({'frontageReviewLocator':'centerline offset sector, not observed curb','reviewObservation':next(r['observation'] for r in frontages if r['review_id']==id)})
  curve.GetPrim().SetCustomDataByKey('sourceContext',source_context)
 review.GetRootLayer().customLayerData={'sourceSnapshot':active['snapshot'],'defaultOff':True,'imageryPixelsEmbedded':False,'geometryAccepted':False};review.GetRootLayer().Export(str(artifact_paths[0]))
 inputs=[ROOT/'config/pilot_aerial_observations.json',ROOT/'web/aerial-review.html',ROOT/'data/processed/pilot.json',ROOT/'data/processed/active.json',folder/'buildings.json',ROOT/'data/imagery/pilot_imagery_manifest.json',ROOT/'data/imagery/pilot_aerial_review_queue.json',ROOT/'data/imagery/aerial_alignment_review.json',ROOT/'scene/college_park.usda',ROOT/'docs/MAIN_STREET_GROUND_AND_CANOPY.md',Path(__file__)]
 dependencies.update({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in inputs});artifacts={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in artifact_paths}
 dictionary={'source_building_key':'Original source parcel string + original building number; current Building_N alias is snapshot-local','source_object_ids':'Original OCPA footprint subarea IDs, guard exact source membership','parcel_id':'Current assigned parcel string; not promoted by aerial review','frame_disposition':'in_frame / partial_frame / outside_frame determined from source footprint intersection','review_status':'Every frozen candidate assessed; outside-frame groups have no visual conclusion','change_disposition':'Qualitative surface/addition finding; no permit fact or measured height','reference_centroid_pixel':'Source-footprint centroid projected using actual returned export extent; not manually traced roof control','source_footprint_frame_fraction':'Geometry intersection fraction; does not quantify accuracy','frontage.geometry_role':'Centerline offset review-sector locator, never observed curb geometry','effective_date':'Unknown; acquisition month and retrieval dates are independent'}
 packet={'schema':'twin.pilot-aerial-review/1','source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pilot_id':pilot['pilot_id'],'pilot_endpoints':pilot['endpoints'],'pilot_reference_date':pilot['reference_date'],'source_reference_manifest_snapshot':manifest['source_snapshot'],'pilot_definition_comparison':'Geographic pilot context bbox verified unchanged; older imagery/queue snapshot aliases are not reused as current IDs','review_method':observations['review_method'],'references':references,'building_reviews':rows,'frontage_reviews':frontages,'field_dictionary':dictionary,'first_five_safe_rows':{'buildings':rows[:5],'frontages':frontages[:5],'references':references[:5]},'coverage':{'frozen_candidates':len(pilot['building_ids']),'reviewed_frozen_candidates':sum(r['review_census_membership']=='frozen_parcel_linked_candidate' for r in rows),'supplemental_context_groups':len(rows)-len(pilot['building_ids']),'reviewed_candidates':len(rows),'physical_source_groups_in_context':physical_context_ids,'unreviewed_physical_context_groups':sorted(unreviewed),'in_frame':sum(r['frame_disposition']=='in_frame' for r in rows),'partial_frame':sum(r['frame_disposition']=='partial_frame' for r in rows),'outside_frame':sum(r['frame_disposition']=='outside_frame' for r in rows),'frontage_sides':2,'frontage_sectors':len(frontages),'continuous_fraction_each_side':1.0,'fraction_means':'review-sector coverage, not visibility or surveyed curb completeness'},'alignment':alignment,'A01_A08_status':{'A-01':'returned frame/CRS/hash arithmetic and current source overlay checked; independent ground controls/residuals and task-specific modeling tolerance unresolved','A-02':'rear hardscape sample remains separately governed; no geometry promoted from this review','A-03':'source building IDs linked; roof/ground and spatial-only identity conflicts retained','A-04':'parking/driveway observations recorded; no hidden curb/stall/accessible-route inference','A-05':'canopy occlusion recorded; no trunk or tree-height inventory inferred','A-06':'facades/tenants require street references; overhead evidence not accepted for them','A-07':'dated review sheets and separate review layer delivered; matched model visual-production acceptance remains separate','A-08':'pilot review only; fullMainStreet replication remains source/coverage ledger work'},'unresolved':['Four linked source groups are wholly outside cached frames; no visual conclusion assigned. They are preserved source/identity/frame exceptions, not counted as confirmed missing buildings.','Partial-frame groups retain unreviewable edges; canopy, parked vehicles, shadows, roof lean and small additions remain unresolved.','Roof brightness changes are surface-change candidates; not confirmed additions, material specifications or construction dates.','No independent surveyed ground controls, native GSD or positional accuracy; imagery remains unaccepted for geometric modeling.','Current2026conditions, facade appearance, roof heights, curb grade/ADA and legal parking/access status are not established.','Source licenseInfo empty: local review only; no aerial pixels redistributed, publicly deployed, used as textures or ML training/evaluation.'],'dependencies':dependencies,'artifacts':artifacts,'geometry_activated':False,'raw_property_links_promoted':False,'default_on':False}
 save(packet_path,packet);save(receipt_path,{'source_snapshot':active['snapshot'],'packet_sha256':sha(packet_path),'artifacts':artifacts});print(json.dumps({'coverage':packet['coverage'],'packet_sha256':sha(packet_path),'artifacts':artifacts},indent=2));return packet

def validate_review(root=ROOT):
 root=Path(root).resolve();path=root/OUT/'review.json';packet=read(path);receipt=read(root/OUT/'receipt.json')
 if packet['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or receipt['source_snapshot']!=packet['source_snapshot'] or receipt['packet_sha256']!=sha(path):raise ValueError('Aerial review packet/snapshot stale')
 if not packet['dependencies'] or not packet['artifacts'] or receipt['artifacts']!=packet['artifacts']:raise ValueError('Aerial dependency/artifact guard missing')
 for relative,digest in {**packet['dependencies'],**packet['artifacts']}.items():
  if sha(inside(root,relative))!=digest:raise ValueError('Aerial evidence changed: '+relative)
 return packet
if __name__=='__main__':build()
