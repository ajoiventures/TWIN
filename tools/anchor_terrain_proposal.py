"""Guarded, incomplete anchoring overlay. No activation or source edits."""
from pathlib import Path
import os,sys,json,argparse
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
from pyproj import Transformer
from pxr import Usd,UsdGeom,Gf,Vt,Sdf
from shapely.geometry import MultiPoint,Point,Polygon,box
from shapely.ops import unary_union
from acquire_dem import checksum,inspect_tile,parse_metadata,study_grid,paste_tile,atomic_json,now,US_FOOT_M
from build_terrain_proposal import verify_source


def verify_dependencies(root,deps):
    for item in deps:
        if checksum(Path(root)/item['path'])!=item['sha256']:
            raise ValueError('Stale source dependency: '+item['path'])


class GroundSampler:
    def __init__(self,values,grid,origin,z_origin=30.):
        self.values=values;self.grid=grid;self.z_origin=z_origin
        self.to_source=Transformer.from_crs(32617,grid['horizontal_epsg'],always_xy=True)
        self.origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*origin)

    def validate_geometry(self,geometry):
        """Reject intersection with any invalid original bilinear support cell."""
        from shapely.ops import transform
        from shapely import box as boxes,intersects
        def project(x,y,z=None):
            return self.to_source.transform(np.asarray(x)+self.origin[0],np.asarray(y)+self.origin[1])
        polygon=transform(project,geometry)
        x0,y0,x1,y1=polygon.bounds;step=self.grid['pixel_size_ft']
        c0=int(np.floor((x0-self.grid['left_ft'])/step-.5));c1=int(np.floor((x1-self.grid['left_ft'])/step-.5))
        r0=int(np.floor((self.grid['top_ft']-y1)/step-.5));r1=int(np.floor((self.grid['top_ft']-y0)/step-.5))
        if min(c0,r0)<0 or r1+1>=self.values.shape[0] or c1+1>=self.values.shape[1]:raise ValueError('outside_valid_raster')
        valid=np.isfinite(self.values[r0:r1+2,c0:c1+2])
        bad=~(valid[:-1,:-1]&valid[1:,:-1]&valid[:-1,1:]&valid[1:,1:])
        rr,cc=np.nonzero(bad)
        if len(rr):
            left=self.grid['left_ft']+(cc+c0+.5)*step
            top=self.grid['top_ft']-(rr+r0+.5)*step
            if intersects(boxes(left,top-step,left+step,top),polygon).any():raise ValueError('nodata_surface_support')

    def sample(self,xy):
        xy=np.asarray(xy,dtype=float).reshape(-1,2)
        x,y=self.to_source.transform(xy[:,0]+self.origin[0],xy[:,1]+self.origin[1])
        col=(x-self.grid['left_ft'])/self.grid['pixel_size_ft']-.5
        row=(self.grid['top_ft']-y)/self.grid['pixel_size_ft']-.5
        r=np.floor(row).astype(int);c=np.floor(col).astype(int)
        if ((r<0)|(c<0)|(r+1>=self.values.shape[0])|(c+1>=self.values.shape[1])).any():
            raise ValueError('outside_valid_raster')
        v=np.column_stack([self.values[r,c],self.values[r,c+1],self.values[r+1,c],self.values[r+1,c+1]])
        if not np.isfinite(v).all():raise ValueError('nodata_interpolation_support')
        u=col-c;t=row-r
        return ((1-u)*(1-t)*v[:,0]+u*(1-t)*v[:,1]+(1-u)*t*v[:,2]+u*t*v[:,3])*US_FOOT_M-self.z_origin


def rigid_delta(points,sampler):
    points=np.asarray(points,float)
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():raise ValueError('invalid_mesh')
    footprint=MultiPoint(points[:,:2]).convex_hull
    center=footprint.representative_point()
    xy=np.asarray(footprint.exterior.coords) if footprint.geom_type=='Polygon' else points[:,:2]
    ground=sampler.sample(np.vstack(([center.x,center.y],xy)))
    return float(ground[0]-points[:,2].min()+.1),{'basepoint_xy_m':[center.x,center.y],
        'original_base_z_m':float(points[:,2].min()),'new_base_z_m':float(ground[0]+.1),
        'footprint_vertex_ground_range_m':[float(ground[1:].min()),float(ground[1:].max())],
        'sampled_ground_relief_m':float(np.ptp(ground[1:])),
        'uncertainty':'Representative basepoint and convex-hull vertex ground samples; not full footprint ground survey. Rigid geometry preserves roof/height; sloping ground may intersect walls.'}


