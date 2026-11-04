from pathlib import Path
import os,sys,unittest
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'));sys.path.insert(0,str(ROOT/'tools'))
from pxr import Usd,UsdGeom,Gf,Sdf
from shapely.geometry import box
from shapely.strtree import STRtree
from asset_clearance import instance_mesh_points,add_inactive_ids,collision_records,footprint,world_points

class AssetClearanceTests(unittest.TestCase):
    def mesh(self,stage,path,points):
        m=UsdGeom.Mesh.Define(stage,path);m.CreatePointsAttr(points);m.CreateFaceVertexCountsAttr([3]);m.CreateFaceVertexIndicesAttr([0,1,2]);return m

    def test_instance_prototype_orientation_scale_and_ancestor_transform(self):
        s=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(s,'/World').AddTranslateOp().Set(Gf.Vec3d(10,20,0))
        proto=UsdGeom.Xform.Define(s,'/Prototypes/Tree');proto.AddTranslateOp().Set(Gf.Vec3d(1,0,0));proto.AddScaleOp().Set(Gf.Vec3f(2,1,1))
        trunk=self.mesh(s,'/Prototypes/Tree/Trunk',[(0,0,0),(1,0,0),(0,1,1)]);trunk.AddTranslateOp().Set(Gf.Vec3d(0,1,0))
        inst=UsdGeom.PointInstancer.Define(s,'/World/Trees');inst.AddTranslateOp().Set(Gf.Vec3d(5,0,0))
        inst.GetPrototypesRel().SetTargets([proto.GetPath()]);inst.CreateProtoIndicesAttr([0]);inst.CreatePositionsAttr([(3,4,0)]);inst.CreateScalesAttr([(.5,2,1)])
        inst.CreateOrientationsAttr([Gf.Quath(.70710678,Gf.Vec3h(0,0,.70710678))])
        points=instance_mesh_points(inst,0,proto.GetPrim(),trunk.GetPrim(),UsdGeom.XformCache())
        self.assertAlmostEqual(points[1][0],16,delta=.003);self.assertAlmostEqual(points[1][1],25.5,delta=.003)
        self.assertGreater(footprint(points).area,0)

    def test_added_inactive_ids_preserve_extent_masks_and_arrays(self):
        base=Usd.Stage.CreateInMemory();inst=UsdGeom.PointInstancer.Define(base,'/World/Trees')
        proto=UsdGeom.Xform.Define(base,'/Prototype');self.mesh(base,'/Prototype/Trunk',[(0,0,0),(1,0,0),(0,1,1)])
        inst.GetPrototypesRel().SetTargets([proto.GetPath()]);inst.CreateIdsAttr([101,205,309]);inst.CreateProtoIndicesAttr([0,0,0]);inst.CreatePositionsAttr([(0,0,0),(5,0,0),(10,0,0)])
        inst.GetPrim().SetMetadata('inactiveIds',Sdf.Int64ListOp.Create(prependedItems=[309]))
        extent=Usd.Stage.CreateInMemory();UsdGeom.PointInstancer(extent.OverridePrim('/World/Trees')).CreateInvisibleIdsAttr([205])
        correction=Usd.Stage.CreateInMemory();add_inactive_ids(correction,'/World/Trees',[101])
        before=base.GetRootLayer().ExportToString();mask_before=extent.GetRootLayer().ExportToString()
        s=Usd.Stage.CreateInMemory();s.GetRootLayer().subLayerPaths=[extent.GetRootLayer().identifier,correction.GetRootLayer().identifier,base.GetRootLayer().identifier]
        combined=UsdGeom.PointInstancer(s.GetPrimAtPath('/World/Trees'))
        self.assertEqual(list(combined.ComputeMaskAtTime(Usd.TimeCode.Default())),[False,False,False])
        self.assertEqual(list(combined.GetIdsAttr().Get()),[101,205,309]);self.assertEqual(list(combined.GetPositionsAttr().Get()),list(inst.GetPositionsAttr().Get()))
        self.assertEqual(base.GetRootLayer().ExportToString(),before);self.assertEqual(extent.GetRootLayer().ExportToString(),mask_before)

    def test_height_separation_and_actual_small_trunk_not_canopy(self):
        rows=[{'path':'/Building','kind':'building','geometry':box(2,2,4,4),'low':0,'high':5}];index=STRtree([r['geometry'] for r in rows])
        self.assertEqual(collision_records(box(-.2,-.2,.2,.2),0,2,rows,index),[])
        self.assertEqual(collision_records(box(2.2,2.2,2.8,2.8),6,8,rows,index),[])
        self.assertEqual(len(collision_records(box(2.2,2.2,2.8,2.8),0,2,rows,index)),1)
        self.assertEqual(len(collision_records(box(-4,-4,4,4),0,8,rows,index)),0) # Bounding-box sliver is not unequivocal.

    def test_mesh_world_transform_before_footprint(self):
        s=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(s,'/Car').AddTranslateOp().Set(Gf.Vec3d(100,200,0))
        mesh=self.mesh(s,'/Car/Body',[(0,0,0),(2,0,0),(0,1,1)]);mesh.AddScaleOp().Set(Gf.Vec3f(2,3,1))
        geometry=footprint(world_points(mesh.GetPrim(),UsdGeom.XformCache()))
        self.assertEqual(geometry.bounds,(100,200,104,203))

if __name__=='__main__':unittest.main()
