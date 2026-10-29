"""Testable editor evidence and session-display helpers; no Kit/UI imports."""
from pathlib import Path
import hashlib,json,datetime

UNKNOWN='Unknown'


def create_workspace_stage(source_path):
    """Transient root absorbs Kit render/camera edits above the saved assembly."""
    from pxr import Sdf,Usd,UsdGeom
    source=Path(source_path).resolve();layer=Sdf.Layer.FindOrOpen(str(source))
    if not layer:raise ValueError('Project scene is unavailable')
    root=Sdf.Layer.CreateAnonymous('twin_workspace.usda');root.subLayerPaths=[str(source)]
    root.customLayerData={'twinWorkspaceSource':str(source),'purpose':'Transient editor camera/render state; save manual edits separately'}
    stage=Usd.Stage.Open(root)
    for name in ('metersPerUnit','upAxis'):
        value=layer.pseudoRoot.GetInfo(name)
        if value is not None:stage.SetMetadata(name,value)
    world=stage.GetPrimAtPath('/World')
    if world:stage.SetDefaultPrim(world)
    return stage


def set_session_camera(stage,viewport,camera_path):
    """Mirror the viewport binding in session; transient project root absorbs Kit writes."""
    from pxr import Sdf,Usd,UsdGeom
    if not stage or not viewport:return False
    camera=stage.GetPrimAtPath(camera_path)
    if not camera or not camera.IsA(UsdGeom.Camera):return False
    product_path=viewport.render_product_path
    if product_path:
        product=stage.GetPrimAtPath(product_path);session=stage.GetSessionLayer()
        if product:
            Sdf.CreatePrimInLayer(session,product.GetPath())
            for name in ('camera','resolution'):
                prop=product.GetProperty(name)
                if prop and not session.GetPropertyAtPath(prop.GetPath()):
                    stack=prop.GetPropertyStack()
                    if stack:Sdf.CopySpec(stack[0].layer,prop.GetPath(),session,prop.GetPath())
    with Usd.EditContext(stage,stage.GetSessionLayer()):
        if product_path and stage.GetPrimAtPath(product_path):
            stage.GetPrimAtPath(product_path).CreateRelationship('camera').SetTargets([camera_path])
        viewport.camera_path=camera_path
    return True

def should_open_project(stage):
    """Replace only a clean anonymous default scene, never saved/user content."""
    if stage is None:return True
    root=stage.GetRootLayer();session=stage.GetSessionLayer()
    if not root.anonymous:return False
    metadata=root.customLayerData
    # Fresh Kit can dirty its empty stage with implicit camera/render state
    # before this bootstrap runs. Recognize only that exact infrastructure.
    sdk_metadata=bool(metadata) and 'cameraSettings' in metadata and set(metadata)<={'cameraSettings','renderSettings'}
    sdk_render=bool(stage.GetPrimAtPath('/Render/OmniverseKit')) if hasattr(stage,'GetPrimAtPath') else False
    sdk_default=sdk_metadata or sdk_render
    if metadata and not sdk_metadata:return False
    if (root.dirty or session.dirty) and not sdk_default:return False
    if getattr(session,'customLayerData',{}):return False
    from pxr import UsdGeom,UsdLux
    for prim in stage.Traverse():
        path=str(prim.GetPath())
        if prim.IsA(UsdGeom.Camera):
            if path.startswith('/OmniverseKit_') or path in ('/World/Camera','/World/Cameras/Camera'):continue
            return False
        if prim.HasAPI(UsdLux.LightAPI):
            if sdk_default and (root.dirty or session.dirty):return False
            continue
        if path in ('/Render','/Render/OmniverseKit','/Render/OmniverseKit/HydraTextures','/Render/Vars','/Render/Vars/LdrColor','/Render/OmniverseGlobalRenderSettings') or path.startswith('/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_'):
            if prim.GetTypeName() in ('','Scope','RenderProduct','RenderSettings','RenderVar'):continue
            return False
        if prim.IsA(UsdGeom.Gprim) or prim.IsA(UsdGeom.PointInstancer):return False
        # Only the familiar empty default grouping hierarchy is disposable.
        if prim.GetName() not in ('World','Cameras','Lighting','Lights'):return False
        if prim.GetTypeName() not in ('','Xform','Scope'):return False
    return True

