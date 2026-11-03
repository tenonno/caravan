from html.parser import HTMLParser
from pathlib import Path
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/caravan/scripts'))
import semantic as s
import developer_report as dev


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.links = []
        self.weight_rows = 0
        self.in_weights = False
        self.in_body = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'table':
            self.in_weights = attrs.get('class') == 'weights'
        if tag == 'tbody':
            self.in_body = True
        if tag == 'tr' and self.in_weights and self.in_body:
            self.weight_rows += 1

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_weights = False
        if tag == 'tbody':
            self.in_body = False


class DeveloperReportTests(unittest.TestCase):
    def report(self):
        perspectives = [dict(**{k: v for k, v in p.items() if k != 'pattern'}, count=0, sessions=0,
                             assessed_sessions=1, uncertain_sessions=0, session_rate=0, status='未観測',
                             findings=[dict(reason='PRIVATE_REASON', session='PRIVATE_ID', refs=['m1'])])
                        for p in s.base.PERSPECTIVES]
        return dict(version='0.5.0', method=s.RUBRIC, generated_at='2026-11-01T00:00:00+00:00',
                    messages=2, sessions=1, days=90, sources={'codex': 1}, perspectives=perspectives,
                    diagnostics={}, sampling=dict(mode='light', total_sessions=1, eligible_sessions=1,
                        cache_hits=0, read_chars=100, new_read_chars=100, char_budget=12000, session_budget=6),
                    **s.base.classify(perspectives, 2, 1))

    def test_all_definitions_weights_and_navigation_without_private_evidence(self):
        html = dev.render(self.report(), s.RUBRIC, s.EXTRACTOR, s.MODES)
        page = Page(html)
        self.assertEqual(page.weight_rows, 16)
        self.assertEqual({x for x in page.ids if x.startswith('axis-') and x not in ('axis-search', 'axis-count')},
                         {'axis-' + p['id'] for p in s.PERSPECTIVES})
        self.assertEqual(len(page.ids), len(set(page.ids)))
        self.assertIn('index.html', page.links)
        for link in page.links:
            if link.startswith('#'):
                self.assertIn(link[1:], page.ids)
        for value in ['PRIVATE_REASON', 'PRIVATE_ID', '__AXES__', '__RULES__']:
            self.assertNotIn(value, html)
        self.assertNotRegex(html, r'(?:src|href)="https?://')

    def test_current_rules_are_rendered_and_report_labels_are_escaped(self):
        report = self.report()
        report['type_catalog'] = [dict(t, name='<script>alert(1)</script>') for t in report['type_catalog']]
        with patch.dict(s.base.CLASSIFICATION_RULES, min_similarity=.731):
            html = dev.render(report, s.RUBRIC, s.EXTRACTOR, s.MODES)
        self.assertIn('0.731', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_render_only_preserves_analysis_and_updates_both_fixed_pages(self):
        root = Path(__file__).resolve().parents[1] / 'output/developer-tests'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            out = Path(directory)
            report = self.report()
            s.write(out / 'report.json', report)
            original = (out / 'report.json').read_bytes()
            with patch.object(s, 'prepare', side_effect=AssertionError('must not reread history')):
                with contextlib.redirect_stdout(io.StringIO()):
                    s.render_pages(out)
                    s.render_pages(out)
            self.assertEqual((out / 'report.json').read_bytes(), original)
            self.assertEqual({p.name for p in out.iterdir()}, {'report.json', 'index.html', 'developer.html'})
            self.assertIn('href="developer.html"', (out / 'index.html').read_text(encoding='utf-8'))
            self.assertIn(report['generated_at'], (out / 'developer.html').read_text(encoding='utf-8'))
            self.assertIn(report['generated_at'], (out / 'index.html').read_text(encoding='utf-8'))
            assert out.resolve().is_relative_to(root.resolve())

    def test_execution_inventory_is_separate_and_not_exported(self):
        import execution
        root=Path(__file__).resolve().parents[1]/'output/developer-tests'
        root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            out=Path(directory);report=self.report()
            s.write(out/'report.json',report)
            original=(out/'report.json').read_bytes()
            audit=execution.aggregate([])
            audit.update(scope='SEPARATE_SCOPE',generated_at='2026-11-03T00:00:00+00:00',days=30)
            audit['models']=['<script>PRIVATE_MODEL</script>']
            s.write(out/'execution-audit.json',audit)
            with contextlib.redirect_stdout(io.StringIO()):s.render_pages(out)
            self.assertEqual(original,(out/'report.json').read_bytes())
            for name in ['index.html','developer.html']:
                text=(out/name).read_text(encoding='utf-8')
                self.assertIn('SEPARATE_SCOPE',text)
                self.assertNotIn('<script>PRIVATE_MODEL</script>',text)
            view=s.rubric.display_report(report);view['execution_audit']=audit
            self.assertNotIn('PRIVATE_MODEL',json.dumps(s.base.make_share(view)))
            assert out.resolve().is_relative_to(root.resolve())


if __name__ == '__main__':
    unittest.main()
