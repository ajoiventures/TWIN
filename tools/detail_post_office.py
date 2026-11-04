"""Bounded post-office frontage reference packet; never invent missing facade evidence."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,datetime,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies')]
from pxr import Usd,UsdGeom

def build():
    source=ROOT/'data/heights/landmarks/college_park_post_office/evidence.json';evidence=json.loads(source.read_text())
    if evidence['parcel_id']!='292223149200010' or evidence['site_address']!='1705 EDGEWATER DR':raise ValueError('Post office identity changed')
    findings=[
      {'url':'https://about.usps.com/newsroom/local-releases/fl/2020/1204-usps-prepares-for-holidays-orlando.htm','role':'primary operator historical identity','result':'December4,2020 USPS release explicitly lists Orlando College Park,1705EdgewaterDrive,32804; no exterior photo'},
      {'url':'https://tools.usps.com/locations/details/1358658','role':'official locator linked from public location listing','result':'Accessible operator locator shell; target address/exterior image not exposed in retrieved content'},
      {'url':'https://www.atly.com/location/UnitedStatesPostalService1487','role':'address-specific public listing','result':'1705Edgewater confirmed on listing; live browser photos show generic postal staff/kiosk images, not accepted target exterior'},
      {'url':'https://redirect.foursquare.com/locations/us-post-office/orlando','role':'address-specific public listing','result':'CollegePark1705Edgewater entry verified; venue gallery requires login; listed thumbnail visually depicts personal printed photos, not exterior'},
      {'url':'https://fastly.4sqi.net/img/general/128x128/13775_ej3bJ5OA-1UxS4ffmLo1xHJy78Dk7MLnVEH0cFolIB0.jpg','role':'actual listing thumbnail reviewed in browser','result':'Rejected: personal photo prints on grass; no building geometry'},
      {'url':'https://local.yahoo.com/info-215406449-us-post-office-orlando/','role':'image-search candidate','result':'Rejected for modeling: listing fetch restricted; exact site identity of exterior image not established'}]
    report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parcel_id':evidence['parcel_id'],'site_address':evidence['site_address'],
      'source_snapshot':evidence['source_snapshot'],'source_evidence_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'historical_cloud_sha256':evidence['cloud_sha256'],'source_acquisition':'2018–2019; current exterior unverified','findings':findings,
      'accepted_exterior_photo':None,'photo_capture_date':'unknown','frontage_geometry_authored':False,
      'status':'reference_gap_no_supported_frontage_geometry','specific_missing_evidence':'Address-verified exterior showing public entrance/canopy, facade openings and materials; current search images are stock, irrelevant, restricted or too unverified.',
      'no_generic_substitution':True,'source_pixels_textures_or_logos_embedded':False,'active_model_modified':False}
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    prim=UsdGeom.Xform.Define(stage,'/World/Landmarks/CollegeParkPostOffice/FrontageReference')
    prim.GetPrim().SetCustomData({'parcelId':evidence['parcel_id'],'siteAddress':evidence['site_address'],'status':report['status'],
      'geometryAuthored':False,'reason':'No address-verified usable exterior image; existing historical mass retained'})
    stage.GetRootLayer().customLayerData={'sourceSnapshot':evidence['source_snapshot'],'purpose':'Reference-gap packet only; zero facade geometry; no activation'}
    output=ROOT/'scene/post_office_frontage_proposal.usda';temporary=output.with_name(output.stem+'.tmp.usda');stage.GetRootLayer().Export(str(temporary));os.replace(temporary,output)
    if any(prim.IsA(UsdGeom.Mesh) for prim in stage.Traverse()):raise ValueError('Unsupported frontage geometry was authored')
    out=ROOT/'data/heights/landmarks/post_office_frontage_reference.json';temporary=out.with_suffix('.json.tmp');temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');os.replace(temporary,out)
    print(json.dumps({'status':report['status'],'layer':str(output),'receipt':str(out),'geometry_authored':False},indent=2));return report

if __name__=='__main__':build()
