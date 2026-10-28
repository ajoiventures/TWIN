"""Historical pitched-roof proposals from bounded measured returns; never activation."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import shape,MultiPoint,box
from shapely.ops import unary_union
from pyproj import Transformer
from pxr import Usd,UsdGeom,Gf
from verify_retail_block import read,save,sha
from verify_final_omissions import SITES
from office_roof_architecture import halfspace,material,finish_mesh
from reconstruct_landmarks import planar_region_geometry

def planes(q,count,minimum_slope):
 center=np.mean(q[:,:2],axis=0);a=np.c_[q[:,:2]-center,np.ones(len(q))];rng=np.random.default_rng(17);available=np.ones(len(q),bool);results=[]
 for k in range(count):
  ids=np.where(available)[0];best=[]
  if len(ids)<50:break
  for attempt in range(1000):
   sample=rng.choice(ids,3,replace=False)
   try:c=np.linalg.solve(a[sample],q[sample,2])
   except np.linalg.LinAlgError:continue
   if not minimum_slope<np.linalg.norm(c[:2])<1.:continue
   hits=ids[np.abs(a[ids]@c-q[ids,2])<.13]
   if len(hits)>len(best):best=hits
  if len(best)<50:break
  c=np.linalg.lstsq(a[best],q[best,2],rcond=None)[0];res=np.abs(a[best]@c-q[best,2]);results.append({'coef':c,'support':q[best],'residual':np.percentile(res,[50,95,100]).tolist()});available[best]=False
 return center,results

def build():
 evidence=read(ROOT/'data/heights/final_omissions/diagnostics.json');active=read(ROOT/'data/processed/active.json')
 if evidence['source_snapshot']!=active['snapshot']:raise ValueError('Stale evidence')
 for relative,digest in evidence['dependencies'].items():
  if sha(ROOT/relative)!=digest:raise ValueError('Changed evidence: '+relative)
 to_utm=Transformer.from_crs(4326,32617,always_xy=True);origin=to_utm.transform(*read(ROOT/'config/study_area.json')['local_origin_wgs84']);features=read(ROOT/'data/heights/final_omissions/roof_support.geojson')['features']
 path=ROOT/'scene/final_omission_roofs_proposal.usda';stage=Usd.Stage.CreateInMemory();stage.SetMetadata('metersPerUnit',1.);UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z);stage.GetRootLayer().customLayerData={'sourceSnapshot':active['snapshot'],'classification':'Historical source-derived pitched roof draft; wall lines and current conditions unverified'}
 wall=material(stage,'FinalOmissionsWall',(.68,.64,.56));roofmat=material(stage,'FinalOmissionsRoof',(.30,.31,.29));records=[]
 for site,pid in SITES:
  data=next(r for r in evidence['rows'] if r['site_id']==site);feature=next(f for f in features if f['properties']['site_id']==site);outline=shapely.transform(shape(feature['geometry']),to_utm.transform,interleaved=False).simplify(.65,preserve_topology=True).buffer(.12,join_style=2).buffer(-.12,join_style=2).buffer(-.04,join_style=2).buffer(.04,join_style=2)
  q=np.load(ROOT/'data/heights/final_omissions'/site/'points.npz')['points'];ground=float(np.median(q[q[:,3]==2,2]));source=q[(np.isin(q[:,3],[1,6]) if site=='edgewater_3457' else q[:,3]==6)&shapely.intersects_xy(outline.buffer(.2),q[:,0],q[:,1])&(q[:,2]>ground+2)&(q[:,2]<ground+15)]
  if site=='edgewater_3457':
   from shapely.geometry import Polygon
   rebuilt=[]
   for polygon in getattr(outline,'geoms',[outline]):
    holes=[]
    for ring in polygon.interiors:
     hole=Polygon(ring);support=q[np.isin(q[:,3],[1,6])&shapely.intersects_xy(hole,q[:,0],q[:,1])&(q[:,2]>ground+2)]
     if len(support)<4:holes.append(ring.coords)
    rebuilt.append(Polygon(polygon.exterior.coords,holes))
   outline=unary_union(rebuilt)
  center,fitted=planes(source,5 if site=='rugby_738' else 4,.20 if site=='edgewater_3457' else .15)
  if len(fitted)<4:raise ValueError('Insufficient supported pitched planes '+site)
  model=shapely.transform(outline,lambda x,y:(x-center[0],y-center[1]),interleaved=False);regions=[]
  if site=='rugby_720':
   for i,fit in enumerate(fitted):
    patch=model
    for j,other in enumerate(fitted):
     if i!=j:patch=halfspace(patch,*(fit['coef']-other['coef']))
    if not patch.is_empty and patch.area>.01:regions.append({'geometry':shapely.transform(patch,lambda x,y:(x+center[0],y+center[1]),interleaved=False),'coefficients_cell_xy':fit['coef'].tolist(),'plane_index':i})
  else:
   # Broad convex support domains preserve the measured lower stepped wing.
   # Assign strongest supported plane first; every remaining patch has nearby measured support.
   remaining=outline
   for i,fit in enumerate(fitted):
    hull=MultiPoint(fit['support'][:,:2]).convex_hull.buffer(.5).intersection(remaining)
    if hull.area>.01:regions.append({'geometry':hull,'coefficients_cell_xy':fit['coef'].tolist(),'plane_index':i});remaining=remaining.difference(hull)
   for piece in getattr(remaining,'geoms',[remaining]):
    if piece.area<.01:continue
    i=min(range(len(fitted)),key=lambda j:MultiPoint(fitted[j]['support'][:,:2]).distance(piece.representative_point()))
    regions.append({'geometry':piece,'coefficients_cell_xy':fitted[i]['coef'].tolist(),'plane_index':i})
  coverage=unary_union([r['geometry'] for r in regions]);missing=outline.difference(coverage).area
  if missing>.02:raise ValueError('Roof coverage gap '+site)
  info={'cell_m':1.,'left_utm_m':center[0],'bottom_utm_m':center[1]}
  independent=False
  try:geometry,mesh_proof=planar_region_geometry(regions,info,origin,ground)
  except ValueError:
   if site!='edgewater_3457':raise
   independent=True;patch_geometry=[planar_region_geometry([r],info,origin,ground)[0] for r in regions];geometry=(sum([g[0] for g in patch_geometry],[]),[],[])
  primpath='/World/Landmarks/FinalOmissions/'+''.join(word.title() for word in site.split('_'));root=UsdGeom.Xform.Define(stage,primpath).GetPrim();root.SetCustomData({'parcelId':pid,'quality':'historical_roof_derived_pitched_draft','currentConditionsVerified':False,'groundWallsVerified':False})
  if independent:
   gates=[]
   for i,g in enumerate(patch_geometry):
    mesh,proof=finish_mesh(stage,primpath+'/RoofPatch'+str(i),g,wall,roofmat);gates.append(proof)
   gate={'passed_closed_shell':all(g['passed_closed_shell'] for g in gates),'component_gates':gates,'scope':'independent disjoint roof-plan volumes; internal shared walls retained'}
  else:mesh,gate=finish_mesh(stage,primpath+'/PitchedRoofMass',geometry,wall,roofmat)
  values=[];classified_values=[]
  for r in regions:
   selected=source[shapely.intersects_xy(r['geometry'],source[:,0],source[:,1])];a=np.c_[selected[:,:2]-center,np.ones(len(selected))];residuals=np.abs(a@np.asarray(r['coefficients_cell_xy'])-selected[:,2]);values.extend(residuals.tolist());classified_values.extend(residuals[selected[:,3]==6].tolist())
  target=Gf.Vec3d(outline.centroid.x-origin[0],outline.centroid.y-origin[1],4);cam=UsdGeom.Camera.Define(stage,'/World/Cameras/'+''.join(word.title() for word in site.split('_'))+'Evidence');cam.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(target+Gf.Vec3d(-45,-50,45),target,Gf.Vec3d(0,0,1)).GetInverse());cam.CreateFocalLengthAttr(35)
  records.append({'site_id':site,'parcel_id':pid,'prim_path':primpath,'camera':str(cam.GetPath()),'ground_reference_navd88_m':ground,'roof_support_outline_m2':outline.area,'plane_count':len(fitted),'patch_count':len(regions),'maximum_rendered_height_m':max(p[2] for p in geometry[0])-.1,'assigned_source_abs_residual_p50_p95_max_m':np.percentile(values,[50,95,100]).tolist(),'classified6_assigned_residual_p50_p95_max_m':np.percentile(classified_values,[50,95,100]).tolist(),'visual_acceptance':'pending_actual_render','source_fit_status':'provisional_high_residual_requires_review' if np.percentile(values,95)>.5 else 'broad_roof_planes_supported_with_local_outliers','source_classes':{str(int(k)):int(n) for k,n in zip(*np.unique(source[:,3],return_counts=True))},'planes':[{'coefficients_centered_xy':f['coef'].tolist(),'support_points':len(f['support']),'residual_p50_p95_max_m':f['residual']} for f in fitted],'closed_shell':gate,'quality':'historical_source_fitted_draft_pending_render','roof_outline_simplification_tolerance_m':.65,'outline_vertex_contact_regularization_m':.12,'independent_roof_patch_volumes':independent,'raw_property_links_promoted':False,'activated':False})
 stage.GetRootLayer().Export(str(path));report={'source_snapshot':active['snapshot'],'proposal_layer':str(path.relative_to(ROOT)).replace('\\','/'),'layer_sha256':sha(path),'dependencies':{**evidence['dependencies'],'data/heights/final_omissions/diagnostics.json':sha(ROOT/'data/heights/final_omissions/diagnostics.json'),'data/heights/final_omissions/roof_support.geojson':sha(ROOT/'data/heights/final_omissions/roof_support.geojson'),'tools/build_final_omission_roofs.py':sha(Path(__file__))},'sites':records,'limits':['2018–2019 historical source; exact flight day and current geometry unverified.','Roof support outlines are simplified classified point-cell boundaries, not surveyed ground walls; no imagery tracing.','Rugby738 and3457 stepped patches use broad source support domains; architectural seam placement remains approximate. 3457 has high full-cloud residual and requires visual/source interpretation before acceptance.','3457 enclosed grid holes are capped only where at least four class1/6 roof-height returns corroborate roof presence; no ground void invented.','No dormers, entrances, windows, signage or facade details invented; no active/root edits.']};save(ROOT/'data/heights/final_omissions/roof_proposal_manifest.json',report);print([(r['site_id'],r['plane_count'],r['patch_count'],r['assigned_source_abs_residual_p50_p95_max_m']) for r in records]);print(report['layer_sha256'])
if __name__=='__main__':build()




