import base64
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/caravan/scripts'))
import brand
import diagnose


class BrandTests(unittest.TestCase):
    def test_portable_logo_keeps_transparency_and_size_budget(self):
        data = (ROOT / 'skills/caravan/assets/brand/caravan-logo.png').read_bytes()
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II', data[16:24]), (640, 213))
        self.assertEqual(data[25], 6)  # RGBA; do not flatten the transparent background.
        self.assertLessEqual(len(data), 128 * 1024)
        html = brand.embed_logo('<img src="__BRANDLOGO__" alt="Caravan">')
        encoded = html.split('base64,')[1].split('"')[0]
        self.assertEqual(base64.b64decode(encoded), data)

    def test_render_brand_does_not_mutate_saved_diagnosis(self):
        import copy
        report = {'method': 'semantic-test', 'generated_at': '2026-01-01',
                  'portrait': {'schema': 'legacy'}}
        original = copy.deepcopy(report)
        html = diagnose.render(report)
        self.assertEqual(report, original)
        self.assertIn('<title>Caravan', html)
        self.assertIn('alt="Caravan"', html)
        self.assertNotIn('__BRANDLOGO__', html)
        self.assertNotIn('AI SINDAN', html)
        self.assertEqual(html.count('data:image/png;base64,'), 2)
