"""Offline, source-guarded historical landmark roof proposals; never activate geometry."""
from pathlib import Path
import collections, datetime, hashlib, json, sys, os
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
import shapely
from shapely.geometry import box,shape,mapping
from shapely.ops import unary_union,polygonize
from scipy import ndimage
from scipy.spatial import cKDTree
from pyproj import Transformer
from pxr import Usd,UsdGeom,Gf
from princeton_evidence import write_surface
from correct_wellesley import polygon_parts
from mesh_topology import closed_shell_report

SITES=[{'id':'college_park_post_office','pin':'292223149200010','prim':'CollegeParkPostOffice',
        'cloud_sha256':'f50af7f58cf139a43555aa4f424f733b1fca9ca305053c1a1dfee7c8d11d8799',
        'bands':[(0,33.2),(33.2,34.7),(34.7,100)]},
       {'id':'andersen_office_1615','pin':'292223016600090','prim':'AndersenOffice1615',
        'cloud_sha256':'809a5e6998c13122e9e2a02f21f99ad33543165cecbf847b5b162699fc98e983',
        'bands':[(0,100)]}]

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def surface_geometry(mask,elevation_grid,grid_info,origin,ground,clip_geometry):
    """Fitted roof cells and one simplified continuous perimeter, no voxel walls."""
    valid=mask&np.isfinite(elevation_grid)
    nearest=ndimage.distance_transform_edt(~valid,return_distances=False,return_indices=True)
    filled=elevation_grid[tuple(nearest)];height,width=mask.shape
    step=grid_info['cell_m'];left=grid_info['left_utm_m'];bottom=grid_info['bottom_utm_m']
    render=np.zeros_like(mask)
    for y in range(height):
        for x in range(width):
            render[y,x]=clip_geometry.intersection(box(left+x*step,bottom+y*step,left+(x+1)*step,bottom+(y+1)*step)).area>1e-8
    sums=np.zeros((height+1,width+1));counts=np.zeros_like(sums)
    for dy,dx in [(0,0),(0,1),(1,0),(1,1)]:
        sums[dy:dy+height,dx:dx+width]+=np.where(render,filled,0)
        counts[dy:dy+height,dx:dx+width]+=render
    corners=sums/np.maximum(counts,1)
    def top(a,b):
        fx=np.clip((a-left)/step,0,width-1e-8);fy=np.clip((b-bottom)/step,0,height-1e-8)
        x,y=int(fx),int(fy);tx,ty=fx-x,fy-y
        z=(1-tx)*(1-ty)*corners[y,x]+tx*(1-ty)*corners[y,x+1]+tx*ty*corners[y+1,x+1]+(1-tx)*ty*corners[y+1,x]
        return(float(a-origin[0]),float(b-origin[1]),float(z-ground+.1))
    points=[];counts=[];indices=[]
    def face(coords):
        start=len(points);points.extend(coords);counts.append(len(coords));indices.extend(range(start,len(points)))
    for y,x in zip(*np.where(render)):
        cut=clip_geometry.intersection(box(left+x*step,bottom+y*step,left+(x+1)*step,bottom+(y+1)*step))
        for polygon in polygon_parts(cut):
            for triangle in shapely.constrained_delaunay_triangles(polygon).geoms:
                coords=list(triangle.exterior.coords)[:-1]
                if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(coords,coords[1:]+coords[:1]))<0:coords.reverse()
                face([top(*p) for p in coords]);face([(a-origin[0],b-origin[1],.1) for a,b in reversed(coords)])
    for polygon in polygon_parts(shapely.orient_polygons(clip_geometry,exterior_cw=False)):
        for ring in [polygon.exterior,*polygon.interiors]:
            coords=list(ring.coords)
            for a,b in zip(coords,coords[1:]):
                n=max(1,int(np.ceil(np.hypot(b[0]-a[0],b[1]-a[1])/step)))
                samples=[(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n+1)]
                for c,d in zip(samples,samples[1:]):face([(c[0]-origin[0],c[1]-origin[1],.1),(d[0]-origin[0],d[1]-origin[1],.1),top(*d),top(*c)])
    if not points or max(indices)>=len(points) or sum(counts)!=len(indices):raise ValueError('Invalid fitted roof mesh')
    return points,counts,indices


