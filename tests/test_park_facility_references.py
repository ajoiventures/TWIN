from pathlib import Path
import hashlib, json, sys, tempfile, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from enrich_park_facilities import parse_page, page_cache, BASE


class ParkFacilityReferenceTests(unittest.TestCase):
    def fixture(self, hours):
        return (f'<html><head><link rel="canonical" href="{BASE}Test-Park"></head>'
                '<body><h1 class="oc-page-title">Test Park</h1>'
                '<div class="gmap-address">123 Example Street, Orlando FL</div>'
                '<div class="gmap-latlong">28.57,-81.39</div>'
                f'<div class="contact-details"><h3>Hours</h3>{hours}<h3>Contact</h3>'
                '<p>DO NOT PUBLISH CONTACT</p></div>'
                '<ul class="park-feature-list"><li>Open Space</li></ul>'
                '<footer>City Hall hours: Monday-Friday</footer></body></html>').encode()

    def test_schedule_scope_and_identity_guard(self):
        parsed = parse_page(self.fixture('Sunrise to Sunset'), BASE + 'Test-Park', 'Test Park')
        self.assertEqual(parsed['published_hours'], {'kind': 'textual_directory_schedule', 'text': 'Sunrise to Sunset'})
        self.assertEqual(parsed['published_features'], ['Open Space'])
        self.assertNotIn('CONTACT', json.dumps(parsed)); self.assertNotIn('City Hall', json.dumps(parsed))
        with self.assertRaises(ValueError): parse_page(self.fixture('Sunrise to Sunset'), BASE + 'Other', 'Test Park')
        with self.assertRaises(ValueError): parse_page(self.fixture('Sunrise to Sunset'), BASE + 'Test-Park', 'Other Park')
        weekly = '<ul class="hours-list">' + ''.join('<li><span class="hours-day">' + day + '</span><ul class="hours-time-list"><li>06:00 AM–11:00 PM</li></ul>' for day in ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')) + '</ul>'
        self.assertEqual(len(parse_page(self.fixture(weekly), BASE + 'Test-Park', 'Test Park')['published_hours']['weekly']), 7)

    def test_offline_cache_missing_tamper_and_host_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); url = BASE + 'Test-Park'
            with self.assertRaises(FileNotFoundError): page_cache(root, url)
            with self.assertRaises(ValueError): page_cache(root, 'https://example.invalid/Test-Park', True)
            folder = root / 'data/cache/park_facility_references'; folder.mkdir(parents=True)
            key = hashlib.sha256(url.encode()).hexdigest(); path = folder / (key + '.html'); proof = folder / (key + '.receipt.json')
            raw = self.fixture('Sunrise to Sunset'); path.write_bytes(raw)
            with self.assertRaises(ValueError): page_cache(root, url)
            proof.write_text(json.dumps({'url': url, 'final_url': url, 'sha256': hashlib.sha256(raw).hexdigest()}))
            self.assertEqual(page_cache(root, url)[0], raw)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError): page_cache(root, url)


if __name__ == '__main__': unittest.main()
