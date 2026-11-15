import gzip, json, glob, os, collections, sys
import numpy as np, pandas as pd
fs=[x[:-len('.reveal.json.gz')]+'.events.json.gz' for x in sorted(glob.glob('runs/events/*.reveal.json.gz'), key=os.path.getmtime)[-900:]]
rows=[]; nw=0
for f in fs:
    w=f[:-len('.events.json.gz')]
    try:
        ev=json.load(gzip.open(f)); snap=json.load(gzip.open(w+'.snapshot.json.gz')); rv=json.load(gzip.open(w+'.reveal.json.gz'))
    except Exception: continue
    if snap.get('level',8)!=8 and rv.get('level',8)!=8: continue
    ref={r['request']['id']:r['request']['referenceFeeCents'] for r in rv['requests']}
    gigs={g['id']:g for g in snap['gigs']}
    if len(gigs)<200: continue
    nw+=1
    nbook=collections.Counter(); last={}
    for e in ev:
        k=e['kind']
        if k=='gig_booked':
            g=gigs.get(e['gigId'])
            if not g: continue
            os_=sorted({s['orderId'] for s in g['stops']}); typ=sum(ref.get(o,0) for o in os_)
            if not typ: continue
            sch=g['schedule']; nbook[e['gigId']]+=1
            first=min(s['at'] for s in g['stops'] if 'at' in s) if False else None
            last[e['gigId']]=dict(w=nw,at=e['at'],fee=e['feeCents']/typ,open=sch[0]['feeCents']/typ,atopen=e['feeCents']<=sch[0]['feeCents'],n=len(os_),k=nbook[e['gigId']],posted=g['postedAt'],day=e['at']//1440,hour=(e['at']%1440)//60,typ=typ/100,drop=0,start=None,drv=e['driverId'])
        elif k=='gig_dropped' and e['gigId'] in last:
            r=last.pop(e['gigId']); r['drop']=1; r['held']=e['at']-r['at']; r['dhour']=(e['at']%1440)//60; rows.append(r)
        elif k=='gig_started' and e['gigId'] in last:
            last[e['gigId']]['start']=e['at']
    for r in last.values():
        if r['start']: r['held']=r['start']-r['at']; rows.append(r)
df=pd.DataFrame(rows); df.to_pickle(sys.argv[1]); print('worlds',nw,'bookings',len(df),'drop rate',df['drop'].mean().round(3))
