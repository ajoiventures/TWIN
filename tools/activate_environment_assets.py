"""Validate rendered environment assets; activate only with explicit --apply.

Root layer metadata/camera/render opinions are retained byte-for-byte semantically.
Source assets and manual edits are never rewritten. No acquisition or Kit launch.
"""
from pathlib import Path
import os,sys,json,hashlib,datetime,argparse,uuid,re
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Sdf


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def relative(root,path):return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
def local(root,path):
    path=(Path(root)/path).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('Dependency escapes project')
    return path


def compare_placements(before,after):
    for name in ('positions','orientations','scales','protoIndices','invisibleIds','ids'):
        path='/World/Trees'
        if str(before.GetPrimAtPath(path).GetAttribute(name).Get())!=str(after.GetPrimAtPath(path).GetAttribute(name).Get()):
            raise ValueError('Tree instance array changed: '+name)
    parent=before.GetPrimAtPath('/World/ParkedVehicles');count=0
    if parent:
        for car in parent.GetChildren():
            path=car.GetPath().AppendChild('DetailedSedan');a=before.GetPrimAtPath(path);b=after.GetPrimAtPath(path)
            if not a:continue
            if not b:raise ValueError('Vehicle missing in candidate')
            if UsdGeom.Xformable(a).ComputeLocalToWorldTransform(Usd.TimeCode.Default())!=UsdGeom.Xformable(b).ComputeLocalToWorldTransform(Usd.TimeCode.Default()):raise ValueError('Vehicle transform changed: '+str(path))
            count+=1
    return {'tree_instances':len(UsdGeom.PointInstancer(before.GetPrimAtPath('/World/Trees')).GetPositionsAttr().Get()),'cars':count}


def verify_render(root,manifest_path):
    root=Path(root);data=json.loads(Path(manifest_path).read_text())
    if data.get('source_stage_saved') is not False or data.get('error') or data.get('status') in ('failed','error'):raise ValueError('Capture did not finish safely')
    image=local(root,data['image'])
    if not image.is_file() or sha(image)!=data.get('image_sha256'):raise ValueError('Capture image missing or changed')
    scene=local(root,data['scene'])
    if not scene.is_file() or sha(scene)!=data.get('scene_sha256'):raise ValueError('Comparison stage changed since capture')
    return data


def validate(root=ROOT):
    root=Path(root);scene=root/'scene';assembly=scene/'college_park_connected.usda';proposal=scene/'asset_upgrade_proposal.usda'
    active=json.loads((root/'data/processed/active.json').read_text())
    captures=[]
    for path in sorted((root/'data/renders').glob('*/manifest.json'),reverse=True):
        try:data=json.loads(path.read_text())
        except (OSError,ValueError):continue
        if str(data.get('camera',''))=='/World/CompareCamera':captures.append(path)
    if not captures:raise ValueError('No actual comparison capture manifest')
    capture_path=captures[0];capture=verify_render(root,capture_path)
    if capture.get('source_snapshot')!=active['snapshot']:raise ValueError('Comparison snapshot is stale')
    assets={};evidence={};evidence_hashes={relative(root,root/'data/processed/active.json'):sha(root/'data/processed/active.json'),
        relative(root,capture_path):sha(capture_path),relative(root,local(root,capture['scene'])):sha(local(root,capture['scene'])),
        relative(root,local(root,capture['image'])):sha(local(root,capture['image']))}
    for name in ('oak_a','oak_b','palm','sedan'):
        key='assets/generated/environment_v2/'+name+'.usdc';path=root/key;digest=sha(path)
        render=capture;render_path=capture_path
        if key not in capture.get('layer_hashes',{}):
            # The side-by-side comparison shows oak_a; oak_b must also have an actual capture receipt.
            matches=[]
            for p in sorted((root/'data/renders').glob('*/manifest.json'),reverse=True):
                try:d=json.loads(p.read_text())
                except (OSError,ValueError):continue
                if key in d.get('layer_hashes',{}) and d.get('source_snapshot')==active['snapshot']:matches.append((p,d));break
            if not matches:raise ValueError('Asset lacks rendered hash evidence: '+name)
            render_path,render=matches[0]
            image=local(root,render['image'])
            if render.get('source_stage_saved') is not False or not image.is_file() or sha(image)!=render.get('image_sha256'):raise ValueError('Supplemental asset capture is invalid')
        if render['layer_hashes'].get(key)!=digest:raise ValueError('Rendered asset hash changed: '+name)
        assets[key]=digest;evidence[name]=relative(root,render_path)
        evidence_hashes[relative(root,render_path)]=sha(render_path)
        evidence_hashes[relative(root,local(root,render['image']))]=sha(local(root,render['image']))
    layer=Sdf.Layer.FindOrOpen(str(proposal))
    if not layer:raise ValueError('Missing proposal')
    # Validate every proposal reference belongs to the already rendered revision.
    references=[]
    def inspect(path):
        spec=layer.GetPrimAtPath(path)
        if not spec:return
        text=str(path)
        if not (text in ('/World','/World/Trees','/World/Trees/Detailed','/World/ParkedVehicles') or re.fullmatch(r'/World/Trees/Detailed/Tree_[0-6]',text) or re.fullmatch(r'/World/ParkedVehicles/Car_\d+(/DetailedSedan)?',text)):
            raise ValueError('Proposal contains an unrelated prim: '+text)
        for prop in spec.properties:
            if not (text=='/World/Trees' and prop.name=='prototypes' and isinstance(prop,Sdf.RelationshipSpec)):
                raise ValueError('Proposal contains an unexpected property: '+str(prop.path))
        for ref in spec.referenceList.GetAppliedItems():
            target=(scene/ref.assetPath).resolve();key=relative(root,target)
            if key not in assets or str(ref.primPath)!='/Asset':raise ValueError('Unexpected proposal reference: '+str(ref))
            references.append(key)
        for child in spec.nameChildren:inspect(child.path)
    for prim in layer.rootPrims:inspect(prim.path)
    if set(references)!=set(assets):raise ValueError('Proposal does not reference all validated assets')
    source=Usd.Stage.Open(str(assembly))
    # Build our own composition rather than trusting the supplied workview ordering.
    temp=Sdf.Layer.CreateAnonymous();temp.subLayerPaths=[str(proposal),str(assembly)];candidate=Usd.Stage.Open(temp)
    placement=compare_placements(source,candidate)
    textures={}
    for key in assets:
        stage=Usd.Stage.Open(str(root/key))
        for prim in stage.Traverse():
            attr=prim.GetAttribute('inputs:file')
            if attr and attr.Get():
                asset=attr.Get()
                if not asset.resolvedPath:raise ValueError('Unresolved asset texture')
                path=Path(asset.resolvedPath);textures[relative(root,path)]=sha(path)
    preserved={relative(root,Path(l.realPath)):sha(l.realPath) for l in source.GetUsedLayers() if l.realPath}
    return {'status':'validated_not_activated','source_snapshot':active['snapshot'],'root_sha256':sha(assembly),
        'proposal_sha256':sha(proposal),'comparison_manifest':relative(root,capture_path),'comparison_manifest_sha256':sha(capture_path),
        'render_evidence_by_asset':evidence,'validation_evidence_hashes':evidence_hashes,'asset_hashes':assets,'texture_hashes':textures,'preserved_source_hashes':preserved,**placement,
        'quality':'Original procedural appearance; existing placement illustrative and unverified; not surveyed species or parking accuracy',
        'limits':['Capture manifests bind USD asset hashes; PNG texture hashes are recorded at activation validation, not retrospectively certified by the older capture manifest.',
            'File hashes are rechecked immediately before atomic root replacement; unrelated programs do not participate in the activation lock.']}


