from data_pipeline import ROOT,Client,atomic_json
url='https://s3-us-west-2.amazonaws.com/usgs-lidar-public/FL_Peninsular_FDEM_Orange_2018/'
c=Client(ROOT/'data/cache/heights');d=c.get(url+'ept.json');atomic_json(ROOT/'data/heights/ept_metadata.json',d)
print({k:d.get(k) for k in ['bounds','boundsConforming','span','dataType','srs','points','schema']})
h=c.get(url+'ept-hierarchy/0-0-0-0.json');atomic_json(ROOT/'data/heights/root_hierarchy.json',h);print('HIERARCHY',len(h),list(h.items())[:12])
