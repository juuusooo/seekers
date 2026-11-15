import pandas as pd, numpy as np, json
S='/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/73e9949c-c810-4dc2-847d-4deed9c32ee9/scratchpad/'
dr=pd.read_pickle(S+'dr.pkl'); dm=pd.read_pickle(S+'dm.pkl'); dc=dr-dm
ev=json.load(open('runs/testfinal_1114_2000/events.json'))
L=[e['line'] for e in ev if e['kind']=='ledger']
import collections
print(collections.Counter(l['kind'] for l in L))
# our truth: revenue at vs fee at per gig
rv={l['orderId']:l['at'] for l in L if l['kind']=='revenue'}
fe={l['gigId']:l['at'] for l in L if l['kind']=='driver_fee'}
snap=json.load(open('runs/testfinal_1114_2000/snapshot.json'))
same=diff=0
for g in snap['gigs']:
    if g['id'] in fe:
        os_={s['orderId'] for s in g['stops']}
        for o in os_:
            if o in rv:
                if rv[o]==fe[g['id']]: same+=1
                else: diff+=1
print('order revenue minute == gig fee minute',same,'differs',diff)
nows=dr.index.values; day=nows//1440
rows=[]
for t in dr.columns:
    r=dr[t]; c=dc[t]
    rs=r>0.005; cs=c>0.005; neg=c<-0.005
    rows.append(dict(team=t,rev=r.sum().round(0),cost=c.sum().round(0),rev_frames=int(rs.sum()),cost_frames=int(cs.sum()),rev_no_cost_frames=int((rs&~cs).sum()),rev_in_nocost=round(r[rs&~cs].sum()/r.sum(),3),cost_no_rev_frames=int((cs&~rs).sum()),cost_in_norev=round(c[cs&~rs].sum()/c.sum(),3),
      med_ratio=round((c[rs&cs]/r[rs&cs]).median(),3), q25=round((c[rs&cs]/r[rs&cs]).quantile(.25),3), q75=round((c[rs&cs]/r[rs&cs]).quantile(.75),3)))
print(pd.DataFrame(rows).sort_values('rev',ascending=False).to_string())