def connected_point_roof_regions(points,component):
    """Architectural regions from dense actual point-plane inliers, not cell labels.

    Class6 seeds the building outline. Class1/6 observations within that outline
    can support a roof plane; vertical facade mixtures cannot manufacture a
    per-cell height. Upper supported planes take precedence over lower returns.
    """
    info=component['grid_info'];step=info['cell_m'];left=info['left_utm_m'];bottom=info['bottom_utm_m']
    clip=component['geometry'];height,width=component['mask'].shape
    building=points[(points[:,3]==6)&shapely.contains_xy(clip,points[:,0],points[:,1])]
    low,high=np.percentile(building[:,2],[1,99])+np.array([-.5,.5])
    source=points[np.isin(points[:,3],[1,6])&shapely.contains_xy(clip,points[:,0],points[:,1])&(points[:,2]>=low)&(points[:,2]<=high)]
    before_normal_count=len(source)
    _,neighbors=cKDTree(source[:,:3]).query(source[:,:3],k=16)
    neighborhood=source[neighbors,:3];centered=neighborhood-neighborhood.mean(axis=1,keepdims=True)
    covariance=np.einsum('nki,nkj->nij',centered,centered)/16
    values,vectors=np.linalg.eigh(covariance)
    normal_z=np.abs(vectors[:,2,0]);planarity=values[:,0]/np.maximum(values[:,1],1e-10)
    source=source[(normal_z>=.65)&(planarity<=.12)]
    if len(source)<1000:raise ValueError('Insufficient locally planar roof-oriented points')
    xy=(source[:,:2]-[left,bottom])/step;A=np.c_[xy,np.ones(len(xy))];z=source[:,2]
    rng=np.random.default_rng(31);selection=rng.choice(len(z),min(10000,len(z)),False);sample_A=A[selection];sample_z=z[selection]
    remaining=np.ones(len(selection),bool);planes=[]
    for iteration in range(9):
        ids=np.where(remaining)[0]
        if len(ids)<120:break
        best=None;score=0
        for _ in range(1200):
            selected=rng.choice(ids,3,False)
            try:coef=np.linalg.solve(sample_A[selected],sample_z[selected])
            except np.linalg.LinAlgError:continue
            if np.linalg.norm(coef[:2])>1.2:continue
            keep=(np.abs(sample_A@coef-sample_z)<=.12)&remaining
            if keep.sum()>score:score=int(keep.sum());best=keep
        if score<120:break
        coef=np.linalg.lstsq(sample_A[best],sample_z[best],rcond=None)[0]
        keep=(np.abs(sample_A@coef-sample_z)<=.12)&remaining;remaining[keep]=False
        inlier=np.abs(A@coef-z)<=.15
        ix=np.floor(xy[inlier,0]).astype(int);iy=np.floor(xy[inlier,1]).astype(int)
        good=(ix>=0)&(ix<width)&(iy>=0)&(iy<height);counts=np.zeros((height,width),int)
        np.add.at(counts,(iy[good],ix[good]),1);mask=counts>=3
        ids,n=ndimage.label(ndimage.binary_closing(mask,iterations=1)|mask)
        sizes=np.bincount(ids.ravel());large=[i for i,count in enumerate(sizes) if i and count>=20]
        mask &= np.isin(ids,large)
        if mask.sum()<25:continue
        classes,ns=np.unique(source[inlier,3].astype(int),return_counts=True)
        planes.append({'coefficients_cell_xy':coef.tolist(),'mask':mask,'point_count':int(inlier.sum()),
            'source_classes':{str(k):int(n) for k,n in zip(classes,ns)},
            'point_residual_p50_p95_m':np.percentile(np.abs(A[inlier]@coef-z[inlier]),[50,95]).tolist()})
    if len(planes)<2:raise ValueError('Insufficient connected roof-plane support')
    yy,xx=np.indices((height,width));predictions=np.stack([p['coefficients_cell_xy'][0]*(xx+.5)+p['coefficients_cell_xy'][1]*(yy+.5)+p['coefficients_cell_xy'][2] for p in planes])
    available=np.stack([p['mask'] for p in planes]);labels=np.argmax(np.where(available,predictions,-1e6),axis=0);observed=available.any(axis=0)
    # Fill only source-outline cells missing a plane assignment from nearest observed region.
    nearest=ndimage.distance_transform_edt(~observed,return_distances=False,return_indices=True)
    labels=np.where(observed,labels,labels[tuple(nearest)])
    # Remove tiny label islands; broad source-supported slopes/levels remain.
    reassigned=0
    for _ in range(3):
        for plane_index in range(len(planes)):
            islands,n=ndimage.label((labels==plane_index)&component['mask'])
            sizes=np.bincount(islands.ravel())
            for island in [i for i,count in enumerate(sizes) if i and count<12]:
                patch=islands==island;ring=ndimage.binary_dilation(patch)&~patch&component['mask']
                neighbors=labels[ring]
                if not len(neighbors):continue
                replacement=int(np.bincount(neighbors,minlength=len(planes)).argmax())
                if replacement!=plane_index:labels[patch]=replacement;reassigned+=int(patch.sum())
    raw_regions=[]
    for plane_index,p in enumerate(planes):
        ids,n=ndimage.label((labels==plane_index)&component['mask'])
        for island in range(1,n+1):
            yy,xx=np.where(ids==island)
            if len(xx)<12:continue
            geometry=unary_union([box(left+x*step,bottom+y*step,left+(x+1)*step,bottom+(y+1)*step) for y,x in zip(yy,xx)]).intersection(clip)
            if geometry.area<12:continue
            raw_regions.append({'plane_index':plane_index,'geometry':geometry,'source_cells':len(xx)})
    # A common partition: simplify within1m, subtract prior regions; assign remaining
    # slivers to the nearest supported region. No holes in the footprint are filled.
    raw_regions.sort(key=lambda r:-r['geometry'].area);regions=[];occupied=shapely.GeometryCollection()
    for region in raw_regions:
        geometry=region['geometry'].simplify(1.,preserve_topology=True).intersection(clip).difference(occupied)
        if geometry.is_empty:continue
        regions.append({**region,'geometry':geometry});occupied=occupied.union(geometry)
    for leftover in polygon_parts(clip.difference(occupied)):
        if leftover.area<1e-8:continue
        nearest_region=min(regions,key=lambda r:r['geometry'].distance(leftover.representative_point()))
        nearest_region['geometry']=nearest_region['geometry'].union(leftover)
    # Evaluate the final partition against actual observations and previous cell data.
    residuals=[];cell_residuals=[];accepted_points=0
    for region in regions:
        p=planes[region['plane_index']];coef=np.asarray(p['coefficients_cell_xy'])
        inside=shapely.contains_xy(region['geometry'],source[:,0],source[:,1]);res=np.abs(A[inside]@coef-z[inside])
        residuals.extend(res.tolist());accepted_points+=int((res<=.25).sum())
        region['coefficients_cell_xy']=coef.tolist()
        region['point_residual_p50_p90_p95_m']=np.percentile(res,[50,90,95]).tolist() if len(res) else None
        yy,xx=np.where(np.isfinite(component['grid'])&component['mask'])
        in_cell=shapely.contains_xy(region['geometry'],left+(xx+.5)*step,bottom+(yy+.5)*step)
        cell_residuals.extend(np.abs(np.c_[xx[in_cell]+.5,yy[in_cell]+.5,np.ones(in_cell.sum())]@coef-component['grid'][yy[in_cell],xx[in_cell]]).tolist())
    evidence={'method':'continuous connected point-supported planar regions; no per-cell roof interpolation',
        'parameters':{'point_plane_inlier_m':.15,'minimum_plane_projected_cells':25,'minimum_connected_region_m2':12,'region_boundary_simplification_m':1.},
        'source_point_z_window_m':[float(low),float(high)],'source_points_before_normal_filter':before_normal_count,
        'point_normal_filter':{'neighbors_3d':16,'minimum_absolute_normal_z':.65,'maximum_small_to_middle_eigenvalue_ratio':.12},
        'source_classes':{str(k):int(n) for k,n in zip(*np.unique(source[:,3].astype(int),return_counts=True))},
        'source_points':len(source),'source_points_within25cm_of_final_region':accepted_points,
        'all_observation_residual_p50_p90_p95_m':np.percentile(residuals,[50,90,95]).tolist(),
        'prior_cell_p75_residual_p50_p90_p95_m':np.percentile(cell_residuals,[50,90,95]).tolist(),
        'region_count':len(regions),'small_island_reassigned_cells':reassigned,
        'planes':[{k:v for k,v in p.items() if k!='mask'} for p in planes],
        'regions':[{'plane_index':r['plane_index'],'area_m2':r['geometry'].area,'point_residual_p50_p90_p95_m':r['point_residual_p50_p90_p95_m']} for r in regions],
        'uncertainty':'Class1/6 planar support within class6-seeded footprint is historical inference. Mixed wall returns remain residuals; unknown current roof equipment/façade not invented.'}
    return regions,evidence


