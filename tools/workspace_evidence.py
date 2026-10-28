"""Testable editor evidence and session-display helpers; no Kit/UI imports."""
from pathlib import Path

UNKNOWN='Unknown'

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
    return bool(root.realPath) and Path(root.realPath).resolve() in {Path(p).resolve() for p in scene_paths}

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

def inspector_text(prim,project_refresh=None,registry=None):
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
    rows=[('Selected',evidence['selected_path']),
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
