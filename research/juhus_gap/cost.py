"""Our cost per order in the 20:00 test final by segment, and Juhus's cost per typical fee from the feed."""
import sys, json, collections, bisect
import numpy as np
sys.path.insert(0, 'research/juhus_gap')
import wins as W
from load import events
X = W.X; ev = events()
byid = {x['id']: x for x in X}
snap = json.load(open('runs/testfinal_1114_2000/snapshot.json'))
orders = {o['id']: o for o in snap['orders']}
gigorders = collections.defaultdict(set)
for e in ev:
    if e['kind'] in ('picked_up', 'delivered'): gigorders[e['gigId']].add(e['orderId'])
for g in snap['gigs']:
    for s in g['stops']: gigorders[g['id']].add(s['orderId'])
cost = collections.Counter(); rev = collections.Counter(); late = collections.Counter(); delivered = {}
for e in ev:
    if e['kind'] == 'delivered': delivered[e['orderId']] = e['at']
    if e['kind'] != 'ledger': continue
    l = e['line']; c = l['cents'] / 100
    if l['kind'] == 'revenue': rev[l['orderId']] += c
    elif l['kind'] == 'late_refund': late[l['orderId']] -= c
    elif l['orderId']: cost[l['orderId']] -= c
    else:
        os_ = [o for o in gigorders[l['gigId']] if o in byid] or ['?']
        tot = sum(byid[o]['typ'] for o in os_ if o != '?') or 1
        for o in os_: cost[o] -= c * (byid[o]['typ'] / tot if o != '?' else 1)
# pairs and rebooks
drops = collections.Counter()
for e in ev:
    if e['kind'] == 'gig_dropped':
        for o in gigorders[e['gigId']]: drops[o] += 1
paired = {o for g, s in gigorders.items() if len(s) > 1 for o in s}
won = [x for x in X if x['ours'] and x['id'] in rev]
def tab(name, fn):
    print('\n==', name); print('%-18s %4s %7s %7s %7s %7s %7s %6s %6s %6s' % ('cell', 'n', 'price', 'typ', 'fee', 'fee/typ', 'p/list', 'late€', 'drops', 'net'))
    cells = collections.defaultdict(list)
    for x in won: cells[fn(x)].append(x)
    for c in sorted(cells, key=str):
        xs = cells[c]; n = len(xs); i = [x['id'] for x in xs]
        P = sum(rev[k] for k in i); T = sum(x['typ'] for x in xs); C = sum(cost[k] for k in i); L = sum(late[k] for k in i); Ls = sum(x['list'] for x in xs)
        print('%-18s %4d %7.1f %7.1f %7.1f %7.3f %7.3f %6.1f %6.2f %6.1f' % (str(c)[:18], n, P / n, T / n, C / n, C / T, P / Ls, L / n, sum(drops[k] for k in i) / n, (P - C - L) / n))
if __name__ == '__main__':
    print('orders with revenue', len(won), 'cost unallocated', round(cost['?'], 2), 'total fee', round(sum(cost.values()), 2), 'late', round(sum(late.values()), 2))
    tab('all', lambda x: 'all')
    tab('day won', lambda x: x['day'])
    tab('day delivered', lambda x: delivered[x['id']] // 1440)
    tab('option sold', lambda x: orders[x['id']]['option'])
    tab('slack h won->deadline', lambda x: 12 * min(8, int((orders[x['id']]['deadline'] - x['rb']) / 720)))
    tab('typical fee EUR', lambda x: [0, 20, 35, 50, 80, 120][bisect.bisect([20, 35, 50, 80, 120], x['typ']) ])
    tab('premium', lambda x: x['prem'])
    tab('paired', lambda x: x['id'] in paired)
    tab('dropped times', lambda x: min(2, drops[x['id']]))
    tab('Thu Helsinki-region (pick in near80)', lambda x: (x['day'] == 3, x['pick'] in json.load(open('kit-best/core/data/near80.json')).get('helsinki', []) or x['pick'] == 'helsinki'))
    tab('hour won', lambda x: 3 * ((x['rb'] % 1440) // 180))
