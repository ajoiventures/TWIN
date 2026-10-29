from pathlib import Path
import os,sys,tempfile,unittest
from types import SimpleNamespace
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'));sys.path.insert(0,str(ROOT/'tools'))
from pxr import Sdf,Usd,UsdGeom,UsdLux
from workspace_evidence import inherited_evidence,inspector_text,set_session_visibility,save_manual_only,available_display_groups,should_open_project,is_project_stage,registry_index,evidence_category,SessionConfidenceFilter,CONFIDENCE_CATEGORIES,create_workspace_stage,set_session_camera,SceneRefresh,government_preview
import json

class WorkspaceEvidenceTests(unittest.TestCase):
    def default_stage(self):
        stage=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(stage,'/World')
        UsdGeom.Camera.Define(stage,'/World/Camera');UsdLux.DistantLight.Define(stage,'/World/Light')
        # Kit establishes a clean anonymous startup baseline. USD Python does
        # not expose MarkClean for anonymous layers, so model only those flags.
        root=SimpleNamespace(anonymous=True,dirty=False,customLayerData={})
        session=SimpleNamespace(dirty=False)
        wrapped=SimpleNamespace(GetRootLayer=lambda:root,GetSessionLayer=lambda:session,Traverse=stage.Traverse)
        return stage,wrapped,root,session

    def test_clean_anonymous_default_opens_project(self):
        stage,wrapped,root,session=self.default_stage()
        self.assertTrue(should_open_project(wrapped))
        UsdGeom.Cube.Define(stage,'/World/ActualGeometry')
        self.assertFalse(should_open_project(wrapped))

    def test_dirty_empty_or_saved_stage_preserved(self):
        stage=Usd.Stage.CreateInMemory();stage.GetRootLayer().customLayerData={'user':'unsaved'}
        self.assertFalse(should_open_project(stage))
        stage,wrapped,root,session=self.default_stage()
        session.dirty=True;self.assertFalse(should_open_project(wrapped))
        session.dirty=False;root.dirty=True;self.assertFalse(should_open_project(wrapped))
        root.dirty=False;root.anonymous=False;self.assertFalse(should_open_project(wrapped))
        self.assertTrue(should_open_project(None))

    def test_fresh_sdk_camera_render_dirt_does_not_block_project_startup(self):
        stage=Usd.Stage.CreateInMemory();stage.GetRootLayer().customLayerData={'cameraSettings':{'boundCamera':'/OmniverseKit_Persp'},'renderSettings':{}}
        UsdGeom.Camera.Define(stage,'/OmniverseKit_Persp');stage.DefinePrim('/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0','RenderProduct')
        self.assertTrue(should_open_project(stage))
        UsdGeom.Cube.Define(stage,'/World/UserCube');self.assertFalse(should_open_project(stage))
        stage.RemovePrim('/World/UserCube');stage.GetRootLayer().customLayerData={'cameraSettings':{},'user':'keep this'}
        self.assertFalse(should_open_project(stage))

    def test_unrelated_stage_not_labeled_project(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'college_park_connected.usda';other=root/'my_scene.usda'
            a=Usd.Stage.CreateNew(str(project));a.GetRootLayer().Save()
            b=Usd.Stage.CreateNew(str(other));b.GetRootLayer().Save()
            self.assertTrue(is_project_stage(a,[project]));self.assertFalse(is_project_stage(b,[project]))

    def test_ancestor_fields_and_nearest_quality(self):
        s=Usd.Stage.CreateInMemory();p=UsdGeom.Xform.Define(s,'/World/Buildings/B').GetPrim()
        p.SetCustomDataByKey('official',{'site_address':'Test address','parcel_id':'P','source':'Agency'})
        p.SetCustomDataByKey('height',{'height_m':8.2,'quality':'estimated'})
        p.SetCustomDataByKey('twin',{'sourceSnapshot':'snap','entityId':'entity'})
        child=UsdGeom.Cube.Define(s,'/World/Buildings/B/Window').GetPrim();child.SetCustomDataByKey('height',{'quality':'child review'})
        d=inherited_evidence(child);self.assertEqual(d['data']['height'],{'height_m':8.2,'quality':'child review'})
        text=inspector_text(child,'activation');self.assertIn('Parcel: P',text);self.assertIn('Snapshot: snap',text)
        self.assertIn('Source acquisition date: Unknown',text);self.assertIn('Project snapshot activation: activation',text)
        self.assertIn('Feature refresh: Unknown',text)

    def test_unknown_selection(self):
        self.assertIn('Address: Unknown',inspector_text(None))
        self.assertIn('Snapshot: Unknown',inspector_text(None))

    def test_registry_dates_require_matching_snapshot_and_unique_identity(self):
        stage=Usd.Stage.CreateInMemory();p=UsdGeom.Cube.Define(stage,'/World/B').GetPrim()
        p.SetCustomDataByKey('twin',{'entityId':'entity','sourceSnapshot':'s1'})
        row={'entity_id':'entity','source_snapshot':'s1','acquisition_interval':{'start':'2018-12-04','end':'2019-04-12'},'valid_time':{'start':None,'end':None,'quality':'current_validity_not_verified'},'evidence_refs':['height:B']}
        text=inspector_text(p,'2026 activation',registry_index({'records':[row]}))
        self.assertIn('2018-12-04 to 2019-04-12',text);self.assertIn('Feature refresh: Unknown',text)
        self.assertIn('Evidence references: height:B',text);self.assertIn('current_validity_not_verified',text)
        row['source_snapshot']='stale'
        self.assertIn('Source acquisition date: Unknown',inspector_text(p,registry=registry_index({'records':[row]})))
        self.assertEqual(registry_index({'records':[row,row]}),{})

    def test_session_display_never_dirties_source_or_manual(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=Usd.Stage.CreateNew(str(root/'base.usda'));UsdGeom.Cube.Define(base,'/World/Buildings/B');base.GetRootLayer().Save()
            manual=Sdf.Layer.CreateNew(str(root/'manual.usda'));manual.Save()
            s=Usd.Stage.CreateInMemory();s.GetRootLayer().subLayerPaths=[str(root/'manual.usda'),str(root/'base.usda')]
            s.SetEditTarget(manual);original=base.GetRootLayer().ExportToString();before=manual.ExportToString()
            self.assertTrue(set_session_visibility(s,'/World/Buildings',False))
            self.assertEqual(s.GetEditTarget().GetLayer(),manual)
            self.assertEqual(UsdGeom.Imageable(s.GetPrimAtPath('/World/Buildings/B')).ComputeVisibility(),'invisible')
            self.assertEqual(base.GetRootLayer().ExportToString(),original);self.assertEqual(manual.ExportToString(),before)
            self.assertFalse(base.GetRootLayer().dirty);self.assertFalse(manual.dirty)
            self.assertFalse(set_session_visibility(s,'/missing',False))
            self.assertIn(('Buildings','/World/Buildings'),available_display_groups(s))
            self.assertNotIn(('Scenario','/World/Scenario'),available_display_groups(s))

    def test_manual_save_isolated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b=Usd.Stage.CreateNew(str(root/'base.usda'));UsdGeom.Xform.Define(b,'/World');b.GetRootLayer().Save()
            manual=Sdf.Layer.CreateNew(str(root/'manual.usda'));manual.Save();before=(root/'base.usda').read_bytes()
            s=Usd.Stage.CreateInMemory();s.GetRootLayer().subLayerPaths=[str(root/'manual.usda'),str(root/'base.usda')]
            s.SetEditTarget(b.GetRootLayer());s.OverridePrim('/World').SetCustomDataByKey('pending','generated unsaved')
            s.SetEditTarget(manual);s.OverridePrim('/World').SetCustomDataByKey('user','manual edit')
            save_manual_only(s,root/'manual.usda')
            self.assertEqual((root/'base.usda').read_bytes(),before);self.assertTrue(b.GetRootLayer().dirty)
            self.assertIn('manual edit',(root/'manual.usda').read_text());self.assertFalse(manual.dirty)
            with self.assertRaises(ValueError):save_manual_only(s,root/'missing.usda')

    def test_confidence_labels_never_promote_unknown_to_observed(self):
        stage=Usd.Stage.CreateInMemory();p=UsdGeom.Cube.Define(stage,'/World/Buildings/B').GetPrim()
        self.assertEqual(evidence_category(p),'unknown')
        p.SetCustomDataByKey('height',{'quality':'floor_count_estimate','source_snapshot':'s1'})
        self.assertEqual(evidence_category(p,'s1'),'estimated')
        p.SetCustomDataByKey('height',{'quality':'historical_lidar_derived','source_snapshot':'s1'})
        self.assertEqual(evidence_category(p,'s1'),'historical_lidar')
        self.assertEqual(evidence_category(p,'s2'),'stale')
        self.assertIn('Snapshot freshness: Stale',inspector_text(p,active_snapshot='s2'))
        self.assertEqual(evidence_category(UsdGeom.Cube.Define(stage,'/World/Scenario/B').GetPrim()),'proposed')

    def test_confidence_filter_restores_session_and_keeps_layers_and_edit_target(self):
        stage=Usd.Stage.CreateInMemory();p=UsdGeom.Cube.Define(stage,'/World/Buildings/Building_1').GetPrim()
        p.SetCustomDataByKey('height',{'quality':'floor_count_estimate'})
        roof=UsdGeom.Cube.Define(stage,'/World/Roofs/Roof_1').GetPrim()
        base=stage.GetRootLayer().ExportToString();target=stage.GetEditTarget().GetLayer()
        self.assertEqual(evidence_category(roof),'estimated')
        controller=SessionConfidenceFilter(stage);allowed={key for key,label in CONFIDENCE_CATEGORIES}-{'estimated'}
        self.assertEqual(controller.apply(allowed)['hidden_groups'],2)
        self.assertFalse(visible_for_test(stage,p))
        controller.reset()
        self.assertTrue(visible_for_test(stage,p));self.assertTrue(visible_for_test(stage,roof))
        self.assertEqual(stage.GetRootLayer().ExportToString(),base);self.assertEqual(stage.GetEditTarget().GetLayer(),target)
        # Pre-existing session hides survive disabling/resetting the filter.
        set_session_visibility(stage,str(p.GetPath()),False)
        before=stage.GetSessionLayer().GetPropertyAtPath(p.GetPath().AppendProperty('visibility')).default
        controller.apply(allowed);controller.reset()
        self.assertEqual(stage.GetSessionLayer().GetPropertyAtPath(p.GetPath().AppendProperty('visibility')).default,before)
        self.assertFalse(visible_for_test(stage,p))

    def test_layer_switch_and_confidence_filter_are_independent(self):
        stage=Usd.Stage.CreateInMemory();p=UsdGeom.Cube.Define(stage,'/World/Buildings/B').GetPrim()
        p.SetCustomDataByKey('height',{'quality':'floor_count_estimate'})
        controller=SessionConfidenceFilter(stage)
        controller.apply({'unknown'});set_session_visibility(stage,'/World/Buildings',False);controller.reset()
        self.assertFalse(visible_for_test(stage,p))

    def test_transient_workspace_absorbs_renderer_root_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'project.usda';source=Usd.Stage.CreateNew(str(path))
            UsdGeom.Xform.Define(source,'/World');UsdGeom.Camera.Define(source,'/World/A');UsdGeom.Camera.Define(source,'/World/B')
            source.DefinePrim('/Render/Product','RenderProduct').CreateRelationship('camera').SetTargets(['/World/A'])
            source.GetRootLayer().Save();before=source.GetRootLayer().ExportToString()
            stage=create_workspace_stage(path)
            self.assertTrue(is_project_stage(stage,[path]));self.assertFalse(should_open_project(stage))
            class Viewport:
                render_product_path='/Render/Product'
                @property
                def camera_path(self):return None
                @camera_path.setter
                def camera_path(self,path):
                    with Usd.EditContext(stage,stage.GetRootLayer()):stage.GetPrimAtPath('/Render/Product').GetRelationship('camera').SetTargets([path])
            set_session_camera(stage,Viewport(),'/World/B')
            self.assertEqual(stage.GetPrimAtPath('/Render/Product').GetRelationship('camera').GetTargets(),[Sdf.Path('/World/B')])
            self.assertEqual(source.GetRootLayer().ExportToString(),before);self.assertFalse(source.GetRootLayer().dirty)

    def test_staged_refresh_undo_preserves_manual_scenario_and_saved_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);scene=root/'scene';scene.mkdir();(root/'data/processed').mkdir(parents=True);(root/'data/snapshots/s1').mkdir(parents=True)
            (root/'data/processed/active.json').write_text(json.dumps({'snapshot':'s1','relative_path':'data/snapshots/s1'}))
            base=Usd.Stage.CreateNew(str(scene/'base.usda'));UsdGeom.Cube.Define(base,'/World/Cube').CreateSizeAttr(1);base.GetRootLayer().Save()
            for name in ('manual','scenario'):Sdf.Layer.CreateNew(str(scene/(name+'.usda'))).Save()
            assembly=Sdf.Layer.CreateNew(str(scene/'assembly.usda'));assembly.subLayerPaths=['manual.usda','scenario.usda','base.usda'];assembly.Save()
            stage=create_workspace_stage(scene/'assembly.usda');manual=Sdf.Layer.FindOrOpen(str(scene/'manual.usda'));scenario=Sdf.Layer.FindOrOpen(str(scene/'scenario.usda'))
            with Usd.EditContext(stage,scenario):UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cube')).MakeInvisible()
            with Usd.EditContext(stage,manual):UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cube')).MakeVisible()
            user_before={l.identifier:l.ExportToString() for l in (manual,scenario)}
            manager=SceneRefresh(stage,root,['base.usda']);text=base.GetRootLayer().ExportToString().replace('double size = 1','double size = 2');(scene/'base.usda').write_text(text)
            self.assertEqual(UsdGeom.Cube(stage.GetPrimAtPath('/World/Cube')).GetSizeAttr().Get(),1)
            self.assertEqual(len(manager.review()['layers']),1);report=manager.apply()
            self.assertEqual(UsdGeom.Cube(stage.GetPrimAtPath('/World/Cube')).GetSizeAttr().Get(),2)
            self.assertTrue(Path(report['recovery_receipt']).exists());manager.undo()
            self.assertEqual(UsdGeom.Cube(stage.GetPrimAtPath('/World/Cube')).GetSizeAttr().Get(),1)
            self.assertEqual((scene/'base.usda').read_text(),text)
            self.assertEqual({l.identifier:l.ExportToString() for l in (manual,scenario)},user_before)
            self.assertTrue(visible_for_test(stage,stage.GetPrimAtPath('/World/Cube')))
            # Missing replacement must preserve the current usable view.
            (scene/'base.usda').unlink()
            with self.assertRaisesRegex(ValueError,'missing'):manager.review()
            self.assertEqual(UsdGeom.Cube(stage.GetPrimAtPath('/World/Cube')).GetSizeAttr().Get(),1)
            with self.assertRaisesRegex(ValueError,'User/scenario'):SceneRefresh(stage,root,['scenario.usda'])

    def test_government_dates_and_default_off_layers_are_explicit(self):
        stage=Usd.Stage.CreateInMemory();parent=UsdGeom.Xform.Define(stage,'/World/Information/FemaEffectiveFloodHazards')
        parent.CreateVisibilityAttr('invisible');parent.GetPrim().SetCustomDataByKey('sourceContext',{'publisher':'FEMA','sourceSnapshot':'s1','acquisitionStart':'unknown','acquisitionEnd':'unknown','effectiveDate':'2009-09-25','retrievedUTC':'2026-10-28T00:00:00Z','quality':'effective reference context'})
        child=UsdGeom.Cube.Define(stage,parent.GetPath().AppendChild('Zone')).GetPrim()
        text=inspector_text(child,active_snapshot='s1')
        self.assertIn('Source: FEMA',text);self.assertIn('Source effective date: 2009-09-25',text);self.assertIn('Original retrieval time: 2026-',text)
        self.assertIn('Acquisition interval: unknown to unknown',text);self.assertFalse(visible_for_test(stage,child))
        self.assertIn(('Effective FEMA flood context',str(parent.GetPath())),available_display_groups(stage))


def visible_for_test(stage,prim):
    return UsdGeom.Imageable(prim).ComputeVisibility()!='invisible'

if __name__=='__main__':unittest.main()