def guarded_replace(path,raw,expected):
    """Atomic replacement guarded against edits since validation."""
    path=Path(path);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_bytes(raw)
        if sha(path)!=expected:raise ValueError('Root changed concurrently; activation refused')
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()


def validated_environment_layer(root=ROOT):
    """Durable pipeline opt-in only after a successful recorded activation."""
    root=Path(root);receipt=root/'data/processed/environment_activation.json'
    if not receipt.exists():return None
    data=json.loads(receipt.read_text())
    if data.get('status')!='activated':raise ValueError('Environment activation receipt is incomplete')
    for key,digest in {**data['asset_hashes'],**data['texture_hashes'],data['activated_layer']:data['activated_layer_sha256']}.items():
        path=local(root,key)
        if not path.is_file() or sha(path)!=digest:raise ValueError('Activated environment dependency changed: '+key)
    return Path(data['activated_layer']).name


def activate(root=ROOT,apply=False):
    root=Path(root);report=validate(root)
    if not apply:return report
    lock=root/'scene/.environment_activation.lock'
    descriptor=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        assembly=root/'scene/college_park_connected.usda';proposal=root/'scene/asset_upgrade_proposal.usda';target=root/'scene/asset_upgrade_environment_v2.usda'
        for key,digest in {**report['preserved_source_hashes'],**report['asset_hashes'],**report['texture_hashes'],**report.get('validation_evidence_hashes',{}),'scene/asset_upgrade_proposal.usda':report['proposal_sha256']}.items():
            if sha(local(root,key))!=digest:raise ValueError('Source changed during activation: '+key)
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup=root/'data/backups'/('environment_'+stamp);backup.mkdir(parents=True)
        (backup/'college_park_connected.usda').write_bytes(assembly.read_bytes())
        if target.exists():(backup/target.name).write_bytes(target.read_bytes())
        receipt=root/'data/processed/environment_activation.json'
        if receipt.exists():(backup/receipt.name).write_bytes(receipt.read_bytes())
        edited=Sdf.Layer.CreateAnonymous();edited.ImportFromString(assembly.read_text(encoding='utf-8'))
        if target.name in edited.subLayerPaths and sha(target)!=report['proposal_sha256']:
            raise ValueError('A different environment revision is already active; refuse in-place asset layer replacement')
        layers=[name for name in edited.subLayerPaths if name!=target.name]
        after=max((i for i,name in enumerate(layers) if name in ('map_extent_guard.usda','manual_edits.usda')),default=-1)+1
        layers.insert(after,target.name);edited.subLayerPaths=layers
        if not target.exists() or sha(target)!=report['proposal_sha256']:target.write_bytes(proposal.read_bytes())
        # Preserve all original root specs and metadata; change only sublayer ordering.
        guarded_replace(assembly,edited.ExportToString().encode('utf-8'),report['root_sha256'])
        report.update({'status':'activated','activated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'backup':relative(root,backup),
            'activated_layer':relative(root,target),'activated_layer_sha256':sha(target),'root_after_sha256':sha(assembly)})
        temporary=receipt.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(report,indent=2));os.replace(temporary,receipt)
        except Exception:
            # Do not leave an active root without its durable pipeline receipt.
            guarded_replace(assembly,(backup/'college_park_connected.usda').read_bytes(),report['root_after_sha256'])
            if temporary.exists():temporary.unlink()
            raise
        return report
    finally:
        os.close(descriptor);lock.unlink()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    report=activate(apply=args.apply);print(json.dumps(report,indent=2))