def bridge_policy(tags):
    if not tags:return 'unknown_bridge_status'
    if tags.get('bridge') not in (None,'no') or tags.get('tunnel') not in (None,'no') or tags.get('layer','0')!='0':
        return 'bridge_tunnel_or_nonzero_layer'
    return None


def tessellated_drape(points,faces,sampler,spacing=6.096012192):
    """Clip each original surface polygon to a common local grid, then triangulate.

    Cell boundaries are shared, with identical DEM interpolation on shared points.
    This retains original outlines/holes rather than extruding a road envelope.
    """
    from shapely import constrained_delaunay_triangles,contains_xy
    points=np.asarray(points,float)
    if np.ptp(points[:,2])>.001:raise ValueError('nonflat_original_surface_offset')
    geometry=unary_union([Polygon(points[f,:2]) for f in faces]).buffer(0)
    if hasattr(sampler,'validate_geometry'):sampler.validate_geometry(geometry)
    lo=np.asarray(geometry.bounds[:2]);hi=np.asarray(geometry.bounds[2:])
    start=np.floor(lo/spacing).astype(int);end=np.ceil(hi/spacing).astype(int)
    if np.prod(end-start)>100000:raise ValueError('surface_tessellation_bound_exceeded')
    vertices=[];triangles=[];lookup={}
    def index(x,y):
        key=(round(float(x),7),round(float(y),7))
        if key not in lookup:lookup[key]=len(vertices);vertices.append(key)
        return lookup[key]
    for ix in range(start[0],end[0]):
        for iy in range(start[1],end[1]):
            piece=geometry.intersection(box(ix*spacing,iy*spacing,(ix+1)*spacing,(iy+1)*spacing))
            if piece.is_empty or piece.area<1e-9:continue
            for triangle in constrained_delaunay_triangles(piece).geoms:
                xy=np.asarray(triangle.exterior.coords)[:3]
                a,b=xy[1]-xy[0],xy[2]-xy[0]
                if a[0]*b[1]-a[1]*b[0]<0:xy=xy[::-1]
                triangles.append([index(x,y) for x,y in xy])
    if not vertices:raise ValueError('no_valid_surface_triangles')
    # Sub-meter interior screening catches original NoData supports between vertices.
    if np.prod(np.ceil((hi-lo)/.5)+1)>2000000:raise ValueError('surface_validation_bound_exceeded')
    xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+.5,.5),np.arange(lo[1],hi[1]+.5,.5))
    xy=np.column_stack((xx.ravel(),yy.ravel()))
    sampler.sample(xy[contains_xy(geometry,xy[:,0],xy[:,1])])
    xy=np.asarray(vertices);z=sampler.sample(xy)+points[0,2]
    return np.column_stack((xy,z)),np.asarray(triangles,dtype=int)


def drape_points(points,sampler,max_edge_m=12.,faces=None):
    points=np.asarray(points,float)
    if not np.isfinite(points).all():raise ValueError('nonfinite_surface')
    if np.ptp(points[:,2])>.001:raise ValueError('nonflat_original_surface_offset')
    if faces is not None:
        for face in faces:
            xy=points[face,:2]
            lengths=np.linalg.norm(xy-np.roll(xy,1,axis=0),axis=1)
            if lengths.max()>max_edge_m:raise ValueError('needs_surface_tessellation')
            # Validate all edge interpolation support, not only original vertices.
            for a,b,length in zip(xy,np.roll(xy,1,axis=0),lengths):
                sampler.sample(np.linspace(a,b,max(2,int(np.ceil(length/.3))+1)))
    out=points.copy();out[:,2]=sampler.sample(points[:,:2])+points[:,2]
    return out


