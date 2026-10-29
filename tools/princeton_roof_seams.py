"""CPU-only diagnostic of analytical roof joins against retained original roof."""
from pathlib import Path
import os,sys,json
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import shape,Point,Polygon
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from shapely.strtree import STRtree
from pyproj import Transformer
from pxr import Usd,UsdGeom
from verify_retail_block import read,save,sha

def build():
 folder=ROOT/'data/heights/princeton/architectural_regions';report=read(folder/'diagnostics.json');origin=Transformer.from_crs(4326,32617,always_xy=True).transform(-81.389,28.572);project=Transformer.from_crs(4326,32617,always_xy=True);center=np.asarray(report['fit_origin_utm_m']);stage=Usd.Stage.Open(str(ROOT/'scene/princeton_correction.usda'));mesh=UsdGeom.Mesh(stage.GetPrimAtPath('/World/Landmarks/PrincetonAtCollegePark/EasternVariableRoof'));points=np.asarray(mesh.GetPointsAttr().Get(),float);counts=list(mesh.GetFaceVertexCountsAttr().Get());indices=list(mesh.GetFaceVertexIndicesAttr().Get());offset=0;polygons=[];coefficients=[];face_ids=[]
 for face,count in enumerate(counts):
  v=points[indices[offset:offset+count]];offset+=count
  if count<3 or np.cross(v[1]-v[0],v[2]-v[0])[2]<=1e-9:continue
  for j in range(1,count-1):
   tri=v[[0,j,j+1]];xy=tri[:,:2]+origin;p=Polygon(xy)
   if p.area<.0001:continue
   c=np.linalg.solve(np.c_[xy-center,np.ones(3)],tri[:,2]);polygons.append(p);coefficients.append(c);face_ids.append(face)
 tree=STRtree(polygons);source_outline=unary_union(polygons);unknown=shapely.set_precision(shapely.make_valid(shapely.transform(shape(read(folder/'unresolved.geojson')['features'][0]['geometry']),project.transform,interleaved=False)),.001);cloud=np.load(ROOT/'data/heights/princeton/points.npz')['points'];raw=cloud[(cloud[:,3]==6)&(cloud[:,2]>41)&(cloud[:,2]<48)];rawtree=cKDTree(raw[:,:2]);ground=31.59;rows=[];all_delta=[];missing=0;features=[]
 for f in read(folder/'regions.geojson')['features']:
  g=shapely.set_precision(shapely.make_valid(shapely.transform(shape(f['geometry']),project.transform,interleaved=False)),.001);c=np.asarray(f['properties']['coefficients_centered_xy']);interface=g.boundary.intersection(unknown.boundary.buffer(.003)).difference(source_outline.boundary.buffer(.02));samples=shapely.get_coordinates(interface.segmentize(.25));delta=[];bad=[]
  for xy in samples:
   point=Point(*xy);hits=[int(i) for i in tree.query(point.buffer(.002)) if polygons[int(i)].distance(point)<.002]
   if not hits:missing+=1;continue
   a=np.r_[xy-center,1.];fit=float(a@c-ground+.1);old=[float(a@coefficients[i]) for i in hits];baseline=float(np.median(old));difference=fit-baseline;delta.append(abs(difference));all_delta.append(abs(difference))
   if abs(difference)>.2:
    near=raw[rawtree.query_ball_point(xy,.5)];fit_errors=np.abs(np.c_[near[:,:2]-center,np.ones(len(near))]@c-near[:,2]) if len(near) else np.array([]);original_errors=[]
    for measured in near:
     source_point=Point(*measured[:2]);source_hits=[int(i) for i in tree.query(source_point.buffer(.002)) if polygons[int(i)].distance(source_point)<.002]
     if source_hits:
      source_a=np.r_[measured[:2]-center,1.];old_z=float(np.median([source_a@coefficients[i] for i in source_hits]))+ground-.1;original_errors.append(abs(measured[2]-old_z))
    original_errors=np.asarray(original_errors);classification='source_neighborhood_unresolved'
    if len(near)>=5 and np.percentile(fit_errors,95)<=.25:classification='measured_neighbor_supports_fitted_surface_over_original_approximation'
    elif len(original_errors)>=5 and np.percentile(original_errors,95)<=.25:classification='measured_neighbor_prefers_original_surface_or_true_step'
    bad.append({'utm_xy':xy.tolist(),'fitted_relative_z_m':fit,'original_relative_z_m':baseline,'difference_m':difference,'source_faces':[face_ids[i] for i in hits],'neighbor_class6_points':len(near),'neighbor_fitted_error_p50_p95_m':np.percentile(fit_errors,[50,95]).tolist() if len(near) else None,'neighbor_original_error_p50_p95_m':np.percentile(original_errors,[50,95]).tolist() if len(original_errors) else None,'interpretation':classification});features.append({'type':'Feature','geometry':{'type':'Point','coordinates':list(Transformer.from_crs(32617,4326,always_xy=True).transform(*xy))},'properties':{'plane_index':f['properties']['plane_index'],'seam_delta_m':difference,'status':'do_not_close_with_artificial_wall'}})
  rows.append({'plane_index':f['properties']['plane_index'],'samples':len(delta),'above_point2m':len(bad),'boundary_delta_p50_p95_max_m':np.percentile(delta,[50,95,100]).tolist() if delta else None,'conflict_samples':bad})
 result={'source_snapshot':report['source_snapshot'],'interface_scope':'Known-to-retained-uncertain boundaries only; original outer/courtyard boundaries and analytical known-known seams excluded','status':'interface_diagnostic_not_geometry_acceptance','sample_spacing_m':.25,'datum':'relative prototype geometry; fittedNAVD88 minus31.59ground plus.1displaybase','boundary_delta_p50_p95_max_m':np.percentile(all_delta,[50,95,100]).tolist(),'samples':len(all_delta),'missing_source_triangle_samples':missing,'above_point2m':sum(r['above_point2m'] for r in rows),'conflict_source_classification':{name:sum(c['interpretation']==name for r in rows for c in r['conflict_samples']) for name in ['measured_neighbor_supports_fitted_surface_over_original_approximation','measured_neighbor_prefers_original_surface_or_true_step','source_neighborhood_unresolved']},'planes':rows,'diagnostic_thresholds':{'height_delta_trigger_m':.2,'source_neighborhood_radius_m':.5,'minimum_source_points':5,'source_preference_p95_m':.25,'meaning':'Diagnostic conflict thresholds, not survey/engineering accuracy acceptance'},'source_observation':'2018-2019historicalclass6; comparison uses samecached acquisition, not independent temporal/current validation','closing_policy':'No seamwall or inferredroofbridge authored. Large source-versus-original deltas require physical/source interpretation before a jointly continuous candidate.','dependencies':{'scene/princeton_correction.usda':sha(ROOT/'scene/princeton_correction.usda'),'data/heights/princeton/architectural_regions/regions.geojson':sha(folder/'regions.geojson'),'tools/princeton_roof_seams.py':sha(Path(__file__)),'data/heights/princeton/architectural_regions/unresolved.geojson':sha(folder/'unresolved.geojson'),'data/heights/princeton/points.npz':sha(ROOT/'data/heights/princeton/points.npz'),'data/heights/princeton/manifest.json':sha(ROOT/'data/heights/princeton/manifest.json')}};save(folder/'seams.json',result);save(folder/'seam_conflicts.geojson',{'type':'FeatureCollection','features':features});print(json.dumps({k:result[k] for k in ['boundary_delta_p50_p95_max_m','samples','missing_source_triangle_samples','above_point2m']},indent=2));return result
if __name__=='__main__':build()
