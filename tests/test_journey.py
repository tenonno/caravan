import base64
import copy
import hashlib
import re
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/caravan/scripts'))
import journey
import portrait
import diagnose


class JourneyTests(unittest.TestCase):
    def test_responsive_image_height_overrides_html_dimensions(self):
        # Regression: width:100% combined with a fixed HTML height left 640px-tall
        # images inside 150-200px cards. This checks that contract, not browser layout.
        template = (journey.ASSETS / 'semantic-report.html').read_text(encoding='utf-8')
        css = re.search(r'<style>(.*?)</style>', template, re.S).group(1)
        for class_name in ('type-art', 'journey-hero', 'summary-art'):
            blocks = re.findall(r'([^{}]*\.' + class_name + r'[^{}]*)\{([^{}]*)\}', css)
            heights = []
            for selector, declarations in blocks:
                if re.search(r'\.' + class_name + r'\s*(?:,|$)', selector.strip()):
                    heights.extend(re.findall(r'(?:^|;)\s*height\s*:\s*([^;]+)', declarations))
            self.assertTrue(heights, class_name + ' must override intrinsic HTML height')
            self.assertTrue(all(value.strip() == 'auto' for value in heights), heights)

    def test_complete_distinct_art_for_all_reachable_types(self):
        types = journey.catalog()
        expected = {''.join(codes) for codes in product('SE', 'GD', 'BI', 'CT')}
        self.assertEqual({t['code'] for t in types}, expected)
        self.assertEqual(len({t['name'] for t in types}), 16)
        art = journey.presentation({'portrait': {'schema': 'portrait-v1'}})['types']
        digests = set()
        for t in art:
            self.assertTrue(t['alt'])
            raw = base64.b64decode(t['image'].split(',', 1)[1], validate=True)
            self.assertTrue(raw.startswith(b'\xff\xd8'))
            self.assertEqual(raw, (journey.ASSETS / 'journey' / (t['code'] + '.jpg')).read_bytes())
            self.assertFalse((journey.ASSETS / 'journey' / (t['code'] + '.png')).exists())
            digests.add(hashlib.sha256(raw).digest())
        self.assertEqual(len(digests), 16)
        self.assertEqual({t['code']: t['name'] for t in portrait.catalog()}, {t['code']: t['name'] for t in types})

    def test_presentation_leaves_evidence_and_legacy_classification_intact(self):
        self.assertIsNone(journey.presentation({'method': 'semantic-38-v3'}))
        self.assertIsNone(journey.presentation({'portrait': {'schema': 'future-schema'}}))
        report = {'method': 'semantic-38-v3', 'generated_at': 'original-date',
                  'portrait': {'schema': 'portrait-v1', 'classification': {'profile': None, 'type_code': '????'}}}
        original = copy.deepcopy(report)
        markup = diagnose.render(report)
        self.assertEqual(report, original)
        self.assertIn('data:image/jpeg;base64,', markup)
        self.assertNotIn('file://', markup)
        self.assertIn('original-date', markup)


if __name__ == '__main__':
    unittest.main()