def is_project_stage(stage,scene_paths):
    if not stage:return False
    root=stage.GetRootLayer()
    allowed={Path(p).resolve() for p in scene_paths}
    if root.realPath:return Path(root.realPath).resolve() in allowed
    source=root.customLayerData.get('twinWorkspaceSource')
    return bool(root.anonymous and source and Path(source).resolve() in allowed and any(layer.realPath and Path(layer.realPath).resolve()==Path(source).resolve() for layer in stage.GetLayerStack()))

def inherited_evidence(prim):
    """Nearest authored values win; missing nested fields fall back to ancestors."""
    result={}; origins={}; selected=str(prim.GetPath()) if prim else UNKNOWN
    while prim and not prim.IsPseudoRoot():
        for key,value in prim.GetCustomData().items():
            if isinstance(value,dict):
                target=result.setdefault(key,{})
                if isinstance(target,dict):
                    for nested,item in value.items():
                        if item not in (None,'') and nested not in target:
                            target[nested]=item;origins[key+'.'+nested]=str(prim.GetPath())
            elif value not in (None,'') and key not in result:
                result[key]=value;origins[key]=str(prim.GetPath())
        prim=prim.GetParent()
    return {'selected_path':selected,'data':result,'origins':origins}

def registry_index(document):
    buckets={}
    for row in document.get('records',[]):
        for field in ('entity_id','local_building_id'):
            if row.get(field):buckets.setdefault(row[field],[]).append(row)
    return {key:rows[0] for key,rows in buckets.items() if len(rows)==1}

def inspector_text(prim,project_refresh=None,registry=None,active_snapshot=None):
    evidence=inherited_evidence(prim);d=evidence['data']
    official=d.get('official',{});height=d.get('height',{});twin=d.get('twin',{});context=d.get('sourceContext',{})
    def pick(*values):return next((str(x) for x in values if x not in (None,'')),UNKNOWN)
    snapshot=pick(twin.get('sourceSnapshot'),height.get('source_snapshot'),official.get('snapshot'),d.get('sourceSnapshot'),context.get('sourceSnapshot'))
    record={}
    if registry:
        record=registry.get(twin.get('entityId'),registry.get(official.get('id'),{}))
        if snapshot==UNKNOWN or record.get('source_snapshot')!=snapshot:record={}
    interval=record.get('acquisition_interval') or {}
    valid=record.get('valid_time') or {}
    acquisition=pick(d.get('sourceDate'),d.get('acquisition_date'),official.get('source_date'),height.get('acquisition_date'))
    if acquisition==UNKNOWN and (interval.get('start') or interval.get('end')):
        acquisition=f"{interval.get('start') or UNKNOWN} to {interval.get('end') or UNKNOWN}"
    category=evidence_category(prim,active_snapshot)
    rows=[('Selected',evidence['selected_path']),
          ('Evidence category',dict(CONFIDENCE_CATEGORIES).get(category,UNKNOWN)),
          ('Snapshot freshness','Stale: differs from active dataset' if category=='stale' else 'Matches active dataset' if active_snapshot and snapshot==active_snapshot else UNKNOWN),
          ('Address',pick(official.get('site_address'))),
          ('Entity',pick(twin.get('entityId'),official.get('id'),d.get('id'))),
          ('Parcel',pick(official.get('parcel_id'),d.get('parcelId'))),
          ('Source',pick(official.get('source'),d.get('source'),context.get('publisher'))),
          ('Source object IDs',pick(d.get('sourceObjectIds'),official.get('source_object_id'))),
          ('Reference feature ID',pick(d.get('sourceZoneId'),d.get('sourceId'))),
          ('Source zone code',pick(d.get('zoneCode'))),
          ('Effective/source status',pick(d.get('sourceStatus'),d.get('productStatus'))),
          ('Source URL',pick(context.get('sourceURL'))),
          ('Display lift meaning',pick(d.get('displayLiftMeaning'))),
          ('Height (m)',pick(height.get('height_m'),d.get('heightMeters'))),
          ('Height method',pick(height.get('method'))),
          ('Height/source notes',pick(height.get('review_notes'),d.get('review_notes'))),
          ('Quality',pick(height.get('quality'),twin.get('quality'),d.get('quality'),official.get('geometry_quality'),context.get('quality'))),
          ('Snapshot',snapshot),
          ('Source acquisition date',acquisition),
          ('Acquisition interval',f"{context.get('acquisitionStart') or UNKNOWN} to {context.get('acquisitionEnd') or UNKNOWN}"),
          ('Source effective date',pick(context.get('effectiveDate'))),
          ('Original retrieval time',pick(context.get('retrievedUTC'))),
          ('Acquisition / mirror group',pick(context.get('acquisitionId'),context.get('sharedAcquisition'))),
          ('Current validity',pick(valid.get('quality'))),
          ('Valid-time interval',f"{valid.get('start') or UNKNOWN} to {valid.get('end') or UNKNOWN}"),
          ('Evidence references',', '.join(record.get('evidence_refs') or []) or UNKNOWN),
          ('Feature refresh',pick(d.get('lastRefresh'),d.get('refreshed_utc'),official.get('retrieved_utc'))),
          ('Project snapshot activation',pick(project_refresh))]
    if evidence['origins']:rows.append(('Evidence inherited from',', '.join(sorted(set(evidence['origins'].values())))))
    if d.get('commercialEvidence'):rows.append(('Market status','Unknown; broker context is not verified current availability'))
    return '\n'.join(f'{label}: {value}' for label,value in rows)


