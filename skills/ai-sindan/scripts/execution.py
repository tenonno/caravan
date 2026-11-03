"""Allowlisted execution metadata. Never inspect tool arguments/output as instructions."""
from collections import Counter
import hashlib
import json
import re
import diagnose as base

VERSION = 'execution-events-v1'
LIMIT = 512
FEATURES = {'model': 'モデル情報', 'effort': '推論設定', 'mcp': 'MCP呼び出し',
            'skill': 'スキル呼び出し', 'delegation': '委譲の要求', 'coordination': 'エージェント間の連絡・待機',
            'compaction': '文脈の圧縮記録', 'opaque_tool': '内訳を判別できないツール呼び出し'}
LIMITATIONS = {
    'codex': 'モデル・推論設定と直接のツール呼び出しに対応。exec等の内部コード、スキル読込、フックの利用は確定しません。',
    'claude': '応答のモデル名とtool_use/tool_resultに対応。スキル・委譲は呼び出し要求であり、完了や本人の選択を意味しません。',
    'antigravity': '現在確認できている会話JSONLでは実行メタデータの読取形式が未対応です。利用なしとは扱いません。',
}


def identifier(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:12]


def model_name(value):
    # Custom deployment names can contain organization identifiers: do not export them.
    if isinstance(value, str) and re.fullmatch(r'(?:gpt-|claude-|gemini-|o[134](?:-|$))[A-Za-z0-9._-]{0,70}', value):
        return value
    return 'custom-or-unknown'


class Collector:
    def __init__(self, source, cutoff, now):
        self.source, self.cutoff, self.now = source, cutoff, now
        self.events, self.seen, self.calls = [], set(), {}
        self.rows_in_range = self.omitted = 0

    def add(self, feature, phase, stamp, key, **fields):
        signature = (feature, phase, key)
        if signature in self.seen:
            return
        if len(self.events) >= LIMIT:
            self.omitted += 1
            return
        self.seen.add(signature)
        self.events.append(dict(id='e'+str(len(self.events)+1), feature=feature, phase=phase,
                                date=stamp, actor='agent' if phase in ('requested','returned','error') else 'runtime',
                                **fields))

    def call(self, name, namespace, call_id, stamp, skill=None):
        if not isinstance(name,str):
            return
        namespace = namespace if isinstance(namespace,str) else ''
        qualified = namespace + '.' + name
        tail = name.rsplit('.',1)[-1]
        if name.startswith('mcp__') or namespace.startswith(('mcp__','mcp.')):
            feature = 'mcp'
        elif self.source == 'claude' and name == 'Skill':
            feature = 'skill'
        elif tail in ('spawn_agent','create_subagent','invoke_subagent') or (self.source == 'claude' and name in ('Agent','Task')):
            feature = 'delegation'
        elif tail in ('send_message','send_message_to_agent','followup_task','wait_agent','wait_for_subagents','interrupt_agent'):
            feature = 'coordination'
        else:
            feature = 'opaque_tool'
        # Tool and skill names are hashed; no inputs, scripts, URLs, credentials or tool results are stored.
        target = identifier(skill if feature == 'skill' and isinstance(skill,str) else qualified)
        key = str(call_id) if isinstance(call_id,str) else 'row-'+str(self.rows_in_range)
        if len(self.calls) < LIMIT:
            self.calls[key] = feature, target
        self.add(feature, 'requested', stamp, key, target=target)

    def result(self, call_id, stamp, error=False):
        if not isinstance(call_id,str) or call_id not in self.calls:
            return
        feature, target = self.calls[call_id]
        self.add(feature, 'error' if error is True else 'returned', stamp, call_id, target=target)

    def feed(self, row):
        date = base.parse_time(row.get('timestamp') or row.get('created_at'))
        if not date or not self.cutoff <= date <= self.now or row.get('isSidechain'):
            return
        self.rows_in_range += 1
        stamp = date.isoformat()
        p = row.get('payload') or {}
        if not isinstance(p,dict):
            p = {}
        if self.source == 'codex':
            if row.get('type') == 'turn_context':
                if p.get('model'):
                    value=model_name(p['model']);self.add('model','recorded',stamp,(stamp,value),value=value)
                if p.get('effort') in ('none','minimal','low','medium','high','xhigh','max','ultra'):
                    value=p['effort'];self.add('effort','recorded',stamp,(stamp,value),value=value)
            if row.get('type') == 'response_item':
                if p.get('type') in ('function_call','custom_tool_call'):
                    self.call(p.get('name'),p.get('namespace'),p.get('call_id') or p.get('id'),stamp)
                elif p.get('type') in ('function_call_output','custom_tool_call_output'):
                    self.result(p.get('call_id'),stamp,p.get('is_error'))
                elif p.get('type') == 'compaction':
                    self.add('compaction','recorded',stamp,stamp)
        elif self.source == 'claude':
            message=row.get('message') or {}
            if not isinstance(message,dict):
                return
            if row.get('type') == 'assistant' and message.get('model'):
                value=model_name(message['model']);self.add('model','recorded',stamp,(stamp,value),value=value)
            content=message.get('content')
            if not isinstance(content,list):
                return
            for block in content:
                if not isinstance(block,dict):continue
                if row.get('type') == 'assistant' and block.get('type') == 'tool_use':
                    args=block.get('input') or {}
                    self.call(block.get('name'),'',block.get('id'),stamp,args.get('skill') if isinstance(args,dict) else None)
                elif row.get('type') == 'user' and block.get('type') == 'tool_result':
                    self.result(block.get('tool_use_id'),stamp,block.get('is_error'))

    def finish(self):
        return dict(schema=VERSION, source=self.source, status='unsupported' if self.source=='antigravity' else 'partial',
                    events=self.events, omitted_events=self.omitted, limit_per_file=LIMIT)


