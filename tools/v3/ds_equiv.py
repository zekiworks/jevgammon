"""Replay 20 stored League 2 exchanges (random from the last 400 matching) against another server
and compare the letter probabilities (last line: "same top letter N/20, ...").
   python3 tools/v3/ds_equiv.py <which> <url>   which: ds-off | qwen-off | lfm-off | gemma-off"""
import re, json, math, random, sqlite3, statistics, sys, time, urllib.request

DB = '/home/cbasaran/code/jevgammon/v3.db'
WHICH, BASE = sys.argv[1], sys.argv[2].rstrip('/')
FILTERS = {
    'ds-off': ("t.provider = 'openrouter:fireworks' and e.request like '%deepseek/deepseek-v4.1-flash%' "
               "and e.request like '%\"enabled\":false%'"),
    'qwen-off': ("e.request like '%\"model\":\"qwen3.8-27b\"%' and e.request like '%\"enable_thinking\":false%' "
                 "and t.created_at > '2026-10-19T22:26'"),
    'lfm-off': ("e.request like '%\"model\":\"lfm2.5-24b-a2b\"%' and e.request like '%<think></think>Answer:%' "
                "and t.created_at > '2026-10-19T22:26'"),
    'gemma-off': ("e.request like '%\"model\":\"gemma-4-31B-it\"%' and e.request like '%\"enable_thinking\":false%' "
                  "and t.created_at > '2026-10-19T22:26'"),
}
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=60)
rows = con.execute(f"""
    select e.id, e.request, e.response from exchanges e join turns t on t.id = e.turn_id
    where {FILTERS[WHICH]} and e.response is not null and e.response like '%top_logprobs%'
    order by e.id desc limit 400""").fetchall()
random.seed(20261020)
sample = random.sample(rows, 20)

def letter_probs(resp, n, prefill):
    content = resp['choices'][0]['logprobs']['content']
    letters = [chr(65 + i) for i in range(n)]
    core = lambda t: t.strip().strip('([{\'".,:)]}')
    for tok in content[:1] if prefill else content:
        if prefill or core(tok['token']) in letters:
            probs = [0.0] * n
            for alt in tok['top_logprobs']:
                t = core(alt['token'])
                if t in letters:
                    probs[ord(t) - 65] += math.exp(alt['logprob'])
            s = sum(probs)
            return [p / s for p in probs] if s else None
    return None


same, dps, lat = 0, [], []
for eid, req, stored in sample:
    body = json.loads(req)
    if WHICH == 'ds-off' and 'openrouter' not in BASE:
        for k in ('provider', 'usage', 'reasoning'):
            body.pop(k, None)
        body['model'] = 'deepseek-v4.1-flash'
        body['chat_template_kwargs'] = {'thinking': False}
    prefill = bool(body.get('continue_final_message'))
    n = len(re.findall(r'^[A-Z]\. ', body['messages'][1]['content'], re.M))
    s = letter_probs(json.loads(stored), n, prefill)
    if s is None:
        print(eid, 'stored response has no letter probabilities'); continue
    t0 = time.time()
    headers = {'Content-Type': 'application/json'}
    if 'openrouter' in BASE:
        headers['Authorization'] = 'Bearer ' + __import__('os').environ['OPENROUTER_API_KEY']
    resp = json.load(urllib.request.urlopen(urllib.request.Request(
        BASE + '/chat/completions', json.dumps(body).encode(), headers), timeout=900))
    lat.append(time.time() - t0)
    local = letter_probs(resp, n, prefill)
    if local is None:
        print(eid, 'no letter probabilities:', resp['choices'][0]['message'].get('content'))
        continue
    a, b = max(range(n), key=s.__getitem__), max(range(n), key=local.__getitem__)
    same += a == b
    dps.append(max(abs(x - y) for x, y in zip(s, local)))
    print(eid, n, chr(65 + a), chr(65 + b), f'{s[a]:.3f}', f'{local[b]:.3f}', f'dp={dps[-1]:.3f}', f'{lat[-1]:.2f}s')
print(f'{WHICH} @ {BASE}: same top letter {same}/20, max |dp| {max(dps):.3f}, '
      f'median |dp| {statistics.median(dps):.4f}, median latency {statistics.median(lat):.2f}s')
