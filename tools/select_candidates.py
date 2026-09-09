"""候选分层抽样；不把人类来源标签当作无需修改的证明。"""
from pathlib import Path
import csv,json,re,hashlib,random,collections
import argparse
parser=argparse.ArgumentParser(description='从冻结原始语料选择候选，不代表验收通过')
parser.add_argument('--out',required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1];out=Path(args.out)
out.mkdir(parents=True,exist_ok=False)
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
pool=[]
for f in sorted((root/'data/reference/c-red/benchmark data').glob('*/*.csv')):
 with f.open(encoding='utf-8-sig') as h:
  for line,r in enumerate(csv.DictReader(h),2):
   text=r['text'].strip();domain=f.parent.name
   title=next((v for k,v in r.items() if k.endswith('_title') and v.strip()),r.get('original_id') or r['id'])
   group=sha(domain+'|'+title.strip())[:20]
   if not 80<=len(text)<=3500:continue
   if re.search(r'\b(?:https?://|1[3-9]\d{9})|身份证|手机号|微信号|患者|患儿|肿瘤|自杀|杀人|强奸',text):continue
   pool.append({'text':text,'source_file':str(f.relative_to(root)),'source_row':line,'source_id':r['id'],'source_generator':r['attribution'],'source_domain':domain,'group_id':group,'original_id':r.get('original_id') or r['id'],'source_sha256':sha(text),'title':title})
random.Random(20260909).shuffle(pool)
quotas={'slop':80,'no_edit':80,'facts':100,'voice_emotion':70,'punctuation':40,'coherence':50,'missing_material':40,'long_form':40}
markers=['综上','总之','不仅','重要意义','至关重要','深刻','值得','彰显','随着','无疑','总而言之','不仅仅','然而','首先','其次','最后']
def eligible(r,cat):
 t=r['text'];human=r['source_generator']=='human';n=len(t)
 if cat=='long_form':return n>=1200
 if n>900:return False
 if cat=='no_edit':return human and 100<=n<=450 and not re.search(r'[!！?？]{2,}|……|\.\.|\[|\]|&|#|\*|“[^”]*$',t)
 if cat=='facts':return len(re.findall(r'\d+(?:\.\d+)?',t))>=3 and r['source_domain'] in ['news','paper','question answer']
 if cat=='voice_emotion':return human and any(w in t for w in ['我','真','喜欢','讨厌','失望','感动','可惜','笑'])
 if cat=='punctuation':return sum(t.count(x) for x in '“”「」《》：；（）—…')>=4
 if cat=='coherence':return n>=350 and len(re.split('[。！？]',t))>=6
 if cat=='missing_material':return not human and n<=550 and not re.search(r'\d',t) and sum(w in t for w in markers)>=2
 if cat=='slop':return not human and sum(w in t for w in markers)>=2
used=set();used_origin=set();texts=set();chosen={}
for cat in ['long_form','facts','no_edit','voice_emotion','punctuation','coherence','missing_material','slop']:
 candidates=[r for r in pool if eligible(r,cat)];chosen[cat]=[]
 for r in candidates:
  original=r['source_domain']+'|'+r['original_id']
  if r['group_id'] in used or original in used_origin or r['source_sha256'] in texts:continue
  used.add(r['group_id']);used_origin.add(original);texts.add(r['source_sha256']);chosen[cat].append(dict(r))
  if len(chosen[cat])==quotas[cat]:break
 assert len(chosen[cat])==quotas[cat],(cat,len(chosen[cat]))
flat=[];pilot=[];rest=[]
for cat in quotas:
 for i,r in enumerate(chosen[cat]):
  r.update(id='zh2-'+cat+'-'+str(i+1).zfill(3),category=cat,split='development' if i<int(quotas[cat]*.6) else 'holdout',selection_status='candidate')
  flat.append(r)
  (pilot if i<int(quotas[cat]*.2) else rest).append(r)
(out/'selected.json').write_text(json.dumps(flat,ensure_ascii=False,indent=2))
(out/'pilot.json').write_text(json.dumps(pilot,ensure_ascii=False,indent=2))
(out/'rest.json').write_text(json.dumps(rest,ensure_ascii=False,indent=2))
print('selected',len(flat),'pilot',len(pilot),'rest',len(rest),'split',collections.Counter(r['split'] for r in flat),'generators',collections.Counter(r['source_generator'] for r in flat),'domains',collections.Counter(r['source_domain'] for r in flat))
