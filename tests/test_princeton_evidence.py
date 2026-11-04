from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np
from shapely.geometry import box, Polygon, Point
from pxr import Usd, UsdGeom
from princeton_evidence import EptReader, legacy_overlap, node_intersects, roof_zones, surface_geometry, write_surface, validate_voids, disjoint_zones, read, Transformer, shapely


def configuration():
    return {'grid_cell_m': 1, 'minimum_cell_points': 5, 'maximum_cell_spread_m': .55,
            'minimum_component_m2': 35, 'gap_infill_m2': 25, 'simplify_m': .45,
            'zone_bands': [{'id': 'a', 'min_z_m': 50.7, 'max_z_m': 53, 'local_review_interpretation': 'high deck'},
                           {'id': 'b', 'min_z_m': 48.7, 'max_z_m': 50.7, 'local_review_interpretation': 'middle roof'},
                           {'id': 'c', 'min_z_m': 42.3, 'max_z_m': 43.7, 'local_review_interpretation': 'low roof'},
                           {'id': 'd', 'min_z_m': 43.7, 'max_z_m': 47.1, 'local_review_interpretation': 'hipped roof'}]}


class PrincetonTests(unittest.TestCase):
    def test_hierarchy_search_uses_actual_xy_node_bounds(self):
        bounds = [0, 0, 0, 100, 100, 100]
        self.assertTrue(node_intersects('1-1-0-0', bounds, [60, 10, 70, 20]))
        self.assertFalse(node_intersects('1-0-1-0', bounds, [60, 10, 70, 20]))

    def test_offline_hierarchy_miss_never_connects(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, 'Offline'):
                EptReader(Path(tmp), live=False).json('https://official.example/ept.json')

    def test_project_maximum_story_count_does_not_flatten_components(self):
        values = []
        for i, z in enumerate([52.05, 49.55, 43.09, 44.69]):
            for y in range(20):
                for x in range(20):
                    for d in [.1, .25, .4, .55, .7, .85]:
                        values.append([x + i * 25 + d, y + d, z, 1])
        values.extend([[i % 10, i // 10, 31.59, 2] for i in range(100)])
        zones, _, _, _ = roof_zones(np.asarray(values), configuration())
        self.assertEqual([z['height_m'] for z in zones], [20.46, 17.96, 11.5, 13.1])
        self.assertTrue(all(z['storeys'] is None for z in zones))

    def test_insufficient_roof_bands_are_not_promoted(self):
        values = np.asarray([[x / 10, y / 10, 43.1, 1] for x in range(100) for y in range(100)] + [[i, 0, 31.59, 2] for i in range(100)])
        with self.assertRaisesRegex(ValueError, 'Insufficient stepped'):
            roof_zones(values, configuration())

    def test_fully_contained_old_spatial_group_can_be_superseded(self):
        result = legacy_overlap(box(1, 1, 2, 2), box(0, 0, 10, 10), 'spatial_review', 'old', 'new', .98)
        self.assertTrue(result['supersession_supported'])
        self.assertEqual(result['action'], 'hide_full')

    def test_small_outside_remainder_is_preserved(self):
        result = legacy_overlap(box(-.1, 0, 10, 10), box(0, 0, 10, 10), 'spatial_review', 'old', 'new', .98)
        self.assertTrue(result['supersession_supported'])
        self.assertEqual(result['action'], 'retain_only_outside_property_remainder')

    def test_weak_overlap_does_not_hide_neighboring_building(self):
        result = legacy_overlap(box(-5, 0, 10, 10), box(0, 0, 10, 10), 'spatial_review', 'old', 'new', .98)
        self.assertFalse(result['supersession_supported'])
        self.assertEqual(result['action'], 'leave_unmodified')

    def test_accepted_or_same_parcel_identity_is_not_silently_superseded(self):
        self.assertFalse(legacy_overlap(box(1, 1, 2, 2), box(0, 0, 10, 10), 'id_and_geometry', 'old', 'new', .98)['supersession_supported'])
        self.assertFalse(legacy_overlap(box(1, 1, 2, 2), box(0, 0, 10, 10), 'spatial_review', 'new', 'new', .98)['supersession_supported'])

    def test_variable_roof_preserves_courtyard_and_source_slope(self):
        mask = np.ones((20, 20), bool); mask[6:14, 6:14] = False
        grid = np.repeat((43 + np.arange(20) * .1)[None, :], 20, axis=0)
        info = {'left_utm_m': 0, 'bottom_utm_m': 0, 'cell_m': 1}
        points, counts, indices = surface_geometry(mask, grid, info, [0, 0], 31.59, box(0, 0, 20, 20))
        area, offset = 0., 0
        for count in counts:
            coords = [points[i] for i in indices[offset:offset + count]]
            if count == 3 and all(p[2] > .2 for p in coords):
                triangle = Polygon([p[:2] for p in coords]); area += triangle.area
                self.assertFalse(triangle.covers(Point(10, 10)))
            offset += count
        self.assertAlmostEqual(area, int(mask.sum()))
        self.assertGreater(max(p[2] for p in points) - min(p[2] for p in points if p[2] > .2), 1)

    def test_surface_is_clipped_to_property_mask_not_extruded_from_it(self):
        mask = np.ones((5, 5), bool); grid = np.full((5, 5), 43.)
        points, _, _ = surface_geometry(mask, grid, {'left_utm_m': 0, 'bottom_utm_m': 0, 'cell_m': 1}, [0, 0], 31.59, box(0, 0, 3.5, 5))
        self.assertLessEqual(max(p[0] for p in points), 3.5)

    def test_surface_mesh_has_matching_topology_normals_and_uv(self):
        mask = np.ones((5, 5), bool); mask[2, 2] = False; grid = np.full((5, 5), 43.)
        geometry = surface_geometry(mask, grid, {'left_utm_m': 0, 'bottom_utm_m': 0, 'cell_m': 1}, [0, 0], 31.59, box(0, 0, 5, 5))
        stage = Usd.Stage.CreateInMemory(); mesh = write_surface(stage, '/World/Landmarks/Princeton/Test', geometry)
        self.assertTrue(mesh.GetPrim().IsDefined())
        self.assertEqual(sum(mesh.GetFaceVertexCountsAttr().Get()), len(mesh.GetFaceVertexIndicesAttr().Get()))
        self.assertEqual(len(mesh.GetNormalsAttr().Get()), len(mesh.GetFaceVertexCountsAttr().Get()))

    def test_protected_courtyard_fails_even_when_global_area_is_small(self):
        config = {'protected_voids_utm': [{'id': 'courtyard', 'bounds': [5, 5, 7, 7]}]}
        with self.assertRaisesRegex(ValueError, 'Protected courtyard'):
            validate_voids(box(0, 0, 8, 8), config)
        self.assertEqual(validate_voids(box(0, 0, 4, 4), config)[0]['roof_overlap_m2'], 0)

    def test_higher_zone_wins_overlap_without_duplicate_massing(self):
        zones = [{'id': 'high', 'geometry': box(0, 0, 10, 10)}, {'id': 'middle', 'geometry': box(9, 0, 20, 10)}]
        footprint, changes = disjoint_zones(zones, box(0, 0, 20, 10))
        self.assertAlmostEqual(zones[0]['geometry'].intersection(zones[1]['geometry']).area, 0)
        self.assertAlmostEqual(changes[1]['removed_overlap_m2'], 10)
        self.assertAlmostEqual(footprint.area, 200)

    def test_actual_historical_cloud_and_rendered_faces_preserve_frozen_courtyard(self):
        cache = ROOT / 'data/heights/princeton/points.npz'
        layer = ROOT / 'scene/princeton_correction.usda'
        if not cache.exists() or not layer.exists():
            self.skipTest('Local historical point evidence/derived proposal not present; synthetic guards still run')
        config = read(ROOT / 'config/princeton_sources.json')
        points = np.load(cache)['points']
        zones, grid, masks, info = roof_zones(points, config)
        flat, changes = disjoint_zones(zones, box(*points[:, :2].min(axis=0), *points[:, :2].max(axis=0)))
        self.assertLess(zones[0]['geometry'].intersection(zones[1]['geometry']).area, 1e-7)
        void = box(*config['protected_voids_utm'][0]['bounds'])
        ys, xs = np.where(masks[2] | masks[3])
        for y, x in zip(ys, xs):
            cell = box(info['left_utm_m']+x, info['bottom_utm_m']+y, info['left_utm_m']+x+1, info['bottom_utm_m']+y+1)
            self.assertLess(cell.intersection(void).area, 1e-7)
        self.assertTrue(all(z['class_support_points_in_supported_cells'] for z in zones))
        self.assertEqual(zones[0]['class_support_points_in_supported_cells'].get('6', 0), 0)
        origin = Transformer.from_crs(4326, 32617, always_xy=True).transform(*config['origin_wgs84'])
        stage = Usd.Stage.Open(str(layer)); checked = 0
        for prim in stage.GetPrimAtPath('/World/Landmarks/PrincetonAtCollegePark').GetChildren():
            if not prim.IsA(UsdGeom.Mesh):
                continue
            mesh = UsdGeom.Mesh(prim); vertices = mesh.GetPointsAttr().Get(); indices = mesh.GetFaceVertexIndicesAttr().Get(); offset = 0
            for count in mesh.GetFaceVertexCountsAttr().Get():
                coords = [vertices[i] for i in indices[offset:offset+count]]; offset += count
                if all(p[2] > .2 for p in coords):
                    face = Polygon([(p[0]+origin[0], p[1]+origin[1]) for p in coords])
                    if face.is_valid and face.area > 1e-8:
                        self.assertLess(face.intersection(void).area, 1e-6); checked += 1
        self.assertGreater(checked, 1000)


if __name__ == '__main__':
    unittest.main()