def connected_cell_roof_regions(component,fitted,evidence,labels):
    """Retain existing post-office plane support in continuous closed regions."""
    valid=component['mask']&np.isfinite(fitted)
    nearest=ndimage.distance_transform_edt(~valid,return_distances=False,return_indices=True)
    labels=np.where(valid,labels,labels[tuple(nearest)])
    reassigned=0
    for _ in range(3):
        for plane_index in range(len(evidence['planes'])):
            islands,n=ndimage.label((labels==plane_index)&component['mask']);sizes=np.bincount(islands.ravel())
            for island in [i for i,count in enumerate(sizes) if i and count<12]:
                patch=islands==island;ring=ndimage.binary_dilation(patch)&~patch&component['mask'];neighbors=labels[ring]
                if not len(neighbors):continue
                replacement=int(np.bincount(neighbors,minlength=len(evidence['planes'])).argmax())
                if replacement!=plane_index:labels[patch]=replacement;reassigned+=int(patch.sum())
    info=component['grid_info'];cell=info['cell_m'];left=info['left_utm_m'];bottom=info['bottom_utm_m']
    regions=[];occupied=shapely.GeometryCollection()
    candidates=[]
    for plane_index,p in enumerate(evidence['planes']):
        islands,n=ndimage.label((labels==plane_index)&component['mask'])
        for island in range(1,n+1):
            yy,xx=np.where(islands==island)
            if not len(xx):continue
            geometry=unary_union([box(left+x*cell,bottom+y*cell,left+(x+1)*cell,bottom+(y+1)*cell) for y,x in zip(yy,xx)]).intersection(component['geometry'])
            if geometry.is_empty:continue
            coef=list(p['coefficients_cell_xy']);coef[2]-=.5*(coef[0]+coef[1])
            candidates.append({'geometry':geometry,'coefficients_cell_xy':coef,'plane_index':plane_index})
    for r in sorted(candidates,key=lambda r:-r['geometry'].area):
        geometry=r['geometry'].simplify(1.,preserve_topology=True).intersection(component['geometry']).difference(occupied)
        if geometry.is_empty:continue
        regions.append({**r,'geometry':geometry});occupied=occupied.union(geometry)
    for leftover in polygon_parts(component['geometry'].difference(occupied)):
        if leftover.area<1e-8:continue
        r=min(regions,key=lambda r:r['geometry'].distance(leftover.representative_point()));r['geometry']=r['geometry'].union(leftover)
    cell_residuals=[]
    yy,xx=np.where(np.isfinite(component['grid'])&component['mask']);centers_x=left+(xx+.5)*cell;centers_y=bottom+(yy+.5)*cell
    assigned=np.zeros(len(xx),bool)
    for region in regions:
        inside=shapely.contains_xy(region['geometry'],centers_x,centers_y)&~assigned;assigned|=inside
        a,b,c=region['coefficients_cell_xy']
        cell_residuals.extend(np.abs(a*(xx[inside]+.5)+b*(yy[inside]+.5)+c-component['grid'][yy[inside],xx[inside]]).tolist())
    evidence['final_region_source_cell_residual_p50_p90_p95_max_m']=np.percentile(cell_residuals,[50,90,95,100]).tolist()
    evidence['final_region_source_cells_evaluated']=len(cell_residuals)
    evidence['final_region_source_cells_within75cm']=int((np.asarray(cell_residuals)<=.75).sum())
    evidence['source_cell_centers_on_boundaries_not_scored']=int((~assigned).sum())
    evidence['continuous_region_partition']={'regions':len(regions),'small_island_reassigned_cells':reassigned,
        'source':'same existing class6 cell-consensus planes; no new source or parcel footprint assumption',
        'cell_center_intercept_conversion_applied':True,'boundary_simplification_m':1.}
    return regions


def resolve_supported_roof_holes(points,component,regions):
    """Only tiny observed roof/equipment gaps may receive a documented lower cap."""
    info=component['grid_info'];reports=[]
    for polygon in polygon_parts(component['geometry']):
        for ring in polygon.interiors:
            hole=shapely.Polygon(ring);q=points[shapely.contains_xy(hole,points[:,0],points[:,1])]
            roof=q[np.isin(q[:,3],[1,6])];center=hole.centroid
            adjacent=[r for r in regions if r['geometry'].distance(center)<=np.sqrt(hole.area)+.1]
            def elevation(r):
                c=r['coefficients_cell_xy'];return c[0]*(center.x-info['left_utm_m'])/info['cell_m']+c[1]*(center.y-info['bottom_utm_m'])/info['cell_m']+c[2]
            candidate=min(adjacent,key=elevation) if adjacent else None
            z=elevation(candidate) if candidate else None
            nearby_support=int((np.abs(roof[:,2]-z)<=.25).sum()) if z is not None else 0
            high_fraction=float(np.mean(roof[:,2]>=z-.15)) if len(roof) and z is not None else 0
            supported=hole.area<=4 and len(roof)>=5 and nearby_support>=2 and high_fraction>=.9 and not np.any(q[:,3]==2)
            if supported:
                candidate['geometry']=candidate['geometry'].union(hole)
                component['geometry']=component['geometry'].union(hole)
            reports.append({'area_m2':hole.area,'centroid_utm_m':[center.x,center.y],'observed_points':len(q),
                'source_classes':{str(k):int(n) for k,n in zip(*np.unique(q[:,3].astype(int),return_counts=True))},
                'observed_z_p05_p50_p95_m':np.percentile(q[:,2],[5,50,95]).tolist() if len(q) else None,
                'lower_cap_plane_navd88_m':z,'points_within25cm_of_lower_plane':nearby_support,'fraction_at_or_above_lower_plane':high_fraction,
                'action':'supported_uncertain_lower_roof_cap_beneath_upper_returns' if supported else 'preserve_unresolved_void',
                'interpretation':'Classification gap with roof-level returns; no ground-reaching courtyard claim' if supported else 'Insufficient lower-roof evidence; no blanket courtyard fill'})
    return reports


