"""Prepare an inactive, photo-interpreted detail delta above the office draft.

Inputs are the existing frontage/roof review and address-specific broker photos.
Outputs go to a new directory; no source scene, active layer or image is changed.
Dimensions are interpreted, not measured. See docs/OFFICE_FRONTAGE_DETAIL.md.
"""
from pathlib import Path
import argparse, hashlib, json, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Gf,Sdf,Usd,UsdGeom,UsdShade

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def appearance_metadata(root=ROOT):
    """Photo evidence identity only; never a parcel/building or currentness link."""
    root=Path(root)
    evidence=json.loads((root/'data/heights/landmarks/office_architectural_roof.json').read_text())
    snapshot=evidence.get('source_snapshot')
    if not isinstance(snapshot,str) or not snapshot:
        raise ValueError('Office source manifest lacks snapshot provenance')
    reference=evidence.get('photo_reference',{})
    url=reference.get('url')
    if not isinstance(url,str) or not url.startswith('https://www.bbdre.com/'):
        raise ValueError('Office photo reference must be reconciled before use')
    context={'quality':'illustrative_photo_interpreted','publisher':'BBDRE broker publication',
        'sourceURL':url,'sourceSnapshot':snapshot,'acquisitionStart':'unknown',
        'acquisitionEnd':'unknown','effectiveDate':'unknown','retrievedUTC':'unknown',
        'photoCaptureDate':'unknown',
        'method':'Qualitative visible architectural detail interpretation; dimensions and placement estimated, not measured/current/as-built'}
    return {'quality':'illustrative_photo_interpreted',
        'appearanceId':'appearance:1615-edgewater:frontage-detail:v1',
        'siteAddress':'1615 Edgewater Dr','sourceSnapshot':snapshot,
        'sourceURL':url,'publisher':context['publisher'],'photoCaptureDate':'unknown',
        'measuredDimensions':False,'physicalIdentityAccepted':False,
        'currentConditionAccepted':False,'sourceContext':context}

def validated_active_detail(root=ROOT):
    """Retain only the accepted, compatible appearance layer on scene rebuild."""
    root=Path(root);receipt=root/'data/processed/office_frontage_detail_activation.json'
    layer=root/'scene/office_frontage_detail.usda'
    if not receipt.exists() and not layer.exists():return None
    if not receipt.is_file() or not layer.is_file():raise ValueError('Office detail activation is incomplete')
    evidence=json.loads(receipt.read_text())
    active=json.loads((root/'data/processed/active.json').read_text())
    if evidence['source_snapshot']!=active['snapshot']:raise ValueError('Office detail snapshot changed; reconcile before use')
    if sha(layer)!=evidence['layer_sha256']:raise ValueError('Office detail layer changed; re-review before use')
    if sha(root/'scene/landmark_buildings.usda')!=evidence['base_layer_sha256']:raise ValueError('Office base changed; reconcile detail placement before use')
    return layer.name

