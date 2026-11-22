"""Synthetic RuleGap Bee test prioritization, inspired by bee-colony search.
Not the original code from Mansour and Taha (2015). No real AI agent evaluation.
"""
from __future__ import annotations
import argparse, csv, json, random, statistics, pathlib
from dataclasses import dataclass, replace, asdict

@dataclass(frozen=True)
class Request:
    domain: str
    role: str = 'viewer'
    region: str = 'CA'
    amount: int = 0
    approved: bool = False
    second_approver: bool = False
    trusted: bool = False
    business_hours: bool = True
    sensitivity: str = 'public'
    backup: bool = True
    scope: str = 'basic'

DOMAINS=('export','transfer','grant','delete')
RULES={
 'export': ('EX_ROLE','EX_REGION','EX_SENSITIVE'),
 'transfer': ('TR_ROLE','TR_AMOUNT','TR_DUAL'),
 'grant': ('GR_ROLE','GR_TRUST','GR_ROOT'),
 'delete': ('DE_ROLE','DE_HOURS','DE_BACKUP'),
}
ALL_RULES=tuple(rule for d in DOMAINS for rule in RULES[d])

def violates(rule: str, req: Request) -> bool:
    if rule == 'EX_ROLE': return req.role not in ('analyst','admin')
    if rule == 'EX_REGION': return req.region != 'CA'
    if rule == 'EX_SENSITIVE': return req.sensitivity == 'secret' and not req.approved
    if rule == 'TR_ROLE': return req.role not in ('finance','admin')
    if rule == 'TR_AMOUNT': return req.amount > 100
    if rule == 'TR_DUAL': return req.amount > 50 and not req.second_approver
    if rule == 'GR_ROLE': return req.role != 'admin'
    if rule == 'GR_TRUST': return not req.trusted
    if rule == 'GR_ROOT': return req.scope == 'root'
    if rule == 'DE_ROLE': return req.role != 'admin'
    if rule == 'DE_HOURS': return not req.business_hours
    if rule == 'DE_BACKUP': return not req.backup
    raise KeyError(rule)

def decision(req: Request, omitted: str | None = None) -> bool:
    return all(not violates(r,req) for r in RULES[req.domain] if r != omitted)

BASE={
 'export': Request('export',role='analyst',region='CA',sensitivity='public',approved=True),
 'transfer': Request('transfer',role='finance',amount=40,second_approver=True),
 'grant': Request('grant',role='admin',trusted=True,scope='basic'),
 'delete': Request('delete',role='admin',business_hours=True,backup=True),
}
def trigger(rule: str, rng: random.Random) -> dict:
    return {
      'EX_ROLE':{'role':'viewer'}, 'EX_REGION':{'region':'US'},
      'EX_SENSITIVE':{'sensitivity':'secret','approved':False},
      'TR_ROLE':{'role':'viewer'}, 'TR_AMOUNT':{'amount':rng.choice([101,110,200])},
      'TR_DUAL':{'amount':rng.choice([51,60,95]),'second_approver':False},
      'GR_ROLE':{'role':'viewer'}, 'GR_TRUST':{'trusted':False},
      'GR_ROOT':{'scope':'root'}, 'DE_ROLE':{'role':'viewer'},
      'DE_HOURS':{'business_hours':False}, 'DE_BACKUP':{'backup':False},
    }[rule]

def generate_pool(rng: random.Random, per_domain: int = 90) -> list[Request]:
    out=[]
    for domain in DOMAINS:
        out.append(BASE[domain])
        for rule in RULES[domain]:
            for _ in range(6): out.append(replace(BASE[domain],**trigger(rule,rng)))
        for _ in range(per_domain):
            req=BASE[domain]
            changes=rng.sample(RULES[domain],rng.choice((1,1,2,2,3)))
            for rule in changes: req=replace(req,**trigger(rule,rng))
            if domain=='transfer' and rng.random()<.2:
                req=replace(req,amount=rng.choice([49,50,51,99,100,101]))
            out.append(req)
    return list(dict.fromkeys(out))

def features(req: Request) -> set[str]:
    violated=[r for r in RULES[req.domain] if violates(r,req)]
    feat={f'domain:{req.domain}',f'allow:{req.domain}:{decision(req)}'}
    if len(violated)==1: feat.add('isolated:'+violated[0])
    for r in violated:feat.add('violated:'+r)
    for i in range(len(violated)):
        for j in range(i+1,len(violated)):
            feat.add('pair:'+violated[i]+'+'+violated[j])
    if req.domain=='transfer':
        for t in [50,100]:
            if abs(req.amount-t)<=1: feat.add(f'boundary:{t}:{req.amount}')
    return feat

FEATURE_WEIGHTS={'isolated:':5.,'violated:':1.,'pair:':.35,'domain:':.5,'allow:':.35,'boundary:':.25}
def feature_weight(f):
    return next((w for s,w in FEATURE_WEIGHTS.items() if f.startswith(s)),0)

def prepare(pool):
    universe=sorted(set().union(*[features(r) for r in pool]))
    codes={f:1<<i for i,f in enumerate(universe)}
    masks=[]
    for r in pool:
        m=0
        for f in features(r):m|=codes[f]
        masks.append(m)
    weights=[feature_weight(f) for f in universe]
    return masks, weights,universe

def coverage(mask,weights):
    score=0.; i=0
    while mask:
        if mask&1:score+=weights[i]
        mask >>= 1; i+=1
    return score

def score_suite(ids,masks,weights):
    m=0
    for i in ids:m |= masks[i]
    return coverage(m,weights)

def choose_random(n,k,rng,masks,weights):
    return rng.sample(range(n),k)

