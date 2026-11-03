import importlib.util
import json
from pathlib import Path
import tempfile
import re
import unittest
from datetime import datetime, timezone

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/ai-sindan/scripts/diagnose.py'
spec = importlib.util.spec_from_file_location('diagnose', SCRIPT)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
STAMP = '2026-10-30T12:00:00Z'

def codex(text, timestamp=STAMP):
    return dict(type='response_item', timestamp=timestamp, payload=dict(type='message', role='user', content=[dict(type='input_text', text=text)]))

class DiagnosisTests(unittest.TestCase):
    def setUp(self):
        root = SCRIPT.parents[3] / 'output' / 'test-tmp'
        root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=root)
        self.home = Path(self.tmp.name)

    def tearDown(self):
        assert self.home.resolve().is_relative_to(SCRIPT.parents[3] / 'output' / 'test-tmp')
        self.tmp.cleanup()

    def write(self, rel, rows):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows), encoding='utf-8')
        return p

    def report(self, **kwargs):
        return d.analyze(self.home, now=NOW, **kwargs)

    def test_codex_canonical_and_archive_dedup(self):
        rows = [dict(type='session_meta', payload=dict(id='session-1')), codex('任せます。最後まで進めて'), dict(type='event_msg', timestamp=STAMP, payload=dict(type='user_message', message='任せます。最後まで進めて'))]
        self.write('.codex/sessions/a.jsonl', rows)
        self.write('.codex/archived_sessions/copy.jsonl', rows)
        r = self.report()
        self.assertEqual(r['messages'], 1)
        self.assertEqual(next(p for p in r['perspectives'] if p['id']=='delegation')['count'], 1)
        self.assertIsNone(r['profile'])

    def test_fallback(self):
        self.write('.codex/sessions/a.jsonl', [dict(type='event_msg', timestamp=STAMP, payload=dict(type='user_message', message='説明して'))])
        self.assertEqual(self.report()['messages'], 1)

    def test_codex_automation_excluded(self):
        self.write('.codex/sessions/auto.jsonl', [dict(type='session_meta', payload=dict(source={'subagent': {'other': 'guardian'}})), codex('検証して')])
        self.write('.codex/sessions/main.jsonl', [codex('# AGENTS.md instructions for project\n検証して'), codex('This block is automatically supplied ambient UI state. 検証して'), codex('作って')])
        r = self.report()
        self.assertEqual(r['messages'], 1)
        self.assertEqual(r['diagnostics']['excluded_subagent_files'], 1)

    def test_claude_tool_results_and_subagents_excluded(self):
        rows = [dict(type='user', timestamp=STAMP, uuid='1', message=dict(content=[dict(type='tool_result', content='いいね'), dict(type='text', text='検証して')])), dict(type='user', isMeta=True, timestamp=STAMP, message=dict(content='任せます')), dict(type='user', isSidechain=True, timestamp=STAMP, message=dict(content='任せます'))]
        self.write('.claude/projects/p/a.jsonl', rows)
        self.write('.claude/projects/p/subagents/a.jsonl', rows)
        r = self.report()
        self.assertEqual(r['messages'], 1)
        self.assertEqual(next(p for p in r['perspectives'] if p['id']=='verification')['count'], 1)
        self.assertEqual(next(p for p in r['perspectives'] if p['id']=='acceptance')['count'], 0)

    def test_filters_and_malformed(self):
        p = self.write('.codex/sessions/a.jsonl', [codex('検証', '2020-01-01T00:00:00Z'), codex('検証', None), codex('実装して')])
        with p.open('a', encoding='utf-8') as f:
            f.write('\n{broken\n[]')
        r = self.report()
        self.assertEqual(r['messages'], 1)
        self.assertEqual(r['diagnostics']['malformed_lines'], 2)
        self.assertEqual(r['diagnostics']['missing_timestamp'], 1)
        self.assertEqual(self.report(source='claude')['messages'], 0)

    def test_wrappers_code_quotes(self):
        text = '<environment_context>検証して</environment_context>\n```\nいいね\n```\n> 任せます\n説明して'
        self.assertEqual(d.clean_text(text), '説明して')

    def test_private_output_and_empty(self):
        secret = 'UNIQUE_PRIVATE_TEXT_123'
        self.write('.codex/sessions/a.jsonl', [codex(secret+' 実装して')])
        result = self.report()
        output = d.render(result)
        self.assertNotIn(secret, output)
        self.assertNotIn(str(self.home), output)
        self.assertNotIn('__REPORT_DATA__', output)
        result['type_name'] = '</script><script>alert(1)</script>'
        self.assertNotIn(result['type_name'], d.render(result))

    def test_empty_history(self):
        r = self.report()
        self.assertEqual(r['messages'], 0)
        self.assertIsNone(r['profile'])
        self.assertIsNone(r['period'])
        self.assertTrue(all(p['rate'] is None and p['status'] == '未観測' for p in r['perspectives']))

    def test_independent_perspectives_and_session_coverage(self):
        # One statement can express several habits; repetition in a statement counts once.
        self.write('.codex/sessions/a.jsonl', [codex('目的は初心者が楽しめること。まずは試作。試作 '+str(i)) for i in range(5)])
        r = self.report()
        by_id = {p['id']: p for p in r['perspectives']}
        for key in ('context', 'audience', 'experiments'):
            self.assertEqual(by_id[key]['count'], 5)
            self.assertEqual(by_id[key]['rate'], 100)
            self.assertEqual(by_id[key]['sessions'], 1)
            self.assertEqual(by_id[key]['status'], '少数の表現を観測')
        self.assertEqual(by_id['reuse']['status'], '未観測')
        self.write('.claude/projects/p/b.jsonl', [dict(type='user', timestamp=STAMP, uuid='1', message=dict(content='まずは試作して'))])
        p = next(p for p in self.report()['perspectives'] if p['id'] == 'experiments')
        self.assertEqual(p['count'], 6)
        self.assertEqual(p['sessions'], 2)
        self.assertEqual(p['status'], '複数の会話で観測')

    def test_non_engineering_language(self):
        self.write('.codex/sessions/a.jsonl', [codex('この参考画像の余白を参考に、ラフを描いて。見やすさを優先したい。')])
        r = self.report()
        p = {p['id']: p for p in r['perspectives']}
        self.assertEqual(p['execution']['count'], 1)
        for key in ('references', 'experiments', 'criteria'):
            self.assertEqual(p[key]['count'], 1)
        self.assertEqual(p['ownership']['count'], 0)

    def test_examples_are_supported_and_not_counted(self):
        # These are authored examples, not the user's evidence.
        for p in d.PERSPECTIVES:
            for role, example in p['examples'].items():
                with self.subTest(perspective=p['id'], role=role):
                    self.assertRegex(example, re.compile(p['pattern'], re.I))
        self.assertTrue(all(p['count'] == 0 for p in self.report()['perspectives']))

    def test_template_payload(self):
        r = self.report()
        markup = d.render(r)
        payload = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', markup, re.S).group(1)
        rendered = json.loads(payload)
        self.assertIsNotNone(d.parse_time(rendered.pop('rendered_at')))
        self.assertEqual(rendered, r)
        self.assertEqual(len(r['perspectives']), 18)
        self.assertNotRegex(markup, r'(?:src|href)="https?://')