def positive_step_intervals(a,b,difference):
    """Split an affine plane-height difference at equality; never bow-tie a wall."""
    da,db=difference(a),difference(b);cuts=[0.,1.]
    if da*db<0:cuts.append(float(da/(da-db)))
    cuts=sorted(cuts);segments=[]
    def interpolate(t):return(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
    for lo,hi in zip(cuts,cuts[1:]):
        if difference(interpolate((lo+hi)/2))>1e-8:segments.append((interpolate(lo),interpolate(hi)))
    return segments


def quantized_valid_geometry(geometry,minimum_roof_xy_area_m2=.001):
    """Validate the coordinates USD will actually author, then compute normals.

    Thin slivers below10cm² projected area are explicitly excluded rather than
    allowing float32 serialization to invert their winding or collapse vertices.
    """
    vertices,counts,indices=geometry;original=np.asarray(vertices,dtype=float)
    quantized=original.astype(np.float32).astype(float);new_points=[];new_counts=[];new_indices=[]
    dropped=collections.Counter();removed_roof_area=0.;offset=0
    for count in counts:
        ids=indices[offset:offset+count];offset+=count;q=quantized[ids];before=original[ids]
        original_normal=np.cross(before[1]-before[0],before[2]-before[0]);old_length=np.linalg.norm(original_normal)
        selected=[]
        for point in q:
            if not selected or np.linalg.norm(point-selected[-1])>1e-7:selected.append(point)
        if len(selected)>1 and np.linalg.norm(selected[-1]-selected[0])<1e-7:selected.pop()
        q=np.asarray(selected)
        if len(q)<3:dropped['collapsed_vertices']+=1;continue
        normal=np.cross(q[1]-q[0],q[2]-q[0]);length=np.linalg.norm(normal)
        if length<1e-8:dropped['zero_area_after_float32']+=1;continue
        projected_area=abs(normal[2])/2
        if old_length and abs(original_normal[2])/old_length>.5 and projected_area<minimum_roof_xy_area_m2:
            dropped['sub_threshold_roof_or_bottom_sliver']+=1;removed_roof_area+=projected_area;continue
        if old_length and np.dot(normal/length,original_normal/old_length)<.999:
            if projected_area<.01:dropped['unstable_sliver_normal']+=1;removed_roof_area+=projected_area;continue
            raise ValueError('Meaningful face normal changed during float32 serialization')
        if len(q)==4 and np.linalg.norm(q[0,:2]-q[3,:2])<1e-6 and np.linalg.norm(q[1,:2]-q[2,:2])<1e-6:
            if (q[3,2]-q[0,2])*(q[2,2]-q[1,2]) < -1e-10:raise ValueError('Self-crossing step quad after float32')
        start=len(new_points);new_points.extend([tuple(p) for p in q]);new_counts.append(len(q));new_indices.extend(range(start,len(new_points)))
    if not new_points:raise ValueError('All roof proposal geometry collapsed')
    return (new_points,new_counts,new_indices),{'coordinate_storage':'float32 before mesh normal calculation',
        'input_faces':len(counts),'output_faces':len(new_counts),'discarded_faces_by_reason':dict(dropped),
        'discarded_projected_roof_plus_bottom_area_m2':removed_roof_area,
        'minimum_roof_xy_area_m2':minimum_roof_xy_area_m2,
        'maximum_vertex_quantization_displacement_m':float(np.linalg.norm(quantized-original,axis=1).max()),
        'self_crossing_step_quads':0}


def mesh_topology_metrics(geometry):
    vertices,counts,indices=geometry;edges=collections.Counter();directions=collections.Counter();offset=0;volume=0
    for count in counts:
        q=[tuple(vertices[i]) for i in indices[offset:offset+count]];offset+=count
        for a,b in zip(q,q[1:]+q[:1]):
            key=tuple(sorted((a,b)));edges[key]+=1;directions[key]+=1 if (a,b)==key else -1
        for j in range(1,len(q)-1):volume+=np.dot(q[0],np.cross(q[j],q[j+1]))/6
    return {'unique_vertices':len(set(tuple(p) for p in vertices)),'unique_edges':len(edges),'faces':len(counts),
        'boundary_edges':sum(n==1 for n in edges.values()),'nonmanifold_edges':sum(n>2 for n in edges.values()),
        'nonmanifold_edge_examples':[(e,n) for e,n in edges.items() if n>2][:3],
        'orientation_conflicts':sum(n==2 and directions[e]!=0 for e,n in edges.items()),
        'signed_volume_m3':float(volume),'euler_characteristic':len(set(tuple(p) for p in vertices))-len(edges)+len(counts)}


def planar_region_geometry(regions,info,origin,ground,_regularization_pass=0):
    """Closed common planar arrangement with every 2D/vertical T-junction noded."""
    step=info['cell_m'];left=info['left_utm_m'];bottom=info['bottom_utm_m']
    def height(region,p):
        c=region['coefficients_cell_xy'];return c[0]*(p[0]+origin[0]-left)/step+c[1]*(p[1]+origin[1]-bottom)/step+c[2]-ground+.1
    local=[]
    for region in regions:
        geometry=shapely.transform(region['geometry'],lambda x,y:(x-origin[0],y-origin[1]),interleaved=False)
        local.append(shapely.set_precision(geometry,.001))
    footprint=unary_union(local)
    lines=unary_union([g.boundary for g in local]+[footprint.boundary])
    cells=[]
    for polygon in polygonize(lines):
        point=polygon.representative_point()
        if not footprint.covers(point):continue
        choices=[i for i,g in enumerate(local) if g.covers(point)]
        if not choices:
            nearest=min(range(len(local)),key=lambda i:local[i].distance(point))
            if local[nearest].distance(point)>.002:raise ValueError('Unassigned common roof arrangement cell')
            choices=[nearest]
        cells.append({'geometry':shapely.orient_polygons(polygon,exterior_cw=False),'region':choices[0]})
    # The arrangement has common atomic edges even at existing region T-junctions.
    edge_cells=collections.defaultdict(list)
    for i,cell in enumerate(cells):
        polygon=cell['geometry']
        for ring in [polygon.exterior,*polygon.interiors]:
            coords=list(ring.coords)
            for a,b in zip(coords,coords[1:]):edge_cells[tuple(sorted((a,b)))].append((i,a,b))
    if any(len(v)>2 for v in edge_cells.values()):raise ValueError('Nonmanifold planar arrangement')
    cuts={}
    for edge,neighbors in edge_cells.items():
        a,b=edge;points=[a,b]
        if len(neighbors)==2:
            ra=regions[cells[neighbors[0][0]]['region']];rb=regions[cells[neighbors[1][0]]['region']]
            da=height(ra,a)-height(rb,a);db=height(ra,b)-height(rb,b)
            if da*db<0:
                t=da/(da-db);point=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
                if min(np.linalg.norm(np.asarray(point)-a),np.linalg.norm(np.asarray(point)-b))>.001:points.insert(1,point)
        cuts[edge]=points
    # All roof/bottom triangles use actual authored float32 XY vertices from here.
    def xy32(p):return tuple(np.asarray(p,dtype=np.float32).astype(float))
    rings=[];xy_regions=collections.defaultdict(set)
    for i,cell in enumerate(cells):
        output=[]
        for ring in [cell['geometry'].exterior,*cell['geometry'].interiors]:
            coords=list(ring.coords);expanded=[]
            for a,b in zip(coords,coords[1:]):
                pts=cuts[tuple(sorted((a,b)))];pts=pts if pts[0]==a else list(reversed(pts))
                expanded.extend(xy32(p) for p in pts[:-1])
            output.append(expanded)
            for p in expanded:xy_regions[p].add(cell['region'])
        rings.append(output)
    levels={};canonical_height={};maximum_weld=0.
    for xy,region_ids in xy_regions.items():
        observations=[(.1,None)]+[(height(regions[i],xy),i) for i in region_ids]
        groups=[]
        for z,i in sorted(observations):
            if groups and z-groups[-1][-1][0]<=.002:groups[-1].append((z,i))
            else:groups.append([(z,i)])
        ls=[]
        for group in groups:
            average=float(np.float32(np.mean([z for z,_ in group])));ls.append(average)
            for z,i in group:canonical_height[(xy,i)]=average;maximum_weld=max(maximum_weld,abs(z-average))
        levels[xy]=ls
    vertices=[];counts=[];indices=[];vertex_ids={};roof_maxres=0.
    def vertex(xy,z):
        key=(*xy,float(np.float32(z)))
        if key not in vertex_ids:vertex_ids[key]=len(vertices);vertices.append(key)
        return vertex_ids[key]
    def triangle(ids):
        q=np.asarray([vertices[i] for i in ids]);normal=np.cross(q[1]-q[0],q[2]-q[0])
        if np.linalg.norm(normal)<1e-8:raise ValueError('Degenerate common-arrangement triangle')
        indices.extend(ids);counts.append(3)
    # Rebuild each cell with all added equality nodes before constrained triangulation.
    for i,cell in enumerate(cells):
        region_id=cell['region'];r=regions[region_id];polygon=shapely.Polygon(rings[i][0],rings[i][1:])
        for tri in shapely.constrained_delaunay_triangles(polygon).geoms:
            xy=list(tri.exterior.coords)[:-1]
            if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(xy,xy[1:]+xy[:1]))<0:xy.reverse()
            upper=[];lower=[]
            for point in xy:
                z=canonical_height[(point,region_id)];upper.append(vertex(point,z));lower.append(vertex(point,canonical_height[(point,None)]))
                roof_maxres=max(roof_maxres,abs(z-height(r,point)))
            triangle(upper);triangle(list(reversed(lower)))
    # Each atomic boundary is emitted once. Vertical endpoint levels include ALL
    # incident roof planes, preventing 3D T-junctions between adjacent step walls.
    for edge,neighbors in edge_cells.items():
        pieces=cuts[edge]
        for a0,b0 in zip(pieces,pieces[1:]):
            a,b=xy32(a0),xy32(b0)
            if len(neighbors)==1:
                cell_id,start,end=neighbors[0];region_id=cells[cell_id]['region']
                if start!=edge[0]:a,b=b,a
                high_id=region_id;low_id=None
            else:
                ia,ib=neighbors[0][0],neighbors[1][0];ra=cells[ia]['region'];rb=cells[ib]['region']
                za=(canonical_height[(a,ra)]+canonical_height[(b,ra)])/2;zb=(canonical_height[(a,rb)]+canonical_height[(b,rb)])/2
                if abs(za-zb)<1e-7:continue
                high_id,low_id=(ra,rb) if za>zb else (rb,ra)
                high_neighbor=next(n for n in neighbors if cells[n[0]]['region']==high_id)
                if high_neighbor[1]!=edge[0]:a,b=b,a
            lo_a=canonical_height[(a,low_id)];lo_b=canonical_height[(b,low_id)]
            hi_a=canonical_height[(a,high_id)];hi_b=canonical_height[(b,high_id)]
            if min(hi_a-lo_a,hi_b-lo_b)<-1e-6:raise ValueError('Unsplit plane crossing in common arrangement')
            length=float(np.linalg.norm(np.asarray(b)-a))
            profile=[(0.,lo_a),(length,lo_b)]
            profile.extend((length,z) for z in levels[b] if lo_b<z<=hi_b)
            profile.append((0.,hi_a));profile.extend((0.,z) for z in reversed(levels[a]) if lo_a<z<hi_a)
            clean=[]
            for p in profile:
                if not clean or p!=clean[-1]:clean.append(p)
            if clean[0]==clean[-1]:clean.pop()
            if len(clean)<3:continue
            wall=shapely.Polygon(clean)
            if wall.area<1e-9:continue
            for tri in shapely.constrained_delaunay_triangles(wall).geoms:
                uz=list(tri.exterior.coords)[:-1]
                if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(uz,uz[1:]+uz[:1]))<0:uz.reverse()
                ids=[]
                for u,z in uz:
                    xy=a if abs(u)<1e-8 else b
                    ids.append(vertex(xy,z))
                triangle(ids)
    result=(vertices,counts,indices);topology=mesh_topology_metrics(result)
    roof_polygons=[];offset=0
    for count in counts:
        q=np.asarray([vertices[i] for i in indices[offset:offset+count]]);offset+=count
        normal=np.cross(q[1]-q[0],q[2]-q[0])
        if normal[2]>1e-10:roof_polygons.append(shapely.Polygon(q[:,:2]))
    roof_union=unary_union(roof_polygons)
    float_footprint=unary_union([shapely.Polygon(r[0],r[1:]) for r in rings])
    coverage={'expected_projected_area_m2':float_footprint.area,'actual_projected_area_m2':roof_union.area,
              'missing_projected_area_m2':float_footprint.difference(roof_union).area,
              'overlapping_projected_area_m2':sum(p.area for p in roof_polygons)-roof_union.area}
    if coverage['missing_projected_area_m2']>1e-6 or coverage['overlapping_projected_area_m2']>1e-6:raise ValueError('Roof partition coverage is incomplete')
    if topology['nonmanifold_edges'] and not topology['boundary_edges'] and _regularization_pass<3:
        # A four-sector high/low checkerboard at one exact XY point is a
        # nonmanifold contact. Resolve only its5mm neighborhood with an existing
        # upper plane; never enlarge the footprint or alter broad roof forms.
        revised=[dict(r) for r in regions];repairs=[]
        for edge,incidence in topology['nonmanifold_edge_examples']:
            xy=edge[0][:2];absolute=shapely.Point(xy[0]+origin[0],xy[1]+origin[1])
            patch=absolute.buffer(.005,quad_segs=1).intersection(unary_union([r['geometry'] for r in revised]))
            candidates=[i for i,r in enumerate(revised) if r['geometry'].distance(absolute)<.01]
            selected=max(candidates,key=lambda i:height(revised[i],xy))
            for i,r in enumerate(revised):r['geometry']=r['geometry'].difference(patch) if i!=selected else r['geometry'].union(patch)
            repairs.append({'xy_local_m':xy,'area_m2':patch.area,'radius_m':.005,'reason':'ambiguous four-sector roof contact made manifold with existing upper plane'})
        result,report=planar_region_geometry(revised,info,origin,ground,_regularization_pass+1)
        report.setdefault('topology_junction_regularization',[]).extend(repairs)
        return result,report
    if topology['boundary_edges'] or topology['nonmanifold_edges'] or topology['orientation_conflicts']:raise ValueError('Roof shell is not closed: '+str(topology))
    return result,{'roof_triangle_plane_residual_max_m':roof_maxres,'roof_regions':len(regions),'mesh_face_count':len(counts),
        'roof_construction':'common noded planar arrangement; exact region planes; all equality and vertical T-junction nodes shared',
        'topology':topology,'roof_coverage':coverage,'topology_xy_snap_m':.001,'maximum_height_weld_m':maximum_weld,
        'arrangement_cells':len(cells),'preserved_footprint_holes':sum(len(p.interiors) for p in polygon_parts(footprint)),
        'arrangement_footprint_area_m2':footprint.area}


