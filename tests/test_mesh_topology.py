import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from mesh_topology import closed_shell_report

class ClosedShellTests(unittest.TestCase):
    points=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
    faces=[[0,2,1],[0,1,3],[1,2,3],[2,0,3]]
    def check(self,faces,points=None):return closed_shell_report(points or self.points,[len(f) for f in faces],[i for f in faces for i in f])
    def test_closed_and_open_shell(self):
        self.assertTrue(self.check(self.faces)['passed_closed_shell'])
        report=self.check(self.faces[:-1]);self.assertFalse(report['passed_closed_shell']);self.assertEqual(report['boundary_edges'],3)
    def test_wrong_orientation_and_duplicate_faces(self):
        faces=[self.faces[0][::-1],*self.faces[1:]]
        self.assertEqual(self.check(faces)['inconsistent_edge_orientation'],3)
        self.assertGreater(self.check(self.faces+[self.faces[0]])['nonmanifold_edges'],0)
    def test_disconnected_face_vertices_are_welded(self):
        points=[self.points[i] for f in self.faces for i in f]
        self.assertTrue(self.check([list(range(i,i+3)) for i in range(0,12,3)],points)['passed_closed_shell'])
    def test_invalid_indices_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):closed_shell_report(self.points,[3],[0,1,99])
        with self.assertRaises(ValueError):closed_shell_report([(float('nan'),0,0)],[3],[0,0,0])
