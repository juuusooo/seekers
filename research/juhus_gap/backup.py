"""Is the backup seller's price in an outage tied to the competitor's level (x K) or to the list price?
runs/quotes.parquet: many variants quoted the same request of a seed at different markups -> a win/loss threshold."""
import polars as pl, numpy as np
q = (pl.scan_parquet('runs/quotes.parquet').filter((pl.col('n_quoted') > 0) & (pl.col('m_max') - pl.col('m_min') < 0.12))
     .with_columns(m=(pl.col('m_min') + pl.col('m_max')) / 2)
     .group_by('seed', 'req').agg(lo=pl.col('m').filter(pl.col('won') == 1).max(), hi=pl.col('m').filter(pl.col('won') == 0).min(),
                                  n=pl.len(), at=pl.col('at').first(), p=pl.col('p_first').first(), lst=pl.col('list').first(), typ=pl.col('typ').first())
     .filter(pl.col('lo').is_not_null() & pl.col('hi').is_not_null() & (pl.col('hi') - pl.col('lo') < 0.08) & (pl.col('hi') - pl.col('lo') > -0.03))
     .with_columns(lt=((pl.col('lo') + pl.col('hi')) / 2).log(), day=pl.col('at') // 1440, hour=(pl.col('at') % 1440) // 60)
     .collect())
print('requests with a tight threshold', len(q), 'seeds', q['seed'].n_unique())
# place level over the seed (median over days), then the cell (seed, day, place) excess
pm = q.group_by('seed', 'p').agg(pmed=pl.col('lt').median(), pn=pl.len())
c = (q.filter((pl.col('hour') >= 8) & (pl.col('hour') < 18)).group_by('seed', 'day', 'p').agg(cmed=pl.col('lt').median(), cn=pl.len())
     .join(pm, on=['seed', 'p']).with_columns(ex=pl.col('cmed') - pl.col('pmed')))
hot = c.filter((pl.col('ex') > 0.15) & (pl.col('cn') >= 3))
dayhot = hot.group_by('seed', 'day').agg(k=pl.len(), nreq=pl.col('cn').sum()).sort('nreq', descending=True).group_by('seed').first().filter(pl.col('nreq') >= 12)
print('seeds with an outage day found', len(dayhot))
out = q.join(dayhot.select('seed', 'day'), on=['seed', 'day']).join(hot.select('seed', 'day', 'p'), on=['seed', 'day', 'p']).filter((pl.col('hour') >= 8) & (pl.col('hour') < 18))
# level of the same day outside the hot places, and of the week (other days)
same = q.join(dayhot.select('seed', 'day'), on=['seed', 'day']).join(hot.select('seed', 'day', 'p'), on=['seed', 'day', 'p'], how='anti').group_by('seed').agg(dayL=pl.col('lt').median(), dn=pl.len())
week = q.join(dayhot.select('seed', 'day'), on=['seed', 'day'], how='anti').group_by('seed').agg(weekL=pl.col('lt').median())
s = out.group_by('seed').agg(outL=pl.col('lt').median(), n=pl.len(), q25=pl.col('lt').quantile(0.25), q75=pl.col('lt').quantile(0.75)).join(same, on='seed').join(week, on='seed').filter((pl.col('n') >= 10) & (pl.col('dn') >= 10))
print('seeds used', len(s))
x = s['dayL'].to_numpy(); y = s['outL'].to_numpy(); w = s['weekL'].to_numpy()
for name, xx in [('same-day level outside the region', x), ('week level (other days)', w)]:
    b, a = np.polyfit(xx, y, 1); r = np.corrcoef(xx, y)[0, 1]
    print('%s: ln(backup) = %.3f + %.3f x ln(level), corr %.2f; resid SD %.3f; SD of ln backup %.3f; SD of ratio %.3f' % (name, a, b, r, np.std(y - a - b * xx), np.std(y), np.std(y - xx)))
print('backup x list: median %.3f, quartiles %.3f %.3f' % (np.exp(np.median(y)), np.exp(np.quantile(y, .25)), np.exp(np.quantile(y, .75))))
print('ratio backup / same-day level: median %.3f, quartiles %.3f %.3f' % (np.exp(np.median(y - x)), np.exp(np.quantile(y - x, .25)), np.exp(np.quantile(y - x, .75))))
print('by same-day level tercile: level, backup x list, ratio')
o = np.argsort(x)
for part in np.array_split(o, 4): print('  %.3f  %.3f  %.3f  (n %d)' % (np.exp(x[part].mean()), np.exp(y[part].mean()), np.exp((y - x)[part].mean()), len(part)))
