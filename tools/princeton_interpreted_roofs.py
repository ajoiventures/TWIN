"""Photo-established roof components, source-anchored interpreted hips; proposal only.

Run with the project's Python and .dependencies. No downloads or active writes.
The component footprints/joins are estimates, not traced aerial measurements.
"""
from pathlib import Path
import os,sys,json,datetime
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import box,Point,mapping
from shapely.ops import unary_union
from scipy.optimize import least_squares
from pyproj import Transformer
from pxr import Usd,UsdGeom,UsdShade,Gf,Sdf
from verify_retail_block import read,save,sha
from constrain_scene import mesh_footprint
from office_roof_architecture import halfspace,finish_mesh,material
from reconstruct_landmarks import planar_region_geometry

TARGET='/World/Landmarks/PrincetonAtCollegePark/EasternVariableRoof'
NEW='/World/Landmarks/PrincetonAtCollegePark/InterpretedCoherentRoof'
# Local metric search windows follow broad historical roof supports. Topological
# interpretation is corroborated by the completed original contractor oblique.
# These are neither photo-traced coordinates nor certified architectural sizes.
COMPONENTS=[
 ('NorthWestCap',(109,-33,135,-20),0.,[3,21]),
 ('NorthCurveCap',(132,-41,151,-22),45.,[14,24]),
 ('MiddleCurveCap',(145,-50,164,-31),45.,[5,17]),
 ('CourtyardPavilion',(131,-55,146,-40),45.,[6,26]),
 ('EastCurveCap',(159,-64,173,-46),0.,[10,22,23,27]),
 ('SouthWestCap',(113,-84,133,-74),0.,[11]),
 ('SouthSquareCap',(137,-84,150,-72),0.,[12,18,19,25]),
 ('SouthFrontCap',(155,-84,177,-61),0.,[1,2]),
 ('SouthEastCap',(175,-84,191,-61),0.,[1,4,20]),
 ('CornerCap',(180,-77,198,-63),45.,[9,13]),
]

def planes_from_parameters(p,base):
 cx,cy,hx,hy,angle,*slopes=p
 u=np.array([np.cos(angle),np.sin(angle)]);v=np.array([-u[1],u[0]]);center=np.array([cx,cy]);out=[]
 for axis,half,sl,sign in [(u,hx,slopes[0],1),(u,hx,slopes[1],-1),(v,hy,slopes[2],1),(v,hy,slopes[3],-1)]:
  a=axis*sl*sign;out.append(np.r_[a,base+sl*half-a@center])
 return out

def predict(xy,planes,base):return np.maximum(base,np.min(np.c_[xy,np.ones(len(xy))]@np.asarray(planes).T,axis=1))

