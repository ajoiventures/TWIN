"""Full Main Street draft pedestrian continuity and dated rear-lot surface proposal."""
from pathlib import Path
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Gf,Sdf
from shapely.geometry import Polygon,LineString,Point,shape
from shapely.ops import unary_union,transform,linemerge
from shapely import constrained_delaunay_triangles,make_valid
from pyproj import Transformer
from build_rear_parking import pixel_ground

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(geometry):
    if geometry.geom_type=='LineString':return [geometry]
    if hasattr(geometry,'geoms'):return [line for part in geometry.geoms for line in lines(part)]
    return []
def polygons(geometry):
    if geometry.geom_type=='Polygon':return [geometry]
    if hasattr(geometry,'geoms'):return [poly for part in geometry.geoms for poly in polygons(part)]
    return []
def mesh_footprint(prim,cache):
    mesh=UsdGeom.Mesh(prim);points=mesh.GetPointsAttr().Get();ids=mesh.GetFaceVertexIndicesAttr().Get();offset=0;parts=[]
    matrix=cache.GetLocalToWorldTransform(prim)
    for count in mesh.GetFaceVertexCountsAttr().Get():
        coordinates=[matrix.Transform(Gf.Vec3d(points[i])) for i in ids[offset:offset+count]];offset+=count
        polygon=Polygon([(p[0],p[1]) for p in coordinates])
        if polygon.is_valid and polygon.area>1e-5:parts.append(polygon)
    return unary_union(parts)

