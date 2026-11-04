"""Bounded historical Princeton eastern roof-plane proposal; no activation."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import shape,box
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from scipy import ndimage
from pyproj import Transformer
from pxr import Usd,UsdGeom,Gf
from verify_retail_block import read,save,sha
from constrain_scene import mesh_footprint
from princeton_evidence import read_points
from reconstruct_landmarks import planar_region_geometry
from office_roof_architecture import finish_mesh,material
TARGET='/World/Landmarks/PrincetonAtCollegePark/EasternVariableRoof'

def fit_planes(q,maximum=28):
 distance,idx=cKDTree(q[:,:3]).query(q[:,:3],k=20,workers=1);delta=q[idx,:3]-q[idx,:3].mean(1)[:,None,:];eigen,vectors=np.linalg.eigh(np.einsum('nki,nkj->nij',delta,delta));normals=vectors[:,:,0];normals*=np.sign(normals[:,2])[:,None]
 keep=(normals[:,2]>.7)&(eigen[:,0]/np.maximum(eigen[:,1],1e-12)<.08)&(distance[:,-1]<1.5);q=q[keep];normals=normals[keep];slopes=-normals[:,:2]/normals[:,2,None];center=q[:,:2].mean(0);a=np.c_[q[:,:2]-center,np.ones(len(q))];available=np.ones(len(q),bool);rng=np.random.default_rng(33);planes=[]
 for number in range(maximum):
  ids=np.where(available)[0]
  if len(ids)<120:break
  sample=rng.choice(ids,min(10000,len(ids)),False);best=[]
  for seed in rng.choice(ids,min(700,len(ids)),False):
   c=np.r_[slopes[seed],q[seed,2]-(q[seed,:2]-center)@slopes[seed]]
   if np.linalg.norm(c[:2])>1:continue
   h=sample[(np.abs(a[sample]@c-q[sample,2])<.15)&((normals[sample]@normals[seed])>.994)]
   if len(h)>len(best):best=h
  if len(best)<45:break
  c=np.linalg.lstsq(a[best],q[best,2],rcond=None)[0];normal=np.r_[-c[:2],1];normal/=np.linalg.norm(normal);h=ids[(np.abs(a[ids]@c-q[ids,2])<.17)&((normals[ids]@normal)>.994)]
  if len(h)<100:break
  for _ in range(4):
   residual=a[h]@c-q[h,2];weight=np.minimum(1.,.06/np.maximum(np.abs(residual),1e-8));c=np.linalg.lstsq(a[h]*weight[:,None],q[h,2]*weight,rcond=None)[0]
  residual=np.abs(a[h]@c-q[h,2]);planes.append({'coefficients':c,'support':q[h],'residual_p50_p95_max_m':np.percentile(residual,[50,95,100]).tolist()});available[h]=False
 return center,planes,q,{'class6_planar_support_points':len(q),'unassigned_points':int(available.sum()),'normal_max_angle_degrees':float(np.degrees(np.arccos(.994))),'point_residual_window_m':.17}

def build():
 config=read(ROOT/'config/princeton_sources.json');manifest=read(ROOT/'data/heights/princeton/manifest.json');active=read(ROOT/'data/processed/active.json');units=read(ROOT/'data/heights/vertical_unit_check.json')
 if manifest['source_snapshot']!=active['snapshot'] or not units['accepted'] or units['ept_z_unit']!='meters':raise ValueError('Stale source snapshot or unit evidence')
 folder=ROOT/active['relative_path'];features=read(folder/'parcels.json')['features'];parcel=next(f for f in features if f['properties']['parcel_id']==config['parcel_id']);points,evidence=read_points(config,shape(parcel['geometry']),ROOT,False);cached=np.load(ROOT/'data/heights/princeton/points.npz')['points']
 if not np.array_equal(points,cached):raise ValueError('Cached derived point cloud differs from original-node offline replay')
 expected={r['key']:r['sha256'] for r in manifest['cloud']['node_receipts']}
 if {r['key']:r['sha256'] for r in evidence['node_receipts']}!=expected:raise ValueError('Original historical source node bytes changed')
 original=Usd.Stage.Open(str(ROOT/'scene/princeton_correction.usda'));old=original.GetPrimAtPath(TARGET);project=Transformer.from_crs(4326,32617,always_xy=True);origin=project.transform(*config['origin_wgs84']);ground=manifest['grid']['ground_median_m'];outline=shapely.affinity.translate(mesh_footprint(old),*origin);original_outline=outline
 # Bounded source-grid simplification only; preserve all original courtyard voids.
 outline=outline.simplify(.65,preserve_topology=True).buffer(-.015,join_style=2).buffer(.01,join_style=2);protected=unary_union([box(*v['bounds']) for v in config['protected_voids_utm']]);outline=outline.difference(protected)
 q=points[(points[:,3]==6)&shapely.intersects_xy(outline,points[:,0],points[:,1])&(points[:,2]>41)&(points[:,2]<48)];center,planes,support,fit=fit_planes(q)
 if len(planes)<8:raise ValueError('Insufficient coherent roof planes')
 # Each source-grid cell votes only for spatially nearby plane inliers; no mixed-corner interpolation.
 left,bottom=np.floor(outline.bounds[:2]);right,top=np.ceil(outline.bounds[2:]);width,height=int(right-left),int(top-bottom);labels=np.full((height,width),-1,int);distances=np.full((height,width),np.inf);trees=[cKDTree(p['support'][:,:2]) for p in planes]
 coordinates=np.array([(left+x+.5,bottom+y+.5) for y in range(height) for x in range(width)]);inside=shapely.intersects_xy(outline,coordinates[:,0],coordinates[:,1]);cells=coordinates[inside];scores=[]
 for plane,tree in zip(planes,trees):scores.append(tree.query(cells,k=1,workers=1)[0])
 scores=np.asarray(scores);best=np.argmin(scores,axis=0);near=scores[best,np.arange(len(cells))];unknown=[];raw_regions=[]
 for xy,label,distance in zip(cells,best,near):
  x=int(np.floor(xy[0]-left));y=int(np.floor(xy[1]-bottom));cell=box(left+x,bottom+y,left+x+1,bottom+y+1).intersection(outline)
  if cell.area<.002:continue
  if distance<=.78:labels[y,x]=int(label);distances[y,x]=distance
  else:unknown.append(cell)
 for i,plane in enumerate(planes):
  yy,xx=np.where(labels==i)
  if not len(xx):continue
  geometry=unary_union([box(left+x,bottom+y,left+x+1,bottom+y+1) for y,x in zip(yy,xx)]).intersection(outline);raw_regions.append({'geometry':geometry,'coefficients_cell_xy':plane['coefficients'].tolist(),'plane_index':i})
 # Whole-cell bound: center within .78m of one actual inlier plus half-diagonal
 # .7072m and sub-centimeter topology quantization remains strictly under1.5m.
 # Boundary slivers without a certified source cell remain original approximation.
 fitted_union=shapely.set_precision(unary_union([r['geometry'] for r in raw_regions]),.001);unsupported_union=outline.difference(fitted_union)
 # Low-support areas preserve source-model roof triangles rather than inventing new flat roofs.
 fallback_regions=[];leftover_area=unsupported_union.area;oldmesh=UsdGeom.Mesh(old);oldpoints=np.asarray(oldmesh.GetPointsAttr().Get(),float);offset=0
 for face,count in enumerate(oldmesh.GetFaceVertexCountsAttr().Get()):
  ids=list(oldmesh.GetFaceVertexIndicesAttr().Get()[offset:offset+count]);offset+=count;vertices=oldpoints[ids]
  if count<3 or np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0])[2]<=1e-9:continue
  for j in range(1,count-1):
   tri=vertices[[0,j,j+1]];absolute=tri[:,:2]+np.asarray(origin);polygon=shapely.set_precision(shapely.Polygon(absolute),.001);patch=polygon.intersection(shapely.set_precision(unsupported_union,.001))
   if patch.is_empty or patch.area<.0001:continue
   a=np.c_[absolute-center,np.ones(3)];coeff=np.linalg.solve(a,tri[:,2]-.1+ground)
   fallback_regions.append({'geometry':patch,'coefficients_cell_xy':coeff.tolist(),'plane_index':-1,'original_face_index':face})
 retained_union=unary_union([r['geometry'] for r in fallback_regions]);unrepresented_unsupported=unsupported_union.difference(retained_union)
 if unrepresented_unsupported.area>.05:
  # Areas added solely by outline simplification without original mesh or nearby
  # fitted support are removed, never filled by an invented roof level.
  outline=outline.difference(unrepresented_unsupported)
 raw_regions=[r for r in raw_regions if not r['geometry'].is_empty and r['geometry'].area>.0001];regions=raw_regions+fallback_regions
 # Node all semantic/plane junctions once, rather than allowing four-sector
 # vertical knife-edge contacts. A .006m patch uses the highest existing local
 # plane, clipped to the existing union; it cannot cross the protected courtyard.
 memberships={}
 for i,r in enumerate(regions):
  for polygon in getattr(r['geometry'],'geoms',[r['geometry']]):
   if polygon.geom_type!='Polygon':continue
   for ring in [polygon.exterior,*polygon.interiors]:
    for x,y in ring.coords:memberships.setdefault((round(x,3),round(y,3)),set()).add(i)
 junctions=[];union_before=unary_union([r['geometry'] for r in regions])
 for xy,candidates in sorted(memberships.items()):
  if len(candidates)<3:continue
  patch=box(xy[0]-.006,xy[1]-.006,xy[0]+.006,xy[1]+.006).intersection(union_before)
  if patch.is_empty:continue
  chosen=max(candidates,key=lambda i:np.dot(np.r_[np.asarray(xy)-center,1.],regions[i]['coefficients_cell_xy']))
  for i,r in enumerate(regions):
   if not r['geometry'].intersects(patch):continue
   r['geometry']=r['geometry'].union(patch) if i==chosen else r['geometry'].difference(patch)
  junctions.append({'utm_xy':list(xy),'area_m2':patch.area,'radius_m':.006,'selected_plane_index':regions[chosen]['plane_index']})
 regions=[r for r in regions if not r['geometry'].is_empty and r['geometry'].area>.00001];raw_regions=[r for r in regions if r['plane_index']>=0];fallback_regions=[r for r in regions if r['plane_index']<0]
 info={'cell_m':1.,'left_utm_m':center[0],'bottom_utm_m':center[1]};geometry,topology=planar_region_geometry(regions,info,origin,ground)
 if fitted_union.intersection(protected).area>.001:raise ValueError('Protected courtyard covered')
 stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');stage.SetMetadata('metersPerUnit',1.);UsdGeom.Imageable(stage.OverridePrim(TARGET)).CreateVisibilityAttr('invisible');root=UsdGeom.Xform.Define(stage,'/World/Landmarks/PrincetonAtCollegePark/CoherentEasternRoof');root.GetPrim().SetCustomData({'sourceSnapshot':active['snapshot'],'parcelId':config['parcel_id'],'quality':'mixed_historical_class6_fitted_planes_and_retained_uncertain_original_triangles_not_current_survey','fittedAreaM2':fitted_union.area,'retainedUncertainAreaM2':retained_union.area,'retainedUncertainPolicy':'Original source-model triangles retained; not new measured fitted roof','retainedWestMiddle':'Existing unclassified class1 deck/roof zones unchanged; not certified roof semantics','unknownComponentAreaM2':leftover_area})
 wall=material(stage,'PrincetonPlaneWall',(.65,.67,.63));roof=material(stage,'PrincetonPlaneRoof',(.40,.43,.42));full,gate=finish_mesh(stage,str(root.GetPath())+'/TemporaryComposite',geometry,wall,roof)
 # Partition exact common-shell faces by semantic support; never create duplicate
 # internal walls by separately extruding the fitted and uncertain regions.
 from princeton_evidence import write_surface
 from pxr import UsdShade,Sdf
 quantized_points=list(full.GetPointsAttr().Get());counts=list(full.GetFaceVertexCountsAttr().Get());indices=list(full.GetFaceVertexIndicesAttr().Get());partition={'SourceFittedPlanes':[],'RetainedUncertainApproximation':[]};region_tree=shapely.STRtree([r['geometry'] for r in regions]);offset=0;uncertain_domain=unary_union([r['geometry'] for r in fallback_regions]);face_provenance=[]
 for face,count in enumerate(counts):
  ids=indices[offset:offset+count];offset+=count;vertices=np.asarray([quantized_points[i] for i in ids]);xy=vertices[:,:2].mean(0)+np.asarray(origin);uncertain=uncertain_domain.distance(shapely.Point(*xy))<.002;name='RetainedUncertainApproximation' if uncertain else 'SourceFittedPlanes';partition[name].append((face,vertices));candidate_regions=[int(i) for i in region_tree.query(shapely.Point(*xy).buffer(.002)) if regions[int(i)]['geometry'].distance(shapely.Point(*xy))<.002];face_provenance.append({'original_common_shell_face':face,'semantic_prim':name,'source_region_indices':candidate_regions,'source_plane_indices':sorted({regions[i]['plane_index'] for i in candidate_regions if regions[i]['plane_index']>=0}),'original_retained_face_indices':sorted({regions[i]['original_face_index'] for i in candidate_regions if 'original_face_index' in regions[i]})})
 render_components=[]
 for label,faces in partition.items():
  pts=[];cs=[];ix=[]
  for _,vertices in faces:
   start=len(pts);pts.extend([tuple(float(value) for value in v) for v in vertices]);cs.append(len(vertices));ix.extend(range(start,len(pts)))
  mesh=write_surface(stage,str(root.GetPath())+'/'+label,(pts,cs,ix));mesh.GetPrim().CreateAttribute('primvars:st:indices',Sdf.ValueTypeNames.IntArray,custom=False).Block();UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(roof)
  quality='historical_class6_normal_consistent_fitted_roof_planes' if label=='SourceFittedPlanes' else 'retained_original_approximation_no_new_measured_plane';mesh.GetPrim().SetCustomData({'quality':quality,'sourceSnapshot':active['snapshot'],'parcelId':config['parcel_id'],'topologyScope':'semantic surface portion of jointly closed shared shell; not an independently extruded volume'});render_components.append({'prim_path':str(mesh.GetPath()),'quality':quality,'faces':len(faces),'topology_scope':'welded union of both semantic meshes is the verified closed shell'})
 stage.RemovePrim(str(full.GetPath()));gate['scope']='welded union of two exact face partitions; each semantic surface is not independently closed'
 # The coverage and actual mesh plane-error checks expose all interpolation/fit limitations.
 residual=[]
 for region in raw_regions:
  hit=q[shapely.intersects_xy(region['geometry'],q[:,0],q[:,1])];a=np.c_[hit[:,:2]-center,np.ones(len(hit))];residual.extend(np.abs(a@np.asarray(region['coefficients_cell_xy'])-hit[:,2]).tolist())
 camera=UsdGeom.Camera.Define(stage,'/World/Cameras/PrincetonCoherentRoofEvidence');target=Gf.Vec3d(outline.centroid.x-origin[0],outline.centroid.y-origin[1],14);camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(target+Gf.Vec3d(100,-130,125),target,Gf.Vec3d(0,0,1)).GetInverse());camera.CreateFocalLengthAttr(35);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25)
 stage.GetRootLayer().customLayerData={'sourceSnapshot':active['snapshot'],'proposalOnly':True,'sourcePrincetonLayerSha256':sha(ROOT/'scene/princeton_correction.usda'),'currentGeometryVerified':False,'privateDataUsed':False};path=ROOT/'scene/princeton_coherent_roof_proposal.usda';stage.GetRootLayer().Export(str(path))
 style=Usd.Stage.CreateInMemory();style.OverridePrim(camera.GetPath());Sdf.CopySpec(stage.GetRootLayer(),camera.GetPath(),style.GetRootLayer(),camera.GetPath());neutral=material(style,'PrincetonMatchedReviewNeutral',(.55,.57,.55))
 for target_path in [TARGET,str(root.GetPath())+'/SourceFittedPlanes',str(root.GetPath())+'/RetainedUncertainApproximation']:
  UsdShade.MaterialBindingAPI.Apply(style.OverridePrim(target_path)).Bind(neutral)
 style.GetRootLayer().customLayerData={'reviewOnly':True,'style':'Identical neutral material on baseline/proposal eastern geometry; inherited district lights unchanged','cameraCopiedFromProposal':str(camera.GetPath())};style_path=ROOT/'scene/princeton_matched_roof_style.usda';style.GetRootLayer().Export(str(style_path));review_hashes={}
 for name,layers in [('baseline',['princeton_matched_roof_style.usda','college_park_connected.usda']),('proposal',['princeton_matched_roof_style.usda','princeton_coherent_roof_proposal.usda','college_park_connected.usda'])]:
  review=Usd.Stage.CreateInMemory();review.GetRootLayer().subLayerPaths=layers;review.GetRootLayer().customLayerData={'reviewOnly':True,'sourceSnapshot':active['snapshot'],'rootSha256':sha(ROOT/'scene/college_park_connected.usda'),'roofProposalSha256':sha(path),'comparison':name,'sameCameraLightAndNeutralMaterial':True};review_path=ROOT/('scene/princeton_coherent_roof_'+name+'_review.usda');review.GetRootLayer().Export(str(review_path));review_hashes[str(review_path.relative_to(ROOT)).replace('\\','/')]=sha(review_path)

 support_path=ROOT/'data/heights/princeton/coherent_roof_support.npz';np.savez_compressed(support_path,**{'plane'+str(i):p['support'] for i,p in enumerate(planes)})
 deps=[support_path,ROOT/'data/heights/princeton/manifest.json',ROOT/'data/heights/princeton/points.npz',ROOT/'config/princeton_sources.json',ROOT/'data/heights/vertical_unit_check.json',ROOT/'scene/princeton_correction.usda',folder/'parcels.json',Path(__file__),ROOT/'tools/office_roof_architecture.py',ROOT/'tools/reconstruct_landmarks.py']
 report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parcel_id':config['parcel_id'],'proposal_layer':str(path.relative_to(ROOT)).replace('\\','/'),'layer_sha256':sha(path),'camera':str(camera.GetPath()),'cloud_replayed_equal_original':True,'source_acquisition_interval':evidence['acquisition'],'source_cloud_sha256':sha(ROOT/'data/heights/princeton/points.npz'),'support_array_path':'data/heights/princeton/coherent_roof_support.npz','support_array_sha256':sha(support_path),'fit_origin_utm_m':center.tolist(),'horizontal_crs':'EPSG32617 meters','source_vertical_datum':'NAVD88 meters','ground_reference_navd88_m':ground,'display_base_offset_m':.1,'fit':fit,'fitted_plane_count':len(planes),'plane_patch_count':len(raw_regions),'source_supported_area_m2':fitted_union.area,'unsupported_approximation_area_m2':retained_union.area,'unsupported_unrepresented_removed_m2':unrepresented_unsupported.area,'unsupported_policy':'Exact clipped original EasternVariableRoof triangles retained; no new flat fallback levels','source_outline_area_m2':original_outline.area,'proposal_outline_area_m2':outline.area,'outline_simplification_m':.65,'point_contact_regularization_m':{'erosion':.015,'dilation':.01},'protected_courtyard_overlap_m2':fitted_union.intersection(protected).area,'assigned_class6_residual_p50_p95_max_m':np.percentile(residual,[50,95,100]).tolist(),'planes':[{'plane_index':i,'coefficients_centered_xy':p['coefficients'].tolist(),'support_points':len(p['support']),'inlier_residual_p50_p95_max_m':p['residual_p50_p95_max_m']} for i,p in enumerate(planes)],'mesh_proof':topology,'junction_regularization':junctions,'junction_regularization_area_m2':sum(j['area_m2'] for j in junctions),'per_face_provenance':face_provenance,'closed_shell':gate,'render_components':render_components,'maximum_support_distance_m':1.5,'maximum_certified_cell_center_distance_m':.78,'maximum_cell_half_diagonal_m':float(np.sqrt(.5)),'maximum_support_bound_with_junction_and_quantization_m':float(.78+np.sqrt(.5)+.006*np.sqrt(2)+.002),'support_bound_method':'Each whole1mcell center within.78m of one actual assigned-plane inlier; entirecell lies within.78+sqrt(.5)<1.488m of that sameinlier, with.012mreserve for topologicalquantization. Boundaryslivers are retainedoriginal, not representative-point extrapolation','maximum_rendered_height_m':max(p[2] for p in geometry[0])-.1,'dependencies':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in deps},'source_node_receipts':evidence['node_receipts'],'matched_review_scenes':review_hashes,'review_style_layer_sha256':sha(style_path),'materials_comparison':'Both baseline/proposal use identical neutral material override on eastern geometry; inherited district lights/camera unchanged; outside components untouched','status':'proposal_not_activated_visual_review_pending','limitations':['Historical 2018-2019 acquisition; localflightday/constructionphase/currentroof changes unknown.','West/middle class1-only source zones remain unchanged and semantically uncertain; not assigned6storeys.','Eastern roof broadplanes use class6 local normals and measured inliers; smallsupport gaps retain separately reported approximation.','Original parcel is search boundary only; original supported envelope/courtyard retained within .65m bounded simplification.','No facade, material identity, current roof certification or imagery tracing/texture reuse.']};save(ROOT/'data/heights/princeton/coherent_roof_regions.geojson',{'type':'FeatureCollection','source_snapshot':active['snapshot'],'features':[{'type':'Feature','id':'roof-region:'+str(i),'geometry':shapely.geometry.mapping(shapely.transform(r['geometry'],Transformer.from_crs(32617,4326,always_xy=True).transform,interleaved=False)),'properties':{'plane_index':r['plane_index'],'support_status':'class6_normal_consistent_fitted_plane' if r['plane_index']>=0 else 'retained_original_approximation_not_new_plane','area_m2':r['geometry'].area,'original_face_index':r.get('original_face_index')}} for i,r in enumerate(regions)]});save(ROOT/'data/heights/princeton/coherent_roof_manifest.json',report);print(json.dumps({k:report[k] for k in ['fitted_plane_count','plane_patch_count','source_supported_area_m2','unsupported_approximation_area_m2','assigned_class6_residual_p50_p95_max_m','closed_shell','layer_sha256']},indent=2));return report
if __name__=='__main__':build()