def components(source,support,origin,base):
 out=[]
 for name,bounds,degrees,ids in COMPONENTS:
  x0,y0,x1,y1=bounds;center=np.array([(x0+x1)/2,(y0+y1)/2]);angle=np.deg2rad(degrees)
  q=np.concatenate([support['plane'+str(i)] for i in ids]);local=q[:,:2]-origin
  keep=(local[:,0]>=x0)&(local[:,0]<=x1)&(local[:,1]>=y0)&(local[:,1]<=y1)&(q[:,2]>base+.12)
  q=q[keep];local=local[keep]
  if len(q)<80:raise ValueError('Insufficient actual source support: '+name)
  axes=np.array([[np.cos(angle),np.sin(angle)],[-np.sin(angle),np.cos(angle)]]);uv=(local-center)@axes.T
  # Starting extents are anchored to actual high-roof points, including the
  # eave descent implied by the observed slope. Fits remain bounded estimates.
  half=np.percentile(np.abs(uv),99,axis=0)+.55
  p0=np.r_[center,half,angle,.45,.45,.45,.45]
  lower=np.r_[center-4.,np.maximum(half-4.,1.5),angle-.18,.22,.22,.22,.22]
  upper=np.r_[center+4.,half+4.,angle+.18,.75,.75,.75,.75]
  guard=[np.array([.75,0.,base-.75*x0]),np.array([-.75,0.,base+.75*x1]),np.array([0.,.75,base-.75*y0]),np.array([0.,-.75,base+.75*y1])]
  sample=np.arange(len(q))[::max(1,len(q)//3500)];xy=local[sample];z=q[sample,2]
  def objective(p):
   return np.r_[predict(xy,planes_from_parameters(p,base)+guard,base)-z,.07*(p[:4]-p0[:4]),.2*(p[4]-p0[4])]
  fit=least_squares(objective,p0,bounds=(lower,upper),loss='soft_l1',f_scale=.12,max_nfev=250)
  planes=planes_from_parameters(fit.x,base)+guard;error=np.abs(predict(local,planes,base)-q[:,2]);gradient=np.c_[local,np.ones(len(local))]@np.asarray(planes).T
  out.append({'name':name,'planes':planes,'parameters':fit.x.tolist(),'source_plane_ids':ids,'support_points':len(q),'source_support_residual_p50_p95_max_m':np.percentile(error,[50,95,100]).tolist(),'fitted_face_support_counts':np.bincount(gradient.argmin(1),minlength=8).tolist(),'estimated_extent_guard_planes':4,'estimated_dimensions_and_joins':True,'search_window_local_m':bounds,'optimization_success':bool(fit.success)})
 return out

def partition(outline,caps,base):
 # An explicit min-of-four-planes is one convex hip. Max over these hips and
 # the flat terrace creates continuous analytical ridge/valley intersections.
 # No cell labels, height snapping, interpolated corners or per-cell seam walls.
 basec=np.array([0.,0.,base]);positive=[];capregions=[]
 for cap in caps:
  domain=outline
  for c in cap['planes']:domain=halfspace(domain,*(basec-c))
  positive.append(domain)
 for n,cap in enumerate(caps):
  for face,c in enumerate(cap['planes']):
   region=positive[n]
   for other in cap['planes']:region=halfspace(region,*(c-other))
   for j,othercap in enumerate(caps):
    if n==j:continue
    higher=region
    for other in othercap['planes']:higher=halfspace(higher,*(c-other))
    region=region.difference(higher)
   if not region.is_empty and region.area>.00001:capregions.append({'geometry':region,'coefficients_cell_xy':c.tolist(),'architectural_component':cap['name'],'face_index':face,'quality':'photo_established_form_source_anchored_interpreted_dimensions'})
 terrace=outline.difference(unary_union(positive))
 if not terrace.is_empty:capregions.append({'geometry':terrace,'coefficients_cell_xy':basec.tolist(),'architectural_component':'LowerFlatTerraces','face_index':0,'quality':'source_anchored_interpreted_common_terrace_level'})
 return capregions

def build():
 config=read(ROOT/'config/princeton_sources.json');active=read(ROOT/'data/processed/active.json');historical=read(ROOT/'data/heights/princeton/manifest.json')
 frozen=ROOT/'data/heights/princeton/rejected_65eb74f6ffcaee3d';oldfit=read(frozen/'data/heights/princeton/coherent_roof_manifest.json')
 cloud=ROOT/'data/heights/princeton/points.npz';supportpath=frozen/oldfit['support_array_path'];photo=ROOT/'data/imagery/princeton_roof_references/contractor_149596176.jpg'
 if active['snapshot']!=historical['source_snapshot'] or sha(cloud)!=oldfit['source_cloud_sha256'] or sha(supportpath)!=oldfit['support_array_sha256']:raise ValueError('Historical source identity changed')
 if sha(photo)!='1bd09a2682ea1ee10b0b10dd17fb61a0ca4ebe6439e2d170f409398f8690f99f':raise ValueError('Completed-form reference changed')
 origin=np.asarray(Transformer.from_crs(4326,32617,always_xy=True).transform(*config['origin_wgs84']));source=np.load(cloud)['points'];support=np.load(supportpath)
 old=Usd.Stage.Open(str(ROOT/'scene/princeton_correction.usda'));original=mesh_footprint(old.GetPrimAtPath(TARGET));protected=unary_union([box(*v['bounds']) for v in config['protected_voids_utm']]);localprotected=shapely.affinity.translate(protected,*(-origin))
 ground=historical['grid']['ground_median_m'];base=float(oldfit['planes'][0]['coefficients_centered_xy'][2])
 restored=[];hole_evidence=[]
 for polygon in getattr(original,'geoms',[original]):
  for ring in polygon.interiors:
   hole=shapely.Polygon(ring);absolute=shapely.affinity.translate(hole,*origin);q=source[shapely.intersects_xy(absolute,source[:,0],source[:,1])];roof=q[(q[:,3]==6)&(q[:,2]>=base-.5)];fraction=len(roof)/max(1,len(q));high_fraction=float(np.mean(q[:,2]>=base-.5)) if len(q) else 0.;eligible=len(roof)>=10 and high_fraction>=.9 and hole.intersection(localprotected).area==0
   hole_evidence.append({'local_centroid_m':list(hole.centroid.coords[0]),'area_m2':hole.area,'all_returns':len(q),'roof_class6_above_terrace_minus50cm':len(roof),'roof_fraction':fraction,'all_class_high_return_fraction':high_fraction,'restored_continuous_estimated_roof':eligible,'source_z_p10_p50_p90_navd88_m':np.percentile(q[:,2],[10,50,90]).tolist() if len(q) else None})
   if eligible:restored.append(hole)
 outline=unary_union([original]+restored).simplify(1.,preserve_topology=True).buffer(-.015,join_style=2).buffer(.01,join_style=2).difference(localprotected)
 caps=components(source,support,origin,base)
 localregions=partition(outline,caps,base)
 union=unary_union([r['geometry'] for r in localregions]);overlap=sum(r['geometry'].area for r in localregions)-union.area
 if outline.symmetric_difference(union).area>.01 or overlap>.01:raise ValueError('Incomplete/overlapping analytic partition')
 localregions=[dict(r,geometry=shapely.make_valid(r['geometry'])) for r in localregions]
 regions=localregions
 geometry,proof=planar_region_geometry(regions,{'left_utm_m':0.,'bottom_utm_m':0.,'cell_m':1.},(0.,0.),ground)
 stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.Imageable(stage.OverridePrim(TARGET)).CreateVisibilityAttr().Set('invisible')
 brick=material(stage,'PrincetonInterpretedWall',(.55,.57,.55));roof=material(stage,'PrincetonInterpretedRoof',(.55,.57,.55));mesh,gate=finish_mesh(stage,NEW,geometry,brick,roof)
 mesh.GetPrim().SetCustomData({'quality':'historical_height_anchored_photo_interpreted_architectural_candidate_not_measured_current_roof','sourceSnapshot':active['snapshot'],'parcelId':config['parcel_id'],'estimatedJoins':True,'captureDate':'unknown','sourceAcquisition':'2018-12-04 through2019-04-12; exact local flight unknown','sourceVerticalDatum':'NAVD88 meters','groundReferenceNAVD88M':float(ground),'unsupportedSmallFeatures':'dormers/equipment omitted, not certified absent'})
 # Exact upward-face assignment is auditable independently of triangulation.
 face_provenance=[];offset=0;interior_wall_area=0.;maximum_interior_step_height=0.
 for face,count in enumerate(geometry[1]):
  q=np.asarray([geometry[0][i] for i in geometry[2][offset:offset+count]]);offset+=count;n=np.cross(q[1]-q[0],q[2]-q[0])
  if abs(n[2])<1e-8 and outline.boundary.distance(Point(*q[:,:2].mean(0)))>.01:
   interior_wall_area+=float(np.linalg.norm(n)/2);maximum_interior_step_height=max(maximum_interior_step_height,float(q[:,2].max()-q[:,2].min()))
  if n[2]>1e-8:
   xy=q[:,:2].mean(0);point=Point(*xy);candidates=[(i,r) for i,r in enumerate(localregions) if r['geometry'].distance(point)<.003];i,r=min(candidates,key=lambda ir:abs(np.r_[xy,1]@ir[1]['coefficients_cell_xy']-ground+.1-q[:,2].mean()))
   face_provenance.append({'face_index':face,'region_index':i,'component':r['architectural_component'],'plane_local_xy_navd88_m':r['coefficients_cell_xy'],'quality':r['quality']})
 residual_source=source[(source[:,3]==6)&shapely.intersects_xy(shapely.affinity.translate(outline,*origin),source[:,0],source[:,1])&(source[:,2]>41)&(source[:,2]<48)];xy=residual_source[:,:2]-origin
 predicted=np.maximum.reduce([np.full(len(xy),base)]+[predict(xy,c['planes'],base) for c in caps]);errors=np.abs(predicted-residual_source[:,2])
 camera=UsdGeom.Camera.Define(stage,'/World/Cameras/PrincetonInterpretedRoofEvidence');target=Gf.Vec3d(outline.centroid.x,outline.centroid.y,14);camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(target+Gf.Vec3d(100,-130,125),target,Gf.Vec3d(0,0,1)).GetInverse());camera.CreateFocalLengthAttr(35);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25)
 layer=ROOT/'scene/princeton_interpreted_roof_proposal.usda';stage.GetRootLayer().customLayerData={'proposalOnly':True,'sourceSnapshot':active['snapshot'],'sourcePrincetonLayerSha256':sha(ROOT/'scene/princeton_correction.usda'),'currentGeometryVerified':False,'estimatedDimensionsAndJoins':True};stage.GetRootLayer().Export(str(layer))
 style=Usd.Stage.CreateInMemory();style.OverridePrim(camera.GetPath());Sdf.CopySpec(stage.GetRootLayer(),camera.GetPath(),style.GetRootLayer(),camera.GetPath());neutral=material(style,'PrincetonInterpretedMatchedNeutral',(.55,.57,.55))
 for targetpath in [TARGET,NEW]:UsdShade.MaterialBindingAPI.Apply(style.OverridePrim(targetpath)).Bind(neutral)
 stylepath=ROOT/'scene/princeton_interpreted_roof_style.usda';style.GetRootLayer().Export(str(stylepath));reviews={}
 for name,layers in [('baseline',[stylepath.name,'college_park_connected.usda']),('proposal',[stylepath.name,layer.name,'college_park_connected.usda'])]:
  review=Usd.Stage.CreateInMemory();review.GetRootLayer().subLayerPaths=layers;review.GetRootLayer().customLayerData={'reviewOnly':True,'sourceSnapshot':active['snapshot'],'rootSha256':sha(ROOT/'scene/college_park_connected.usda'),'roofProposalSha256':sha(layer),'comparison':name,'sameCameraLightAndNeutralMaterial':True};path=ROOT/('scene/princeton_interpreted_roof_'+name+'_review.usda');review.GetRootLayer().Export(str(path));reviews[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
 out=ROOT/'data/heights/princeton/interpreted_roof';out.mkdir(parents=True,exist_ok=True)
 save(out/'regions.json',{'coordinate_frame':'local EPSG32617 offset; zNAVD88meters','origin_utm_m':origin.tolist(),'regions':[dict(r,geometry=mapping(r['geometry'])) for r in localregions]})
 deps=[Path(__file__),cloud,supportpath,photo,frozen/'data/heights/princeton/coherent_roof_manifest.json',ROOT/'data/heights/princeton/manifest.json',ROOT/'data/imagery/princeton_roof_references/receipts.json',ROOT/'config/princeton_sources.json',ROOT/'scene/princeton_correction.usda',ROOT/'tools/reconstruct_landmarks.py',ROOT/'tools/office_roof_architecture.py']
 report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'interpreted_candidate_not_activated_visual_review_pending','parcel_id':config['parcel_id'],'proposal_layer':str(layer.relative_to(ROOT)).replace('\\','/'),'layer_sha256':sha(layer),'camera':str(camera.GetPath()),'origin_utm_m':origin.tolist(),'ground_reference_navd88_m':ground,'base_terrace_level_navd88_m':base,'components':[{**c,'planes':[p.tolist() for p in c['planes']]} for c in caps],'analytical_region_count':len(regions),'footprint_area_m2':outline.area,'outline_simplification_m':1.,'source_grid_point_contact_regularization_m':{'erosion':.015,'dilation':.01},'restored_roof_voids':hole_evidence,'restored_roof_void_area_m2':sum(h.area for h in restored),'source_outline_symmetric_difference_m2':original.symmetric_difference(outline).area,'protected_courtyard_overlap_m2':outline.intersection(localprotected).area,'whole_class6_evaluated_points':len(errors),'whole_class6_residual_p50_p95_max_m':np.percentile(errors,[50,95,100]).tolist(),'internal_vertical_interface_wall_area_m2':interior_wall_area,'maximum_internal_step_height_m':maximum_interior_step_height,'mesh_proof':proof,'closed_shell':gate,'upward_face_provenance':face_provenance,'maximum_rendered_height_m':max(p[2] for p in geometry[0])-.1,'dependencies':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in deps},'matched_review_scenes':reviews,'style_sha256':sha(stylepath),'reference_capture_date':'unknown','reference_use':'qualitative completed component topology only; no tracing/textures/source pixels redistributed','limits':['All component dimensions and joins are interpreted estimates; no1.5m source-support extrapolation guarantee is claimed.','A symmetric/hip component model may not capture unequal slopes, original terraces, parapets, dormers or equipment; residuals measure that limitation.','Historical class6 heights and a completed undated photo are different temporal evidence; not a measured current roof.','West/middle source-uncertain geometry and every active/root layer remain unchanged.']}
 save(out/'manifest.json',report)
 svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 15 105 80"><g transform="scale(1,-1)">']
 for i,r in enumerate(localregions):
  for polygon in getattr(r['geometry'],'geoms',[r['geometry']]):
   if polygon.geom_type!='Polygon':continue
   rings=[polygon.exterior,*polygon.interiors];d=' '.join('M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in ring.coords)+' Z' for ring in rings);svg.append(f'<path d="{d}" fill="hsl({i*43%360} 35% 65%)" fill-rule="evenodd" stroke="#222" stroke-width=".08"/>')
 svg.append('</g></svg>');(out/'regions.svg').write_text(''.join(svg),encoding='utf8')
 from PIL import Image,ImageDraw
 im=Image.new('RGB',(1200,900),'white');draw=ImageDraw.Draw(im);faces=[];offset=0
 for count in geometry[1]:
  q=np.asarray([geometry[0][i] for i in geometry[2][offset:offset+count]]);offset+=count;n=np.cross(q[1]-q[0],q[2]-q[0])
  if n[2]>1e-8:faces.append(q)
 for q in sorted(faces,key=lambda q:float(q[:,1].mean()+q[:,0].mean()*.4),reverse=True):
  points=[((a[0]-105)*9+(a[1]+85)*3+50,700-(a[1]+85)*5-a[2]*12) for a in q];n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n);value=int(130+70*float(n@np.array([-.4,-.5,.76])));draw.polygon(points,fill=(value,value,value))
 draw.text((20,20),'CPU diagnostic: estimated cap/terrace roof; no materials or visual acceptance',fill='black');im.save(out/'cpu_roof.png')
 print(json.dumps({k:report[k] for k in ['status','analytical_region_count','whole_class6_residual_p50_p95_max_m','closed_shell','layer_sha256']},indent=2));return report

if __name__=='__main__':build()
