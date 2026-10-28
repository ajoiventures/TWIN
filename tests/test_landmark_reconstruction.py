from pathlib import Path
import hashlib,json,sys,unittest,tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
from shapely.geometry import box,shape,Polygon,Point
from shapely.ops import unary_union
from pxr import Usd,UsdGeom
from reconstruct_landmarks import supported_components,verify_source,SITES,read,fit_roof_planes,simplify_supported_outline,planar_region_geometry,roof_normal_metrics,positive_step_intervals,quantized_valid_geometry

def synthetic():
    points=[]
    for y in range(20):
        for x in range(20):
            if 7<=x<12 and 7<=y<12:continue
            for d in [.1,.3,.5,.7,.9]:points.append([x+d,y+d,35+x*.05,6])
    # Adjacent ground, outside roof but within3m, and broader parcel ground.
    points += [[edge+i*.005,y*.1,29.5,2] for edge in [-1,21] for i in range(100) for y in range(100)]
    return np.asarray(points)

class LandmarkTests(unittest.TestCase):
    def test_no_building_can_be_seeded_by_unclassified_trees(self):
        p=synthetic();p[p[:,3]==6,3]=1
        with self.assertRaisesRegex(ValueError,'classified building'):supported_components(p,[(0,100)],box(-5,-5,30,30))
    def test_no_nonfinite_points_accepted(self):
        p=synthetic();p[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'Nonfinite'):supported_components(p,[(0,100)],box(-5,-5,30,30))
    def test_holes_slope_and_parcel_search_mask_are_preserved(self):
        components,report=supported_components(synthetic(),[(0,100)],box(-5,-5,30,30))
        roof=unary_union([c['geometry'] for c in components])
        self.assertFalse(roof.covers(Point(9,9)));self.assertTrue(roof.covers(Point(4,4)))
        self.assertLess(roof.area,400);self.assertAlmostEqual(report['ground_median_navd88_m'],29.5)
        self.assertGreater(components[0]['roof_z_p05_p50_p95_m'][2]-components[0]['roof_z_p05_p50_p95_m'][0],.5)
    def test_different_roof_levels_remain_separate(self):
        p=synthetic();p[(p[:,3]==6)&(p[:,0]<5),2]=32.7
        components,_=supported_components(p,[(0,33.2),(33.2,100)],box(-5,-5,30,30))
        self.assertEqual(len(components),2)
        self.assertLess(min(c['roof_z_p05_p50_p95_m'][1] for c in components),33)
        self.assertAlmostEqual(components[0]['geometry'].intersection(components[1]['geometry']).area,0)
    def test_cloud_identity_guard_fails_before_reconstruction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'data/heights/landmarks'/SITES[0]['id'];folder.mkdir(parents=True)
            (folder/'evidence.json').write_text(json.dumps({'parcel_id':SITES[0]['pin'],'source_snapshot':'fixture','cloud_sha256':'expected'}))
            with patch('reconstruct_landmarks.sha',return_value='changed'):
                with self.assertRaisesRegex(ValueError,'cloud changed'):verify_source(root,SITES[0],{'snapshot':'fixture'})
    def test_consensus_fit_removes_isolated_spikes_and_preserves_steps_slopes(self):
        yy,xx=np.indices((30,30));rng=np.random.default_rng(1)
        grid=np.where(xx<15,35+.08*yy,40+.03*yy)+rng.normal(0,.03,(30,30))
        grid[8,8]=47;grid[22,23]=50
        fitted,report=fit_roof_planes(grid,np.ones(grid.shape,bool))
        self.assertLess(fitted.max(),41.5)
        self.assertLess(abs(fitted[8,8]-(35+.08*8)),.15)
        self.assertGreater(np.median(fitted[:,20])-np.median(fitted[:,5]),3)
        self.assertGreater(fitted[25,5]-fitted[5,5],1.4)
        self.assertGreaterEqual(report['outlier_or_unresolved_cells'],2)
        self.assertLess(report['accepted_residual_p50_p95_max_m'][1],.15)
    def test_outline_simplification_preserves_actual_hole_and_edge_bound(self):
        polygon=Polygon([(0,0),(5,.3),(10,0),(10,10),(0,10)],holes=[[(3,3),(3,7),(7,7),(7,3)]])
        result=simplify_supported_outline(polygon,box(-1,-1,11,11))
        self.assertAlmostEqual(result.intersection(box(3,3,7,7)).area,0)
        self.assertTrue(polygon.buffer(1.000001).covers(result))
    def test_whole_regions_have_exact_planes_and_preserve_steps_and_holes(self):
        left=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(3,3),(3,6),(6,6),(6,3)]])
        regions=[{'geometry':left,'coefficients_cell_xy':[.2,0,35]},
                 {'geometry':box(10,0,20,10),'coefficients_cell_xy':[0,0,40]}]
        mesh,evidence=planar_region_geometry(regions,{'left_utm_m':0,'bottom_utm_m':0,'cell_m':1},[0,0],29.5)
        self.assertAlmostEqual(evidence['roof_triangle_plane_residual_max_m'],0)
        self.assertEqual(roof_normal_metrics(mesh)['distinct_roof_normals_rounded_3dec'],2)
        vertices,counts,indices=mesh;offset=0;roof_area=0
        for count in counts:
            q=[vertices[i] for i in indices[offset:offset+count]];offset+=count
            if count==3 and min(p[2] for p in q)>.2:
                triangle=Polygon([p[:2] for p in q]);roof_area+=triangle.area
                self.assertAlmostEqual(triangle.intersection(box(3,3,6,6)).area,0)
        self.assertAlmostEqual(roof_area,left.area+100)
    def test_crossing_step_edge_is_split_at_plane_intersection(self):
        difference=lambda p:1.721-2.473*p[0]
        segments=positive_step_intervals((0,0),(1,0),difference)
        self.assertEqual(len(segments),1)
        self.assertAlmostEqual(segments[0][1][0],1.721/2.473)
        for a,b in segments:self.assertGreaterEqual(difference(a)*difference(b),-1e-10)
        opposite=positive_step_intervals((0,0),(1,0),lambda p:-difference(p))
        self.assertEqual(len(opposite),1)
        self.assertAlmostEqual(opposite[0][0][0],segments[0][1][0])
    def test_float32_slivers_and_collapsed_wall_vertices_are_removed(self):
        vertices=[(20,-655,10),(21,-655,10),(20.5,-654.999999,10),
                  (0,0,0),(1,0,0),(1,0,2),(0,0,0),
                  (0,0,5),(2,0,5),(0,2,5)]
        mesh,report=quantized_valid_geometry((vertices,[3,4,3],list(range(10))))
        self.assertEqual(report['output_faces'],2)
        self.assertEqual(mesh[1],[3,3])
        self.assertTrue(report['discarded_faces_by_reason'])
        stage=Usd.Stage.CreateInMemory()
        from princeton_evidence import write_surface
        authored=write_surface(stage,'/World/Test',mesh)
        points=np.asarray(authored.GetPointsAttr().Get());offset=0
        for count,normal in zip(authored.GetFaceVertexCountsAttr().Get(),authored.GetNormalsAttr().Get()):
            ids=authored.GetFaceVertexIndicesAttr().Get()[offset:offset+count];offset+=count
            q=points[ids];n=np.cross(q[1]-q[0],q[2]-q[0]);n=n/np.linalg.norm(n)
            self.assertGreater(np.dot(n,normal),.99999)
    def test_actual_proposal_topology_bounds_and_provisional_contract(self):
        manifest_path=ROOT/'data/heights/landmarks/proposal_manifest.json'
        if not manifest_path.exists():self.skipTest('Ignored proposal evidence unavailable')
        manifest=read(manifest_path);stage=Usd.Stage.Open(manifest['layer'])
        self.assertEqual(hashlib.sha256(Path(manifest['layer']).read_bytes()).hexdigest(),manifest['layer_sha256'])
        self.assertEqual(manifest['global_height_rows_modified'],0)
        for site in manifest['sites']:
            self.assertFalse(site['accepted_current_geometry']);self.assertFalse(site['legacy_geometry_hidden'])
            self.assertTrue(site['prim_path'].startswith('/World/Landmarks/'))
            self.assertLess(site['diagnostics']['roof_union_area_m2'],site['diagnostics']['parcel_search_area_m2']*.5)
            for component in site['components']:
                self.assertIn('6',component['roof_source_classes'])
                self.assertTrue(set(component['roof_source_classes']).issubset({'1','6'}))
                self.assertEqual(component.get('footprint_seed_source_classes'),['6'])
                self.assertGreater(component['source_building_points'],0)
                mesh=UsdGeom.Mesh(stage.GetPrimAtPath(component['prim_path']));vertices=mesh.GetPointsAttr().Get();counts=mesh.GetFaceVertexCountsAttr().Get();indices=mesh.GetFaceVertexIndicesAttr().Get()
                self.assertEqual(sum(counts),len(indices));self.assertLess(max(indices),len(vertices))
                self.assertTrue(np.isfinite(np.asarray(vertices)).all())
                self.assertAlmostEqual(max(v[2] for v in vertices)-.1,component['maximum_rendered_height_m'],places=4)
                self.assertEqual(len(mesh.GetNormalsAttr().Get()),len(counts))
                if site['site_id']=='andersen_office_1615':
                    fit=component['roof_interpretation']
                    self.assertAlmostEqual(fit['roof_triangle_plane_residual_max_m'],0)
                    self.assertLessEqual(fit['roughness_comparison']['continuous_region_roof']['distinct_roof_normals_rounded_3dec'],12)
                    self.assertLess(fit['roughness_comparison']['continuous_region_roof']['roof_face_count'],200)
                    self.assertEqual(fit['float_serialization_validation']['self_crossing_step_quads'],0)
                    offset=0;authored_normals=mesh.GetNormalsAttr().Get()
                    for count,authored in zip(counts,authored_normals):
                        q=np.asarray([vertices[i] for i in indices[offset:offset+count]],dtype=float);offset+=count
                        cross=np.cross(q[1]-q[0],q[2]-q[0]);length=np.linalg.norm(cross)
                        self.assertGreater(length,1e-8)
                        self.assertGreater(np.dot(cross/length,authored),.99999)
                        if count==4:
                            self.assertGreaterEqual((q[3,2]-q[0,2])*(q[2,2]-q[1,2]),-1e-10)


if __name__=='__main__':unittest.main()
