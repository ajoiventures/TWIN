from pathlib import Path
import os,sys,tempfile,unittest
from types import SimpleNamespace
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'));sys.path.insert(0,str(ROOT/'tools'))
from pxr import Sdf,Usd,UsdGeom,UsdLux
from workspace_evidence import inherited_evidence,inspector_text,set_session_visibility,save_manual_only,available_display_groups,should_open_project,is_project_stage,registry_index,evidence_category,SessionConfidenceFilter,CONFIDENCE_CATEGORIES,create_workspace_stage,set_session_camera,SceneRefresh,government_preview
from workspace_evidence import normalize_boundary_switches,preflight_workspace_stage,create_review_stage
import json

class WorkspaceEvidenceTests(unittest.TestCase):
    def test_render_wrapper_preserves_units_and_precomposes_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.usda';proposal=root/'proposal.usda'
            stage=Usd.Stage.CreateNew(str(source));UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
            stage.SetStartTimeCode(12);UsdGeom.Cube.Define(stage,'/World/Box').CreateSizeAttr(2);stage.GetRootLayer().Save()
            change=Usd.Stage.CreateNew(str(proposal));change.OverridePrim('/World/Box').CreateAttribute('size',Sdf.ValueTypeNames.Double).Set(3);change.GetRootLayer().Save()
            before=source.read_bytes();review=create_review_stage(source,proposal)
            self.assertEqual(UsdGeom.GetStageUpAxis(review),'Z');self.assertEqual(UsdGeom.GetStageMetersPerUnit(review),1)
            self.assertEqual(review.GetStartTimeCode(),12);self.assertEqual(review.GetPrimAtPath('/World/Box').GetAttribute('size').Get(),3)
            self.assertTrue(review.GetRootLayer().anonymous);self.assertEqual(source.read_bytes(),before)
            empty=root/'implicit.usda';implicit=Usd.Stage.CreateNew(str(empty));implicit.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError,'explicitly author'):create_review_stage(empty)

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
        # A constant filter must hide animated session visibility too, then
        # restore the exact previous property, including samples and metadata.
        with Usd.EditContext(stage,stage.GetSessionLayer()):
            attr=UsdGeom.Imageable(p).CreateVisibilityAttr()
            attr.Set('inherited',Usd.TimeCode(1));attr.Set('invisible',Usd.TimeCode(2))
            attr.SetDocumentation('User visibility animation');attr.SetCustomData({'keep':'original'})
        path=p.GetPath().AppendProperty('visibility');old=stage.GetSessionLayer().GetPropertyAtPath(path)
        saved={key:old.GetInfo(key) for key in old.ListInfoKeys()}
        controller.apply(allowed)
        self.assertEqual(UsdGeom.Imageable(p).ComputeVisibility(Usd.TimeCode(1)),'invisible')
        self.assertEqual(stage.GetSessionLayer().ListTimeSamplesForPath(path),[])
        controller.reset();restored=stage.GetSessionLayer().GetPropertyAtPath(path)
        self.assertEqual({key:restored.GetInfo(key) for key in restored.ListInfoKeys()},saved)
        self.assertEqual(UsdGeom.Imageable(p).ComputeVisibility(Usd.TimeCode(1)),'inherited')
        self.assertEqual(stage.GetRootLayer().ExportToString(),base)
        self.assertEqual(stage.GetEditTarget().GetLayer(),target)

    def test_layer_switch_and_confidence_filter_are_independent(self):
        stage=Usd.Stage.CreateInMemory();p=UsdGeom.Cube.Define(stage,'/World/Buildings/B').GetPrim()
        p.SetCustomDataByKey('height',{'quality':'floor_count_estimate'})
        controller=SessionConfidenceFilter(stage)
        controller.apply({'unknown'});set_session_visibility(stage,'/World/Buildings',False);controller.reset()
        self.assertFalse(visible_for_test(stage,p))

    def test_interpreted_detail_inspection_and_filter_preserve_source(self):
        stage=Usd.Stage.CreateInMemory()
        root=UsdGeom.Xform.Define(stage,'/World/OfficeFrontageDetail').GetPrim()
        root.SetCustomData({'siteAddress':'1615 Edgewater Dr','appearanceId':'appearance:1615:detail',
            'quality':'illustrative_photo_interpreted','sourceSnapshot':'s1',
            'sourceContext':{'publisher':'Broker reference','sourceURL':'https://example.org/reference'}})
        detail=UsdGeom.Cube.Define(stage,'/World/OfficeFrontageDetail/Cornice').GetPrim()
        source=stage.GetRootLayer().ExportToString()
        text=inspector_text(detail,active_snapshot='s1')
        self.assertIn('Address: 1615 Edgewater Dr',text)
        self.assertIn('Appearance ID: appearance:1615:detail',text)
        self.assertIn('Source acquisition date: Unknown',text)
        self.assertEqual(evidence_category(detail,'s1'),'illustrative')
        controller=SessionConfidenceFilter(stage,'s1')
        self.assertEqual(controller.apply({'unknown'})['hidden_groups'],1)
        self.assertFalse(visible_for_test(stage,detail))
        controller.reset();self.assertTrue(visible_for_test(stage,detail))
        self.assertEqual(stage.GetRootLayer().ExportToString(),source)

    def test_boundary_switch_normalization_preserves_appearance_and_global_hides(self):
        stage=Usd.Stage.CreateInMemory();parent=UsdGeom.Xform.Define(stage,'/World/StudyBoundaries')
        main=UsdGeom.Xform.Define(stage,'/World/StudyBoundaries/MainStreet').GetPrim()
        neighborhood=UsdGeom.Xform.Define(stage,'/World/StudyBoundaries/Neighborhood').GetPrim()
        parent.CreateVisibilityAttr('invisible')
        source=stage.GetRootLayer().ExportToString();target=stage.GetEditTarget().GetLayer()
        self.assertTrue(normalize_boundary_switches(stage))
        self.assertFalse(visible_for_test(stage,main));self.assertFalse(visible_for_test(stage,neighborhood))
        set_session_visibility(stage,str(main.GetPath()),True)
        self.assertTrue(visible_for_test(stage,main));self.assertFalse(visible_for_test(stage,neighborhood))
        session=stage.GetSessionLayer().ExportToString()
        self.assertFalse(normalize_boundary_switches(stage));self.assertEqual(stage.GetSessionLayer().ExportToString(),session)
        self.assertEqual(stage.GetRootLayer().ExportToString(),source);self.assertEqual(stage.GetEditTarget().GetLayer(),target)
        # An ancestor hide alone must not trigger normalization or be lifted.
        other=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(other,'/World').CreateVisibilityAttr('invisible')
        UsdGeom.Xform.Define(other,'/World/StudyBoundaries');child=UsdGeom.Xform.Define(other,'/World/StudyBoundaries/MainStreet').GetPrim()
        before=other.GetSessionLayer().ExportToString();self.assertFalse(normalize_boundary_switches(other))
        self.assertEqual(other.GetSessionLayer().ExportToString(),before);self.assertFalse(visible_for_test(other,child))

    def test_transient_workspace_absorbs_renderer_root_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'project.usda';source=Usd.Stage.CreateNew(str(path))
            UsdGeom.Xform.Define(source,'/World');UsdGeom.Camera.Define(source,'/World/A');UsdGeom.Camera.Define(source,'/World/B')
            UsdGeom.Cube.Define(source,'/World/VisibleGeometry')
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
            # A restarted editor can recover the previous generated view from disk,
            # without replacing unsaved manual/scenario opinions or saved sources.
            base.GetRootLayer().Reload(True)
            recovered=SceneRefresh(stage,root,['base.usda'])
            self.assertEqual(recovered.recover_latest()['status'],'previous_view_recovered_in_memory')
            self.assertEqual(UsdGeom.Cube(stage.GetPrimAtPath('/World/Cube')).GetSizeAttr().Get(),1)
            self.assertEqual((scene/'base.usda').read_text(),text)
            self.assertEqual({l.identifier:l.ExportToString() for l in (manual,scenario)},user_before)
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
        aerial=UsdGeom.Xform.Define(stage,'/World/Information/PilotAerialReview')
        aerial.CreateVisibilityAttr('invisible')
        curve=UsdGeom.BasisCurves.Define(stage,aerial.GetPath().AppendChild('Review')).GetPrim()
        curve.SetCustomDataByKey('sourceContext',{'sourceBuildingKey':'roof:17','sourceParcelId':'P17','assignedParcelId':'P18','sourceObjectIds':'17,18','reviewId':'R17','reviewObservationJSON':'{"status":"out_of_frame"}'})
        text=inspector_text(curve)
        self.assertIn('Source building key: roof:17',text);self.assertIn('Parcel: P17',text)
        self.assertIn('Source object IDs: 17,18',text);self.assertIn('Assigned parcel reference: P18',text)
        self.assertIn('out_of_frame',text)
        self.assertIn(('Dated aerial review',str(aerial.GetPath())),available_display_groups(stage))

    def test_startup_preflight_rejects_partial_and_empty_scene_without_user_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);user=Usd.Stage.CreateInMemory();UsdGeom.Cube.Define(user,'/UserWork')
            user_before=user.GetRootLayer().ExportToString()
            with self.assertRaisesRegex(ValueError,'missing'):create_workspace_stage(root/'missing.usda')
            source=Usd.Stage.CreateNew(str(root/'source.usda'));UsdGeom.Cube.Define(source,'/World/Cube');source.GetRootLayer().Save()
            self.assertTrue(preflight_workspace_stage(create_workspace_stage(root/'source.usda')))
            broken=Sdf.Layer.CreateNew(str(root/'broken.usda'));broken.subLayerPaths=['source.usda','missing_child.usda'];broken.Save()
            with self.assertRaisesRegex(ValueError,'incomplete|dependency missing'):create_workspace_stage(root/'broken.usda')
            source.DefinePrim('/World/Material/Texture','Shader').CreateAttribute('inputs:file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('missing_texture.png'));source.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError,'dependency missing'):create_workspace_stage(root/'source.usda')
            empty=Usd.Stage.CreateNew(str(root/'empty.usda'));UsdGeom.Xform.Define(empty,'/World');UsdGeom.Camera.Define(empty,'/World/Camera');empty.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError,'no useful visible geometry'):create_workspace_stage(root/'empty.usda')
            hidden=UsdGeom.Cube.Define(empty,'/World/HiddenCube');hidden.CreateVisibilityAttr('invisible');empty.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError,'no useful visible geometry'):create_workspace_stage(root/'empty.usda')
            empty.RemovePrim('/World/HiddenCube');UsdGeom.Mesh.Define(empty,'/World/EmptyMesh');empty.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError,'no useful visible geometry'):create_workspace_stage(root/'empty.usda')
            self.assertEqual(user.GetRootLayer().ExportToString(),user_before)

    def test_startup_preflight_ignores_unloaded_optional_payload_and_dormant_variant(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'optional.usda';layer=Sdf.Layer.CreateNew(str(path));world=Sdf.CreatePrimInLayer(layer,'/World');world.specifier=Sdf.SpecifierDef;world.typeName='Xform'
            child=Sdf.CreatePrimInLayer(layer,'/World/Optional');child.specifier=Sdf.SpecifierDef;child.typeName='Xform';child.payloadList.prependedItems=[Sdf.Payload('unloaded_optional.usda')];layer.Save()
            stage=Usd.Stage.Open(layer,load=Usd.Stage.LoadNone);UsdGeom.Cube.Define(stage,'/World/VisibleGeometry')
            variant=stage.GetPrimAtPath('/World').GetVariantSets().AddVariantSet('detail');variant.AddVariant('off');variant.AddVariant('optional')
            variant.SetVariantSelection('optional')
            with variant.GetVariantEditContext():stage.DefinePrim('/World/DormantTexture','Shader').CreateAttribute('inputs:file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('dormant_missing.png'))
            variant.SetVariantSelection('off')
            self.assertFalse(stage.GetPrimAtPath('/World/Optional').IsLoaded());self.assertTrue(preflight_workspace_stage(stage))


def visible_for_test(stage,prim):
    return UsdGeom.Imageable(prim).ComputeVisibility()!='invisible'

if __name__=='__main__':unittest.main()
