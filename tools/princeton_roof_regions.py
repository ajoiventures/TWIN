"""Connected source-plane regions with measured adjacency and analytical boundaries.
Produces2D diagnostics only; no scene/root edits or roof activation.
"""
from pathlib import Path
import os,sys,json,datetime,itertools
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import shape,MultiPoint,box,Point,mapping
from shapely.ops import unary_union
from scipy import ndimage
from scipy.spatial import cKDTree
from pyproj import Transformer
from pxr import Usd
from constrain_scene import mesh_footprint
from verify_retail_block import read,save,sha
from office_roof_architecture import halfspace
FROZEN=ROOT/'data/heights/princeton/rejected_65eb74f6ffcaee3d'
def build():
 manifest=read(FROZEN/'data/heights/princeton/coherent_roof_manifest.json')
 if read(ROOT/'data/processed/active.json')['snapshot']!=manifest['source_snapshot'] or sha(FROZEN/manifest['support_array_path'])!=manifest['support_array_sha256'] or sha(ROOT/'data/heights/princeton/points.npz')!=manifest['source_cloud_sha256']:raise ValueError('Frozen historical source/support identity changed')
 support=np.load(FROZEN/manifest['support_array_path']);center=np.asarray(manifest['fit_origin_utm_m']);source=np.load(ROOT/'data/heights/princeton/points.npz')['points'];config=read(ROOT/'config/princeton_sources.json');origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*config['origin_wgs84']);stage=Usd.Stage.Open(str(ROOT/'scene/princeton_correction.usda'));outline=shapely.affinity.translate(mesh_footprint(stage.GetPrimAtPath('/World/Landmarks/PrincetonAtCollegePark/EasternVariableRoof')),*origin);protected=unary_union([box(*x['bounds']) for x in config['protected_voids_utm']]);outline=outline.difference(protected);regions=[];rejected_clusters=[];merged_planes=[]
 candidates=[]
 for plane in manifest['planes']:
  candidates.append({'plane_index':plane['plane_index'],'coefficients_centered_xy':plane['coefficients_centered_xy'],'points':support['plane'+str(plane['plane_index'])],'source_plane_indices':[plane['plane_index']]})
 for i,a in enumerate(candidates):
  if a.get('merged'):continue
  for b in candidates[i+1:]:
   if b.get('merged'):continue
   ca=np.asarray(a['coefficients_centered_xy']);cb=np.asarray(b['coefficients_centered_xy']);na=np.r_[-ca[:2],1.];nb=np.r_[-cb[:2],1.];angle=float(na@nb/(np.linalg.norm(na)*np.linalg.norm(nb)))
   if angle<.998:continue
   combined=np.concatenate([a['points'],b['points']]);x=np.c_[combined[:,:2]-center,np.ones(len(combined))];gap=np.percentile(np.abs(x@(ca-cb)),95)
   if gap>.2:continue
   c=np.linalg.lstsq(x,combined[:,2],rcond=None)[0];res=np.percentile(np.abs(x@c-combined[:,2]),95)
   if res>.18:continue
   a['coefficients_centered_xy']=c.tolist();a['points']=combined;a['source_plane_indices']+=b['source_plane_indices'];b['merged']=True;merged_planes.append({'target_plane':a['plane_index'],'source_planes':b['source_plane_indices'],'combined_fit_p95_m':float(res),'predicted_plane_gap_p95_m':float(gap)})
 candidates=[p for p in candidates if not p.get('merged')]
 for plane in candidates:
  index=plane['plane_index'];q=plane['points'];cell=.75;left,bottom=np.floor(q[:,:2].min(0)/cell)*cell;xy=np.floor((q[:,:2]-[left,bottom])/cell).astype(int);w,h=xy.max(0)+1;grid=np.zeros((h,w),bool);grid[xy[:,1],xy[:,0]]=True;labels,_=ndimage.label(grid,structure=np.ones((3,3)));point_labels=labels[xy[:,1],xy[:,0]];hulls=[];kept=[]
  for label in np.unique(point_labels):
   cluster=q[point_labels==label]
   if len(cluster)<80:rejected_clusters.append({'plane_index':index,'points':len(cluster),'reason':'Small/disconnected support cluster; no architectural region inferred'});continue
   hull=MultiPoint(cluster[:,:2]).convex_hull
   if hull.area<3:rejected_clusters.append({'plane_index':index,'points':len(cluster),'reason':'Insufficient2Dsupport area'});continue
   # Rounded support buffer is a confidence bound, never a ridge/valley inference.
   confidence_cell=.5;lo=np.floor(cluster[:,:2].min(0)/confidence_cell)*confidence_cell;cells=np.floor((cluster[:,:2]-lo)/confidence_cell).astype(int)+1;cw,ch=cells.max(0)+2;mask=np.zeros((ch,cw),bool);mask[cells[:,1],cells[:,0]]=True;mask=ndimage.binary_dilation(mask,structure=np.ones((3,3)));yy,xx=np.where(mask);confidence=unary_union([box(lo[0]+(x-1)*confidence_cell,lo[1]+(y-1)*confidence_cell,lo[0]+x*confidence_cell,lo[1]+y*confidence_cell) for y,x in zip(yy,xx)])
   hull=hull.buffer(.25,join_style=2).intersection(outline).intersection(confidence)
   if hull.area>1:hulls.append(hull);kept.append(cluster)
  if hulls:regions.append({'plane_index':index,'coefficients':plane['coefficients_centered_xy'],'geometry':unary_union(hulls),'points':np.concatenate(kept),'cluster_count':len(hulls),'source_plane_indices':plane['source_plane_indices']})
 joins=[];unresolved=[];unknown=[]
 for ia,ib in itertools.combinations(range(len(regions)),2):
  a,b=regions[ia],regions[ib];overlap=a['geometry'].intersection(b['geometry'])
  if overlap.area<.002:continue
  ca=np.asarray(a['coefficients']);cb=np.asarray(b['coefficients']);difference=ca-cb;pa=a['points'];pb=b['points'];neighborhood=overlap.buffer(1.0);local_a=pa[shapely.intersects_xy(neighborhood,pa[:,0],pa[:,1])];local_b=pb[shapely.intersects_xy(neighborhood,pb[:,0],pb[:,1])];pa=local_a if len(local_a)>=15 else pa;pb=local_b if len(local_b)>=15 else pb;ha=np.c_[pa[:,:2]-center,np.ones(len(pa))]@difference;hb=np.c_[pb[:,:2]-center,np.ones(len(pb))]@difference;ma=float(np.median(ha));mb=float(np.median(hb));signa=float(np.mean(ha<=0)) if ma<=0 else float(np.mean(ha>=0));signb=float(np.mean(hb<=0)) if mb<=0 else float(np.mean(hb>=0));near=float(cKDTree(pa[:,:3]).query(pb[:,:3],k=1,workers=1)[0].min())
  if ma*mb<0 and signa>=.8 and signb>=.8 and near<=2.0 and np.linalg.norm(difference[:2])>.01:
   model=shapely.affinity.translate(overlap,-center[0],-center[1]);c=difference if ma<=0 else -difference;part=halfspace(model,*c);part=shapely.affinity.translate(part,*center);other=overlap.difference(part);a['geometry']=a['geometry'].difference(overlap).union(part);b['geometry']=b['geometry'].difference(overlap).union(other)
   joins.append({'plane_a':a['plane_index'],'plane_b':b['plane_index'],'method':'analyticalheight-equalityline, sides independently supported by source inliers','a_side_fraction':signa,'b_side_fraction':signb,'a_local_support_points':len(pa),'b_local_support_points':len(pb),'closest_measured3Dsupport_m':near,'overlap_partitioned_m2':overlap.area,'boundary_height_jump_m':0.0})
  else:
   a['geometry']=a['geometry'].difference(overlap);b['geometry']=b['geometry'].difference(overlap);unknown.append(overlap);unresolved.append({'plane_a':a['plane_index'],'plane_b':b['plane_index'],'area_m2':overlap.area,'reason':'No unique source-supported ridge/valley relation; retain original approximation instead of nearest-plane stair interface','a_side_fraction':signa,'b_side_fraction':signb,'a_local_support_points':len(pa),'b_local_support_points':len(pb),'closest_measured3Dsupport_m':near})
 for r in regions:
  if r['geometry'].geom_type=='GeometryCollection':r['geometry']=unary_union([g for g in r['geometry'].geoms if g.geom_type in ['Polygon','MultiPolygon']])
 regions=[r for r in regions if not r['geometry'].is_empty and r['geometry'].area>.01];union=unary_union([r['geometry'] for r in regions]);unknown_union=outline.difference(union);residual=[];bound=0.;features=[];to_wgs=Transformer.from_crs(32617,4326,always_xy=True)
 def export_geometry(geometry):
  value=shapely.make_valid(shapely.transform(geometry,to_wgs.transform,interleaved=False))
  if value.geom_type=='GeometryCollection':value=unary_union([g for g in value.geoms if g.geom_type in ['Polygon','MultiPolygon']])
  return mapping(shapely.set_precision(value,1e-9))
 for r in regions:
  p=source[(source[:,3]==6)&shapely.intersects_xy(r['geometry'],source[:,0],source[:,1])];a=np.c_[p[:,:2]-center,np.ones(len(p))];e=np.abs(a@np.asarray(r['coefficients'])-p[:,2]);residual.extend(e.tolist());boundary=shapely.get_coordinates(r['geometry'].boundary.segmentize(.2));maximum=float(cKDTree(r['points'][:,:2]).query(boundary,k=1,workers=1)[0].max());bound=max(bound,maximum);features.append({'type':'Feature','id':'plane:'+str(r['plane_index']),'geometry':export_geometry(r['geometry']),'properties':{'plane_index':r['plane_index'],'coefficients_centered_xy':r['coefficients'],'merged_source_plane_indices':r['source_plane_indices'],'area_m2':r['geometry'].area,'source_clusters':r['cluster_count'],'assigned_class6_residual_p50_p95_max_m':np.percentile(e,[50,95,100]).tolist() if len(e) else None,'boundary_sample_max_support_distance_m':maximum}})
 out=ROOT/'data/heights/princeton/architectural_regions';out.mkdir(parents=True,exist_ok=True);save(out/'regions.geojson',{'type':'FeatureCollection','features':features});save(out/'unresolved.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','geometry':export_geometry(unknown_union),'properties':{'status':'retain_original_approximation_not_source_fitted_architecture'}}]})
 x0,y0,x1,y1=outline.bounds;scale=8;paths=[]
 def svgpath(g):
  result=[]
  for polygon in getattr(g,'geoms',[g]):
   if polygon.geom_type!='Polygon':continue
   for ring in [polygon.exterior,*polygon.interiors]:result.append('M'+' L'.join(f'{(x-x0)*scale+10:.2f},{(y1-y)*scale+10:.2f}' for x,y in ring.coords)+' Z')
  return ' '.join(result)
 paths.append('<path fill="#d8d8d8" fill-rule="evenodd" d="'+svgpath(unknown_union)+'"/>')
 for r in regions:paths.append('<path fill="hsl('+str(r['plane_index']*47%360)+',55%,65%)" stroke="#223" stroke-width=".6" fill-rule="evenodd" d="'+svgpath(r['geometry'])+'"><title>Plane'+str(r['plane_index'])+'</title></path>')
 (out/'regions.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+str((x1-x0)*scale+20)+' '+str((y1-y0)*scale+20)+'">'+''.join(paths)+'</svg>',encoding='utf-8');from PIL import Image,ImageDraw
 import colorsys
 image=Image.new('RGB',(int((x1-x0)*11)+50,int((y1-y0)*11)+70),'white')
 def paint(geometry,color):
  overlay=Image.new('RGBA',image.size,(0,0,0,0));draw=ImageDraw.Draw(overlay)
  for polygon in getattr(geometry,'geoms',[geometry]):
   if polygon.geom_type!='Polygon':continue
   xy=lambda ring:[((x-x0)*11+25,(y1-y)*11+45) for x,y in ring.coords]
   draw.polygon(xy(polygon.exterior),fill=color,outline='#333333')
   for ring in polygon.interiors:draw.polygon(xy(ring),fill=(0,0,0,0),outline='#333333')
  image.paste(overlay,(0,0),overlay)
 paint(unknown_union,'#cccccc')
 for region in regions:
  rgb=tuple(int(v*255) for v in colorsys.hsv_to_rgb((region['plane_index']*.618)%1,.42,.88));paint(region['geometry'],rgb)
 labels=ImageDraw.Draw(image)
 for region in regions:
  c=region['geometry'].representative_point();labels.text(((c.x-x0)*11+25,(y1-c.y)*11+45),str(region['plane_index']),fill='black')
 labels.text((20,12),'Connected source-plane regions; grey retains unresolved original approximation',fill='black');image.save(out/'regions.png')
 report={'status':'2Dsource-and-seam-diagnostic_only_no3Dpromotion','source_snapshot':manifest['source_snapshot'],'original_rejected_proposal_sha256':manifest['layer_sha256'],'geojson_export_precision_degrees':1e-9,'geojson_export_policy':'Polygonal make-valid plus submillimeter WGS84 serialization grid only; UTM analytical regions/source-fit calculations unchanged','fit_origin_utm_m':center.tolist(),'source_supported_area_m2':union.area,'retain_original_unresolved_area_m2':unknown_union.area,'plane_regions':len(regions),'merged_coplanar_fits':merged_planes,'support_confidence_bound_m':float(np.sqrt(.5)+2*np.sqrt(.125)),'support_bound_method':'0.5m occupancy grid uses only one8neighbor dilation; actualsource-to-seedcenter plus seed-to-neighborcenter plus neighborcenter-to-corner <=1.414214m. This is confidence clipping only, not plane-label partitioning.','analytic_shared_boundaries':joins,'unresolved_relations':unresolved,'small_unsupported_clusters':rejected_clusters,'class6_residual_p50_p95_max_m':np.percentile(residual,[50,95,100]).tolist(),'boundary_sample_max_support_m':bound,'protected_courtyard_overlap_m2':union.intersection(protected).area,'dependencies':{str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in [FROZEN/'data/heights/princeton/coherent_roof_manifest.json',FROZEN/manifest['support_array_path'],ROOT/'data/heights/princeton/points.npz',ROOT/'scene/princeton_correction.usda',ROOT/'config/princeton_sources.json',Path(__file__)]},'source_regions':features,'limits':['No architectural ridge/valley is asserted merely from min/max planes; accepted joins require measured adjacent source supports and independently consistent opposite halfspaces.','Confidence outlines come from source-point hulls clipped to rigorously1.414214m-bounded source occupancy neighborhoods; no aerial tracing, sourcepixels or current/photorealism acceptance.','Grey unresolved regions retain original approximation in a futureproposal; no new microterrace interfaces are invented.']};save(out/'diagnostics.json',report);print(json.dumps({k:report[k] for k in ['source_supported_area_m2','retain_original_unresolved_area_m2','plane_regions','class6_residual_p50_p95_max_m','boundary_sample_max_support_m','protected_courtyard_overlap_m2']},indent=2));print('analytic joins',len(joins),'unresolved',len(unresolved))
if __name__=='__main__':build()
