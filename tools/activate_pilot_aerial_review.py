"""Guarded default-off aerial review composition; prepare unless --apply."""
from pathlib import Path
import sys,json,datetime,os,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Sdf,Usd,UsdGeom
from complete_pilot_aerial_review import validate_review,OUT
from activate_environment_assets import sha,guarded_replace,local,relative
LAYER='scene/pilot_aerial_review.usda';PRIM='/World/Information/PilotAerialReview'

def validate(root=ROOT):
 root=Path(root).resolve();packet=validate_review(root);layer=root/LAYER;assembly=root/'scene/college_park_connected.usda';stage=Usd.Stage.Open(str(layer));prim=stage.GetPrimAtPath(PRIM)
 if packet.get('default_on') is not False or packet.get('geometry_activated') is not False or packet.get('raw_property_links_promoted') is not False:raise ValueError('Aerial review must remain default-off and unpromoted')
 if not prim or UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':raise ValueError('Aerial review source root must be invisible')
 expected={r['review_id']:r for r in packet['building_reviews']};seen=set();curve_count=0
 for child in stage.Traverse():
  path=str(child.GetPath())
  if path not in ('/World','/World/Information') and not path.startswith(PRIM+'/') and path!=PRIM:raise ValueError('Unexpected aerial layer opinions: '+path)
  if child.IsA(UsdGeom.Mesh):raise ValueError('Aerial review must not embed replacement surfaces')
  if child.IsA(UsdGeom.BasisCurves):
   curve_count+=1;context=child.GetCustomData().get('sourceContext',{});id=context.get('reviewId')
   if context.get('sourceSnapshot')!=packet['source_snapshot'] or context.get('acquisitionDates')!='2022-01,2024-01,2025-01':raise ValueError('Review curve provenance/dates missing')
   if id in expected:
    row=expected[id]
    if context.get('sourceBuildingKey')!=row['source_building_key'] or context.get('sourceParcelId')!=row['source_parcel_id'] or context.get('sourceObjectIds')!=','.join(row['source_object_ids']):raise ValueError('Review source identities do not match packet')
    seen.add(id)
 if seen!=set(expected) or curve_count!=len(expected)+len(packet['frontage_reviews']):raise ValueError('Aerial scene review census incomplete')
 dependencies={**packet['dependencies'],**packet['artifacts']}
 for path in [assembly,root/OUT/'review.json',root/OUT/'receipt.json',Path(__file__).resolve()]:
  if path.is_relative_to(root):dependencies[relative(root,path)]=sha(path)
 manual=root/'scene/manual_edits.usda'
 if manual.exists():dependencies[relative(root,manual)]=sha(manual)
 return {'status':'validated_not_activated','source_snapshot':packet['source_snapshot'],'layer':LAYER,'layer_sha256':sha(layer),'default_visibility':'invisible','quality':'Historical qualitative source review; unknown positional accuracy, no facade/height inference','source_geometry_promoted':False,'dependencies':dependencies,'root_sha256':sha(assembly),'manual_edits_modified':False,'source_layers_modified':False,'building_review_curves':len(seen),'frontage_review_curves':len(packet['frontage_reviews'])}

def validate_active_aerial(root=ROOT):
 root=Path(root).resolve();receipt=root/OUT/'activation.json'
 if not receipt.exists():return None
 data=json.loads(receipt.read_text(encoding='utf-8'));packet=validate_review(root)
 if data.get('status')!='activated' or data.get('source_snapshot')!=packet['source_snapshot'] or data.get('layer')!=LAYER or sha(local(root,data['layer']))!=data.get('layer_sha256'):raise ValueError('Activated aerial review stale; revalidate before composition')
 return Path(data['layer']).name

def activate(root=ROOT,apply=False):
 root=Path(root).resolve();report=validate(root)
 if not apply:return report
 assembly=root/'scene/college_park_connected.usda';lock=root/'scene/.aerial_review_activation.lock';descriptor=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 try:
  for relative_path,digest in report['dependencies'].items():
   if sha(local(root,relative_path))!=digest:raise ValueError('Aerial activation dependency changed: '+relative_path)
  old=assembly.read_bytes();layer=Sdf.Layer.CreateAnonymous();layer.ImportFromString(old.decode('utf-8'));name=Path(LAYER).name;paths=[p for p in layer.subLayerPaths if p!=name];index=max((i for i,p in enumerate(paths) if p in ('manual_edits.usda','map_extent_guard.usda')),default=-1)+1;paths.insert(index,name);layer.subLayerPaths=paths
  stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup=root/OUT/'activation_backups'/stamp;backup.mkdir(parents=True);(backup/assembly.name).write_bytes(old);receipt=root/OUT/'activation.json'
  if receipt.exists():(backup/receipt.name).write_bytes(receipt.read_bytes())
  guarded_replace(assembly,layer.ExportToString().encode('utf-8'),report['root_sha256']);report.update({'status':'activated','activated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_after_sha256':sha(assembly),'backup':relative(root,backup)})
  temporary=receipt.with_suffix('.json.tmp')
  try:temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');os.replace(temporary,receipt)
  except Exception:
   guarded_replace(assembly,old,report['root_after_sha256'])
   if temporary.exists():temporary.unlink()
   raise
  return report
 finally:os.close(descriptor);lock.unlink()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args();print(json.dumps(activate(apply=args.apply),indent=2))