CONFIDENCE_CATEGORIES=(('historical_lidar','Historical LiDAR-derived heights'),
    ('observed','Observed (explicit source declaration)'),('estimated','Estimated'),
    ('illustrative','Illustrative'),('proposed','Proposed / future scenario'),
    ('unknown','Unknown evidence'),('stale','Stale source snapshot'))


def evidence_category(prim,active_snapshot=None):
    """Evidence labels describe provenance; they are not measured accuracy scores."""
    if not prim:return 'unknown'
    path=str(prim.GetPath())
    if path.startswith('/World/Roofs/Roof_'):
        counterpart=prim.GetStage().GetPrimAtPath('/World/Buildings/Building_'+prim.GetName()[5:])
        if counterpart:return evidence_category(counterpart,active_snapshot)
    d=inherited_evidence(prim)['data'];height=d.get('height',{});twin=d.get('twin',{});official=d.get('official',{})
    snapshot=twin.get('sourceSnapshot') or height.get('source_snapshot') or official.get('snapshot') or d.get('sourceSnapshot')
    if active_snapshot and snapshot and snapshot!=active_snapshot:return 'stale'
    if path.startswith(('/World/Scenario/','/World/Scenarios/')) or path in ('/World/Scenario','/World/Scenarios') or d.get('status') in ('proposed','proposal','future_scenario'):return 'proposed'
    quality=str(height.get('quality') or twin.get('quality') or d.get('quality') or '').lower()
    if quality=='historical_lidar_derived' or height.get('method') in ('usgs_lidar','usgs_lidar_roof_percentile','lidar_roof_percentile'):return 'historical_lidar'
    if d.get('observationKind')=='observed':return 'observed'
    if quality in ('estimated','floor_count_estimate') or str(height.get('method','')).startswith(('appraiser_','floor_')):return 'estimated'
    if any(path==root or path.startswith(root+'/') for root in ('/World/Trees','/World/ParkedVehicles','/World/Storefronts','/World/StreetFurniture','/World/RearParkingSamples')) or 'illustrative' in quality:return 'illustrative'
    return 'unknown'


def confidence_targets(stage):
    """Whole semantic groups only; never traverse/edit instance proxies."""
    if not stage:return []
    targets=[]
    for root in ('/World/Buildings','/World/Roofs','/World/Landmarks'):
        parent=stage.GetPrimAtPath(root)
        if parent:targets.extend(p for p in parent.GetChildren() if not p.IsInstanceProxy())
    for root in ('/World/Trees','/World/ParkedVehicles','/World/Storefronts','/World/StreetFurniture','/World/RearParkingSamples','/World/Scenario','/World/Scenarios'):
        prim=stage.GetPrimAtPath(root)
        if prim:targets.append(prim)
    return targets