def roof_normal_metrics(geometry):
    vertices,counts,indices=geometry;offset=0;normals=[]
    for count in counts:
        q=np.asarray([vertices[i] for i in indices[offset:offset+count]]);offset+=count
        normal=np.cross(q[1]-q[0],q[2]-q[0]);length=np.linalg.norm(normal)
        if length and normal[2]/length>.55 and min(q[:,2])>.2:normals.append(normal/length)
    return {'roof_face_count':len(normals),'distinct_roof_normals_rounded_3dec':len(np.unique(np.round(normals,3),axis=0))}


def fit_roof_planes(grid,mask,tolerance=.25,max_planes=8,return_labels=False):
    """Deterministic consensus planes; sparse high tails do not become roof spikes.

    Spatial label regularization acts only among supported plane candidates;
    discontinuities greater than0.8m receive a small boundary penalty so real
    roof steps survive. Unmatched source cells remain explicit uncertainty.
    """
    valid=mask&np.isfinite(grid);yy,xx=np.where(valid);z=grid[valid]
    if len(z)<35:raise ValueError('Insufficient cells for robust roof interpretation')
    A=np.column_stack([xx,yy,np.ones(len(xx))]);remaining=np.ones(len(z),bool);rng=np.random.default_rng(17);planes=[]
    minimum=max(25,int(len(z)*.025))
    for iteration in range(max_planes):
        ids=np.where(remaining)[0]
        if len(ids)<minimum:break
        best=None;score=0
        for _ in range(800):
            sample=rng.choice(ids,3,replace=False)
            try:coeff=np.linalg.solve(A[sample],z[sample])
            except np.linalg.LinAlgError:continue
            if np.linalg.norm(coeff[:2])>.9:continue
            keep=(np.abs(A@coeff-z)<=tolerance)&remaining
            if keep.sum()>score:best=keep;score=int(keep.sum())
        if score<minimum:break
        coeff=np.linalg.lstsq(A[best],z[best],rcond=None)[0]
        keep=(np.abs(A@coeff-z)<=tolerance)&remaining
        if keep.sum()<minimum:break
        remaining[keep]=False
        planes.append({'coefficients_cell_xy':coeff.tolist(),'consensus_cells':int(keep.sum()),'consensus_z_range_m':[float(z[keep].min()),float(z[keep].max())],
                       'consensus_residual_p50_p95_m':np.percentile(np.abs(A[keep]@coeff-z[keep]),[50,95]).tolist()})
    if not planes:raise ValueError('No robust architectural roof plane')
    predictions=np.column_stack([A@np.asarray(p['coefficients_cell_xy']) for p in planes])
    residual=np.abs(predictions-z[:,None])
    admissible=np.column_stack([(predictions[:,i]>=p['consensus_z_range_m'][0]-.25)&(predictions[:,i]<=p['consensus_z_range_m'][1]+.25) for i,p in enumerate(planes)])
    candidate_cost=np.where(admissible,residual,1e6);labels=np.argmin(candidate_cost,axis=1)
    # An outlier cannot demand an extreme plane: use nearby consensus geometry.
    outlier=residual.min(axis=1)>.75
    image=np.full(grid.shape,-1,int);image[valid]=labels
    for _ in range(5):
        updated=image.copy()
        for index,(y,x) in enumerate(zip(yy,xx)):
            cost=np.where(admissible[index],np.minimum(residual[index],.8)**2,1e6)
            for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
                ny,nx=y+dy,x+dx
                if 0<=ny<grid.shape[0] and 0<=nx<grid.shape[1] and image[ny,nx]>=0:
                    weight=.18 if abs(grid[ny,nx]-z[index])<=.8 else .025
                    cost+=weight*(np.arange(len(planes))!=image[ny,nx])
            updated[y,x]=int(np.argmin(cost))
        image=updated
    labels=image[valid];fit=predictions[np.arange(len(z)),labels]
    outlier=np.abs(fit-z)>.75
    if outlier.any():
        source_inlier=np.zeros(grid.shape,bool);source_inlier[valid]=~outlier
        nearest=ndimage.distance_transform_edt(~source_inlier,return_distances=False,return_indices=True)
        for index in np.where(outlier)[0]:
            y,x=yy[index],xx[index];label=image[nearest[0,y,x],nearest[1,y,x]]
            fit[index]=predictions[index,label]
            image[y,x]=label
    # Explicitly preserve a bound for cells treated as supporting the fit.
    accepted=np.abs(fit-z)<=.75
    if accepted.mean()<.85:raise ValueError('Roof model has insufficient source agreement')
    result=np.full(grid.shape,np.nan);result[valid]=fit
    evidence={'method':'deterministic consensus planes with spatial assignment, not raw-cell extrusion',
        'parameters':{'plane_tolerance_m':tolerance,'maximum_planes':max_planes,'minimum_plane_cells':minimum,
                      'maximum_slope_m_per_m':.9,'support_residual_bound_m':.75,'edge_simplification_bound_m':1.0},
        'planes':planes,'source_cells':len(z),'accepted_fit_cells':int(accepted.sum()),
        'outlier_or_unresolved_cells':int((~accepted).sum()),
        'source_fit_absolute_residual_p50_p90_p95_max_m':np.percentile(np.abs(fit-z),[50,90,95,100]).tolist(),
        'accepted_residual_p50_p95_max_m':np.percentile(np.abs(fit[accepted]-z[accepted]),[50,95,100]).tolist(),
        'source_z_range_m':[float(z.min()),float(z.max())],'fitted_z_range_m':[float(fit.min()),float(fit.max())],
        'outlier_policy':'Excluded high/low cells use surrounding supported roof interpretation; equipment is not inferred from isolated returns. No added occupied floors.',
        'uncertainty':'Consensus is historical geometric interpretation, not certified roof segmentation; residual bound is source agreement, not survey accuracy.'}
    return (result,evidence,image) if return_labels else (result,evidence)


