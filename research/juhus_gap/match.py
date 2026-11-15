"""Match a team's single-delivery feed steps (revenue, fee) to requests: price / list on a 0.01 grid, inside the
delivery window. Gives price level and fee / typical per matched order."""
import sys, collections, json
import numpy as np
sys.path.insert(0, 'research/juhus_gap')
import wins as W
from load import reveal
rv = reveal()
RQ = {x['request']['id']: x['request'] for x in rv['requests']}
nows = np.array(W.nows)

def steps(t):
    s = np.array([(a[1], a[2]) for a in W.series[t]]); d = np.diff(np.vstack([[0, 0], s]), axis=0)
    out = []
    for i in range(len(nows)):
        if d[i, 0] > 0.005: out.append((nows[i - 1] if i else 0, nows[i], round(d[i, 0] * 100), round((d[i, 0] - d[i, 1]) * 100)))
    return out  # (from, to, revenue cents, cost cents)

def match(t, grid=True):
    lab = W.labels(t)
    possible = [j for j in range(len(W.X)) if lab.get(j, True)]  # not known lost
    res = []
    for a, b, P, C in steps(t):
        cands = []
        for j in possible:
            r = RQ[W.X[j]['id']]
            if r['respondBy'] > b: continue
            for o in r['options']:
                if b > o['deadline'] + 4 * 1440 or len(r['legs']) > 1: continue
                m = P / o['listPriceCents']
                if not 1.0 <= m <= 2.6: continue
                if grid and abs(round(P / o['listPriceCents'], 2) * o['listPriceCents'] - P) > 0.51: continue
                cands.append((j, o['kind'], m, b <= o['deadline']))
        res.append((a, b, P, C, cands))
    return res

if __name__ == '__main__':
    for t in ['team-anonymous', 'juhus', 'progresful', 'team-moonshot', 'mathnet1']:
        for grid in [True, False]:
            r = match(t, grid)
            n = collections.Counter(min(3, len({c[0] for c in x[4]})) for x in r)
            print(t, 'grid' if grid else 'any', 'steps', len(r), 'candidates 0/1/2/3+:', [n[k] for k in range(4)])
    # check on ourselves: unique grid matches vs truth
    truth = {x['request']['id']: x for x in rv['requests'] if x['outcome'] == 'won'}
    snap = json.load(open('runs/testfinal_1114_2000/snapshot.json')); price = {o['id']: o['priceCents'] for o in snap['orders']}
    r = match('team-anonymous'); ok = bad = 0
    for a, b, P, C, c in r:
        ids = {x[0] for x in c}
        if len(ids) == 1:
            i = W.X[next(iter(ids))]['id']
            if price.get(i) == P: ok += 1
            else: bad += 1
    print('own unique grid matches right', ok, 'wrong', bad)