class SessionConfidenceFilter:
    """Own only transient visibility properties; restore exact earlier session opinions.

    Root/manual/source layers and the user's current edit target are untouched.
    Visibility switches on ancestor groups continue to operate independently.
    """
    def __init__(self,stage,active_snapshot=None):
        from pxr import Sdf
        self.stage=stage;self.active_snapshot=active_snapshot;self.saved={};self.backup=Sdf.Layer.CreateAnonymous()

    def counts(self):
        result={key:0 for key,label in CONFIDENCE_CATEGORIES}
        for prim in confidence_targets(self.stage):result[evidence_category(prim,self.active_snapshot)]+=1
        return result

    def apply(self,enabled):
        from pxr import Sdf,Usd,UsdGeom
        allowed={key for key,label in CONFIDENCE_CATEGORIES}
        if not set(enabled)<=allowed:raise ValueError('Unknown evidence category')
        stage=self.stage;session=stage.GetSessionLayer();hidden=0;skipped=0
        for prim in confidence_targets(stage):
            if prim.IsInstanceProxy():skipped+=1;continue
            path=prim.GetPath().AppendProperty('visibility');key=str(path)
            hide=evidence_category(prim,self.active_snapshot) not in enabled
            if hide:
                if key not in self.saved:
                    old=session.GetPropertyAtPath(path);self.saved[key]=bool(old)
                    if old:
                        Sdf.CreatePrimInLayer(self.backup,prim.GetPath());Sdf.CopySpec(session,path,self.backup,path)
                with Usd.EditContext(stage,session):
                    # Every target is a typed imageable; do not retype source groups.
                    if not UsdGeom.Imageable(prim):skipped+=1;continue
                    UsdGeom.Imageable(prim).CreateVisibilityAttr().Set('invisible')
                hidden+=1
            elif key in self.saved:
                spec=session.GetPrimAtPath(prim.GetPath());prop=session.GetPropertyAtPath(path)
                if prop:spec.RemoveProperty(prop)
                if self.saved.pop(key):Sdf.CopySpec(self.backup,path,session,path)
        return {'hidden_groups':hidden,'skipped_groups':skipped,'counts':self.counts()}

    def reset(self):
        return self.apply({key for key,label in CONFIDENCE_CATEGORIES})

def set_session_visibility(stage,path,visible):
    from pxr import Sdf,Usd,UsdGeom
    if not stage:return False
    prim=stage.GetPrimAtPath(path)
    if not prim:return False
    with Usd.EditContext(stage,stage.GetSessionLayer()):
        # Original grouping prims can be untyped. Supply a displayable grouping
        # schema only in the transient session, leaving all authored files intact.
        if not prim.GetTypeName():stage.OverridePrim(path).SetTypeName('Xform')
        imageable=UsdGeom.Imageable(prim)
        if not imageable:return False
        imageable.CreateVisibilityAttr().Set('inherited' if visible else 'invisible')
    return True

def visible(stage,path):
    from pxr import UsdGeom
    prim=stage.GetPrimAtPath(path) if stage else None
    if not prim:return False
    imageable=UsdGeom.Imageable(prim)
    return not imageable or imageable.ComputeVisibility()!='invisible'

def save_manual_only(stage,path):
    """Save exactly the existing composed manual layer; never Stage.Save()."""
    if not stage:raise ValueError('No stage is open')
    target=Path(path).resolve()
    layer=next((layer for layer in stage.GetLayerStack() if layer.realPath and Path(layer.realPath).resolve()==target),None)
    if layer is None:raise ValueError('Manual edit layer is not composed; no layers saved')
    if layer.anonymous or not layer.permissionToSave:raise ValueError('Manual edit layer cannot be saved')
    if not layer.Save():raise RuntimeError('Manual edit layer save failed')
    return str(target)