def simplify_supported_outline(geometry,parcel,tolerance=1.):
    simplified=geometry.simplify(tolerance,preserve_topology=True).intersection(parcel)
    # Preserve actual internal voids even if smoothing would shift their boundary.
    polygons=list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry]
    holes=[shapely.Polygon(ring) for polygon in polygons for ring in polygon.interiors]
    if holes:simplified=simplified.difference(unary_union(holes))
    if not geometry.buffer(tolerance+1e-6).covers(simplified):raise ValueError('Outline exceeds source edge displacement bound')
    return simplified


def supported_components(points,bands,parcel,cell=1.,minimum_component_m2=12.):
    if points.ndim!=2 or points.shape[1]!=4 or not np.isfinite(points).all(): raise ValueError('Nonfinite or malformed source points')
    ground_points=points[points[:,3]==2,2]
    if len(ground_points)<100: raise ValueError('Insufficient classified local ground')
    ground=float(np.median(ground_points))
    source=points[(points[:,3]==6)&(points[:,2]>ground+2)&(points[:,2]<ground+16)]
    if len(source)<500: raise ValueError('Insufficient classified building evidence')
    left,bottom=np.floor(source[:,:2].min(axis=0)/cell)*cell
    ix=np.floor((source[:,0]-left)/cell).astype(int);iy=np.floor((source[:,1]-bottom)/cell).astype(int)
    width,height=int(ix.max()+1),int(iy.max()+1)
    if width*height>100000: raise ValueError('Bounded roof grid exceeded')
    codes=iy*width+ix;order=np.argsort(codes);ids,starts,counts=np.unique(codes[order],return_index=True,return_counts=True)
    grid=np.full((height,width),np.nan);density=np.zeros((height,width),int)
    for code,start,count in zip(ids,starts,counts):
        z=source[order[start:start+count],2]
        if count>=3:
            grid.flat[code]=np.percentile(z,75);density.flat[code]=count
    info={'left_utm_m':float(left),'bottom_utm_m':float(bottom),'cell_m':cell}
    # Closing can only use separately observed building/unclassified returns near the proposed roof.
    auxiliary=points[np.isin(points[:,3],[1,6])]
    ax=np.floor((auxiliary[:,0]-left)/cell).astype(int);ay=np.floor((auxiliary[:,1]-bottom)/cell).astype(int)
    in_grid=(ax>=0)&(ax<width)&(ay>=0)&(ay<height)
    auxiliary=auxiliary[in_grid];ax=ax[in_grid];ay=ay[in_grid]
    auxiliary_codes=ay*width+ax
    components=[];occupied=shapely.GeometryCollection()
    # Higher roof groups win any overlapping morphological boundary.
    for band_index,(lo,hi) in reversed(list(enumerate(bands))):
        raw=np.isfinite(grid)&(grid>=lo)&(grid<hi)
        candidate=ndimage.binary_closing(raw,iterations=1)|raw
        added=candidate&~raw
        for y,x in zip(*np.where(added)):
            z=auxiliary[auxiliary_codes==y*width+x,2]
            nearby=grid[max(0,y-1):y+2,max(0,x-1):x+2]
            center=np.nanmedian(nearby) if np.isfinite(nearby).any() else np.nan
            if not np.isfinite(center) or np.sum(np.abs(z-center)<=.75)<3: candidate[y,x]=False
        labels,n=ndimage.label(candidate)
        for label in range(1,n+1):
            mask=labels==label
            if mask.sum()*cell*cell<minimum_component_m2: continue
            yy,xx=np.where(mask)
            footprint=unary_union([box(left+x*cell,bottom+y*cell,left+(x+1)*cell,bottom+(y+1)*cell) for y,x in zip(yy,xx)]).intersection(parcel).difference(occupied)
            if footprint.area<minimum_component_m2:continue
            supported=mask&raw
            if supported.sum()/mask.sum()<.85:raise ValueError('Excessive unsupported morphology')
            elevations=grid[supported]
            components.append({'id':f'RoofBand{band_index}_Component{label}','mask':mask,'grid':np.where(raw,grid,np.nan),
                'geometry':footprint,'ground_m':ground,'grid_info':info,'area_m2':footprint.area,
                'supported_cells':int(supported.sum()),'observed_auxiliary_infill_cells':int((mask&~raw).sum()),
                'source_building_points':int(density[supported].sum()),
                'roof_z_p05_p50_p95_m':np.percentile(elevations,[5,50,95]).tolist(),
                'relative_height_p05_p50_p95_m':(np.percentile(elevations,[5,50,95])-ground).tolist(),
                'interpretation':'Historical classified-building upper surface; variable roof profile, per-wing storeys unknown'})
            occupied=occupied.union(footprint)
    if not components:raise ValueError('No supported building component')
    if occupied.area>parcel.area*.85:raise ValueError('Roof proposal resembles parcel envelope; inspect support')
    primary=max(components,key=lambda c:c['area_m2'])
    nearby=points[(points[:,3]==2)&shapely.contains_xy(primary['geometry'].buffer(3),points[:,0],points[:,1])]
    if len(nearby)<100:raise ValueError('Insufficient building-adjacent ground for relative height')
    reference=float(np.median(nearby[:,2]))
    for c in components:
        c['ground_m']=reference
        c['relative_height_p05_p50_p95_m']=(np.asarray(c['roof_z_p05_p50_p95_m'])-reference).tolist()
    return components,{'ground_median_navd88_m':reference,'parcel_ground_median_navd88_m':ground,
        'ground_reference_method':'Median class2 within3m of largest supported roof footprint; common local scene datum across site components',
        'building_adjacent_ground_points':len(nearby),'building_adjacent_ground_z_p05_p95_m':np.percentile(nearby[:,2],[5,95]).tolist(),'ground_points':len(ground_points),
        'classified_building_points_in_height_window':len(source),'ground_z_p05_p95_m':np.percentile(ground_points,[5,95]).tolist(),
        'cell_m':cell,'point_class_scope':'Footprint seeds and roof heights use class6 only; class1 can corroborate small closing cells but cannot seed a building.',
        'height_estimator':'Class6 per-cell p75 observations interpreted by consensus roof planes; not surveyed planes',
        'roof_union_area_m2':occupied.area,'parcel_search_area_m2':parcel.area}

