from pathlib import Path
import sys
import tempfile
import unittest
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np
from shapely.geometry import box, Point, Polygon
from pxr import Usd, UsdGeom
from correct_wellesley import corrected_height_rows, digest, mesh_geometry, mesh_payload, planar_roof, resolve_target, validate_guard, write_mesh, supported_multilevel_roof, read, polygon_parts


def parameters():
    return {'cell_size_m': 1., 'minimum_cell_points': 5, 'maximum_cell_p85_p15_m': .3, 'maximum_cell_plane_deviation_m': .4,
            'minimum_height_above_ground_m': 15, 'maximum_height_above_ground_m': 30, 'histogram_bin_m': .1,
            'opening_iterations': 1, 'closing_iterations': 1, 'minimum_component_area_m2': 100,
            'maximum_enclosed_gap_fill_m2': 25, 'simplification_tolerance_m': .1,
            'minimum_total_upper_area_m2': 500, 'minimum_concavity_void_area_m2': 200}


def synthetic_points(rectangle=False):
    values = []
    for y in range(40):
        for x in range(40):
            if rectangle or x < 12 or y < 12 or y >= 28:
                for dx, dy in [(.1, .1), (.3, .3), (.5, .5), (.7, .7), (.9, .9), (.2, .8)]:
                    values.append([x + dx, y + dy, 53.35, 1])
    values.extend([[i % 10, i // 10, 30., 2] for i in range(100)])
    return np.asarray(values, dtype=float)


class WellesleyTests(unittest.TestCase):
    def test_dense_planar_roof_preserves_open_courtyard(self):
        roof, evidence, before, after = planar_roof(synthetic_points(), parameters())
        self.assertFalse(roof.covers(Point(25, 20)))
        self.assertTrue(roof.covers(Point(5, 20)))
        self.assertTrue(roof.covers(Point(25, 5)))
        self.assertAlmostEqual(evidence['height_m'], 23.35)
        self.assertGreater(evidence['accepted_planar_support_points'], 1000)

    def test_rectangle_that_fills_courtyard_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Courtyard'):
            planar_roof(synthetic_points(rectangle=True), parameters())

    def test_class6_only_points_do_not_become_class1_roof(self):
        points = synthetic_points()
        points[points[:, 3] == 1, 3] = 6
        with self.assertRaisesRegex(ValueError, 'unclassified high-surface'):
            planar_roof(points, parameters())

    def test_nonplanar_isolated_tree_cells_not_added_to_roof(self):
        points = synthetic_points()
        noisy = np.asarray([[46 + i / 10, 20 + i / 10, z, 1] for i, z in enumerate([51, 52, 53, 54, 55, 56])])
        roof, _, _, _ = planar_roof(np.vstack([points, noisy]), parameters())
        self.assertFalse(roof.covers(Point(46.5, 20.5)))

    def test_only_target_height_row_changes(self):
        rows = [{'building_id': 'Building_9999', 'height_m': 4.3, 'parcel_id': None}, {'building_id': 'Building_0001', 'height_m': 7.2, 'parcel_id': '00001'}]
        result = corrected_height_rows(rows, 'Building_9999', {'height_m': 23.35, 'floors_used': 7})
        self.assertEqual(result[1], rows[1])
        self.assertIsNone(result[0]['parcel_id'])
        self.assertEqual(rows[0]['height_m'], 4.3)

    def test_duplicate_height_targets_fail(self):
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            corrected_height_rows([{'building_id': 'X'}, {'building_id': 'X'}], 'X', {'height_m': 23})

    def test_mesh_triangulation_does_not_fill_polygon_holes(self):
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], holes=[[(3, 3), (3, 7), (7, 7), (7, 3)]])
        points, counts, indices = mesh_geometry([(polygon, .1, 23.45)], roofs_only=True)
        self.assertEqual(sum(counts), len(indices))
        area, offset = 0., 0
        for count in counts:
            triangle = Polygon([points[i][:2] for i in indices[offset:offset + count]])
            self.assertFalse(triangle.covers(Point(5, 5)))
            area += triangle.area
            offset += count
        self.assertAlmostEqual(area, polygon.area)

    def test_authored_uv_normals_and_indices_match_new_mesh(self):
        stage = Usd.Stage.CreateInMemory()
        mesh = write_mesh(stage, '/World/Buildings/New', [(box(0, 0, 10, 10), .1, 23.45)])
        points = mesh.GetPointsAttr().Get()
        indices = mesh.GetFaceVertexIndicesAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        self.assertEqual(sum(counts), len(indices))
        self.assertEqual(len(mesh.GetNormalsAttr().Get()), len(counts))
        self.assertEqual(len(UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st').Get()), len(indices))
        self.assertLess(max(indices), len(points))
        roof = write_mesh(stage, '/World/Roofs/New', [(box(0, 0, 10, 10), .1, 23.45)], roofs_only=True)
        self.assertTrue(all(n[2] > .99 for n in roof.GetNormalsAttr().Get()))

    def test_resolve_source_identity_survives_generated_id_change(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, '/World/Buildings/Building_9999')
        mesh = write_mesh(stage, '/World/Buildings/Building_9999', [(box(0, 0, 10, 10), .1, 6.6)])
        mesh.GetPrim().SetCustomData({'parcelId': 'oldPID', 'buildingNumber': '1', 'sourceObjectIds': '3,1,2'})
        config = {'source_parcel_id': 'oldPID', 'source_building_number': '1', 'source_object_ids': ['1', '2', '3'], 'original_building_id': 'Building_2933'}
        records = [{'id': 'Building_9999', 'usd_path': '/World/Buildings/Building_9999', 'source_parcel_id': 'oldPID', 'match_method': 'ambiguous_or_unmatched'}]
        record, prim = resolve_target(config, stage, records)
        self.assertEqual(record['id'], 'Building_9999')
        with tempfile.TemporaryDirectory() as tmp:
            cloud = Path(tmp) / 'points'; cloud.write_bytes(b'fixed cloud')
            config.update({'source_base_mesh_sha256': digest(mesh_payload(mesh)), 'source_cloud_sha256': hashlib.sha256(cloud.read_bytes()).hexdigest(), 'expected_match_method': 'ambiguous_or_unmatched'})
            validate_guard(config, {'snapshot': 'refreshed'}, record, prim, cloud)
            mesh.CreatePointsAttr([(0, 0, 0)])
            with self.assertRaisesRegex(ValueError, 'source mesh changed'):
                validate_guard(config, {'snapshot': 'refreshed'}, record, prim, cloud)

    def test_equipment_returns_do_not_cut_full_depth_roof_holes(self):
        points = synthetic_points()
        equipment = np.asarray([[4+x/8, 15+y/8, 57.0, 1] for x in range(40) for y in range(40)])
        config = parameters(); config.update({'minimum_deck_cell_points':3,'maximum_supported_equipment_gap_m2':150,
            'minimum_raised_patch_m2':2.25,'surface_simplification_m':.5,'protected_upper_voids_utm':[]})
        roof,evidence,_,_,patches = supported_multilevel_roof(np.vstack([points,equipment]),config)
        self.assertTrue(roof.covers(Point(6,17)))
        self.assertFalse(roof.covers(Point(25,20)))
        self.assertTrue(any(p['roof_z_m']>56 for p in patches))
        # Raised components begin at the main deck, never at ground.
        self.assertGreater(evidence['accepted_planar_support_points'],1000)

    def test_empty_unobserved_roof_hole_remains_unknown(self):
        points=synthetic_points()
        points=points[~((points[:,0]>2)&(points[:,0]<10)&(points[:,1]>14)&(points[:,1]<24))]
        config=parameters();config.update({'minimum_deck_cell_points':3,'maximum_supported_equipment_gap_m2':150,
            'minimum_raised_patch_m2':2.25,'surface_simplification_m':.5,'protected_upper_voids_utm':[]})
        roof,evidence,_,_,_=supported_multilevel_roof(points,config)
        self.assertFalse(roof.covers(Point(6,19)))
        self.assertTrue(any(g['action']=='preserve_unresolved_void' for g in evidence['gap_diagnostics']))

    def test_actual_equipment_gaps_filled_and_observed_courtyard_preserved(self):
        path=ROOT/'data/heights/wellesley_correction/local_points.npz'
        if not path.exists(): self.skipTest('Ignored historical point evidence unavailable')
        config=read(ROOT/'config/building_corrections.json')['roof_extraction']
        roof,evidence,_,_,patches=supported_multilevel_roof(np.load(path)['points'],config)
        self.assertEqual(len(evidence['prior_enclosed_holes']),3)
        for hole in evidence['prior_enclosed_holes']:
            self.assertAlmostEqual(hole['new_supported_deck_overlap_m2'],hole['area_m2'],places=5)
            self.assertGreater(hole['z_p10_p50_p90_m'][0],54.5)
        for guard in config['protected_upper_voids_utm']:
            self.assertAlmostEqual(roof.intersection(box(*guard['bounds'])).area,0)
        self.assertLess(evidence['simplified_boundary_vertices'],evidence['raw_boundary_vertices']/2)
        self.assertTrue(patches)
        components=[(roof,.1,23.45)]+[(p['geometry'],23.45,.1+p['height_m']) for p in patches]
        vertices,counts,indices=mesh_geometry(components,roofs_only=True)
        offset=0;void=box(*config['protected_upper_voids_utm'][0]['bounds'])
        for count in counts:
            face=Polygon([vertices[i][:2] for i in indices[offset:offset+count]]);offset+=count
            self.assertLess(face.intersection(void).area,1e-7)


if __name__ == '__main__':
    unittest.main()
