"""Outage backup price: tied to the competitor's level or to the list price? Win rate of quotes in outage cells
by absolute markup and by markup / the seed's level, split by the seed's level. runs/quotes.parquet."""
import polars as pl, numpy as np
q = (pl.scan_parquet('runs/quotes.parquet').filter((pl.col('n_quoted') > 0) & (pl.col('m_max') - pl.col('m_min') < 0.12))
     .select('seed', 'req', 'at', pl.col('p_first').alias('p'), 'won', m=(pl.col('m_min') + pl.col('m_max')) / 2)
     .with_columns(day=pl.col('at') // 1440, hour=(pl.col('at') % 1440) // 60).collect())
print('quotes', len(q))
# the seed's level: markup where the win rate crosses one half (logistic fit on ln m, all quotes)
def m50(g):
    x = np.log(g['m'].to_numpy()); y = g['won'].to_numpy().astype(float)
    a, b = 0.0, -8.0; xm = x.mean()
    for _ in range(25):
        p = 1 / (1 + np.exp(-(a + b * (x - xm)))); w = p * (1 - p) + 1e-9
        ga, gb = (y - p).sum(), ((y - p) * (x - xm)).sum()
        haa, hab, hbb = w.sum(), (w * (x - xm)).sum(), (w * (x - xm) ** 2).sum()
        det = haa * hbb - hab ** 2
        a += (hbb * ga - hab * gb) / det; b += (haa * gb - hab * ga) / det
    return float(np.exp(xm - a / b))
lv = pl.DataFrame([{'seed': k[0], 'L': m50(g), 'nq': len(g)} for k, g in q.group_by('seed') if len(g) >= 3000])
lv = lv.filter((pl.col('L') > 1.1) & (pl.col('L') < 1.8))
print('seeds with a level', len(lv), 'level quartiles', lv['L'].quantile(.25), lv['L'].median(), lv['L'].quantile(.75))
q = q.join(lv, on='seed').with_columns(r=pl.col('m') / pl.col('L'))
work = q.filter((pl.col('hour') >= 8) & (pl.col('hour') < 18) & (pl.col('day') <= 4))
hi = work.filter(pl.col('r') > 1.1)
cell = hi.group_by('seed', 'day', 'p').agg(n=pl.len(), w=pl.col('won').mean(), nreq=pl.col('req').n_unique())
base = hi['won'].mean(); print('win rate of quotes over 1.1 x level, all cells: %.3f' % base)
hot = cell.filter((pl.col('n') >= 8) & (pl.col('nreq') >= 2) & (pl.col('w') >= 0.6))
dh = hot.group_by('seed', 'day').agg(k=pl.len(), n=pl.col('n').sum()).sort('n', descending=True).group_by('seed').first().filter(pl.col('k') >= 2)
print('seeds with an outage day', len(dh), 'by weekday', dh.group_by('day').len().sort('day').rows())
out = work.join(dh.select('seed', 'day'), on=['seed', 'day']).join(hot.select('seed', 'day', 'p'), on=['seed', 'day', 'p'])
print('outage quotes', len(out), 'requests', out.select('seed', 'req').unique().height)
t = lv.join(dh.select('seed'), on='seed')['L']; c1, c2 = t.quantile(1 / 3), t.quantile(2 / 3)
print('level terciles of those seeds: under %.3f, to %.3f, over' % (c1, c2))
out = out.with_columns(tc=pl.when(pl.col('L') < c1).then(0).when(pl.col('L') < c2).then(1).otherwise(2))
print('\nwin rate by ABSOLUTE markup (x list); columns = cheap / middle / dear weeks (n)')
for lo in np.arange(1.3, 2.3, 0.1):
    row = []
    for tcv in range(3):
        s = out.filter((pl.col('tc') == tcv) & (pl.col('m') >= lo) & (pl.col('m') < lo + 0.1))
        row.append('%.2f (%6d)' % (s['won'].mean() or 0, len(s)) if len(s) > 30 else '   -          ')
    print('%.1f-%.1f  ' % (lo, lo + 0.1) + '   '.join(row))
print('\nwin rate by markup / week level; columns = cheap / middle / dear weeks (n)')
for lo in np.arange(0.9, 1.6, 0.05):
    row = []
    for tcv in range(3):
        s = out.filter((pl.col('tc') == tcv) & (pl.col('r') >= lo) & (pl.col('r') < lo + 0.05))
        row.append('%.2f (%6d)' % (s['won'].mean() or 0, len(s)) if len(s) > 30 else '   -          ')
    print('%.2f-%.2f  ' % (lo, lo + 0.05) + '   '.join(row))
out.write_parquet('/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/4c1b8b55-dea9-44c6-8565-5eb815aa750a/scratchpad/outq.parquet')