def verify_source(root,site,active):
    folder=root/'data/heights/landmarks'/site['id'];evidence_path=folder/'evidence.json';cloud=folder/'points.npz';evidence=read(evidence_path)
    if evidence['parcel_id']!=site['pin'] or evidence['source_snapshot']!=active['snapshot']:raise ValueError('Landmark identity/snapshot changed')
    if sha(cloud)!=site['cloud_sha256'] or sha(cloud)!=evidence['cloud_sha256']:raise ValueError('Historical cloud changed; review reconstruction')
    if evidence['source']['ept_url']!='https://s3-us-west-2.amazonaws.com/usgs-lidar-public/FL_Peninsular_FDEM_Orange_2018/':raise ValueError('Unexpected historical acquisition')
    if evidence['ocpa_footprint_features']!=0:raise ValueError('New official footprint evidence requires reconciliation')
    unit=read(root/'data/heights/vertical_unit_check.json')
    if not unit.get('accepted') or unit.get('ept_z_unit')!='meters':raise ValueError('Vertical meter validation missing')
    for receipt in evidence['source']['node_receipts']:
        path=Path(receipt['cache']).resolve()
        if not path.is_relative_to((root/'data/cache').resolve()) or sha(path)!=receipt['sha256']:raise ValueError('Original source-node checksum/path mismatch')
    return np.load(cloud)['points'],evidence,sha(evidence_path)

