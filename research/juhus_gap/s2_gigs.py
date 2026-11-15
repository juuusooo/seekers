import pandas as pd, numpy as np, json
P='runs/testfinal_1114_2000/rank_analysis/'
b=pd.read_pickle(P+'board.pkl'); df=pd.read_pickle(P+'req3.pkl')
ME='team-anonymous'
fin=b[b.now==b.now.max()].set_index('team')
top=fin[fin.ranked].sort_values('marginCents',ascending=False).head(14).index.tolist()
T=[ME]+[t for t in top if t!=ME]
rev=b[b.team.isin(T)].pivot(index='now',columns='team',values='revenueCents')/100
mar=b[b.team.isin(T)].pivot(index='now',columns='team',values='marginCents')/100
nows=rev.index.values
print('frames',len(nows),'median gap',np.median(np.diff(nows)))
dr=rev.diff().fillna(rev.iloc[0]); dm=mar.diff().fillna(mar.iloc[0])
# truth ours: gigs paid
ev=json.load(open('runs/testfinal_1114_2000/events.json'))
fees=[(e['line']['at'],-e['line']['cents']/100) for e in ev if e['kind']=='ledger' and e['line']['kind']=='driver_fee']
revs=[(e['line']['at'],e['line']['cents']/100) for e in ev if e['kind']=='ledger' and e['line']['kind']=='revenue']
print('our true: fee lines',len(fees),'revenue lines',len(revs))
ft=np.array([a for a,_ in fees]); iv=np.searchsorted(nows,ft,side='left')
print('our true distinct frames with a fee line',len(set(iv)),' frames with rev step (feed)',(dr[ME]>0).sum())
hour=(nows%1440)//60; day=nows//1440
res=[]
for t in T:
    step=dr[t]>0.005
    # poisson estimate of gig completions by (day,hour) bucket
    g=0
    for (d,h),idx in pd.Series(range(len(nows))).groupby([day,hour]).groups.items():
        n=len(idx); z=(~step.values[idx]).sum()
        if z==n: continue
        p0=max(z,0.5)/n
        g+=-np.log(p0)*n
    n=fin.wonOrders[t]; R=fin.revenueCents[t]/100; M=fin.marginCents[t]/100
    res.append(dict(team=t,margin=M,orders=n,stepframes=int(step.sum()),gigs_est=round(g),orders_per_gig=round(n/g,2),rev_per_order=round(R/n,1),cost_per_order=round((R-M)/n,1),cost_share=round(1-M/R,3),
        med_step=round(dr[t][step].median(),0),p90_step=round(dr[t][step].quantile(.9),0)))
print(pd.DataFrame(res).to_string())
print('our true orders per paid gig',len(revs)/len(fees))
# hour of delivery revenue share
hb=pd.cut(hour,[-1,6,9,12,15,18,21,24])
print((dr[T[:8]].groupby(hb).sum()/dr[T[:8]].sum()).round(3).to_string())
dr.to_pickle('/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/73e9949c-c810-4dc2-847d-4deed9c32ee9/scratchpad/dr.pkl'); dm.to_pickle('/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/73e9949c-c810-4dc2-847d-4deed9c32ee9/scratchpad/dm.pkl')