def size(value):
    return len(json.dumps(value,ensure_ascii=False,separators=(',',':')))


def excerpt(record, start, end, budget):
    """Only facts within the excerpt, plus the latest prior model/effort snapshot."""
    record = record or dict(status='unavailable',events=[],omitted_events=0)
    start,end=base.parse_time(start),base.parse_time(end)
    candidates=[dict(e,scope='excerpt') for e in record['events'] if start <= base.parse_time(e['date']) <= end]
    for feature in ('model','effort'):
        before=[e for e in record['events'] if e['feature']==feature and base.parse_time(e['date'])<start]
        if before:candidates.insert(0,dict(max(before,key=lambda e:base.parse_time(e['date'])),scope='prior_context'))
    payload=dict(status=record['status'],events=[],omitted_events=len(record['events'])+record['omitted_events'])
    for e in candidates:
        if len(payload['events']) >= 6:break
        proposed=dict(payload,events=payload['events']+[e])
        if size(proposed)<=budget:payload=proposed
    payload['omitted_events']-=len(payload['events'])
    return payload


def aggregate(records):
    sources=Counter(); counts={};models=set();efforts=set();omitted=0
    for record in records:
        sources[record['source']]+=1;omitted+=record['omitted_events']
        for e in record['events']:
            feature=e['feature'];counts.setdefault(feature,Counter())[e['phase']]+=1
            if feature=='model':models.add(e['value'])
            if feature=='effort':efforts.add(e['value'])
    return dict(schema=VERSION,sessions=sum(sources.values()),sources=dict(sources),
                features=[dict(id=k,label=label,**dict(counts.get(k,{}))) for k,label in FEATURES.items()],
                models=sorted(models),efforts=sorted(efforts),omitted_events=omitted,
                limit_per_file=LIMIT,limitations={s:LIMITATIONS[s] for s in sources},
                attribution='unknown',note='Partial execution records, not user intent, feature availability, task success, or competence. Zero means no matched record in this scan, not no usage.')