def build(root=ROOT):
    active=read(root/'data/processed/active.json');snapshot=(root/active['relative_path']).resolve()
    if not snapshot.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Invalid snapshot path')
    parcels=read(snapshot/'parcels.json')['features'];t=Transformer.from_crs(4326,32617,always_xy=True)
    origin=t.transform(-81.389,28.572)
    layer_path=root/'scene/landmark_building_proposal.usda';stage=Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z');reports=[]
    for site in SITES:
        points,evidence,evidence_sha=verify_source(root,site,active)
        rows=[f for f in parcels if f['properties']['parcel_id']==site['pin']]
        if len(rows)!=1:raise ValueError('Expected exactly one target parcel')
        feature=rows[0];parcel=shapely.transform(shape(feature['geometry']),t.transform,interleaved=False)
        components,diagnostics=supported_components(points,site['bands'],parcel)
        root_path='/World/Landmarks/'+site['prim'];project=UsdGeom.Xform.Define(stage,root_path)
        project.GetPrim().SetCustomData({'parcelId':site['pin'],'siteAddress':evidence['site_address'],
          'quality':'historical_2018_2019_point_derived_proposal_not_current_survey','sourceSnapshot':active['snapshot'],
          'sourceCloudSha256':site['cloud_sha256'],'parcelLinkStatus':'new landmark context only; no legacy association promoted'})
        records=[];rendered_occupied=shapely.GeometryCollection()
        for component in components:
            original_outline=component['geometry']
            component['geometry']=simplify_supported_outline(original_outline,parcel).difference(rendered_occupied)
            rendered_occupied=rendered_occupied.union(component['geometry'])
            if site['id']=='andersen_office_1615':
                regions,fit_evidence=connected_point_roof_regions(points,component)
                fit_evidence['source_hole_review']=resolve_supported_roof_holes(points,component,regions)
                rendered_occupied=rendered_occupied.union(component['geometry'])
                geometry,mesh_evidence=planar_region_geometry(regions,component['grid_info'],origin,component['ground_m'])
                geometry,float_evidence=quantized_valid_geometry(geometry,minimum_roof_xy_area_m2=0.)
                if float_evidence['input_faces']!=float_evidence['output_faces']:raise ValueError('Closed roof lost a face during float validation')
                fit_evidence.update(mesh_evidence)
                fit_evidence['float_serialization_validation']=float_evidence
                prior_fit,_=fit_roof_planes(component['grid'],component['mask'])
                prior_mesh=surface_geometry(component['mask'],prior_fit,component['grid_info'],origin,component['ground_m'],component['geometry'])
                fit_evidence['roughness_comparison']={'prior_mixed_cell_roof':roof_normal_metrics(prior_mesh),'continuous_region_roof':roof_normal_metrics(geometry)}
                fit_evidence['reference_review']={'source':'https://www.bbdre.com/wp-content/uploads/2023/05/1615-Edgewater-Dr-2025-1.pdf','reviewed_physical_pages':[3,4,9],
                    'photo_capture_date':'unknown;2025 filename and2023 uploadpath do not establish capturedate',
                    'qualitative_corroboration':'Two-storey brick office, dark pitched roof, dormers, chimneys, central colonnaded clock pediment; point-supported side slopes about26degrees.',
                    'image_tracing_or_texture_reuse':False}
            else:
                fitted,fit_evidence,labels=fit_roof_planes(component['grid'],component['mask'],return_labels=True)
                regions=connected_cell_roof_regions(component,fitted,fit_evidence,labels)
                geometry,mesh_evidence=planar_region_geometry(regions,component['grid_info'],origin,component['ground_m'])
                geometry,float_evidence=quantized_valid_geometry(geometry,minimum_roof_xy_area_m2=0.)
                if float_evidence['input_faces']!=float_evidence['output_faces']:raise ValueError('Closed post-office roof lost a face')
                fit_evidence.update(mesh_evidence);fit_evidence['float_serialization_validation']=float_evidence
                fit_evidence['roughness_comparison']={'prior_mixed_cell_roof':roof_normal_metrics(surface_geometry(component['mask'],fitted,component['grid_info'],origin,component['ground_m'],component['geometry'])),
                    'continuous_region_roof':roof_normal_metrics(geometry)}
            fit_evidence['closed_shell_export_gate']=closed_shell_report(*geometry)
            if not fit_evidence['closed_shell_export_gate']['passed_closed_shell']:raise ValueError('Reconstructed component failed closed-shell gate')
            fit_evidence['original_outline_area_m2']=original_outline.area
            fit_evidence['simplified_outline_area_m2']=component['geometry'].area
            component['area_m2']=component['geometry'].area
            component['roof_interpretation']=fit_evidence
            mesh=write_surface(stage,root_path+'/'+component['id'],geometry)
            mesh.CreateDisplayColorAttr([Gf.Vec3f(.74,.73,.69)])
            mesh.GetPrim().SetCustomData({'quality':'historical_consensus_roof_plane_candidate','storeys':'unknown per component',
                'sourceBuildingPoints':component['source_building_points'],'roofElevationMedianNAVD88Meters':component['roof_z_p05_p50_p95_m'][1]})
            record={k:v for k,v in component.items() if k not in ['mask','grid','geometry','grid_info']}
            ground_bounds=diagnostics['building_adjacent_ground_z_p05_p95_m']
            record['main_roof_height_ground_reference_range_m']=[component['roof_z_p05_p50_p95_m'][1]-ground_bounds[1],component['roof_z_p05_p50_p95_m'][1]-ground_bounds[0]]
            record['height_uncertainty_note']='Range expresses observed adjacent-ground p05-p95 variation only, not statistical confidence or survey accuracy; roof slope/source classification/grid remain additional uncertainty.'
            record.update({'usd_path':str(mesh.GetPath()),'prim_path':str(mesh.GetPath()), 'status':'provisional_historical_source_derived', 'accepted_current_geometry':False,
                'main_roof_height_m':component['roof_z_p05_p50_p95_m'][1]-component['ground_m'],
                'roof_support_area_m2':component['supported_cells'], 'footprint_seed_source_classes':['6'],
                'roof_source_classes':fit_evidence.get('source_classes',{'6':component['source_building_points']}),'faces':len(geometry[1]),'vertices':len(geometry[0]),
                'footprint_utm':mapping(component['geometry']),'maximum_rendered_height_m':max(p[2] for p in geometry[0])-.1})
            records.append(record)
        if site['id']=='andersen_office_1615':
            diagnostics['point_class_scope']='Class6 seeds outline; locally planar roof-oriented class1/6 points support continuous planes inside that outline. No tax-link acceptance.'
            diagnostics['height_estimator']='Continuous connected point-supported roof planes; main height retains observed class6 cell median, maximum uses interpreted mesh.'
        diagnostics['source_seed_roof_union_area_m2']=diagnostics['roof_union_area_m2']
        diagnostics['roof_union_area_m2']=rendered_occupied.area
        center=parcel.centroid;camera=UsdGeom.Camera.Define(stage,'/World/Cameras/'+site['prim']+'Evidence')
        target=Gf.Vec3d(center.x-origin[0],center.y-origin[1],5);eye=target+Gf.Vec3d(-85,-90,85)
        camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse());camera.CreateFocalLengthAttr(32)
        reports.append({'site_id':site['id'],'parcel_id':site['pin'],'site_address':evidence['site_address'],
            'source_snapshot':active['snapshot'],'prim_path':root_path,'status':'provisional_historical_source_derived','accepted_current_geometry':False,
            'main_roof_height_m':max(records,key=lambda c:c['area_m2'])['main_roof_height_m'],
            'maximum_rendered_height_m':max(c['maximum_rendered_height_m'] for c in records),
            'roof_interpretation_revision':4 if site['id']=='andersen_office_1615' else 3,
            'main_roof_height_ground_reference_range_m':max(records,key=lambda c:c['area_m2'])['main_roof_height_ground_reference_range_m'],
            'height_uncertainty_note':records[0]['height_uncertainty_note'],
            'roof_support_area_m2':sum(c['roof_support_area_m2'] for c in records),'roof_source_classes':dict(collections.Counter({k:sum(c['roof_source_classes'].get(k,0) for c in records) for k in set().union(*(c['roof_source_classes'] for c in records))})),
            'cloud_sha256':site['cloud_sha256'],'evidence_sha256':evidence_sha,
            'source_evidence':str(root/'data/heights/landmarks'/site['id']/'evidence.json'),
            'official_property_context':feature['properties'],'diagnostics':diagnostics,'components':records,
            'camera':str(camera.GetPath()),'legacy_geometry_hidden':False,'original_parcel_links_modified':False})
    stage.GetRootLayer().customLayerData={'activation':'proposal_only_not_composed','quality':'historical classified roof candidates; current shape and facade unverified','sourceSnapshot':active['snapshot']}
    temporary_layer=layer_path.with_name(layer_path.stem+'.tmp.usda')
    stage.GetRootLayer().Export(str(temporary_layer));os.replace(temporary_layer,layer_path)
    manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],
        'tool_sha256':sha(Path(__file__)),'layer':str(layer_path),'layer_sha256':sha(layer_path),'sites':reports,
        'action':'await_parent_identity_geometry_review_before_composition','network_requests':0,
        'global_height_rows_modified':0,'registry_modified':False,'root_assembly_modified':False,
        'limitations':['Historical2018–2019 cloud; local flight date and current shape unverified.','Class6 labels and cell p75 are source-supported candidates, not certified architectural segmentation.',
            'No facade, signs, canopy use, entrances, window layout, occupation or public/service area inferred.',
            'Parcel clips/searches only; no cadastral envelope extrusion. No existing source groups hidden without identity review.',
            'Scene uses relative local ground datum; NAVD88 metadata is not terrain rebasing. Grid edges and roof pitch approximate.']}
    out=root/'data/heights/landmarks/proposal_manifest.json';temporary=out.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(manifest,indent=2),encoding='utf-8');os.replace(temporary,out)
    print(json.dumps([{'site':r['site_id'],'components':len(r['components']),**r['diagnostics']} for r in reports],indent=2))
    return manifest

if __name__=='__main__':build()
