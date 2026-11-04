"""Activate independently reviewed historical geometry without inventing tax links."""
from pathlib import Path
import argparse,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Sdf,Usd,UsdGeom,UsdUtils
from data_pipeline import atomic_json,now
from mesh_topology import closed_shell_report

def validated_post_office(root=ROOT):
    """Guard the separately reviewed historical site; never replace the office."""
    root=Path(root).resolve();receipt=root/'data/processed/post_office_historical_activation.json'
    layer=root/'scene/post_office_historical.usda'
    if not receipt.exists() and not layer.exists():return None
    if not receipt.is_file() or not layer.is_file():raise ValueError('Post-office activation is incomplete')
    packet=json.loads(receipt.read_text(encoding='utf-8'))
    if packet.get('schema')!='twin.post-office-historical-activation/1':raise ValueError('Unsupported post-office receipt schema')
    active=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))
    if packet['source_snapshot']!=active['snapshot']:raise ValueError('Post-office source snapshot is stale')
    if packet['layer']!='scene/post_office_historical.usda' or packet['site']['site_id']!='college_park_post_office':raise ValueError('Unexpected historical site identity')
    required={'scene/landmark_building_proposal.usda','data/heights/landmarks/proposal_manifest.json',
        'data/heights/landmarks/college_park_post_office/evidence.json','data/heights/landmarks/college_park_post_office/points.npz'}
    dependencies=packet.get('dependencies')
    if not isinstance(dependencies,dict) or not required.issubset(dependencies):raise ValueError('Post-office required source dependencies missing')
    if hashlib.sha256(layer.read_bytes()).hexdigest()!=packet['layer_sha256']:raise ValueError('Post-office layer changed; re-review required')
    for relative,digest in dependencies.items():
        dependency=(root/relative).resolve()
        if not dependency.is_relative_to(root) or hashlib.sha256(dependency.read_bytes()).hexdigest()!=digest:raise ValueError('Post-office source dependency changed')
    manifest=json.loads((root/'data/heights/landmarks/proposal_manifest.json').read_text(encoding='utf-8'))
    canonical=next((s for s in manifest['sites'] if s['site_id']=='college_park_post_office'),None)
    if canonical is None or packet['site']!=canonical or canonical.get('parcel_id')!='292223149200010' or canonical.get('prim_path')!='/World/Landmarks/CollegeParkPostOffice' or canonical.get('source_snapshot')!=active['snapshot']:
        raise ValueError('Post-office identity differs from source manifest')
    if dependencies['scene/landmark_building_proposal.usda']!=manifest['layer_sha256'] or dependencies['data/heights/landmarks/college_park_post_office/points.npz']!=canonical['cloud_sha256'] or dependencies['data/heights/landmarks/college_park_post_office/evidence.json']!=canonical['evidence_sha256']:
        raise ValueError('Post-office canonical source hashes differ')
    if packet.get('raw_property_links_promoted') is not False or packet.get('accepted_current_geometry') is not False:
        raise ValueError('Historical post-office receipt cannot promote current geometry or tax links')
    return packet