def build(root=ROOT):
    read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    active=read(root/'data/processed/active.json');folder=root/active['relative_path'];study=read(root/'config/study_area.json')
    projection=Transformer.from_crs(4326,32617,always_xy=True)
    ox,oy=projection.transform(*study['local_origin_wgs84'])
    def local(x,y,z=None):
        a,b=projection.transform(x,y);return a-ox,b-oy
    boundaries=read(root/'data/processed/study_boundaries.geojson')
    main=transform(local,shape(next(f['geometry'] for f in boundaries['features'] if f['id']=='main_street')))
    streets=read(folder/'streets.json')['features']
    edge_features=[f for f in streets if f['properties'].get('FullStreetName')=='EDGEWATER DR']
    edge=unary_union([transform(local,shape(f['geometry'])).intersection(main.buffer(1)) for f in edge_features])
    edge=linemerge(edge) if edge.geom_type=='MultiLineString' else edge
    other=[(f['properties'].get('FullStreetName','Unknown'),transform(local,shape(f['geometry']))) for f in streets if f['properties'].get('FullStreetName')!='EDGEWATER DR']
    if edge.is_empty:raise ValueError('No official Edgewater centerline inside Main Street')
    source_path=root/'scene/college_park_connected.usda';source=Usd.Stage.Open(str(source_path));cache=UsdGeom.XformCache()
    ground=mesh_footprint(source.GetPrimAtPath('/World/Ground'),cache)
    # The program polygon can include only one frontage. Select longitudinal
    # extent with that boundary, then retain BOTH sides in a working corridor.
    scope=edge.buffer(18,cap_style=2).intersection(ground)
    road_parts=[];edge_parts=[];shoulders=[];obstacle_parts=[]
    streets_prim=source.GetPrimAtPath('/World/Streets')
    for prim in streets_prim.GetChildren():
        if not prim.IsA(UsdGeom.Mesh):continue
        if prim.GetName().startswith('Road_'):
            g=mesh_footprint(prim,cache);road_parts.append(g)
            if prim.GetCustomData().get('roadName')=='Edgewater Drive':edge_parts.append(g)
        elif prim.GetName().startswith('Shoulders_'):
            road=source.GetPrimAtPath('/World/Streets/'+prim.GetName().replace('Shoulders_','Road_'))
            if road and road.GetCustomData().get('roadName')=='Edgewater Drive':shoulders.append((prim,mesh_footprint(prim,cache)))
    for name in ('Buildings','Landmarks','Water'):
        parent=source.GetPrimAtPath('/World/'+name)
        if not parent:continue
        for prim in Usd.PrimRange(parent):
            if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':
                # Cull distant objects before polygon union.
                extent=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']).ComputeWorldBound(prim).ComputeAlignedRange()
                if extent.IsEmpty():continue
                lo,hi=extent.GetMin(),extent.GetMax()
                from shapely.geometry import box
                if not box(lo[0],lo[1],hi[0],hi[1]).intersects(scope.buffer(100)):continue
                obstacle_parts.append(mesh_footprint(prim,cache))
    roads=unary_union(road_parts);edge_roads=unary_union(edge_parts);obstacles=unary_union(obstacle_parts)
    if edge_roads.is_empty:raise ValueError('Current Edgewater carriageway source missing')
    # Existing model widths are OSM highway fallbacks, not accepted curb lines.
    # Follow their exterior so the draft never covers the modeled carriageway.
    draft=edge_roads.buffer(2.2,join_style=2).difference(edge_roads.buffer(.2,join_style=2)).intersection(scope)
    sidewalk=make_valid(draft.difference(roads.buffer(.12)).difference(obstacles.buffer(.12)))
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    world=UsdGeom.Xform.Define(stage,'/World');stage.SetDefaultPrim(world.GetPrim())
    parent=UsdGeom.Xform.Define(stage,'/World/CorridorGround')
    def material(name,color):
        m=UsdShade.Material.Define(stage,'/World/CorridorGround/Materials/'+name)
        s=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'));s.CreateIdAttr('UsdPreviewSurface')
        s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.92)
        m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface');return m
    concrete=material('ConcreteDraft',(.64,.61,.54));asphalt=material('HistoricalAsphalt',(.19,.20,.20))
    surfaces=[]
    def surface(name,geometry,z,mat,quality):
        points=[]
        for polygon in polygons(make_valid(geometry)):
            for tri in constrained_delaunay_triangles(polygon).geoms:
                if polygon.covers(tri):
                    coords=list(tri.exterior.coords)[:3]
                    if Polygon(coords).exterior.is_ccw is False:coords.reverse()
                    points.extend([(x,y,z) for x,y in coords])
        if not points:return
        mesh=UsdGeom.Mesh.Define(stage,'/World/CorridorGround/'+name)
        mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr([3]*(len(points)//3));mesh.CreateFaceVertexIndicesAttr(list(range(len(points))))
        mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True)
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat)
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set([(x/3,y/3) for x,y,z in points])
        mesh.GetPrim().SetCustomData({'quality':quality,'sourceSnapshot':active['snapshot'],'surveyAccepted':False,'widthAccepted':False})
        rendered=unary_union([Polygon([(p[0],p[1]) for p in points[i:i+3]]) for i in range(0,len(points),3)])
        if abs(rendered.area-geometry.area)>.02:raise ValueError('Surface triangulation area mismatch')
        if rendered.intersection(roads).area>.02 or rendered.intersection(obstacles).area>.02:raise ValueError('Surface overlaps visible road/building/water')
        if rendered.difference(ground).area>.02:raise ValueError('Surface leaves current scene ground')
        surfaces.append({'name':name,'area_m2':round(rendered.area,2),'triangles':len(points)//3,'quality':quality})
    surface('EdgewaterSidewalkDraft',sidewalk,.09,concrete,'centerline_derived_draft_current_OSM_widths_not_surveyed')
    replaced=[]
    for prim,g in shoulders:
        if not g.intersects(scope):continue
        # Preserve portions outside this proposal instead of hiding the entire way.
        UsdGeom.Imageable(stage.OverridePrim(prim.GetPath())).CreateVisibilityAttr('invisible')
        remainder=g.difference(scope).difference(roads.buffer(.01)).difference(obstacles.buffer(.01))
        if not remainder.is_empty:surface('Retained_'+prim.GetName(),remainder,.035,concrete,'unchanged_legacy_buffer_outside_review_corridor')
        replaced.append(str(prim.GetPath()))
    # Conservative asphalt interiors traced on the already-cached dated aerial.
    # No source pixels or speculative full-lot boundaries are embedded.
    aerial_manifest=read(root/'data/imagery/pilot_imagery_manifest.json')
    ref=next(r for r in aerial_manifest['references'] if r['service_name']=='OCPA/Aerials2025')
    image=root/ref['image_path']
    if sha(image)!=ref['image_fetch']['sha256']:raise ValueError('Dated aerial hash mismatch')
    project=Transformer.from_crs(2236,32617,always_xy=True)
    samples=[('WestNorth',[(18,315),(125,315),(129,465),(121,491),(18,491)]),
             ('WestSouth',[(69,548),(168,548),(179,650),(174,750),(65,750),(65,625)]),
             ('WestConnectingDrive',[(145,488),(187,488),(198,531),(192,650),(175,650),(165,535),(145,535)]),
             ('EastRear',[(614,401),(686,401),(695,518),(696,744),(612,744)])]
    parking=[];prior_parking=Polygon()
    for name,pixels in samples:
        g=pixel_ground(pixels,ref['export_extent'],ref['image_fetch']['width'],ref['image_fetch']['height'],project,(ox,oy))
        trimmed=g.intersection(ground).difference(obstacles.buffer(.15)).difference(roads.buffer(.15)).difference(sidewalk.buffer(.05)).difference(prior_parking)
        surface('RearAsphalt'+name,trimmed,.052,asphalt,'2025_01_aerial_interpreted_visible_asphalt_interior_not_lot_boundary')
        parking.append({'id':name,'pixels':pixels,'interpreted_area_m2':round(g.area,2),'rendered_area_m2':round(trimmed.area,2),'removed_for_source_conflicts_m2':round(g.area-trimmed.area,2)})
        prior_parking=unary_union([prior_parking,trimmed])
    # The expanded surfaces replace only the previous three local samples.
    for name in ('west_north_interior','west_south_interior','east_rear_interior'):
        path='/World/RearParkingSamples/'+name
        if source.GetPrimAtPath(path):UsdGeom.Imageable(stage.OverridePrim(path)).CreateVisibilityAttr('invisible')
    stations=[];index=0
    for segment in lines(edge):
        if segment.coords[0][1]>segment.coords[-1][1]:segment=LineString(list(segment.coords)[::-1])
        for i in range(max(1,math.ceil(segment.length/25))+1):
            distance=min(i*25,segment.length);p=segment.interpolate(distance)
            before=segment.interpolate(max(0,distance-.5));after=segment.interpolate(min(segment.length,distance+.5))
            dx,dy=after.x-before.x,after.y-before.y;norm=math.hypot(dx,dy)
            if not norm:continue
            near=sorted([(name,line.distance(p)) for name,line in other if line.distance(p)<13],key=lambda pair:pair[1])
            for side,sign in [('west',1),('east',-1)]:
                # Do not assume the City line bisects the OSM carriageway:
                # northern bends have materially different centerline offsets.
                ray=LineString([(p.x-sign*dy/norm*d,p.y+sign*dx/norm*d) for d in (0,18)])
                supported=sidewalk.intersection(ray).length
                stations.append({'station_id':index,'side':side,'xy_local_m':[round(p.x,2),round(p.y,2)],'draft_strip_present':supported>.3,'cross_section_draft_width_m':round(supported,2),'quality':'draft_width_not_verified','gap_reason':None if supported>.3 else ('junction_curb_ramp_crosswalk_unresolved: '+near[0][0] if near else 'source_footprint_or_extent_conflict_needs_aerial_review')})
            index+=1
    princeton=[{'street':name,'distance_to_edge_m':round(line.distance(edge),2)} for name,line in other if 'PRINCETON' in name and line.distance(edge)<3]
    gap_count=sum(not row['draft_strip_present'] for row in stations)
    report={'source_snapshot':active['snapshot'],'city_edgewater_features':len(edge_features),'edgewater_length_in_main_street_m':round(edge.length,2),
        'sidewalk_nominal_draft_width_m':2,'width_basis':'Existing OSM highway-class carriageway fallback; 0.2 m visual curb setback and 2 m draft strip, not measured curb/sidewalk dimensions.',
        'working_scope':'18 m both-side buffer around City Edgewater centerline clipped longitudinally to Main Street program area; not an amended official boundary.',
        'actual_sidewalk_edge_geometry_available':False,'current_conditions_only':True,'future_complete_street_applied':False,
        'surface_records':surfaces,'replaced_edgewater_shoulders':replaced,'rear_parking':parking,
        'aerial_acquisition':'2025-01','aerial_sha256':sha(image),'aerial_coverage_limit':'Princeton to southern Smith pilot only; other commercial rear lots remain unverified lawn/ground placeholders.',
        'gap_ledger':stations,'sampled_side_stations':len(stations),'draft_present_stations':len(stations)-gap_count,'unresolved_side_stations':gap_count,
        'princeton_intersection':{'city_reference_lines':princeton,'crosswalks_added':0,'ramps_added':0,'status':'Crosswalk candidate lifecycle/width domains unresolved; no invented crossings, ramps or curb radii.'},
        'remaining_gaps':['All draft sidewalk/curb widths and driveway crossings need actual edge inventory or broader dated-aerial interpretation.','Intersection cuts are deliberate: ramps, crossing alignments and traffic controls not accepted.','Full Main Street rear-lot asphalt boundaries/access/islands and northern/southern dated aerial coverage remain unresolved.','Flat prototype ground is retained; no accepted grade, curb height or ADA slope.'],
        'dependencies':{'scene/college_park_connected.usda':sha(source_path),'scene/college_park.usda':sha(root/'scene/college_park.usda'),'data/processed/study_boundaries.geojson':sha(root/'data/processed/study_boundaries.geojson'),'data/imagery/pilot_imagery_manifest.json':sha(root/'data/imagery/pilot_imagery_manifest.json'),str((folder/'streets.json').relative_to(root)):sha(folder/'streets.json')}}
    output=root/'scene/corridor_ground_proposal.usda'
    stage.GetRootLayer().customLayerData={'purpose':'Full Main Street Edgewater continuous block-side sidewalk draft plus bounded January2025 rear asphalt interpretation. Inactive proposal, not as-built acceptance.','sourceSnapshot':active['snapshot'],'surveyAccepted':False,'geometryReportJson':json.dumps(report,sort_keys=True)}
    stage.GetRootLayer().Export(str(output));report['layer_sha256']=sha(output)
    (root/'data/transport/corridor_ground_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key not in ('gap_ledger','dependencies')},indent=2));return report

if __name__=='__main__':build()