class TypeSystemTests(unittest.TestCase):
    def vector(self, values):
        return [dict(id=p['id'],count=100 if values.get(p['id']) else 0,sessions=values.get(p['id'],0)) for p in d.PERSPECTIVES]

    def test_all_sixteen_prototypes(self):
        self.assertEqual(len(d.TYPES),16)
        self.assertEqual(len({t['code'] for t in d.TYPES}),16)
        self.assertEqual(len({t['name'] for t in d.TYPES}),16)
        ids={p['id'] for p in d.PERSPECTIVES}
        self.assertEqual(set().union(*(t['weights'].keys() for t in d.TYPES)),ids)
        for t in d.TYPES:
            with self.subTest(style=t['code']):
                r=d.classify(self.vector({k:v*10 for k,v in t['weights'].items()}),200,100)
                self.assertEqual(r['profile']['code'],t['code'])
                self.assertGreaterEqual(len(r['alternatives'][0]['reasons']),2)

    def test_sparse_and_uniform_are_not_forced(self):
        r=d.classify(self.vector({'audience':30}),200,100)
        self.assertIsNone(r['profile'])
        self.assertFalse(r['evidence_ready'])
        r=d.classify(self.vector({p['id']:20 for p in d.PERSPECTIVES}),200,100)
        self.assertIsNone(r['profile'])
        self.assertEqual(len(r['candidate_codes']),16)
        self.assertIsNone(d.classify(self.vector({}),0,0)['profile'])

    def test_additional_dimensions_change_result(self):
        # Reuse, validation, and boundaries now affect classification directly.
        first=d.classify(self.vector({'learning':30,'verification':30,'refinement':20,'reuse':20}),200,100)
        second=d.classify(self.vector({'reuse':30,'verification':30,'execution':20,'boundaries':20}),200,100)
        self.assertEqual(first['profile']['name'],'研究者')
        self.assertEqual(second['profile']['name'],'仕上げ職人')

    def test_share_allowlist(self):
        r=dict(method='habits-18-prototypes-v1', days=90, evidence_ready=True,type_name='研究者',candidate_codes=['S14'],
               sources={'secret-tool':20}, generated_at='PRIVATE_TIME', raw='SECRET',
               perspectives=[dict(id=p['id'],session_rate=20,status='複数の会話で観測',count=345,sessions=67) for p in d.PERSPECTIVES])
        share=d.make_share(r)
        self.assertEqual(set(share),{'schema','method','days','sample','type_name','candidate_codes','metrics'})
        self.assertTrue(all(set(m)=={'id','session_rate','status'} for m in share['metrics']))
        self.assertNotIn('SECRET',json.dumps(share))
        self.assertNotIn('secret-tool',json.dumps(share))

if __name__ == '__main__':
    unittest.main()
