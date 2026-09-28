#!/usr/bin/env python3
"""Bounded, resumable OpenRouter image executor. Linux, Python 3.10+, Pillow.

The LLM plans and inspects; this CLI validates paths/versions, renders prompts,
serializes spending, persists attempts, and publishes only hash-reviewed assets.
It is a cooperative guard, not an OS security boundary for unrestricted agents.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

from PIL import Image

API = 'https://openrouter.ai/api/v1/images'
MODEL = 'openai/gpt-image-2.5-sunburst'
CHECKS = ('sources', 'context', 'text', 'visual_claims', 'arrows', 'learning_goal', 'phone', 'a4')


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def money(value):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError('Invalid nonnegative amount')
    return result


def within(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError('Path escapes configured root')
    return path


def nonempty(obj, keys):
    for key in keys:
        if not obj.get(key):
            raise ValueError('Required field: ' + key)


def load_job(config, job_path):
    job = read(job_path)
    nonempty(job, ['id', 'request_id', 'learner', 'target', 'role', 'sources', 'plan'])
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}', job['id']):
        raise ValueError('Invalid stable job ID')
    if job['request_id'] != config['request_id']:
        raise ValueError('Request not authorized by this configuration')
    repo = Path(config['learners'][job['learner']]['repo']).resolve()
    target = within(repo, job['target'])
    allowed = config['learners'][job['learner']]['targets']
    if job['target'] not in allowed or not target.is_file():
        raise ValueError('Target outside authorized page allowlist')
    if job['role'] not in ('banner', 'infographic', 'infographic-2'):
        raise ValueError('Unsupported visual role')
    if len(job['sources']) > 30:
        raise ValueError('Excessive source list')
    if job['target'] not in [s['path'] for s in job['sources']]:
        raise ValueError('Target version missing')
    for source in job['sources']:
        if sha(within(repo, source['path'])) != source['sha256']:
            raise ValueError('Stale source: ' + source['path'])
    plan = job['plan']
    nonempty(plan, ['goal', 'scope', 'decision_reason', 'context', 'composition', 'visible_text', 'claims', 'style', 'aspect_ratio', 'constraints'])
    if plan['aspect_ratio'] not in ('21:9', '3:2', '2:3', '4:3', '3:4'):
        raise ValueError('Unsupported aspect ratio')
    if job['role'] == 'banner' and plan['aspect_ratio'] != '21:9':
        raise ValueError('Banner must remain wide and low')
    if not isinstance(plan['visible_text'], list) or not all(isinstance(x, str) for x in plan['visible_text']):
        raise ValueError('Exact visible text must be a list of strings')
    for claim in plan['claims']:
        nonempty(claim, ['text', 'source'])
    return job, repo


def compile_prompt(job):
    p = job['plan']
    kind = 'széles, alacsony tanulási fejlécet' if job['role'] == 'banner' else 'önállóan érthető tanító infografikát'
    lines = [f'Készíts {kind}, magyar nyelven.', 'Tanulási cél: ' + p['goal'],
             'Látható bevezetés és kontextus: ' + p['context'],
             'Kompozíció és olvasási sorrend: ' + p['composition'],
             'Kizárólag az alábbi szövegek jelenjenek meg feliratként, pontosan, ebben az olvasási sorrendben. Minden más tervmező rajzolási utasítás, nem képfelirat; ne másold a képre a munkafolyamatot vagy az ellenőrzési szempontokat:',
             *[json.dumps(t, ensure_ascii=False) for t in p['visible_text']],
             'Képi állítások: ' + '; '.join(c['text'] for c in p['claims'])]
    for key, label in [('relationships', 'Kapcsolatok és irányok'), ('sequence', 'Sorrend és időskála'),
                       ('comparison', 'Közös összehasonlítási szempontok'), ('metaphor', 'Metafora megfeleltetése és korlátja'),
                       ('example', 'Ellenőrzött példa és megengedett tanulság'), ('optional', 'Elhagyható motívumok')]:
        if p.get(key):
            lines.append(label + ': ' + json.dumps(p[key], ensure_ascii=False))
    lines += ['Stílus: ' + p['style'], 'Képarány: ' + p['aspect_ratio'],
              'Pontossági korlátok: ' + p['constraints'],
              'A kép legyen szép és elnézegethető, világos fő olvasattal. A feliratok legyenek nagyok, hibátlan magyar ékezetekkel. Ne adj hozzá új tényt, feliratot vagy kapcsolatot. A kötelező tartalom elé helyezd a megértéshez szükséges kontextust. Ne bízd a hiányzó magyarázatot külső szövegre.']
    if job['role'] != 'banner':
        lines.append('A4-es elhelyezéshez a tartalom körül legalább 10 mm biztonsági margó. A rajz legyen nyomtatható, torzítás nélküli illesztéssel; ne apró betűvel próbáld elhelyezni a lényeget.')
    return '\n\n'.join(lines) + '\n'


@contextmanager
def locked(config):
    state = Path(config['state_dir']).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'executor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = state / 'ledger.json'
        ledger = read(ledger_path) if ledger_path.exists() else {'request_id': config['request_id'], 'jobs': {}}
        if ledger['request_id'] != config['request_id']:
            raise ValueError('Existing state belongs to another request; do not reset it')
        yield state, ledger_path, ledger


def spent(ledger):
    return sum((money(a['cost_usd']) for j in ledger['jobs'].values() for a in j['attempts'] if a.get('cost_usd') is not None), Decimal(0))


def api_call(payload, config):
    # Explicit env file; never print it, return it, or use shell evaluation.
    values = dict(os.environ)
    if config.get('env_file'):
        for line in Path(config['env_file']).expanduser().read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k.strip() == 'OPENROUTER_API_KEY':
                    values[k.strip()] = v.strip().strip('\"\'')
    key = values.get('OPENROUTER_API_KEY')
    if not key:
        raise ValueError('Missing OPENROUTER_API_KEY')
    req = urllib.request.Request(API, data=json.dumps(payload).encode(), headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    # Avoid forwarding authorization through redirects. No retries.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with urllib.request.build_opener(NoRedirect).open(req, timeout=300) as response:
        return json.load(response)


def finish_response(folder, result, attempt):
    # Persist the provider result before image processing so a crash is reconcilable.
    write(folder / 'response.json', result)
    cost = result.get('usage', {}).get('cost', result.get('cost'))
    if cost is not None:
        attempt['cost_usd'] = str(money(cost))
    data = result['data']
    if len(data) != 1 or data[0].get('media_type', 'image/png') not in ('image/png', 'image/jpeg', 'image/webp'):
        raise ValueError('Expected exactly one raster image')
    raw = base64.b64decode(data[0]['b64_json'], validate=True)
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError('Image too large')
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        width, height = im.size
        im.save(folder / 'image.png')
    attempt.update({'sha256': sha(folder / 'image.png'), 'width': width, 'height': height,
                    'state': 'generated' if cost is not None else 'unknown', 'finished_at': now()})
    metadata = {k: v for k, v in result.items() if k != 'data'}
    write(folder / 'generation.json', metadata)


def run_generate(config, job_path, repair=None, transport=None):
    job, repo = load_job(config, job_path)
    transport = transport or api_call
    fingerprint = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
    logical = job['learner'] + ':' + job['target'] + ':' + job['role']
    with locked(config) as (state, ledger_path, ledger):
        for other in ledger['jobs'].values():
            if other['logical'] == logical and other['id'] != job['id']:
                raise ValueError('Logical target already registered; resume its original ID')
        entry = ledger['jobs'].get(job['id'])
        if entry and entry['fingerprint'] != fingerprint:
            raise ValueError('Job changed; use repair instructions, not a reset')
        if entry and entry.get('accepted'):
            return {'state': 'accepted', 'reused': True, **entry['accepted']}
        # Any unknown charge blocks the whole request, including other jobs.
        for other in ledger['jobs'].values():
            if any(a['state'] == 'unknown' or a.get('cost_usd') is None for a in other['attempts']):
                raise ValueError('Reconcile pending provider call/cost before new spending')
        if entry and entry['attempts'][-1]['state'] == 'generated':
            return {'state': 'needs-review', **entry['attempts'][-1]}
        if entry and (not repair or entry['attempts'][-1]['state'] != 'rejected'):
            raise ValueError('Repair requires a recorded rejected review and targeted instructions')
        if entry and len(entry['attempts']) >= int(config.get('max_attempts', 3)):
            raise ValueError('Attempt bound reached; select a usable candidate or request a specific exception')
        if repair and not entry:
            raise ValueError('No initial attempt to repair')
        reserve = money(config['reservation_usd'])
        if not reserve or spent(ledger) + reserve > money(config['max_total_usd']):
            raise ValueError('Whole-request spending bound would be exceeded')
        learner_spent = sum((money(a['cost_usd']) for j in ledger['jobs'].values() if j['learner'] == job['learner'] for a in j['attempts']), Decimal(0))
        if learner_spent + reserve > money(config['learners'][job['learner']]['max_usd']):
            raise ValueError('Learner spending bound would be exceeded')
        if not entry:
            entry = {'id': job['id'], 'learner': job['learner'], 'logical': logical, 'fingerprint': fingerprint, 'attempts': []}
            ledger['jobs'][job['id']] = entry
        attempt_no = len(entry['attempts']) + 1
        folder = state / job['id'] / str(attempt_no)
        folder.mkdir(parents=True, exist_ok=True)
        prompt = compile_prompt(job)
        if repair:
            prompt += '\nCélzott javítás; az egyéb helyes részeket őrizd meg:\n' + Path(repair).read_text()
        (folder / 'prompt.txt').write_text(prompt)
        payload = {'model': MODEL, 'prompt': prompt, 'quality': 'high', 'aspect_ratio': job['plan']['aspect_ratio'], 'n': 1}
        write(folder / 'request.json', payload)
        attempt = {'number': attempt_no, 'state': 'unknown', 'started_at': now(), 'reserved_usd': str(reserve), 'cost_usd': None, 'folder': str(folder)}
        entry['attempts'].append(attempt)
        write(ledger_path, ledger)  # Durable reservation BEFORE any network activity.
        try:
            result = transport(payload, config)
            finish_response(folder, result, attempt)
            write(ledger_path, ledger)
            return {'job': job['id'], **attempt, 'total_usd': str(spent(ledger))}
        except Exception as exc:
            # Preserve reserved/unknown; never print raw provider errors or secrets.
            attempt['failure_type'] = type(exc).__name__
            write(ledger_path, ledger)
            raise ValueError('Provider attempt unresolved; inspect saved response and reconcile, no automatic retry') from None


def reconcile(config, job_path):
    job, _ = load_job(config, job_path)
    with locked(config) as (_, ledger_path, ledger):
        attempt = ledger['jobs'][job['id']]['attempts'][-1]
        if attempt['state'] != 'unknown':
            return {'state': attempt['state'], 'no_change': True}
        folder = Path(attempt['folder'])
        if not (folder / 'response.json').exists():
            raise ValueError('No saved response: obtain provider billing/output evidence; do not reset or retry')
        finish_response(folder, read(folder / 'response.json'), attempt)
        write(ledger_path, ledger)
        return attempt


def review(config, job_path, review_path):
    job, repo = load_job(config, job_path)
    report = read(review_path)
    nonempty(report, ['verifier', 'checked_at', 'sha256', 'observed', 'decision', 'checks'])
    if report['decision'] not in ('accepted', 'rejected'):
        raise ValueError('Review must explicitly accept or reject')
    with locked(config) as (state, ledger_path, ledger):
        entry = ledger['jobs'][job['id']]
        fingerprint = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
        if entry['fingerprint'] != fingerprint:
            raise ValueError('Job changed since generation; review original job')
        candidates = [a for a in entry['attempts'] if a.get('sha256') == report['sha256']]
        if not candidates:
            raise ValueError('Review hash not found among this job attempts')
        attempt = candidates[-1]
        if attempt.get('cost_usd') is None or attempt['state'] == 'unknown':
            raise ValueError('Unresolved provider cost/status')
        file = Path(attempt['folder']) / 'image.png'
        if sha(file) != report['sha256']:
            raise ValueError('Image changed since review')
        if entry.get('accepted'):
            if entry['accepted']['sha256'] != report['sha256']:
                raise ValueError('Already accepted another version; do not silently replace')
            return {'state': 'accepted', **entry['accepted']}
        if report['decision'] == 'accepted':
            if not all(report['checks'].get(key) in ('pass', 'not-applicable') for key in CHECKS):
                raise ValueError('Required QA checks missing or failed')
            if any(report['checks'].get(key) == 'not-applicable' for key in CHECKS if key != 'arrows'):
                raise ValueError('Only arrow check may be inapplicable')
            if report.get('material_defects'):
                raise ValueError('Materially defective image cannot be published')
            # Versioned destination determined by role and ID, never arbitrary job output path.
            relative = 'wiki/assets/' + ('banner/' if job['role'] == 'banner' else '') + job['id'] + '.png'
            output = within(repo, relative)
            if output.exists() and sha(output) != report['sha256']:
                raise ValueError('Destination exists with different bytes')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(file.read_bytes())
            entry['accepted'] = {'path': relative, 'sha256': report['sha256'], 'attempt': attempt['number']}
        else:
            nonempty(report, ['material_defects'])
        attempt['state'] = report['decision']
        attempt['review'] = report
        evidence = within(repo, 'docs/evidence/media/' + job['id'])
        evidence.mkdir(parents=True, exist_ok=True)
        write(evidence / 'job.json', job)
        (evidence / f"prompt-{attempt['number']}.txt").write_text((Path(attempt['folder']) / 'prompt.txt').read_text())
        write(evidence / f"review-{attempt['number']}.json", report)
        write(evidence / f"receipt-{attempt['number']}.json", {k: v for k, v in attempt.items() if k not in ('folder', 'review')})
        write(ledger_path, ledger)
        return {'state': report['decision'], **entry.get('accepted', {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Trusted private policy, outside Git')
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('validate', 'prompt', 'generate', 'review', 'reconcile'):
        p = sub.add_parser(command)
        p.add_argument('--job', required=True)
        if command == 'generate':
            p.add_argument('--repair', help='Targeted correction after rejected review; same ID/counters')
        if command == 'review':
            p.add_argument('--report', required=True)
    sub.add_parser('status')
    args = parser.parse_args()
    try:
        config = read(args.config)
        if not 1 <= int(config.get('max_attempts', 3)) <= 3:
            raise ValueError('Default executor supports at most three attempts; explicit exceptions require reviewed policy change')
        if args.command == 'status':
            with locked(config) as (_, _, ledger):
                print(json.dumps({'request_id': config['request_id'], 'spent_usd': str(spent(ledger)), 'cap_usd': config['max_total_usd'], 'jobs': [{ 'id': j['id'], 'attempts': len(j['attempts']), 'state': j['attempts'][-1]['state']} for j in ledger['jobs'].values()]}, ensure_ascii=False))
        elif args.command in ('validate', 'prompt'):
            job, _ = load_job(config, args.job)
            print(compile_prompt(job) if args.command == 'prompt' else json.dumps({'valid': True, 'id': job['id']}))
        elif args.command == 'reconcile':
            print(json.dumps(reconcile(config, args.job), ensure_ascii=False))
        elif args.command == 'generate':
            print(json.dumps(run_generate(config, args.job, args.repair), ensure_ascii=False))
        else:
            print(json.dumps(review(config, args.job, args.report), ensure_ascii=False))
        return 0
    except (ValueError, KeyError, OSError, InvalidOperation) as exc:
        print(json.dumps({'error': str(exc), 'type': type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
