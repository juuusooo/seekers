"""Who wins which requests in the 20:00 test final, from the public feed.
Exact labels where a feed interval is all-won or all-lost; cell win rates from interval counts (least squares)."""
import sys, bisect, collections, json
import numpy as np
sys.path.insert(0, 'research/juhus_gap')
from load import frames, reveal, events

F = frames()
i0 = max(i for i, f in enumerate(F) if f[1] == 'scheduled')
R = F[i0 + 1:]
rv = reveal()
REQ = [x for x in rv['requests']]
TEAMS = ['juhus', 'mathnet1', 'progresful', 'source-exp', 'pelaaja-juhlii', 'team-anonymous', 'klmisbest', 'eth', 'team-moonshot']

def feats(x):
    r = x['request']
    leg = r['legs'][0]
    lists = {o['kind']: o['listPriceCents'] / 100 for o in r['options']}
    lst = min(lists.values())
    typ = r['referenceFeeCents'] / 100
    day = r['arrivedAt'] // 1440
    dl = max(o['deadline'] for o in r['options'])
    return dict(id=r['id'], day=day, rb=r['respondBy'], typ=typ, list=lst, tl=typ / lst, nleg=len(r['legs']),
                kinds=tuple(sorted(lists)), slackH=(dl - r['arrivedAt']) / 60, dueDay=dl // 1440,
                pick=leg['pickup']['placeId'], drop=leg['delivery']['placeId'], prem=leg['car']['premium'],
                note=r['note'] is not None, ours=x['outcome'] == 'won', dealer=r['dealerId'],
                q=min(x['quote'].values()) / 100 / lst if x['quote'] else None)

X = [feats(x) for x in REQ]
# feed intervals
nows, seen = [], set()
series = {t: [] for t in TEAMS}
for now, st, tm in R:
    if now in seen:
        for t in TEAMS: series[t][-1] = tm[t]
        continue
    seen.add(now); nows.append(now)
    for t in TEAMS: series[t].append(tm[t])
edges = [0] + nows
rb = np.array([x['rb'] for x in X])
iv = np.searchsorted(np.array(nows), rb, side='left')  # interval index holding respondBy (edges[i] < rb <= nows[i])
nI = len(nows)
dwin = {t: np.diff([0] + [s[0] for s in series[t]]) for t in TEAMS}

def labels(t):
    """request index -> True/False where the interval is all-won or all-lost."""
    by = collections.defaultdict(list)
    for j, i in enumerate(iv): by[i].append(j)
    lab = {}
    for i, js in by.items():
        d = dwin[t][i]
        if d <= 0:
            for j in js: lab[j] = False
        elif d >= len(js):
            for j in js: lab[j] = True
    return lab

def cellrates(t, cellfn):
    """least squares: interval wins = sum over cells of rate x count."""
    cells = sorted({cellfn(x) for x in X}, key=str)
    A = np.zeros((nI, len(cells)))
    for j, x in enumerate(X): A[iv[j], cells.index(cellfn(x))] += 1
    keep = A.sum(1) > 0
    p, *_ = np.linalg.lstsq(A[keep], np.clip(dwin[t][keep], 0, None), rcond=None)
    return dict(zip(cells, p)), dict(zip(cells, A.sum(0)))

if __name__ == '__main__':
    lab = labels('team-anonymous')
    ok = sum(lab[j] == X[j]['ours'] for j in lab)
    print('own labels', len(lab), 'right', ok, 'won share labelled', np.mean([lab[j] for j in lab]), 'true', np.mean([x['ours'] for x in X]))
    for t in TEAMS:
        l = labels(t); print(t, 'labelled', len(l), 'won', sum(l.values()), 'final orders', series[t][-1][0], 'sum pos steps', int(np.clip(dwin[t], 0, None).sum()))
    def show(name, fn):
        print('\n==', name)
        rows = {t: cellrates(t, fn) for t in TEAMS}
        cells = list(rows[TEAMS[0]][0])
        print('%-22s %5s ' % ('cell', 'n') + ' '.join('%7s' % t[:7] for t in TEAMS) + '   ours-true')
        for c in cells:
            tr = np.mean([x['ours'] for x in X if fn(x) == c])
            print('%-22s %5d ' % (str(c)[:22], rows[TEAMS[0]][1][c]) + ' '.join('%7.2f' % rows[t][0][c] for t in TEAMS) + '   %.2f' % tr)
    show('request day', lambda x: x['day'])
    show('typical / list', lambda x: min(4, int(x['tl'] / 0.2)))
    show('option kinds', lambda x: '+'.join(k[:4] for k in x['kinds']))
    show('slack hours (longest option)', lambda x: 12 * min(8, int(x['slackH'] // 12)))
    show('list price', lambda x: [0, 50, 80, 120, 200, 1e9][bisect.bisect([50, 80, 120, 200], x['list'])])
    show('premium', lambda x: x['prem'])
    show('legs', lambda x: min(x['nleg'], 3))
    show('hour of day', lambda x: 3 * ((x['rb'] % 1440) // 180))