def build(output,root=ROOT):
    output=Path(output).resolve()
    if not output.is_relative_to(root/'data/diagnostics') or output.exists():
        raise ValueError('Use a new directory inside data/diagnostics; previous work is preserved')
    review=root/'scene/office_frontage_review.usda'
    source=Usd.Stage.Open(str(review))
    if not source or source.GetCompositionErrors():raise ValueError('Office review composition is unavailable')
    hashes={str(Path(l.realPath).relative_to(root)):sha(Path(l.realPath)) for l in source.GetUsedLayers() if l.realPath}
    evidence_path=root/'data/heights/landmarks/office_architectural_roof.json'
    hashes[str(evidence_path.relative_to(root))]=sha(evidence_path)
    photos={f'data/imagery/landmark_reference/1615_exterior_page_{n}.png':sha(root/f'data/imagery/landmark_reference/1615_exterior_page_{n}.png') for n in (3,4,9)}
    skin=UsdGeom.Mesh(source.GetPrimAtPath('/World/OfficeFrontageProposal/BrickFrontSkin'))
    if not skin:raise ValueError('Office public frontage missing')
    points=skin.GetPointsAttr().Get();ids=skin.GetFaceVertexIndicesAttr().Get()
    walls=[];offset=0
    for count in skin.GetFaceVertexCountsAttr().Get():
        face=[points[i] for i in ids[offset:offset+count]];offset+=count
        if max(v[1] for v in face)-min(v[1] for v in face)>.2:walls.append(face)
    y0=min(v[1] for f in walls for v in f);y1=max(v[1] for f in walls for v in f)
    center=(y0+y1)/2
    def wall_x(y):
        candidates=[sum(v[0] for v in f)/len(f) for f in walls if min(v[1] for v in f)<=y<=max(v[1] for v in f)]
        if not candidates:raise ValueError('Detail lies outside frontage')
        return min(candidates)
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    base='/World/OfficeFrontageDetail'
    prim=UsdGeom.Xform.Define(stage,base).GetPrim()
    prim.SetCustomData({'classification':'Photo-interpreted architectural detail proposal','siteAddress':'1615 Edgewater Dr','photoCaptureDate':'Unknown','measuredDimensions':False,'active':False})
    metadata=appearance_metadata(root)
    for key,value in metadata.items():prim.SetCustomDataByKey(key,value)
    mat=UsdShade.Material.Define(stage,base+'/Materials/Trim');shader=UsdShade.Shader.Define(stage,mat.GetPath().AppendChild('Surface'))
    shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.72,.73,.69));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.68)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    def bind(obj):UsdShade.MaterialBindingAPI.Apply(obj.GetPrim()).Bind(mat)
    def box(name,center,size):
        obj=UsdGeom.Cube.Define(stage,base+'/'+name);obj.CreateSizeAttr(1);obj.AddTranslateOp().Set(Gf.Vec3d(*center));obj.AddScaleOp().Set(Gf.Vec3f(*size));bind(obj)
    # Cornice follows each actual modeled wall segment, rather than spanning recesses.
    cornice_segments=0
    for index,face in enumerate(walls):
        low=min(v[1] for v in face);high=max(v[1] for v in face)
        if high-low<.25:continue
        if high>center-4.8 and low<center+4.8:continue
        x=sum(v[0] for v in face)/len(face)
        for suffix,z,depth,height in [('Fascia',7.72,.28,.20),('Upper',7.87,.38,.10),('Lower',7.57,.23,.08)]:
            box(f'Cornice/Segment{index}_{suffix}',(x-.08,(low+high)/2,z),(depth,high-low,height))
        cornice_segments+=1
    # Two small street-facing pediments visible beside the central portico.
    # Bay center/width are approximate proportions; do not replace measured roof data.
    pediments=[]
    for side,station in [('South',center-(y1-y0)*.22),('North',center+(y1-y0)*.22)]:
        x=wall_x(station)-.18;half=2.5;bottom=7.83;tip=8.85;depth=.30
        vertices=[(xx,yy,zz) for xx in (x-depth/2,x+depth/2) for yy,zz in [(station-half,bottom),(station+half,bottom),(station,tip)]]
        mesh=UsdGeom.Mesh.Define(stage,base+'/Pediments/'+side)
        mesh.CreatePointsAttr(vertices);mesh.CreateFaceVertexCountsAttr([3,3,4,4,4]);mesh.CreateFaceVertexIndicesAttr([0,2,1,3,4,5,0,1,4,3,1,2,5,4,2,0,3,5]);mesh.CreateSubdivisionSchemeAttr('none');bind(mesh)
        # Recessed triangular insert makes the cornice outline legible.
        inset=UsdGeom.Mesh.Define(stage,base+'/Pediments/'+side+'Inset')
        inset.CreatePointsAttr([(x-depth/2-.005,station-half+.40,bottom+.12),(x-depth/2-.005,station+half-.40,bottom+.12),(x-depth/2-.005,station,tip-.23)])
        inset.CreateFaceVertexCountsAttr([3]);inset.CreateFaceVertexIndicesAttr([0,2,1]);inset.CreateSubdivisionSchemeAttr('none')
        inset.CreateDisplayColorAttr([Gf.Vec3f(.33,.35,.33)])
        pediments.append({'station_y':station,'width_m':5.,'base_z_m':bottom,'tip_z_m':tip,'status':'qualitative photo interpretation, dimensions approximate'})
    # The photograph shows charcoal roofing; use an original material override.
    roof='/World/LandmarkMaterials/OfficeArchitectureRoof/Surface'
    if not source.GetPrimAtPath(roof):raise ValueError('Expected roof material unavailable')
    shade=UsdShade.Shader(stage.OverridePrim(roof))
    shade.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.035,.041,.045))
    shade.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.82)
    # Picking a detail mesh directly must retain the same appearance-only context.
    # Material overrides outside this detail root are not physical entities.
    for child in stage.Traverse():
        if child.GetPath().HasPrefix(prim.GetPath()) and child.IsA(UsdGeom.Gprim):
            for key,value in metadata.items():child.SetCustomDataByKey(key,value)
    output.mkdir(parents=True)
    stage.GetRootLayer().customLayerData={'purpose':'Inactive office detail review; no measured/current-condition claim','sourceHashesJson':json.dumps(hashes,sort_keys=True),'photoHashesJson':json.dumps(photos,sort_keys=True),'limitations':'Cornice and small pediment proportions interpreted from broker photos of unknown capture date; base roof geometry retained; no original pixels used as textures.'}
    layer=output/'detail.usda';stage.GetRootLayer().Export(str(layer))
    combined=Usd.Stage.CreateInMemory();combined.GetRootLayer().subLayerPaths=[str(layer),str(review)]
    workview=output/'workview.usda';combined.GetRootLayer().Export(str(workview))
    if any(sha(root/name)!=digest for name,digest in hashes.items()):raise ValueError('Source changed during detail build')
    result={'proposal_only':True,'site_address':'1615 Edgewater Dr','source_snapshot':metadata['sourceSnapshot'],'appearance_metadata':metadata,'source_hashes':hashes,'photo_hashes':photos,'cornice_segments':cornice_segments,'pediments':pediments,'photo_capture_date':None,'measured_dimensions':False,'original_pixels_embedded':False,'activation':False,'files':{p.name:sha(p) for p in (layer,workview)}}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(build(args.output),indent=2))
