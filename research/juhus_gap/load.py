"""Shared loaders for the 20:00 test final: feed frames, reveal, our events."""
import json, pickle, os
D = 'runs/testfinal_1114_2000/'
CACHE = '/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/4c1b8b55-dea9-44c6-8565-5eb815aa750a/scratchpad/frames.pkl'

def frames():
    """List of (now, {team: (orders, revenue, margin, onTime)}) in feed order, de-duplicated on now."""
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    out = []
    for l in open(D + 'leaderboard_sse.txt', errors='ignore'):
        if not l.startswith('data:'):
            continue
        try:
            d = json.loads(l[5:])
        except Exception:
            continue
        if not isinstance(d, dict) or 'teams' not in d:
            continue
        out.append((d.get('now'), d.get('status'), {x['team']: (x['wonOrders'], x['revenueCents'] / 100, x['marginCents'] / 100, x['onTimeShare']) for x in d['teams']}))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(out, open(CACHE, 'wb'))
    return out

def reveal():
    return json.load(open(D + 'reveal.json'))

def events():
    return json.load(open(D + 'events.json'))
