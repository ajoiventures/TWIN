"""Bounded historical evidence for the final three original omission candidates."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
import shapely.affinity
from shapely.geometry import shape,mapping
from pyproj import Transformer
from princeton_evidence import read_points
from verify_retail_block import read,save,sha
SITES=[('rugby_720','292214077700010'),('rugby_738','292214077700020'),('edgewater_3457','292211305603460')]
def roof_support(points,parcel):
 from scipy import ndimage
 from shapely.geometry import box
 from shapely.ops import unary_union
 roof=points[(points[:,3]==6)&shapely.contains_xy(parcel,points[:,0],points[:,1])]
 if len(roof)<100:return None,[]
 left,bottom=np.floor(roof[:,:2].min(axis=0));ix=np.floor(roof[:,0]-left).astype(int);iy=np.floor(roof[:,1]-bottom).astype(int)
 width,height=int(ix.max()+1),int(iy.max()+1);counts=np.bincount(iy*width+ix,minlength=width*height).reshape(height,width)
 labels,n=ndimage.label(counts>=3);geometries=[];components=[]
 for label in range(1,n+1):
  yy,xx=np.where(labels==label)
  if len(xx)<8:continue
  g=unary_union([box(left+x,bottom+y,left+x+1,bottom+y+1) for y,x in zip(yy,xx)]).intersection(parcel)
  if g.area<8:continue
  q=roof[shapely.intersects_xy(g,roof[:,0],roof[:,1])];center=np.mean(q[:,:2],axis=0);a=np.c_[q[:,:2]-center,np.ones(len(q))];coef=np.linalg.lstsq(a,q[:,2],rcond=None)[0];res=np.abs(a@coef-q[:,2])
  components.append({'source_dense_cell_area_m2':g.area,'support_points':len(q),'z_p05_p50_p95_navd88_m':np.percentile(q[:,2],[5,50,95]).tolist(),'single_plane_abs_residual_p50_p95_m':np.percentile(res,[50,95]).tolist(),'interpretation':'classified roof-cell support, not wall footprint or architectural roof mesh'})
  geometries.append(g)
 return unary_union(geometries) if geometries else None,components

def build(live=False):
 units=read(ROOT/'data/heights/vertical_unit_check.json')
 if not units.get('accepted') or units.get('ept_z_unit')!='meters':raise ValueError('Accepted EPT meter units required')
 active=read(ROOT/'data/processed/active.json');features=read(ROOT/active['relative_path']/'parcels.json')['features'];config=read(ROOT/'config/princeton_sources.json');config.update({'ept_max_depth':10,'maximum_ept_nodes':100,'maximum_node_bytes':16777216})
 from pxr import Usd,UsdGeom
 from constrain_scene import mesh_footprint
 from shapely.strtree import STRtree
 stage=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'));visible=[];paths=[]
 origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*read(ROOT/'config/study_area.json')['local_origin_wgs84'])
 for prim in stage.Traverse():
  if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible' and str(prim.GetPath()).startswith(('/World/Buildings/','/World/Landmarks/')):
   g=mesh_footprint(prim)
   if not g.is_empty:
    visible.append(shapely.affinity.translate(g,*origin));paths.append(str(prim.GetPath()))
 tree=STRtree(visible)
 t=Transformer.from_crs(4326,32617,always_xy=True);back=Transformer.from_crs(32617,4326,always_xy=True);rows=[];geo=[];dependencies={}
 for site,pid in SITES:
  f=next(f for f in features if f['properties']['parcel_id']==pid);parcel=shapely.transform(shape(f['geometry']),t.transform,interleaved=False);out=ROOT/'data/heights/final_omissions'/site;out.mkdir(parents=True,exist_ok=True);cloud=out/'points.npz';receipt=out/'acquisition.json'
  if cloud.exists() and receipt.exists():
   packet=read(receipt)
   if packet['source_snapshot']!=active['snapshot'] or sha(cloud)!=packet['cloud_sha256']:raise ValueError('Stale final omission cloud')
   if packet['parcel_geometry']!=f['geometry']:raise ValueError('Parcel search geometry changed')
   points=np.load(cloud)['points']
  else:
   points,source=read_points(config,shape(f['geometry']),ROOT,live);np.savez_compressed(cloud,points=points);packet={'source_snapshot':active['snapshot'],'site_id':site,'parcel_id':pid,'source':source,'cloud_sha256':sha(cloud),'parcel_geometry':f['geometry']};save(receipt,packet)
  frame=read(out/'aerial_receipt.json')
  if sha(out/'aerial2025_local_review.jpg')!=frame['image_sha256']:raise ValueError('Aerial local review bytes changed')
  ground=points[points[:,3]==2,2];roof=points[points[:,3]==6];row={'site_id':site,'parcel_id':pid,'official_record':f['properties'],'points':len(points),'class_counts':{str(int(k)):int(n) for k,n in zip(*np.unique(points[:,3],return_counts=True))},'ground_p05_p50_p95_m':np.percentile(ground,[5,50,95]).tolist() if len(ground) else None,'class6_z_p05_p50_p95_m':np.percentile(roof[:,2],[5,50,95]).tolist() if len(roof) else None,'cloud_sha256':sha(cloud),'parcel_area_m2':parcel.area};outline,components=roof_support(points,parcel);row['roof_support_components']=components
  row['state']='historical_classified_roof_present_current_wall_shape_unverified' if outline is not None else 'roof_support_inconclusive'
  row['physical_building_count']=None;row['current_geometry_verified']=False;row['proposal_activated']=False
  row['interpretation']='Built-site evidence: vacant label does not establish vacant land' if site=='edgewater_3457' else 'Distinct pitched-roof building visible qualitatively in official 2025 aerial; historical cloud supports missing roof form'
  row['aerial_review']={'nominal_year':2025,'capture_day':'unknown','use':'local qualitative only; no traced geometry','reviewed_building_present':True}
  if outline is not None:
   row['visible_building_overlaps']=[{'usd_path':paths[int(i)],'roof_support_overlap_m2':outline.intersection(visible[int(i)]).area} for i in tree.query(outline) if outline.intersection(visible[int(i)]).area>.01]
   row['historical_roof_omission_confirmed_against_current_stage']=not row['visible_building_overlaps']
   row['roof_support_area_m2']=outline.area
   geo.append({'type':'Feature','geometry':mapping(shapely.transform(outline,back.transform,interleaved=False)),'properties':{'site_id':site,'parcel_id':pid,'state':row['state'],'geometry_role':'source classified roof support only; never ground walls'}})
  for path in [cloud,receipt,out/'aerial_receipt.json',out/'aerial2025_local_review.jpg']:
   if path.exists():dependencies[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
  rows.append(row)
 for layer in stage.GetUsedLayers():
  if layer.realPath:
   path=Path(layer.realPath).resolve()
   if path.is_relative_to(ROOT):dependencies[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
 dependencies[str((ROOT/active['relative_path']/'parcels.json').relative_to(ROOT)).replace('\\','/')]=sha(ROOT/active['relative_path']/'parcels.json')
 dependencies['tools/verify_final_omissions.py']=sha(Path(__file__));dependencies['data/processed/active.json']=sha(ROOT/'data/processed/active.json')
 save(ROOT/'data/heights/final_omissions/diagnostics.json',{'source_snapshot':active['snapshot'],'dependencies':dependencies,'source_acquisition':'USGS OrangeCounty2018, 2018-12-04 to 2019-04-12; exact local flight day unknown','rows':rows,'limits':['No active writes, no parcel extrusion, no current ground-wall or facade verification.','Historical roof presence is established; whole-building footprint, roof planes and current scene integration remain pending.','One-meter classified dense-cell polygons are source support, not surveyed outlines; no hole closing or aerial tracing. Parcel clipping can omit overhangs or continuations outside search boundaries.']})
 save(ROOT/'data/heights/final_omissions/roof_support.geojson',{'type':'FeatureCollection','source_snapshot':active['snapshot'],'features':geo});print(json.dumps(rows,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');build(p.parse_args().live)