def available_display_groups(stage):
    candidates=[('Buildings','/World/Buildings'),('Landmark reconstructions','/World/Landmarks'),
        ('Roofs','/World/Roofs'),('Streets','/World/Streets'),('Parks','/World/Parks'),('Water','/World/Water'),
        ('Trees and vegetation','/World/Trees'),('Street furniture','/World/StreetFurniture'),
        ('Storefronts','/World/Storefronts'),('Parked vehicles','/World/ParkedVehicles'),
        ('Parcel outlines','/World/ParcelBoundaries'),('Main Street boundary','/World/StudyBoundaries/MainStreet'),
        ('Neighborhood boundary','/World/StudyBoundaries/Neighborhood'),
        ('Rear parking samples','/World/RearParkingSamples'),('Effective FEMA flood context','/World/Information/FemaEffectiveFloodHazards'),
        ('Historical water / land-cover context','/World/WaterLandcoverContext'),('Scenario','/World/Scenario'),('Scenarios','/World/Scenarios')]
    return [(label,path) for label,path in candidates if stage and stage.GetPrimAtPath(path)]


class SceneRefresh:
    """Review/apply local generated layers atomically in memory; never fetch or save sources.

    Agency snapshot builds remain the pipeline's staged responsibility. This
    controller gates the editor's adoption of completed local layer replacements
    and keeps prior generated views recoverable without touching manual/scenario.
    """
    def __init__(self,stage,root,names):
        self.stage=stage;self.root=Path(root).resolve();self.paths=[self.root/'scene'/name for name in names]
        if any('manual' in p.name.lower() or 'scenario' in p.name.lower() for p in self.paths):raise ValueError('User/scenario layers cannot be refresh targets')
        self.hashes={str(p):self.sha(p) for p in self.paths if p.is_file()};self.plan=None;self.previous=None;self.owned_rollback={}
        self.snapshot=self.active_snapshot()

    @staticmethod
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def active_snapshot(self):
        path=self.root/'data/processed/active.json'
        if not path.is_file():raise ValueError('Snapshot pointer missing; existing scene preserved')
        packet=json.loads(path.read_text(encoding='utf-8'));folder=(self.root/packet['relative_path']).resolve()
        if not folder.is_relative_to(self.root/'data/snapshots') or not folder.is_dir():raise ValueError('Snapshot path unavailable; existing scene preserved')
        return packet['snapshot']

    def pending_paths(self):
        return [p for p in self.paths if (not p.is_file() and str(p) in self.hashes) or (p.is_file() and self.sha(p)!=self.hashes.get(str(p)))]

    def review(self):
        from pxr import Sdf,UsdUtils
        snapshot=self.active_snapshot();registry=self.root/'data/processed/asset_registry.json'
        if registry.exists() and json.loads(registry.read_text(encoding='utf-8')).get('source_snapshot')!=snapshot:raise ValueError('Generated registry has not caught up with the staged snapshot; scene preserved')
        rows=[]
        for path in self.pending_paths():
            if not path.is_file():raise ValueError('Generated layer missing: '+path.name+'; existing scene preserved')
            live=Sdf.Layer.Find(str(path).replace('\\','/'))
            if live and live.dirty and self.owned_rollback.get(str(path))!=hashlib.sha256(live.ExportToString().encode()).hexdigest():raise ValueError('Unsaved generated-layer edits: '+path.name)
            candidate=Sdf.Layer.OpenAsAnonymous(str(path))
            if not candidate:raise ValueError('Unreadable candidate: '+path.name)
            candidate_snapshot=candidate.customLayerData.get('sourceSnapshot',candidate.customLayerData.get('snapshot'))
            if candidate_snapshot and candidate_snapshot!=snapshot:raise ValueError('Candidate layer snapshot is stale: '+path.name)
            if path.name=='fema_effective_hazards.usda':
                from build_flood_overlay import validate_packet
                validate_packet(self.root)
            if path.name=='water_landcover_context.usda':
                from build_water_context import validate_water_context
                validate_water_context(self.root)
            def resolve(asset):
                if not asset:return asset
                target=Path(asset)
                target=target if target.is_absolute() else path.parent/target
                if not target.is_file():raise ValueError('Unavailable asset: '+asset+'; existing scene preserved')
                return str(target.resolve())
            UsdUtils.ModifyAssetPaths(candidate,resolve)
            _,_,unresolved=UsdUtils.ComputeAllDependencies(candidate.identifier)
            if unresolved:raise ValueError('Unresolved candidate assets; existing scene preserved')
            rows.append({'path':str(path),'before_disk_sha256':self.hashes.get(str(path)),'candidate_sha256':self.sha(path),'bytes':path.stat().st_size})
        self.plan={'before_snapshot':self.snapshot,'candidate_snapshot':snapshot,'layers':rows,'manual_and_scenarios_excluded':True}
        return self.plan

    def apply(self):
        from pxr import Sdf
        if self.plan is None:raise ValueError('Review local scene updates first')
        plan=self.plan
        if self.active_snapshot()!=plan['candidate_snapshot']:raise ValueError('Snapshot changed since review; review again')
        for row in plan['layers']:
            if self.sha(row['path'])!=row['candidate_sha256']:raise ValueError('Candidate changed since review; existing scene preserved')
        if not plan['layers']:return {**plan,'status':'no_local_changes'}
        before={};layers={}
        for row in plan['layers']:
            layer=Sdf.Layer.Find(row['path'].replace('\\','/'))
            if layer:
                if layer.dirty and self.owned_rollback.get(row['path'])!=hashlib.sha256(layer.ExportToString().encode()).hexdigest():raise ValueError('Unsaved layer changed after review')
                before[row['path']]=layer.ExportToString();layers[row['path']]=layer
        if not layers:raise ValueError('Changed optional files are not composed; integrate their validated layer before refreshing')
        if sum(len(text.encode()) for text in before.values())>256*1024*1024:raise ValueError('Recovery snapshot exceeds 256 MiB bound; current view preserved')
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=self.root/'data/processed/workspace_refresh';folder.mkdir(parents=True,exist_ok=True)
        receipt=folder/(stamp+'.json');payload={**plan,'previous_layer_text':before,'status':'prepared'}
        receipt.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        try:
            with Sdf.ChangeBlock():
                for layer in layers.values():
                    if not layer.Reload(True):raise RuntimeError('Layer reload failed')
            if self.active_snapshot()!=plan['candidate_snapshot'] or any(self.sha(row['path'])!=row['candidate_sha256'] for row in plan['layers']):raise ValueError('Source changed during refresh; previous view restored')
        except Exception:
            with Sdf.ChangeBlock():
                for key,text in before.items():layers[key].ImportFromString(text)
            self.owned_rollback={key:hashlib.sha256(text.encode()).hexdigest() for key,text in before.items()}
            raise
        after={key:hashlib.sha256(layer.ExportToString().encode()).hexdigest() for key,layer in layers.items()}
        self.previous={'before':before,'after':after,'plan':plan,'receipt':str(receipt)};self.snapshot=plan['candidate_snapshot']
        for row in plan['layers']:self.hashes[row['path']]=row['candidate_sha256']
        self.owned_rollback={};self.plan=None;payload['status']='applied_in_editor';receipt.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        return {**plan,'status':'applied_in_editor','recovery_receipt':str(receipt)}

    def undo(self):
        from pxr import Sdf
        if not self.previous:raise ValueError('No applied scene refresh to undo')
        previous=self.previous;layers={}
        for key,digest in previous['after'].items():
            layer=Sdf.Layer.Find(key.replace('\\','/'))
            if not layer or hashlib.sha256(layer.ExportToString().encode()).hexdigest()!=digest:raise ValueError('Scene changed since refresh; preserve edits and reopen the recovery receipt instead')
            layers[key]=layer
        with Sdf.ChangeBlock():
            for key,text in previous['before'].items():layers[key].ImportFromString(text)
        self.owned_rollback={key:hashlib.sha256(text.encode()).hexdigest() for key,text in previous['before'].items()}
        for row in previous['plan']['layers']:self.hashes[row['path']]=row['before_disk_sha256']
        self.snapshot=previous['plan']['before_snapshot'];self.previous=None;self.plan=None
        return {'status':'previous_view_restored_in_memory','source_files_and_api_snapshot_unchanged':True,'recovery_receipt':previous['receipt']}

    def recover_latest(self):
        """Recover the prior view from the last durable receipt after an app restart."""
        from pxr import Sdf
        candidates=sorted((self.root/'data/processed/workspace_refresh').glob('*.json'),reverse=True)
        if not candidates:raise ValueError('No saved scene-recovery receipt')
        path=candidates[0];receipt=json.loads(path.read_text(encoding='utf-8'));texts=receipt.get('previous_layer_text',{})
        allowed={str(p) for p in self.paths}
        if not texts or set(texts)-allowed:raise ValueError('Recovery receipt has no allowed generated-layer snapshot')
        layers={};current={}
        for key in texts:
            layer=Sdf.Layer.Find(key.replace('\\','/'))
            if not layer or layer.dirty:raise ValueError('Recovery would replace missing or unsaved generated content; current view preserved')
            layers[key]=layer;current[key]=layer.ExportToString()
        try:
            with Sdf.ChangeBlock():
                for key,text in texts.items():
                    if not layers[key].ImportFromString(text):raise ValueError('Invalid recovery layer')
        except Exception:
            with Sdf.ChangeBlock():
                for key,text in current.items():layers[key].ImportFromString(text)
            raise
        self.owned_rollback={key:hashlib.sha256(text.encode()).hexdigest() for key,text in texts.items()}
        for row in receipt['layers']:self.hashes[row['path']]=row['before_disk_sha256']
        self.snapshot=receipt['before_snapshot'];self.previous=None;self.plan=None
        return {'status':'previous_view_recovered_in_memory','source_files_and_api_snapshot_unchanged':True,'recovery_receipt':str(path)}