def build(root=ROOT):
    root=Path(root);folder=root/'data/heights/dem'
    terrain=json.loads((folder/'terrain_proposal.json').read_text())
    deps=list(terrain['dependencies'])
    deps += [{'path':terrain['layer'],'sha256':terrain['layer_sha256']},
             {'path':'data/heights/dem/terrain_proposal.json','sha256':checksum(folder/'terrain_proposal.json')}]
    verify_dependencies(root,deps)
    if terrain['scene_z_origin_navd88_m']!=30. or terrain['vertical_datum']!='NAVD88':raise ValueError('Unsupported vertical frame')
    config=json.loads((root/'config/terrain_sources.json').read_text());grid=mosaic=covered=None
    for tile in config['tiles']:
        path=folder/(tile['id']+'.tif');xml=folder/(tile['id']+'.xml')
        info,values,valid=inspect_tile(path,parse_metadata(xml),config)
        if grid is None:
            grid=study_grid(config,info);mosaic=np.full((grid['height'],grid['width']),np.nan,dtype=np.float32);covered=np.zeros(mosaic.shape,bool)
        paste_tile(mosaic,covered,grid,info,values,valid)
    with np.load(folder/'study_valid_pixels.npz',allow_pickle=False) as mask:mosaic[~mask['inside_study']]=np.nan
    sampler=GroundSampler(mosaic,grid,terrain['local_origin_wgs84'])
    assembly=root/'scene/college_park_connected.usda';source=Usd.Stage.Open(str(assembly))
    for layer in source.GetUsedLayers():
        if layer.realPath:
            p=Path(layer.realPath);deps.append({'path':p.relative_to(root).as_posix(),'sha256':checksum(p)})
    stage=Usd.Stage.CreateInMemory();stage.GetRootLayer().subLayerPaths=[str(root/'scene/terrain_proposal.usda'),str(assembly)]
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z);UsdGeom.SetStageMetersPerUnit(stage,1.)
    applied=[];queue=[]
    def skip(path,reason):queue.append({'path':str(path),'reason':reason})
    def safe(prim):
        if prim.IsInstanceProxy() or prim.IsInstance():return False
        p=prim
        while p and p.GetPath()!= '/':
            if UsdGeom.Xformable(p) and UsdGeom.Xformable(p).GetOrderedXformOps():return False
            p=p.GetParent()
        return True
    water=[]
    for prim in source.GetPrimAtPath('/World/Water').GetChildren():
        if prim.IsA(UsdGeom.Mesh):
            pts=np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get());water.append(MultiPoint(pts[:,:2]).convex_hull)
    water=unary_union(water)
    for prim in source.GetPrimAtPath('/World/Buildings').GetChildren():
        path=prim.GetPath()
        if UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        if not safe(prim) or not prim.IsA(UsdGeom.Mesh):skip(path,'transform_or_instance_requires_separate_review');continue
        pts=np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get())
        if MultiPoint(pts[:,:2]).convex_hull.intersects(water):skip(path,'water_intersection');continue
        roof=source.GetPrimAtPath('/World/Roofs/Roof_'+prim.GetName().split('_')[-1])
        if roof and not safe(roof):skip(path,'paired_roof_transform_requires_review');continue
        try:delta,detail=rigid_delta(pts,sampler)
        except ValueError as error:skip(path,str(error));continue
        for target in [prim]+([roof] if roof else []):
            override=stage.OverridePrim(target.GetPath());xf=UsdGeom.Xformable(override)
            xf.AddTranslateOp(opSuffix='terrainAnchor').Set(Gf.Vec3d(0,0,delta))
        applied.append({'path':str(path),'paired_roof':str(roof.GetPath()) if roof else None,'delta_z_m':delta,**detail})
    osm_path=root/'data/openstreetmap.json'
    osm=json.loads(osm_path.read_text()) if osm_path.exists() else {'elements':[]}
    tags={str(e['id']):e.get('tags',{}) for e in osm['elements']}
    if osm_path.exists():deps.append({'path':osm_path.relative_to(root).as_posix(),'sha256':checksum(osm_path)})
    for prim in source.GetPrimAtPath('/World/Streets').GetChildren():
        if UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        path=prim.GetPath();wid=prim.GetName().rsplit('_',1)[-1]
        reason=bridge_policy(tags.get(wid))
        if reason:skip(path,reason);continue
        if not safe(prim) or not prim.IsA(UsdGeom.Mesh):skip(path,'transform_or_instance_requires_review');continue
        mesh=UsdGeom.Mesh(prim);pts=np.asarray(mesh.GetPointsAttr().Get())
        if MultiPoint(pts[:,:2]).convex_hull.intersects(water):skip(path,'water_intersection');continue
        indices=np.asarray(mesh.GetFaceVertexIndicesAttr().Get());counts=mesh.GetFaceVertexCountsAttr().Get()
        faces=[];offset=0
        for count in counts:faces.append(indices[offset:offset+count]);offset+=count
        try:
            out,new_faces=tessellated_drape(pts,faces,sampler)
        except ValueError as error:skip(path,str(error));continue
        override=UsdGeom.Mesh(stage.OverridePrim(path));override.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(out.astype(np.float32)))
        override.CreateFaceVertexCountsAttr([3]*len(new_faces));override.CreateFaceVertexIndicesAttr(new_faces.flatten().tolist())
        override.CreateExtentAttr([Gf.Vec3f(*map(float,out.min(0))),Gf.Vec3f(*map(float,out.max(0)))])
        override.CreateNormalsAttr().Block()
        UsdGeom.PrimvarsAPI(override).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,'vertex').Set(Vt.Vec2fArray.FromNumpy((out[:,:2]/5).astype(np.float32)))
        applied.append({'path':str(path),'method':'grid_tessellated_drape','triangles':len(new_faces),'original_surface_offset_m':float(pts[0,2]),
            'bridge_status_unverified':tags.get(wid,{}).get('bridge')!='no',
            'bridge_evidence':'OSM explicit bridge=no' if tags.get(wid,{}).get('bridge')=='no' else 'No explicit bridge/tunnel flag in cached OSM; grade remains unverified',
            'appearance_note':'UVs regenerated from local XY / 5m after tessellation; inspection proposal only'})
    for path in ['/World/Ground','/World/Context','/World/Landmarks','/World/Trees','/World/ParkedVehicles','/World/Storefronts','/World/StreetFurniture','/World/RearParkingSamples','/World/Parks','/World/Water','/World/ParcelBoundaries','/World/StudyBoundaries']:
        if source.GetPrimAtPath(path):skip(path,'not_anchored_in_this_proposal; active geometry retained, scene incomplete')
    stage.GetRootLayer().customLayerData={'status':'INCOMPLETE_UNACTIVATED_TERRAIN_ANCHORING_PROPOSAL','sceneZOriginNAVD88Meters':30.}
    output=root/'scene/terrain_anchoring_proposal.usda'
    deps.append({'path':Path(__file__).relative_to(root).as_posix(),'sha256':checksum(__file__)})
    # Fail if source assembly/dependencies changed during computation.
    verify_dependencies(root,deps)
    # Relative references resolve from the exported scene folder, after authoring.
    export=Sdf.Layer.CreateAnonymous()
    export.ImportFromString(stage.GetRootLayer().ExportToString())
    export.subLayerPaths=['terrain_proposal.usda','college_park_connected.usda']
    export.Export(str(output))
    report={'created_utc':now(),'status':'incomplete_unactivated_proposal','activated':False,'scene_z_origin_navd88_m':30.,
        'dependencies':deps,'layer':output.relative_to(root).as_posix(),'layer_sha256':checksum(output),
        'applied_candidates':applied,'skip_queue':queue,'candidate_count':len(applied),'skip_count':len(queue),
        'limits':['Not ready for activation: queued objects and flat ground remain unchanged.',
            'Bilinear DEM interpolation requires four actual valid original raster samples; no extrapolation.',
            'Building offsets are rigid and retain existing relative heights, including existing uncertainty.',
            'Roads with missing bridge tags are provisional grade-unverified candidates; explicit bridges/tunnels and water crossings are excluded.',
            'Proposal must be rebuilt through this tool if any recorded source hash changes; opening USD alone does not enforce stale guards.']}
    atomic_json(folder/'anchoring_proposal.json',report)
    return report


if __name__=='__main__':
    result=build();print(json.dumps({k:result[k] for k in ('status','candidate_count','skip_count','layer')},indent=2))