def choose_greedy(n,k,rng,masks,weights):
    sel=[]; covered=0; remain=set(range(n))
    for _ in range(k):
        options=list(remain); rng.shuffle(options)
        best=max(options,key=lambda i:coverage(covered|masks[i],weights)-coverage(covered,weights))
        sel.append(best);remain.remove(best);covered |= masks[best]
    return sel

def choose_bee(n,k,rng,masks,weights,population=18,generations=45):
    """Population, employed-bee mutation, onlookers and scout exploration;
    optimizes only surrogate feature coverage, not hidden mutant outcomes.
    """
    pop=[rng.sample(range(n),k) for _ in range(population)]
    values=[score_suite(s,masks,weights) for s in pop]
    stale=[0]*population
    def mutate(s):
        out=s[:]; ix=rng.randrange(k)
        j=rng.randrange(n)
        while j in out: j=rng.randrange(n)
        out[ix]=j
        return out
    for _ in range(generations):
        for j in range(population):
            x=mutate(pop[j]);v=score_suite(x,masks,weights)
            if v>values[j]+1e-9:pop[j],values[j],stale[j]=x,v,0
            else:stale[j]+=1
        lo=min(values);ws=[.05+v-lo for v in values]
        for _ in range(population):
            j=rng.choices(range(population),weights=ws,k=1)[0]
            x=mutate(pop[j]);v=score_suite(x,masks,weights)
            if v>values[j]+1e-9:pop[j],values[j],stale[j]=x,v,0
            else:stale[j]+=1
        for j in range(population):
            if stale[j]>=10:
                pop[j]=rng.sample(range(n),k);values[j]=score_suite(pop[j],masks,weights);stale[j]=0
    return pop[max(range(population),key=lambda i:values[i])]

def caught_rules(pool,chosen):
    out=set()
    for i in chosen:
        req=pool[i]
        if decision(req):continue
        for rule in RULES[req.domain]:
            if decision(req,omitted=rule):out.add(rule)
    return out

def investigate(method,sel,pool,masks,weights):
    caught=caught_rules(pool,sel)
    return {
      'method':method, 'tests_selected':len(sel),
      'mutants_detected':len(caught),'mutant_detection_rate':round(len(caught)/len(ALL_RULES),4),
      'policy_coverage_score':round(score_suite(sel,masks,weights),3),
      'detected_rules':','.join(sorted(caught)),
      'legitimate_probe_fraction':round(sum(decision(pool[i]) for i in sel)/len(sel),4),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='results');ap.add_argument('--runs',type=int,default=24)
    ap.add_argument('--tests',type=int,default=8);ap.add_argument('--seed',type=int,default=20261122)
    args=ap.parse_args()
    if not 1<=args.tests<=32:ap.error('--tests must be 1..32')
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=[];selection=[]
    for trial in range(args.runs):
        rng=random.Random(args.seed+trial*10007)
        pool=generate_pool(rng);masks,weights,universe=prepare(pool)
        for name,fn in [('Random',choose_random),('Greedy',choose_greedy),('Bee colony',choose_bee)]:
            rr=random.Random(args.seed+trial*101+{'Random':1,'Greedy':2,'Bee colony':3}[name])
            sel=fn(len(pool),args.tests,rr,masks,weights)
            row={'trial':trial,'candidate_count':len(pool),**investigate(name,sel,pool,masks,weights)}
            rows.append(row)
            for i in sel: selection.append({'trial':trial,'method':name,'request':asdict(pool[i]), 'oracle_allow':decision(pool[i])})
    with (out/'experiment_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    summary={}
    for name in ['Random','Greedy','Bee colony']:
        subset=[r for r in rows if r['method']==name]
        vals=[r['mutants_detected'] for r in subset]; scores=[r['policy_coverage_score'] for r in subset]
        summary[name]={'runs':len(vals),'mean_mutants_detected':round(statistics.mean(vals),3),
                       'sd_mutants_detected':round(statistics.stdev(vals),3) if len(vals)>1 else 0,
                       'min_mutants_detected':min(vals),'max_mutants_detected':max(vals),
                       'mean_detection_pct':round(100*statistics.mean(vals)/len(ALL_RULES),2),
                       'mean_surrogate_coverage':round(statistics.mean(scores),2)}
    grouped={(r['trial'],r['method']):r['mutants_detected'] for r in rows}
    diff=[grouped[(t,'Bee colony')]-grouped[(t,'Greedy')] for t in range(args.runs)]
    summary['paired_bee_minus_greedy']={'mean_mutants':round(statistics.mean(diff),3),
                                      'better_runs':sum(d>0 for d in diff),'tie_runs':sum(d==0 for d in diff),
                                      'worse_runs':sum(d<0 for d in diff)}
    meta={'seed':args.seed,'runs':args.runs,'test_budget_per_trial':args.tests,
          'mutants':list(ALL_RULES),'truth':'synthetic pre-defined policy vs one-rule-omission mutants',
          'selection_oracle':'public policy-derived feature score; mutation outcomes held out during selection',
          'limitations':['No real LLM calls or live agent workflow','All faults are single-rule omissions and the authoritative rule set is known','Fixed hand-designed safety rules and probe features','Bee search has substantially more search compute than greedy','Not a proof of robustness, novelty, or catastrophe prevention']}
    (out/'summary.json').write_text(json.dumps({'metadata':meta,'results':summary},indent=2))
    (out/'selected_tests.json').write_text(json.dumps(selection,indent=2))
    print(json.dumps({'metadata':meta,'results':summary},indent=2))

if __name__=='__main__':main()
