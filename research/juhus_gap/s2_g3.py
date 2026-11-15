import pandas as pd, numpy as np
S='/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/73e9949c-c810-4dc2-847d-4deed9c32ee9/scratchpad/'
dr=pd.read_pickle(S+'dr.pkl'); dm=pd.read_pickle(S+'dm.pkl'); dc=dr-dm
day=pd.Series(dr.index.values//1440,index=dr.index)
T=['team-anonymous','juhus','progresful','pelaaja-juhlii','team-moonshot','mathnet1','source-exp']
pd.set_option('display.width',250)
for name,f in [('revenue',lambda t,m: dr[t][m].sum()),('cost',lambda t,m: dc[t][m].sum()),('cost share',lambda t,m: dc[t][m].sum()/max(1,dr[t][m].sum())),
   ('rev step frames',lambda t,m:(dr[t][m]>0.005).sum()),
   ('median cost/rev of step frames',lambda t,m:(dc[t][m&(dr[t]>0.005)&(dc[t]>0.005)]/dr[t][m&(dr[t]>0.005)&(dc[t]>0.005)]).median()),
   ('share of step frames with cost/rev>0.8',lambda t,m:((dc[t]/dr[t])[m&(dr[t]>0.005)&(dc[t]>0.005)]>0.8).mean()),
   ('share of step frames with cost/rev<0.5',lambda t,m:((dc[t]/dr[t])[m&(dr[t]>0.005)&(dc[t]>0.005)]<0.5).mean()),
   ('negative-margin money (frames dm<0)',lambda t,m: dm[t][m&(dm[t]<0)].sum())]:
    print('\n'+name)
    print(pd.DataFrame({t:{d:round(f(t,(day==d)),3 if 'share' in name or 'median' in name else 0) for d in [0,1,2,3,4,5,7,8]} for t in T}).to_string())
