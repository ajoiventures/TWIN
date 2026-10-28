import io,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from imagery_reference import Client,acquisition_month,check_url,image_statistics,pixel_resolution,review_queue,build

class ImageryReferenceTests(unittest.TestCase):
    def test_service_year_does_not_become_acquisition_date(self):
        self.assertIsNone(acquisition_month({'title':'Aerials2025'},{})['month'])
    def test_descriptive_capture_month_has_month_precision(self):
        for snippet,expected in [('Orthophotos flown January 2025 by Sanborn','2025-01'),('2024 Aerial imagery flown Jan by Sanborn','2024-01'),('Aerial photography acquired in January 2022','2022-01')]:
            row=acquisition_month({'snippet':snippet},{})
            self.assertEqual(row['month'],expected);self.assertEqual(row['precision'],'month');self.assertIsNone(row['exact_capture_date'])
    def test_private_or_unrelated_host_not_used(self):
        for url in ['http://vgispublic.ocpafl.org/a','https://vgishostedweb.ocpafl.org:6443/a','https://vgispublic.ocpafl.org.evil.example/a']:
            with self.assertRaises(ValueError):check_url(url)
    def test_offline_cache_miss_does_not_attempt_download(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'Offline'):Client(Path(d),offline=True).json('https://vgispublic.ocpafl.org/test')
    def test_export_resolution_converts_us_survey_feet_only(self):
        row=pixel_resolution({'extent':{'xmin':0,'xmax':100,'ymin':0,'ymax':200,'spatialReference':{'latestWkid':2236}},'width':100,'height':200})
        self.assertAlmostEqual(row['x_m'],1200/3937);self.assertIn('not native',row['meaning'])
        with self.assertRaisesRegex(ValueError,'CRS'):pixel_resolution({'extent':{'xmin':0,'xmax':1,'ymin':0,'ymax':1,'spatialReference':{'wkid':4326}},'width':10,'height':10})
    def test_blank_and_nonimage_responses_rejected(self):
        from PIL import Image
        image=Image.new('RGB',(8,8),'white');raw=io.BytesIO();image.save(raw,format='PNG')
        with self.assertRaisesRegex(ValueError,'blank'):image_statistics(raw.getvalue())
        with self.assertRaises(Exception):image_statistics(b'{"error":"Token required"}')
    def test_reference_variation_does_not_assert_accuracy(self):
        from PIL import Image
        image=Image.new('RGB',(8,8),'black')
        for x in range(4):
            for y in range(8):image.putpixel((x,y),(255,255,255))
        raw=io.BytesIO();image.save(raw,format='PNG');result=image_statistics(raw.getvalue())
        self.assertEqual(result['width'],8);self.assertIn('not an accuracy test',result['coverage_evidence'])
    def test_review_queue_keeps_spatial_links_unaccepted_and_allowlisted(self):
        rows=review_queue({'building_ids':['B']},[{'id':'B','parcel_id':'00123','site_address':'A','match_method':'spatial_review','owner':'EXCLUDED'}])
        self.assertFalse(rows[0]['link_accepted']);self.assertEqual(rows[0]['parcel_id'],'00123');self.assertNotIn('owner',rows[0])
        self.assertTrue(all(v=='unresolved' for v in rows[0]['review_topics'].values()))
    def test_stale_pilot_stops_before_network_or_images(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir();(root/'data/processed').mkdir(parents=True)
            (root/'config/imagery_sources.json').write_text('{}')
            (root/'data/processed/pilot.json').write_text(json.dumps({'source_snapshot':'old'}))
            (root/'data/processed/active.json').write_text(json.dumps({'snapshot':'new'}))
            with self.assertRaisesRegex(ValueError,'Pilot/snapshot mismatch'):build(root,offline=True)

if __name__=='__main__':unittest.main()
