"""Compose inactive terrain candidates and audit shared sources and coverage.

Writes a fresh ignored review folder only. Never changes the active root,
snapshot, manual layer, accepted receipts, editor or source data.
"""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Usd, UsdGeom, Sdf, Gf


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_path(relative,root=ROOT):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or nonlocal candidate input: '+str(relative))
    return path


def read_candidate(path,snapshot,root=ROOT):
    path=local_path(path,root);packet=json.loads(path.read_text(encoding='utf-8'))
    if packet.get('source_snapshot')!=snapshot:raise ValueError('Candidate snapshot mismatch: '+str(path))
    dependencies=packet.get('dependencies')
    if not isinstance(dependencies,dict) or not dependencies:raise ValueError('Candidate source hashes required')
    for relative,digest in dependencies.items():
        if sha(local_path(relative,root))!=digest:raise ValueError('Stale candidate dependency: '+relative)
    layer_path=local_path(packet['layer'],root)
    if sha(layer_path)!=packet['layer_sha256']:raise ValueError('Candidate layer changed: '+str(layer_path))
    layer=Sdf.Layer.FindOrOpen(str(layer_path))
    if not layer or layer.subLayerPaths:raise ValueError('Candidate must be one standalone override layer')
    if layer.pseudoRoot.GetInfo('upAxis')!='Z' or layer.pseudoRoot.GetInfo('metersPerUnit')!=1:
        raise ValueError('Candidate must explicitly use Z-up/meters')
    properties=set();metadata={}
    def inspect(path):
        prim=layer.GetPrimAtPath(path)
        if prim and path!=Sdf.Path.absoluteRootPath:
            if str(path).startswith(('/World/Cameras','/World/Lighting')) or prim.typeName=='Camera' or prim.typeName.endswith('Light'):
                raise ValueError('Candidate authors presentation prim: '+str(path))
            keys=set(prim.ListInfoKeys())
            if keys&{'references','payload','inheritPaths','specializes'}:
                raise ValueError('Candidate composition arcs forbidden: '+str(path))
            if keys&{'active','instanceable','variantSelection','variantSetNames'}:
                raise ValueError('Candidate changes source activation/instancing/variants: '+str(path))
            for key in keys-{'specifier'}:metadata[(str(path),key)]=str(prim.GetInfo(key))
        if layer.GetPropertyAtPath(path):
            if str(path).startswith(('/World/Cameras','/World/Lighting')):
                raise ValueError('Candidate changes presentation source: '+str(path))
            properties.add(str(path))
    layer.Traverse(Sdf.Path.absoluteRootPath,inspect)
    dispositions=[]
    for status in ('applied','held','unchanged'):
        for row in packet.get(status,[]):
            if not isinstance(row,dict) or not str(row.get('path','')).startswith('/World/'):
                raise ValueError('Candidate disposition requires exact source path')
            dispositions.append({**row,'status':status})
    if not dispositions:raise ValueError('Candidate must account for applied/held source paths')
    return packet,layer_path,properties,metadata,dispositions


