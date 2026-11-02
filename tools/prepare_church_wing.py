"""Prepare inactive source-bound church wing roof/form studies.

Default is an interior two-plane crop. Full mode preserves the rejected
end-transition study; continuous mode uses a qualified roof-cover interpretation,
optional explicitly estimated wall enclosure and bounded source masks. No active
scene writes, tax-link promotion or current/surveyed building claims.
"""
from pathlib import Path
import os, sys, json, hashlib, argparse
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

POINTS = 'data/diagnostics/next_landmark_20261030/church_on_drive/points.npz'
ASSESSMENT = 'data/diagnostics/church_wings_20261102/wing_point_assessment.json'
EXPECTED = {POINTS: 'addff8f918e8823c35baeacbec1f581b40805be7a296b1488ebec93743bd84e4',
    ASSESSMENT: '74c59cdeea07c64bea1ef576f80d7ab4ce0afb44197b110ad6c0720463a5c4a9',
    'data/diagnostics/church_wings_20261102/review_manifest.json': '07b039d1ba73621716b9e3c472ca3cfcb7a093a579be873787eb67a68b179724'}
SNAPSHOT = '20261028T160543372334Z'
PRIM = '/World/Landmarks/ChurchSoutheastWingRoofStudy'
MATERIAL = '/World/ChurchBelfryAppearance/Materials/InterpretedMetalRoof'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(output, root=ROOT):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(root / 'data/diagnostics'):
        raise ValueError('Fresh ignored diagnostic output required')
    for path, digest in EXPECTED.items():
        if sha(root / path) != digest:
            raise ValueError('Source evidence changed: ' + path)
    source_recipe = json.loads((root / 'data/diagnostics/church_wings_20261102/review_manifest.json').read_text())['dependencies']
    for path, digest in source_recipe.items():
        actual = (root / path).resolve()
        if not actual.is_relative_to(root) or not actual.is_file() or sha(actual) != digest:
            raise ValueError('Original source/dated reference changed: ' + path)
    active = root / 'data/processed/active.json'
    if json.loads(active.read_text())['snapshot'] != SNAPSHOT:
        raise ValueError('Snapshot stale')
    protected = ['scene/college_park_connected.usda', 'scene/manual_edits.usda',
        'scene/church_historical.usda', 'scene/landmark_buildings.usda', 'data/processed/active.json']
    before = {p: sha(root / p) for p in protected}
    evidence = json.loads((root / ASSESSMENT).read_text())
    planes = next(z for z in evidence['zones'] if z['name'] == 'southeast_front_wing')['planes'][:2]
    cloud = np.load(root / POINTS)['points']
    origin = np.array(evidence['origin_utm32617'])
    supports, coefficients = [], []
    for plane in planes:
        indices = plane['original_npz_indices']
        rows = cloud[indices]
        if not np.all(rows[:, 3] == 6) or plane['connectivity']['largest_component_point_fraction'] != 1:
            raise ValueError('Require actual connected class6 support')
        xyz = rows[:, :3].copy()
        xyz[:, :2] -= origin
        a, b, c = plane['coefficients_centered_z_navd88_m']
        center = np.array(plane['center_local_xy'])
        coefficients.append(np.array([a, b, c - np.dot([a, b], center)]))
        supports.append(xyz)
    first, second = coefficients
    da, db, dc = first - second
    if abs(db) < .1 or first[1] * second[1] >= 0:
        raise ValueError('Opposed southeast slopes/ridge not established')
    ridge = lambda x: -(da * x + dc) / db
    # Explicit INTERIOR study crops, not an inferred outer roof/wall outline.
    # All boundaries derive from actual support extrema with 1.25m inset. Source
    # searches truncate support, so this deliberately does not model full ends.
    inset = 1.25
    xmin = max(q[:, 0].min() for q in supports) + inset
    xmax = min(q[:, 0].max() for q in supports) - inset
    north = supports[0][:, 1].max() - inset
    south = supports[1][:, 1].min() + inset
    if not south < min(ridge(xmin), ridge(xmax)) < max(ridge(xmin), ridge(xmax)) < north:
        raise ValueError('Ridge not interior to source-supported study')
    xy = np.array([[xmin, south], [xmax, south], [xmin, ridge(xmin)],
        [xmax, ridge(xmax)], [xmin, north], [xmax, north]])
    z = []
    for i, (x, y) in enumerate(xy):
        coeff = second if i < 2 else first
        z.append(np.dot(coeff, [x, y, 1]))
    # Same datum placement as existing sanctuary, explicitly not terrain.
    ground, offset = 30.69, .1
    points = np.c_[xy, np.array(z) - ground + offset].astype(np.float32)
    faces = [[0, 1, 3], [0, 3, 2], [2, 3, 5], [2, 5, 4]]
    face_plane = [1, 1, 0, 0]
    normals = []
    for face in faces:
        normal = np.cross(points[face[1]] - points[face[0]], points[face[2]] - points[face[0]])
        normal /= np.linalg.norm(normal)
        if normal[2] <= 0:
            raise ValueError('Roof face winding invalid')
        normals.append(normal.tolist())
    # Independently sample the interior of each analytical patch against its
    # assigned actual support points. No unsupported cap or facade is added.
    distances = []
    for index, (coeff, support) in enumerate(zip(coefficients, supports)):
        xs = np.linspace(xmin, xmax, 45)
        samples = []
        for x in xs:
            lo, hi = (ridge(x), north) if index == 0 else (south, ridge(x))
            samples.extend((x, y) for y in np.linspace(lo, hi, 25))
        samples = np.array(samples)
        nearest = []
        for batch in np.array_split(samples, 20):
            nearest.extend(np.sqrt(((batch[:, None, :] - support[None, :, :2]) ** 2).sum(2)).min(1))
        maximum = float(max(nearest))
        if maximum > 1.:
            raise ValueError('Analytical study exceeds 1m assigned-source support distance: plane ' + str(index) + ', distance ' + str(maximum))
        distances.append({'plane_id': planes[index]['plane_id'], 'samples': len(samples),
            'maximum_horizontal_distance_to_assigned_inlier_m': maximum})
    source_stage = Usd.Stage.Open(str(root / 'scene/college_park_connected.usda'))
    if not source_stage.GetPrimAtPath(MATERIAL):
        raise ValueError('Accepted church original roof material unavailable')
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    prim = UsdGeom.Xform.Define(stage, PRIM).GetPrim()
    prim.SetCustomData({'quality': 'historical_lidar_derived_open_roof_surface_study',
        'sourceSnapshot': SNAPSHOT, 'publisher': 'USGS 3DEP', 'sourceURL': 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/FL_Peninsular_FDEM_Orange_2018/',
        'acquisitionStart': '2018-12-04', 'acquisitionEnd': '2019-04-12', 'photoDate': '2021-11-08',
        'currentConditionsVerified': False, 'rawTaxLinksAccepted': False,
        'publicDerivativeReleaseAccepted': False, 'fullRoofOutlineVerified': False,
        'walllineVerified': False, 'closedShell': False, 'physicalBuildingCountKnown': False,
        'scope': 'Southeast opposed-plane interior crop only; open study edges, not eaves/walls/full wing',
        'sourceParcelContext': ['292214146004210', '292214146005190']})
    mesh = UsdGeom.Mesh.Define(stage, PRIM + '/MeasuredPlaneSurface')
    mesh.CreatePointsAttr(points.tolist())
    mesh.CreateFaceVertexCountsAttr([3] * 4)
    mesh.CreateFaceVertexIndicesAttr([i for f in faces for i in f])
    mesh.CreateNormalsAttr(normals)
    mesh.SetNormalsInterpolation('uniform')
    mesh.CreateSubdivisionSchemeAttr('none')
    mesh.CreateDoubleSidedAttr(True)
    uv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, 'vertex')
    uv.Set([(float(x), float(y)) for x, y in xy])
    for path in [MATERIAL]:
        Sdf.CreatePrimInLayer(stage.GetRootLayer(), Sdf.Path(path).GetParentPath())
        Sdf.CopySpec(source_stage.Flatten(), path, stage.GetRootLayer(), path)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(UsdShade.Material(stage.GetPrimAtPath(MATERIAL)))
    output.mkdir(parents=True)
    stage.GetRootLayer().Export(str(output / 'site.usda'))
    review = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(review, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(review, 1)
    review.GetRootLayer().subLayerPaths = [str(output / 'site.usda'), str(root / 'scene/college_park_connected.usda')]
    camera = UsdGeom.Camera.Define(review, '/World/Cameras/ChurchSoutheastWingRoofStudy')
    center = Gf.Vec3d(float((xmin + xmax) / 2), float((south + north) / 2), float(np.mean(points[:, 2])))
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(center + Gf.Vec3d(35, -27, 23), center, Gf.Vec3d(0, 0, 1)).GetInverse())
    camera.CreateFocalLengthAttr(45)
    camera.CreateHorizontalApertureAttr(36)
    camera.CreateVerticalApertureAttr(20.25)
    camera.CreateClippingRangeAttr(Gf.Vec2f(.1, 2000))
    camera.CreateFStopAttr(0)
    review.GetRootLayer().Export(str(output / 'review.usda'))
    if before != {p: sha(root / p) for p in protected}:
        raise ValueError('Protected source changed during preparation')
    area = (xmax - xmin) * (north - south)
    manifest = {'schema': 'twin.church-wing-roof-study/1', 'source_snapshot': SNAPSHOT,
        'activated': False, 'prim_path': PRIM, 'camera': '/World/Cameras/ChurchSoutheastWingRoofStudy',
        'review_stage': {'up_axis': 'Z', 'meters_per_unit': 1.}, 'roof_only': True, 'closed_shell': False,
        'boundary_policy': 'Four outer edges are interior study crops, NOT observed roof ends/eaves or walls',
        'crop_inset_from_actual_support_extrema_m': inset, 'crop_xy_bounds': [xmin, south, xmax, north],
        'projected_study_area_m2': area, 'source_planes': planes, 'plane_coefficients_local_xy_to_navd88': [x.tolist() for x in coefficients],
        'ridge_equation': {'a': float(da), 'b': float(db), 'c': float(dc), 'meaning': 'a*x+b*y+c=0; localXY, exact planeintersection'},
        'ground_reference_navd88_m': ground, 'scene_offset_m': offset, 'world_origin_utm32617': origin.tolist(),
        'support_distance_checks': distances, 'source_mesh_faces': 4, 'face_plane_indices': face_plane,
        'copied_original_material': MATERIAL, 'original_points_sha256': EXPECTED[POINTS],
        'dependencies': {**source_recipe, **EXPECTED, **before, 'tools/prepare_church_wing.py': sha(Path(__file__))},
        'outputs': {x: sha(output / x) for x in ['site.usda', 'review.usda']}, 'protected_files_unchanged': True,
        'limits': ['No wall/body or true fullroof outline', 'No courtyard/southbar bridging', 'No legacy suppression or tax-link promotion',
            'Historical acquisition and2024/25aerialcorroboration, not current surveyed geometry', 'Visual review pending; no activation']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return {k: manifest[k] for k in ['projected_study_area_m2', 'support_distance_checks', 'outputs']}


def build_full(output, root=ROOT, continuous=False, estimated_body=False):
    """Qualified full roof-cover interpretation, with separate lower returns.

    No body. Small step closures are interpreted interfaces, never surveyed
    facade faces. Frozen interior study C is not rewritten.
    """
    import shapely
    from shapely.geometry import shape, Polygon, LineString
    from shapely.ops import split, unary_union
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(root / 'data/diagnostics'):
        raise ValueError('Fresh full-roof candidate output required')
    evidence_path = 'data/diagnostics/church_wings_20261102/se_fullroof_outline_evidence_v3.json'
    if sha(root / evidence_path) != '82cfbaddc9500debe72ada77ca7d470c8da96cdc3b090084343d486ebd7172c7':
        raise ValueError('Full roof outline/end evidence changed')
    evidence = json.loads((root / evidence_path).read_text())
    for path, digest in evidence['dependencies'].items():
        if sha(root / path) != digest:
            raise ValueError('Full roof evidence dependency changed: ' + path)
    if json.loads((root / 'data/processed/active.json').read_text())['snapshot'] != SNAPSHOT:
        raise ValueError('Snapshot stale')
    protected = ['scene/college_park_connected.usda', 'scene/manual_edits.usda', 'scene/church_historical.usda',
        'scene/landmark_buildings.usda', 'data/processed/active.json']
    before = {path: sha(root / path) for path in protected}
    source = json.loads((root / ASSESSMENT).read_text())
    planes = source['zones'][0]['planes'][:2]
    coeff = []
    for p in planes:
        a,b,c = p['coefficients_centered_z_navd88_m']; x,y = p['center_local_xy']
        coeff.append(np.array([a,b,c-a*x-b*y]))
    outline = shape(evidence['roof_cover_outline_interpretation']['local_xy_polygon'])
    a,b,c = coeff[0]-coeff[1]
    ridge = LineString([(x, -(a*x+c)/b) for x in [outline.bounds[0]-10, outline.bounds[2]+10]])
    originals = []
    for part in split(outline, ridge).geoms:
        p = part.representative_point()
        index = 0 if p.y > -(a*p.x+c)/b else 1
        originals.append((part, coeff[index], planes[index]['plane_id']))
    lower = []
    for plane in evidence['lower_end_return_plane_candidates']:
        a,b,c = plane['coefficients_centered_z_navd88_m'];x,y = plane['center_local_xy']
        co = np.array([a,b,c-a*x-b*y])
        for component in plane['connected_support_components']:
            # Bounded connected-support interpretation, not an arbitrary whole
            # end strip. A .10m allowance avoids tracing sample noise. Boundary
            # remains estimated within the declared 1m interpretation allowance.
            part = Polygon(component['hull_coordinates']).simplify(.15, preserve_topology=True).buffer(.10, join_style=2).intersection(outline)
            if part.area < .1:
                continue
            lower.append((part, co, component['id'], component['source_indices']))
    unresolved_lower = lower
    if continuous:
        lower=[]
    cut = unary_union([r[0] for r in lower])
    support_membership={p['plane_id']:p['original_npz_indices'] for p in planes}
    regions = [(p.difference(cut), co, name, support_membership[name]) for p,co,name in originals] + lower
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, 'Z');UsdGeom.SetStageMetersPerUnit(stage,1.)
    path = '/World/Landmarks/ChurchSoutheastWingContinuousRoof' if continuous else '/World/Landmarks/ChurchSoutheastWingFullRoof'
    parent = UsdGeom.Xform.Define(stage,path).GetPrim()
    parent.SetCustomData({'quality':'historical_measured_planes_with_interpreted_roofcover_and_return_boundaries',
        'sourceSnapshot':SNAPSHOT,'publisher':'USGS 3DEP / OCPA dated aerial context',
        'currentConditionsVerified':False,'rawTaxLinksAccepted':False,'publicDerivativeReleaseAccepted':False,
        'walllineVerified':False,'closedShell':False,'purpose':'Bounded southeast roof with separately qualified envelope closure' if estimated_body else 'Full bounded southeast roof-cover candidate only; no building body',
        'boundaryAllowanceM':1.,'photoDate':'2021-11-08','acquisitionStart':'2018-12-04','acquisitionEnd':'2019-04-12'})
    if continuous:
        parent.SetCustomDataByKey('sourceBuildingGroupContext','Building_2892; existingunderheight sourcegroup, notnewphysicalentity')
        parent.SetCustomDataByKey('lowerReturnPolicy','Unresolvedmultilevelreturns are observations only; no upperroofcuts withoutdatedimageopeningproof')
        parent.SetCustomDataByKey('edgeInterpretationLimit','2024vs2025 apparentedge shift around1m; sourcelean/alignment/epoch unresolved; notmeasuredwestedgecorrection')
    active = Usd.Stage.Open(str(root/'scene/college_park_connected.usda'))
    Sdf.CreatePrimInLayer(stage.GetRootLayer(),Sdf.Path(MATERIAL).GetParentPath())
    Sdf.CopySpec(active.Flatten(),MATERIAL,stage.GetRootLayer(),MATERIAL)
    material = UsdShade.Material(stage.GetPrimAtPath(MATERIAL))
    receipts = []
    def author(name, vertices, counts, ids, quality):
        mesh=UsdGeom.Mesh.Define(stage,path+'/'+name)
        mesh.CreatePointsAttr(vertices);mesh.CreateFaceVertexCountsAttr(counts);mesh.CreateFaceVertexIndicesAttr(ids)
        mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True)
        uv=UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,'vertex')
        if 'transition' in quality:
            values=[]
            for start in range(0,len(vertices),4):
                q=np.array(vertices[start:start+4]);length=float(np.linalg.norm(q[1,:2]-q[0,:2]))
                values.extend([(0.,float(q[0,2])),(length,float(q[1,2])),(length,float(q[2,2])),(0.,float(q[3,2]))])
            uv.Set(values)
        else:
            uv.Set([(float(v[0]),float(v[1])) for v in vertices])
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
        mesh.GetPrim().SetCustomData({'quality':quality,'currentConditionsVerified':False})
        return mesh
    for i,(poly,co,name,indices) in enumerate(regions):
        vertices=[];ids=[]
        for triangle in shapely.constrained_delaunay_triangles(poly).geoms:
            xy=np.array(triangle.exterior.coords)[:3]
            if triangle.area<.001:continue
            u,v=xy[1]-xy[0],xy[2]-xy[0]
            if u[0]*v[1]-u[1]*v[0]<0:xy=xy[::-1]
            xyz=np.c_[xy,np.c_[xy,np.ones(3)]@co-30.69+.1].astype(np.float32)
            ids.extend(range(len(vertices),len(vertices)+3));vertices.extend(xyz.tolist())
        mesh=author('RoofPatch_'+str(i+1),vertices,[3]*(len(ids)//3),ids,'historical_source_plane_with_estimated_edge_continuation' if continuous else 'historical_source_plane_with_interpreted_boundary')
        mesh.GetPrim().SetCustomDataByKey('sourcePlaneId',name)
        receipts.append({'prim_path':str(mesh.GetPath()),'source_plane_id':name,'area_m2':poly.area,
            'coefficients_localxy_to_navd88':co.tolist(),'original_npz_indices':indices,
            'boundary_status':'estimated_from_connected_returns_and_dated_aerial; not measuredwallline'})
    # Each actual lower patch has local interpreted vertical transition faces.
    # The order can reverse at plane intersections: split before authoring.
    from reconstruct_landmarks import positive_step_intervals
    seam_faces=0
    for i,(low,lowco,name,indices) in enumerate(lower):
        vertices=[];ids=[]
        for upper,highco,_ in originals:
            shared=low.boundary.intersection(upper)
            lines=list(shared.geoms) if hasattr(shared,'geoms') else [shared]
            for line in lines:
                if line.geom_type!='LineString':continue
                coords=list(line.coords)
                for aa,bb in zip(coords,coords[1:]):
                    aa,bb=np.array(aa),np.array(bb)
                    diff=lambda xy:float(np.r_[xy,1]@(highco-lowco))
                    for v,w in positive_step_intervals(aa,bb,diff):
                        top=np.array([np.r_[v,1]@highco,np.r_[w,1]@highco])-30.69+.1
                        bottom=np.array([np.r_[v,1]@lowco,np.r_[w,1]@lowco])-30.69+.1
                        face=np.array([[*v,bottom[0]],[*w,bottom[1]],[*w,top[1]],[*v,top[0]]],dtype=np.float32)
                        if np.linalg.norm(np.cross(face[1]-face[0],face[2]-face[0]))<1e-6:continue
                        ids.extend(range(len(vertices),len(vertices)+4));vertices.extend(face.tolist())
        if ids:
            author('InterpretedEndTransition_'+str(i+1),vertices,[4]*(len(ids)//4),ids,'illustrative_interpreted_roof_level_transition_not_measured_wall')
            seam_faces+=len(ids)//4
    if estimated_body:
        if not continuous:
            raise ValueError('Envelope closure only supported in continuous interpretation mode')
        # Explicit roof-envelope wall assumption. No inferred setback/overhang,
        # windows, doors, floor count or physical tax identity is authored.
        brick_path='/World/ChurchFrontageAppearance/Materials/Brick'
        Sdf.CreatePrimInLayer(stage.GetRootLayer(),Sdf.Path(brick_path).GetParentPath())
        Sdf.CopySpec(active.Flatten(),brick_path,stage.GetRootLayer(),brick_path)
        vertices=[];ids=[];counts=[]
        coords=list(outline.exterior.coords)
        for aa,bb in zip(coords,coords[1:]):
            aa,bb=np.array(aa),np.array(bb)
            va=float(np.r_[aa,1]@(coeff[0]-coeff[1]));vb=float(np.r_[bb,1]@(coeff[0]-coeff[1]))
            cuts=[0.,1.]
            if va*vb<0:cuts.append(va/(va-vb))
            cuts=sorted(cuts)
            for lo,hi in zip(cuts,cuts[1:]):
                q=aa+(bb-aa)*lo;r=aa+(bb-aa)*hi
                midpoint=(q+r)/2;co=coeff[0] if float(np.r_[midpoint,1]@(coeff[0]-coeff[1]))<0 else coeff[1]
                zq=float(np.r_[q,1]@co-30.69+.1);zr=float(np.r_[r,1]@co-30.69+.1)
                ids.extend(range(len(vertices),len(vertices)+4));counts.append(4)
                vertices.extend([[*r,.1],[*q,.1],[*q,zq],[*r,zr]])
        walls=author('EstimatedRoofEnvelopeClosure',vertices,counts,ids,'illustrative_estimated_roofenvelope_wallline_transition')
        UsdShade.MaterialBindingAPI.Apply(walls.GetPrim()).Bind(UsdShade.Material(stage.GetPrimAtPath(brick_path)))
        walls.GetPrim().SetCustomDataByKey('assumption','Wall plane at interpretedroofcover edge; zerooverhangassumption, truewallline/overhangunknown; no windows/floorsinvented')
    output.mkdir(parents=True);stage.GetRootLayer().Export(str(output/'site.usda'))
    mask_proofs=[]
    if continuous:
        from prepare_church_legacy_mask import author as mask_author, projected_mesh
        mask_stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(mask_stage,'Z');UsdGeom.SetStageMetersPerUnit(mask_stage,1.)
        targets=[active.GetPrimAtPath('/World/'+group+'/'+prefix+str(number)) for number in [2892,2919]
                 for group,prefix in [('Buildings','Building_'),('Roofs','Roof_')]]
        storefront=active.GetPrimAtPath('/World/Storefronts/Building_2892')
        if storefront:targets.extend(p for p in Usd.PrimRange(storefront) if p.GetTypeName()=='Mesh')
        xf=UsdGeom.XformCache()
        for source_prim in targets:
            if not source_prim:raise ValueError('Expected source alias absent')
            if xf.GetLocalToWorldTransform(source_prim)!=Gf.Matrix4d(1):
                raise ValueError('Nonidentity source transform requires explicit world/local mask conversion')
            geometry=projected_mesh(source_prim)
            overlap=geometry.intersection(outline).area
            if overlap<.00001:continue
            proof=mask_author(mask_stage,source_prim,outline)
            proof.update(prim_path=str(source_prim.GetPath()),source_projection_area_m2=geometry.area,
                mask_intersection_m2=overlap,retained_projection_m2=geometry.difference(outline).area,
                status='INACTIVE_exact_source_surface_remainder_proposal_only; sourceidentitynotpromoted')
            mask_proofs.append(proof)
        mask_stage.GetRootLayer().customLayerData={'proposalOnly':True,'sourceSnapshot':SNAPSHOT,
            'purpose':'Boundedsource-surface remainder on2892/2919 +generic2892storefronts only; no wholecampushide'}
        mask_stage.GetRootLayer().Export(str(output/'legacy_mask_proposal.usda'))
    review=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(review,'Z');UsdGeom.SetStageMetersPerUnit(review,1.)
    review.GetRootLayer().subLayerPaths=[str(output/'site.usda')]+([str(output/'legacy_mask_proposal.usda')] if continuous else [])+[str(root/'scene/college_park_connected.usda')]
    camera=UsdGeom.Camera.Define(review,'/World/Cameras/ChurchSoutheastWingContinuousRoof' if continuous else '/World/Cameras/ChurchSoutheastWingFullRoof')
    target=Gf.Vec3d(outline.centroid.x,outline.centroid.y,8.8)
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(target+Gf.Vec3d(38,-29,25),target,Gf.Vec3d(0,0,1)).GetInverse())
    camera.CreateFocalLengthAttr(45);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25);camera.CreateFStopAttr(0);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,2000))
    review.GetRootLayer().Export(str(output/'review.usda'))
    if before!={p:sha(root/p) for p in protected}:raise ValueError('Protected source changed')
    manifest={'schema':'twin.church-se-continuous-envelope-candidate/1' if continuous else 'twin.church-se-fullroof-candidate/1','source_snapshot':SNAPSHOT,'activated':False,
        'prim_path':path,'camera':str(camera.GetPath()),'roof_only':not estimated_body,'closed_shell':False,
        'continuous_upperroof_interpretation':continuous,'estimated_envelope_body':estimated_body,
        'unmodeled_lowerreturn_components': [r[2] for r in unresolved_lower] if continuous else [],
        'lowerreturn_semantics':'Notexclusiveupperroof: no datedimageproof ofopenings; no automatic roofcuts' if continuous else 'REJECTED interpretation: sourcefitdoesnotestablishupperroofexclusivity',
        'interpreted_roofcover_area_m2':outline.area,'lower_return_interpreted_area_m2':cut.area,
        'regions':receipts,'interpreted_step_faces':seam_faces,'protected_files_unchanged':True,
        'dependencies':{**evidence['dependencies'],evidence_path:sha(root/evidence_path),**before,'tools/prepare_church_wing.py':sha(Path(__file__))},
        'outputs':{p:sha(output/p) for p in ['site.usda','review.usda']+(['legacy_mask_proposal.usda'] if continuous else [])},
        'legacy_mask_proofs':mask_proofs,'existing_source_group_context':'Building_2892 NUM4; sourcePID4210/assigned5190spatialreviewonly; notnewphysicalentity',
        'limits':['Continuousmeasuredplane interpretation withestimatededgecontinuation; lowerreturnsunmodeled' if continuous else 'REJECTEDexclusive lowerpatchinterpretation',
            'Roof-envelopebody isexplicitlyestimatedwallclosure' if estimated_body else 'No body', 'No extra floor or truewallline claim',
            'No courtyard orwalkwaybridge; nolegacy/taxchanges','Tinyraisedfeaturesunmodeledpendingclassification','Actualvisualreviewpending']}
    if continuous:
        for relative in ['data/diagnostics/church_wings_20261102/all_source_census_v1.json',
                         'data/diagnostics/church_wings_20261102/allscene_overlap_v1.json',
                         'data/diagnostics/church_wings_20261102/lower_return_semantics_v1.json',
                         'tools/prepare_church_legacy_mask.py']:
            manifest['dependencies'][relative]=sha(root/relative)
        manifest['context_ground_reference']='Courtyardclass2supportmedian30.67; nominalscene30.69, notfoundation survey'
        manifest['enclosure_wall_policy']='Zerooverhang nominalroofedgeclosure; actualwallline/overhangunknown; no facadeopenings/storiesinvented'
    (output/'captured_helper.py').write_bytes(Path(__file__).read_bytes())
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return {'outputs':manifest['outputs'],'area_m2':outline.area,'lower_returns_m2':cut.area,'interpreted_step_faces':seam_faces}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--full',action='store_true',help='Qualified full southeast roof-cover candidate; no body')
    parser.add_argument('--continuous',action='store_true',help='Continuous image-supported upper roof; lower returns remain observations')
    parser.add_argument('--estimated-body',action='store_true',help='Separate explicitly estimated roof-envelope wall closure, no facade details')
    args = parser.parse_args()
    result=build_full(ROOT/args.output,continuous=args.continuous,estimated_body=args.estimated_body) if (args.full or args.continuous) else build(ROOT/args.output)
    print(json.dumps(result,indent=2))
