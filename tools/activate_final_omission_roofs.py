"""Explicit reviewed per-site historical roof activation; no root composition edits."""
from pathlib import Path
import sys,json,argparse,os,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Usd,UsdGeom
from verify_retail_block import read,save,sha,inside
from mesh_topology import closed_shell_report
ALLOWED={'rugby_720','rugby_738'}
MANIFEST='data/heights/final_omissions/roof_proposal_manifest.json'
ACTIVATION='data/heights/final_omissions/activation.json'
DESTINATION='scene/final_omission_roofs.usda'

def prepare(root,proofs,approved_site_ids):
 root=Path(root).resolve();approved=set(approved_site_ids)
 if not approved or not approved<=ALLOWED:raise ValueError('Only explicitly reviewed Rugby720/738 may activate;3457 is blocked')
 if set(proofs)!=approved:raise ValueError('Require exactly one pinned render proof per selected site')
 active=read(root/'data/processed/active.json');manifest_path=inside(root,MANIFEST);manifest=read(manifest_path)
 if manifest['source_snapshot']!=active['snapshot']:raise ValueError('Stale roof source snapshot')
 proposal=inside(root,manifest['proposal_layer'])
 if sha(proposal)!=manifest['layer_sha256']:raise ValueError('Roof proposal bytes changed')
 dependencies={};review_context={}
 for relative,digest in manifest['dependencies'].items():
  path=inside(root,relative)
  if not path.is_file() or sha(path)!=digest:raise ValueError('Roof source dependency changed: '+relative)
  if relative.replace('\\','/').startswith(('scene/','assets/')):review_context[relative]=digest
  else:dependencies[relative]=digest
 stage=Usd.Stage.Open(str(proposal));selected=[]
 for site in manifest['sites']:
  if site['site_id'] not in approved:continue
  if site.get('source_fit_status')!='broad_roof_planes_supported_with_local_outliers':raise ValueError('High-residual site remains unaccepted')
  render_relative,pinned=proofs[site['site_id']];render_path=inside(root,render_relative)
  if sha(render_path)!=pinned:raise ValueError('Reviewed render manifest changed')
  render=read(render_path)
  if render.get('source_snapshot')!=active['snapshot'] or render.get('camera')!=site['camera'] or render.get('layer_hashes',{}).get(manifest['proposal_layer'])!=manifest['layer_sha256']:raise ValueError('Render does not prove selected roof/camera/snapshot')
  for relative,digest in render['layer_hashes'].items():
   path=inside(root,relative)
   if not path.is_file() or sha(path)!=digest:raise ValueError('Reviewed render context changed: '+relative)
  image=inside(root,render['image'])
  if sha(image)!=render['image_sha256']:raise ValueError('Render image changed')
  from PIL import Image
  with Image.open(image) as pixels:
   if list(pixels.size)!=render['requested_resolution']:raise ValueError('Incomplete render resolution')
   pixels.verify()
  prim=stage.GetPrimAtPath(site['prim_path'])
  if not prim or prim.GetCustomData().get('parcelId')!=site['parcel_id']:raise ValueError('Roof source identity changed')
  components=[]
  for child in Usd.PrimRange(prim):
   if not child.IsA(UsdGeom.Mesh):continue
   mesh=UsdGeom.Mesh(child);gate=closed_shell_report(mesh.GetPointsAttr().Get(),mesh.GetFaceVertexCountsAttr().Get(),mesh.GetFaceVertexIndicesAttr().Get())
   if not gate['passed_closed_shell']:raise ValueError('Roof mesh is not closed')
   components.append({'prim_path':str(child.GetPath()),'closed_shell':gate})
  if not components:raise ValueError('Selected site has no geometry')
  selected.append({**site,'components':components,'parcel_ids':[site['parcel_id']],'render_manifest':render_relative,'render_manifest_sha256':pinned,'quality':'historical_source_fitted_pitched_roof_draft_current_walls_unverified'})
  for path in [render_path,image]:dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
 for path in [manifest_path,proposal,Path(__file__).resolve()]:
  if path.is_relative_to(root):dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
 return {'source_snapshot':active['snapshot'],'sites':selected,'layer':DESTINATION,'proposal_layer':manifest['proposal_layer'],'proposal_layer_sha256':manifest['layer_sha256'],'dependencies':dependencies,'reviewed_context_dependencies':review_context,'raw_property_links_promoted':False,'accepted_current_geometry':False,'prepared_only':True,'limitations':manifest['limits']+['Activation is historical roof-mass display only; current walls, facades and architectural visual acceptance are not established by shell closure.']}

def validate_active(root=ROOT,snapshot=None):
 root=Path(root).resolve();packet=read(root/ACTIVATION)
 if packet['source_snapshot']!=(snapshot or read(root/'data/processed/active.json')['snapshot']) or packet['prepared_only'] is not False:raise ValueError('Stale roof activation')
 if {s['site_id'] for s in packet['sites']}-ALLOWED:raise ValueError('Unapproved roof site')
 if sha(inside(root,packet['layer']))!=packet['layer_sha256']:raise ValueError('Activated roof has manual changes')
 for relative,digest in packet['dependencies'].items():
  if sha(inside(root,relative))!=digest:raise ValueError('Activated roof evidence changed: '+relative)
 return packet

def activate(root,proofs,approved_site_ids):
 root=Path(root).resolve();packet=prepare(root,proofs,approved_site_ids);destination=root/DESTINATION;prior_path=root/ACTIVATION
 if destination.exists():
  if not prior_path.exists() or sha(destination)!=read(prior_path).get('layer_sha256'):raise ValueError('Untracked or manually edited roof layer; preserve it')
 layer=Usd.Stage.Open(str(root/packet['proposal_layer'])).Flatten();stage=Usd.Stage.Open(layer);selected={s['site_id'] for s in packet['sites']}
 for site in read(root/MANIFEST)['sites']:
  if site['site_id'] not in selected:stage.RemovePrim(site['prim_path'])
 layer.customLayerData={**layer.customLayerData,'activation':'reviewed_historical_draft','sourceSnapshot':packet['source_snapshot']}
 temporary=destination.with_name(destination.stem+'.tmp.usda');layer.Export(str(temporary))
 if read(root/'data/processed/active.json')['snapshot']!=packet['source_snapshot']:temporary.unlink();raise ValueError('Snapshot changed during activation')
 os.replace(temporary,destination);packet.update({'prepared_only':False,'layer_sha256':sha(destination),'activated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});save(root/ACTIVATION,packet);return packet

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--site-id',action='append',required=True);p.add_argument('--proof',action='append',required=True,help='site_id|root-relative render manifest|sha256');p.add_argument('--apply',action='store_true');a=p.parse_args();proofs={}
 for item in a.proof:
  site,path,digest=item.split('|');proofs[site]=(path,digest)
 packet=activate(ROOT,proofs,a.site_id) if a.apply else prepare(ROOT,proofs,a.site_id);print(json.dumps(packet,indent=2))