def review_cameras(stage,root):
    """Add fixed diagnostic cameras to a review stage, never the active root."""
    for name,eye,target in [('TerrainEdgewaterNorth',(-44,-65,8),(-49,240,3)),
                            ('TerrainEdgewaterSouth',(-47,140,8),(-42,-160,3))]:
        camera=UsdGeom.Camera.Define(stage,'/World/Cameras/'+name)
        camera.CreateFocalLengthAttr(28);camera.CreateHorizontalApertureAttr(36)
        camera.CreateVerticalApertureAttr(20.25);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,6000))
        camera.CreateFStopAttr(0)
        UsdGeom.Xformable(camera).AddTransformOp().Set(Gf.Matrix4d().SetLookAt(
            Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
    camera_source=local_path('data/diagnostics/church_se_wing_continuous_20261102_b/review.usda',root)
    source=Sdf.Layer.FindOrOpen(str(camera_source));path='/World/Cameras/ChurchSoutheastWingContinuousRoof'
    if not Sdf.CopySpec(source,path,stage.GetRootLayer(),path):raise ValueError('Unable to copy fixed church review camera')
    return camera_source


def compose(manifests,output,root=ROOT,baseline_only=False):
    helper=Path(__file__);producer_bytes=helper.read_bytes();producer_sha=hashlib.sha256(producer_bytes).hexdigest()
    root=Path(root).resolve();output=(root/output).resolve()
    if output.exists() or not output.is_relative_to((root/'data/diagnostics').resolve()):
        raise ValueError('Use a fresh ignored review directory')
    snapshot=json.loads((root/'data/processed/active.json').read_text())['snapshot']
    baseline=root/'scene/college_park_connected.usda';before=sha(baseline)
    dependencies={helper.relative_to(root).as_posix():producer_sha};layers=[];properties=set();metadata={};dispositions=[]
    if baseline_only:
        if manifests:raise ValueError('Baseline review cannot contain candidate manifests')
        dependencies.update({'scene/college_park_connected.usda':before,
            'data/processed/active.json':sha(root/'data/processed/active.json')})
        dispositions=[{'path':'/World','status':'unchanged','policy':'Unmodified baseline source composition'}]
    elif not manifests:raise ValueError('Candidate manifests required')
    for manifest in manifests:
        packet,path,authored,prim_info,rows=read_candidate(manifest,snapshot,root)
        overlap=properties&authored
        if overlap:raise ValueError('Candidate authored-property conflict: '+', '.join(sorted(overlap)[:8]))
        for key,value in prim_info.items():
            if key in metadata and metadata[key]!=value:raise ValueError('Candidate prim metadata conflict: '+str(key))
            metadata[key]=value
        properties.update(authored);layers.append(path);dispositions.extend(rows)
        for relative,digest in packet['dependencies'].items():
            if relative in dependencies and dependencies[relative]!=digest:
                raise ValueError('Builders used different source versions: '+relative)
            dependencies[relative]=digest
        for path in (local_path(manifest,root),path):dependencies[path.relative_to(root).as_posix()]=sha(path)
    if dependencies.get('scene/college_park_connected.usda')!=before:
        raise ValueError('All builders must bind the exact current active root')
    source=Usd.Stage.Open(str(baseline));candidate=Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(candidate,'Z');UsdGeom.SetStageMetersPerUnit(candidate,1)
    candidate.GetRootLayer().subLayerPaths=[str(p) for p in layers]+[str(baseline)]
    if candidate.GetCompositionErrors():raise ValueError('Candidate USD composition failed: '+str(candidate.GetCompositionErrors()))
    anchors=sorted({str(Sdf.Path(p).GetPrimPath()) for p in properties if Sdf.Path(p).name.startswith('xformOp:')})
    for index,path in enumerate(anchors):
        if any(other.startswith(path+'/') for other in anchors[index+1:]):
            raise ValueError('Nested newly authored transforms require a single family anchor: '+path)
    covered={d['path'] for d in dispositions};missing=[];binding_changes=[];identity_changes=[]
    source_visible=0
    def coverage(path):return any(path==p or path.startswith(p+'/') for p in covered)
    def preserves(original,current):
        return all(k in current and (preserves(v,current[k]) if isinstance(v,dict) and isinstance(current[k],dict) else v==current[k]) for k,v in original.items())
    for prim in Usd.PrimRange(source.GetPseudoRoot(),Usd.TraverseInstanceProxies()):
        target=candidate.GetPrimAtPath(prim.GetPath());path=str(prim.GetPath())
        if not target:identity_changes.append(path+': missing prim');continue
        if prim.GetTypeName()!=target.GetTypeName() or prim.IsActive()!=target.IsActive():
            identity_changes.append(path+': original type or active state changed')
        if not preserves(prim.GetCustomData(),target.GetCustomData()):identity_changes.append(path+': original customData changed')
        for relationship in prim.GetRelationships():
            if 'material:binding' in relationship.GetName():
                changed=target.GetRelationship(relationship.GetName())
                if not changed or relationship.GetTargets()!=changed.GetTargets():binding_changes.append(path)
        if prim.IsA(UsdGeom.Boundable) and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':
            source_visible+=1
            if not coverage(path):missing.append(path)
    # Missing handling is deliberately a failed acceptance result, rather than
    # silently claiming an all-object scene from a successful USD composition.
    camera_source=review_cameras(candidate,root)
    dependencies[camera_source.relative_to(root).as_posix()]=sha(camera_source)
    report={'schema':'twin.terrain-composed-review/1','source_snapshot':snapshot,
        'kind':'fixed_camera_baseline' if baseline_only else 'coordinated_candidate',
        'activated':False,'source_visible_boundables':source_visible,'authored_properties':len(properties),
        'unaccounted_visible_paths':missing,'changed_original_identity_paths':identity_changes,
        'changed_material_binding_paths':sorted(set(binding_changes)),
        'dispositions':dispositions,'dependencies':dependencies,
        'passed_composition_and_source_identity':not(missing or identity_changes or binding_changes),
        'ready_for_activation':False,
        'limits':['Composition/coverage check only; contact, seams, datum handling and actual images need independent review',
            'Held bridge/grade/shoreline/geometry cases remain unresolved; no current/surveyed/full-ticket acceptance']}
    for relative,digest in dependencies.items():
        if sha(local_path(relative,root))!=digest:raise ValueError('Source changed during composition: '+relative)
    if sha(baseline)!=before:raise ValueError('Active root changed during review')
    output.mkdir(parents=True)
    (output/'captured_helper.py').write_bytes(producer_bytes)
    layer=output/'review.usda';candidate.GetRootLayer().Export(str(layer))
    report.update(review_layer=layer.relative_to(root).as_posix(),review_layer_sha256=sha(layer),
        helper_sha256=sha(output/'captured_helper.py'))
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return {k:v for k,v in report.items() if k not in ('dependencies','dispositions')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',action='append',default=[])
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--output',required=True);args=parser.parse_args()
    print(json.dumps(compose(args.manifest,args.output,baseline_only=args.baseline),indent=2))
