import pandas as pd, numpy as np
pd.set_option('display.width',250)
df=pd.read_pickle('runs/testfinal_1114_2000/rank_analysis/req3.pkl'); w=df[df.won&(df.status=='delivered')].copy()
w['dd']=w.rev_at//1440; w['cr']=(w.fee+w.refund+w.other)/w.price; w['hi']=w.cr>0.8
w['wait_h']=(w.booked_at-w.posted)/60; w['lead_h']=(w.deadline-w.arr)/60
w['kind']=np.where(w.late,'late',np.where(w.drops>0,'dropped',np.where(w.dlclose,'warned',np.where(w.paid_fee_gig>w.open_fee_gig*1.001,'raised','at open'))))
print('all: cost', (w.fee+w.refund+w.other).sum().round(), 'rev', w.price.sum().round())
g=w.groupby('kind').agg(n=('id','size'),rev=('price','sum'),fee=('fee','sum'),refund=('refund','sum'),ref=('ref','sum'),margin=('margin','sum'),plist=('price',lambda x:0))
g['fee/ref']=g.fee/g.ref; g['cost/rev']=(g.fee+g.refund)/g.rev; g['m/ord']=g.margin/g.n
print(g.round(2).to_string())
print('\nby delivery day x kind: n, cost/rev')
print(w.pivot_table(index='dd',columns='kind',values='id',aggfunc='size',fill_value=0).to_string())
x=w.groupby(['dd','kind']).apply(lambda d:(d.fee+d.refund).sum()/d.price.sum()).unstack().round(2); print(x.to_string())
print('\nhi-cost (>0.8) orders by delivery day, option, aday')
print(w[w.hi].groupby(['dd','option','aday']).agg(n=('id','size'),rev=('price','sum'),cost=('fee','sum'),refund=('refund','sum'),drops=('drops','sum'),pl=('price',lambda x:(x/w.loc[x.index,'list']).mean()),fr=('fee',lambda x:(x/w.loc[x.index,'ref']).mean())).round(2).to_string())
print('\nexcess cost over 0.60 x price in hi orders:', ((w.fee+w.refund-0.6*w.price)[w.hi]).sum().round(), 'n', w.hi.sum())
print('what if every dropped/warned/late order had the at-open cost ratio per day:')
base=w[w.kind=='at open'].groupby('dd').apply(lambda d:d.fee.sum()/d.ref.sum())
ex=0
for k in ['dropped','warned','late','raised']:
    d=w[w.kind==k]; e=(d.fee+d.refund-d.ref*d.dd.map(base)).sum(); print(k,len(d),round(e)); ex+=e
print('total excess',round(ex))
