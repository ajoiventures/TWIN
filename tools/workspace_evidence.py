"""Testable editor evidence and session-display helpers; no Kit/UI imports."""
from pathlib import Path

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
    if not root.anonymous or root.dirty or session.dirty or root.customLayerData:return False
    from pxr import UsdGeom,UsdLux
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Camera) or prim.HasAPI(UsdLux.LightAPI):continue
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
    official=d.get('official',{});height=d.get('height',{});twin=d.get('twin',{})
    def pick(*values):return next((str(x) for x in values if x not in (None,'')),UNKNOWN)
    snapshot=pick(twin.get('sourceSnapshot'),height.get('source_snapshot'),official.get('snapshot'),d.get('sourceSnapshot'))
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
          ('Source',pick(official.get('source'),d.get('source'))),
          ('Source object IDs',pick(d.get('sourceObjectIds'),official.get('source_object_id'))),
          ('Height (m)',pick(height.get('height_m'),d.get('heightMeters'))),
          ('Height method',pick(height.get('method'))),
          ('Height/source notes',pick(height.get('review_notes'),d.get('review_notes'))),
          ('Quality',pick(height.get('quality'),twin.get('quality'),d.get('quality'),official.get('geometry_quality'))),
          ('Snapshot',snapshot),
          ('Source acquisition date',acquisition),
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
        ('Rear parking samples','/World/RearParkingSamples'),('Scenario','/World/Scenario'),('Scenarios','/World/Scenarios')]
    return [(label,path) for label,path in candidates if stage and stage.GetPrimAtPath(path)]