def government_preview(root,snapshot):
    """Only fixed public adapter reports and their prefiltered safe previews."""
    root=Path(root);result={}
    for label in ('FEMA effective NFHL','Historical water / land cover'):
        try:
            if label=='FEMA effective NFHL':
                from build_flood_overlay import validate_packet
                packet=validate_packet(root)
                dates={'acquisition_interval':'Unknown; effective panel dates are not acquisition dates',
                    'effective_panel_dates':sorted({f['properties'].get('effective_date_utc') for f in packet['tables']['effective_panels']['features'] if f['properties'].get('effective_date_utc')}),
                    'original_retrieval_times':sorted({r['retrieved_utc'] for r in packet.get('source_requests',[]) if r.get('retrieved_utc')}),
                    'preliminary_status':packet['preliminary_status']}
                preview={'publisher':packet['publisher'],'source_product':packet['source_product'],'source_url':packet['source_url'],'created_utc':packet['created_utc'],
                    'dates':dates,'field_dictionary':packet['field_dictionary'],'first_five_safe_rows':packet['first_five_safe_rows'],'coverage':packet['coverage'],'unresolved':packet['unresolved'],'limits':packet['limits']}
            else:
                from build_water_context import validate_water_context
                packet=validate_water_context(root)
                dates={name:{key:value.get(key,'Unknown') for key in ('publisher','url','acquisition_start','acquisition_end','effective_date','date_precision','item_modified_utc','data_edit_utc','request_retrieval_range_utc','vertical_datum','reuse_conditions')} for name,value in packet['sources'].items()}
                preview={'publisher':packet['publisher'],'source_product':'Historical water and land-cover reference context','source_url':packet['official_catalog'],'created_utc':packet['built_utc'],
                    'dates':dates,'field_dictionary':packet['field_dictionary'],'first_five_safe_rows':{name:[f['properties'] for f in table['features'][:5]] for name,table in packet['collections'].items()},
                    'coverage':packet['quality'],'unresolved':packet['unresolved'],'limits':[packet['accepted_context_policy'],packet['ground_intersection']['decision'],packet['shoreline_alignment']['acceptance']]}
            if packet.get('source_snapshot')!=snapshot:raise ValueError('Stale snapshot; rebuild this adapter')
            result[label]=preview
            result[label]['status']='Current snapshot and source hashes checked; dates are not interchangeable'
        except (OSError,ValueError,TypeError,KeyError) as error:result[label]={'status':'Unavailable / not current','reason':str(error)}
    return json.dumps(result,indent=2,ensure_ascii=False)