def activate(root=ROOT,site_ids=None):
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    manifest_path=root/'data/heights/landmarks/proposal_manifest.json';manifest=read(manifest_path);active=read(root/'data/processed/active.json')
    if manifest['source_snapshot']!=active['snapshot']:raise ValueError('Stale landmark proposal')
    proposal=(root/'scene/landmark_building_proposal.usda').resolve()
    if Path(manifest['layer']).resolve()!=proposal or hashlib.sha256(proposal.read_bytes()).hexdigest()!=manifest['layer_sha256']:raise ValueError('Proposal layer changed')
    selected=[site for site in manifest['sites'] if site_ids is None or site['site_id'] in site_ids]
    if not selected or (site_ids and set(site_ids)-{site['site_id'] for site in selected}):raise ValueError('Unknown landmark selection')
    if (root/'data/processed/post_office_historical_activation.json').exists() and any(s['site_id']=='college_park_post_office' for s in selected):
        raise ValueError('Post-office form has a separate reviewed layer; preserve it instead of overwriting the office assembly')
    dependencies=[manifest_path,proposal];source_stage=Usd.Stage.Open(str(proposal))
    for site in selected:
        for component in site['components']:
            mesh=UsdGeom.Mesh(source_stage.GetPrimAtPath(component['prim_path']))
            topology=closed_shell_report(mesh.GetPointsAttr().Get(),mesh.GetFaceVertexCountsAttr().Get(),mesh.GetFaceVertexIndicesAttr().Get())
            if not topology['passed_closed_shell']:raise ValueError('Unaccepted open/nonmanifold landmark shell: '+component['prim_path']+' '+str(topology))
        folder=root/'data/heights/landmarks'/site['site_id'];cloud=folder/'points.npz';evidence=folder/'evidence.json'
        if hashlib.sha256(cloud.read_bytes()).hexdigest()!=site['cloud_sha256'] or hashlib.sha256(evidence.read_bytes()).hexdigest()!=site['evidence_sha256']:raise ValueError('Landmark source changed')
        dependencies.extend([cloud,evidence])
    destination=root/'scene/landmark_buildings.usda';layers=[proposal]
    if any(site['site_id']=='andersen_office_1615' for site in selected):
        names=['office_brick_material_proposal.usda','office_frontage_proposal.usda','office_architectural_roof_proposal.usda','landmark_appearance_proposal.usda']
        layers=[root/'scene'/name for name in names]+layers
        for derived in layers[:-1]:
            evidence=Sdf.Layer.FindOrOpen(str(derived)).customLayerData
            if evidence.get('geometryProposalSha256')!=manifest['layer_sha256']:raise ValueError('Stale derived geometry '+derived.name)
        front=Sdf.Layer.FindOrOpen(str(layers[1])).customLayerData
        if front.get('architecturalRoofSha256')!=hashlib.sha256(layers[2].read_bytes()).hexdigest():raise ValueError('Stale office frontage')
        material=Sdf.Layer.FindOrOpen(str(layers[0])).customLayerData
        if material.get('frontageSha256')!=hashlib.sha256(layers[1].read_bytes()).hexdigest():raise ValueError('Stale office material')
        for name,digest in json.loads(material['textureHashesJson']).items():
            texture=root/'assets/generated/office_brick'/name
            if hashlib.sha256(texture.read_bytes()).hexdigest()!=digest:raise ValueError('Office material changed')
            dependencies.append(texture)
        dependencies.extend(layers[:-1])
    combined=Usd.Stage.CreateInMemory();combined.GetRootLayer().subLayerPaths=[str(path) for path in layers]
    layer=combined.Flatten();stage=Usd.Stage.Open(layer)
    for site in manifest['sites']:
        if site not in selected:stage.RemovePrim(site['prim_path'])
    layer.customLayerData={**layer.customLayerData,'activation':'display_historical_draft_current_shape_unverified'}
    bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'])
    for site in selected:
        prim=stage.GetPrimAtPath(site['prim_path'])
        if not prim:raise ValueError('Missing landmark root')
        prim.SetCustomDataByKey('classification','Historical landmark reconstruction')
        prim.SetCustomDataByKey('heightMeters',site['main_roof_height_m'])
        actual_max=float(bounds.ComputeWorldBound(prim).ComputeAlignedRange().GetMax()[2])-.1
        site['source_proposal_maximum_rendered_height_m']=site['maximum_rendered_height_m']
        site['maximum_rendered_height_m']=actual_max
        for component in site['components']:
            current=UsdGeom.Mesh(stage.GetPrimAtPath(component['prim_path']))
            if not closed_shell_report(current.GetPointsAttr().Get(),current.GetFaceVertexCountsAttr().Get(),current.GetFaceVertexIndicesAttr().Get())['passed_closed_shell']:raise ValueError('Composed landmark body is open')
            component['source_proposal_faces']=component.get('faces')
            component['faces']=len(current.GetFaceVertexCountsAttr().Get())
            component['vertices']=len(current.GetPointsAttr().Get())
        prim.SetCustomDataByKey('maximumRenderedHeightMeters',actual_max)
        prim.SetCustomDataByKey('sourceSnapshot',active['snapshot'])
        prim.SetCustomDataByKey('source','USGS 2018-2019 LiDAR; OCPA property context; photo-interpreted architectural detail')
        prim.SetCustomDataByKey('sourceDate','2018-12-04/2019-04-12 acquisition interval; local flight day and broker photo date unknown')
        prim.SetCustomDataByKey('quality','historical_lidar_derived_current_geometry_unverified')
    temporary=destination.with_name(destination.stem+'.tmp.usda');layer.Export(str(temporary));os.replace(temporary,destination)
    report={'source_snapshot':active['snapshot'],'activated_utc':now(),'layer':'scene/landmark_buildings.usda','layer_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'dependencies':{str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},'sites':selected,'raw_property_links_promoted':False,'accepted_current_geometry':False,'limitations':manifest['limitations']+['Office roof block transitions, dormer and frontage proportions are photo-interpreted, not measured architectural dimensions.','Maximum rendered height includes source-supported chimneys; it is not an extra occupied floor.','Activated for historical draft display; full ticket and conference visual acceptance remain pending.']}
    atomic_json(root/'data/heights/landmarks/activation.json',report);print('Activated historical landmark layer; current-condition and façade acceptance remain open')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--site-id',action='append');args=parser.parse_args();activate(site_ids=args.site_id)
