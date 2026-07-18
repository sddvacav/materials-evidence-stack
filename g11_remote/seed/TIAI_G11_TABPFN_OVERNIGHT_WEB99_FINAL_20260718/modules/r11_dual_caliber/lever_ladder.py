STAGE_ORDER={'data':0,'domain_generalization':1,'features':2,'algorithm':3}
def validate_ladder(levers):
 seen=set();prev=-1
 for x in levers:
  miss={'id','stage','priority','status','requires_receipts','acceptance_receipt'}-set(x)
  if miss:raise ValueError(f'missing {miss}')
  if x['id'] in seen:raise ValueError('duplicate lever id')
  seen.add(x['id']);cur=STAGE_ORDER[x['stage']]
  if cur<prev:raise ValueError('stage order')
  prev=cur
def next_lever(levers,available_receipts):
 validate_ladder(levers);a=set(available_receipts);c=[x for x in levers if x['status'] not in {'BLOCKED','REJECTED'} and set(x['requires_receipts'])<=a and x['acceptance_receipt'] not in a]
 return None if not c else sorted(c,key=lambda x:(STAGE_ORDER[x['stage']],x['priority'],x['id']))[0]
