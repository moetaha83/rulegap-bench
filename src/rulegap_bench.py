"""RuleGap Bench v0.1. Offline synthetic policy checking research, not safety certification."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import argparse, csv, json, random

DOMAINS = ('records', 'payments', 'access')
RULES = {
    'records': ('require_export_approval', 'restrict_sensitive_destination', 'require_data_owner'),
    'payments': ('require_high_value_approval', 'restrict_unverified_payee', 'require_finance_role'),
    'access': ('require_privilege_approval', 'require_mfa', 'restrict_external_admin'),
}
HIGH_IMPACT = {'restrict_sensitive_destination','restrict_unverified_payee','restrict_external_admin'}

@dataclass(frozen=True)
class Case:
    id: str
    split: str
    domain: str
    context: dict
    true_rules: tuple[str, ...]
    authority_rules: tuple[str, ...] | None
    deployed_rules: tuple[str, ...]
    authority_revision: int
    deployed_revision: int
    fault: str
    oracle_allowed: bool

def violates(rule: str, c: dict) -> bool:
    match rule:
        case 'require_export_approval': return bool(c['external_export'] and not c['approved'])
        case 'restrict_sensitive_destination': return bool(c['sensitive'] and c['external_export'])
        case 'require_data_owner': return not bool(c['owner_confirmed'])
        case 'require_high_value_approval': return bool(c['amount'] > 1000 and not c['approved'])
        case 'restrict_unverified_payee': return not bool(c['verified_payee'])
        case 'require_finance_role': return c['role'] != 'finance'
        case 'require_privilege_approval': return bool(c['privileged'] and not c['approved'])
        case 'require_mfa': return not bool(c['mfa'])
        case 'restrict_external_admin': return bool(c['privileged'] and c['external_actor'])
        case _: raise ValueError('unknown rule ' + rule)

def digest(rules: tuple[str,...]) -> str:
    return sha256(json.dumps(sorted(rules),separators=(',',':')).encode()).hexdigest()[:16]

def draw_context(rng:random.Random,domain:str,unsafe:bool) -> dict:
    for _ in range(10000):
        c = {'external_export':bool(rng.getrandbits(1)), 'approved':bool(rng.getrandbits(1)),
             'sensitive':bool(rng.getrandbits(1)), 'owner_confirmed':bool(rng.getrandbits(1)),
             'amount':rng.choice([10,200,1000,1001,1500,10000]),
             'verified_payee':bool(rng.getrandbits(1)), 'role':rng.choice(['finance','staff','admin']),
             'privileged':bool(rng.getrandbits(1)), 'mfa':bool(rng.getrandbits(1)),
             'external_actor':bool(rng.getrandbits(1))}
        is_unsafe = any(violates(rule,c) for rule in RULES[domain])
        if is_unsafe==unsafe:return c
    raise RuntimeError('scenario sampling failed')

def generate(split:str,seed:int,per_domain:int=84) -> list[Case]:
    rng=random.Random(seed)
    faults=('intact','deployed_omission','authority_and_deployed_omission',
            'stale_revision','authority_unavailable','harmless_revision_change',
            'partial_authority', 'deployed_unrelated_omission')
    out=[]
    for domain in DOMAINS:
        full=RULES[domain]
        for idx in range(per_domain):
            is_unsafe = (idx % 2 == 0)
            c=draw_context(rng,domain,is_unsafe)
            fault=faults[(idx // 2) % len(faults)]
            rev = 4 + rng.randrange(5); dep_rev=rev
            authority=full; deployed=full
            violated=[r for r in full if violates(r,c)]
            target=rng.choice(violated if violated else list(full))
            if fault=='deployed_omission':deployed=tuple(x for x in full if x!=target)
            elif fault=='authority_and_deployed_omission':
                authority=tuple(x for x in full if x!=target)
                deployed=authority
            elif fault=='stale_revision':dep_rev=rev-1
            elif fault=='authority_unavailable':authority=None
            elif fault=='harmless_revision_change':dep_rev=rev+1
            elif fault=='partial_authority':authority=tuple(x for x in full if x!=target)
            elif fault=='deployed_unrelated_omission':
                other=rng.choice([x for x in full if x!=target]);deployed=tuple(x for x in full if x!=other)
            out.append(Case(id=f'{split[:1].upper()}-{domain}-{idx:03d}',split=split,domain=domain,
                            context=c,true_rules=full,authority_rules=authority,
                            deployed_rules=deployed,authority_revision=rev,deployed_revision=dep_rev,
                            fault=fault,oracle_allowed=not is_unsafe))
    rng.shuffle(out)
    return out

def gate(case:Case,method:str)-> tuple[str,str]:
    local_block=any(violates(rule,case.context) for rule in case.deployed_rules)
    local='block' if local_block else 'allow'
    if method=='local':return (local,'local policy evaluation')
    if method=='always_withhold':return ('withhold','conservative control baseline')
    if method=='revision':
        if case.authority_rules is None:return ('withhold','reference unavailable')
        if case.deployed_revision!=case.authority_revision:return ('withhold','revision mismatch')
        return (local,'matching revision label')
    if method=='fingerprint':
        if case.authority_rules is None:return ('withhold','reference unavailable')
        if digest(case.deployed_rules)!=digest(case.authority_rules):return ('withhold','manifest mismatch')
        if case.deployed_revision!=case.authority_revision:return ('withhold','revision mismatch')
        return (local,'matching manifest and revision')
    if method=='rulegap':
        for r in sorted(HIGH_IMPACT.intersection(RULES[case.domain])):
            if violates(r,case.context):return ('block','independent high-impact constraint '+r)
        if case.authority_rules is None:return ('withhold','authority missing: cannot prove coverage')
        if digest(case.deployed_rules)!=digest(case.authority_rules):return ('withhold','rule source does not match deployed policy')
        if case.deployed_revision!=case.authority_revision:return ('withhold','rule revision drift')
        if any(r not in case.authority_rules for r in RULES[case.domain]):
            return ('withhold','expected policy class missing')
        return (local,'declared coverage matched; no global safety certification')
    raise ValueError(method)

METHODS=('local','revision','fingerprint','rulegap','always_withhold')

def evaluate(cases:list[Case]):
    raw=[]; summ=[]
    for c in cases:
        for name in METHODS:
            verdict,why=gate(c,name)
            raw.append({'case_id':c.id,'split':c.split,'domain':c.domain,'fault':c.fault,
                        'expected':'allow' if c.oracle_allowed else 'block','method':name,
                        'decision':verdict,'reason':why,'false_approval':int(not c.oracle_allowed and verdict=='allow'),
                        'legitimate_allowed':int(c.oracle_allowed and verdict=='allow'),
                        'unsafe_blocked_or_withheld':int(not c.oracle_allowed and verdict!='allow'),
                        'unnecessary_withhold':int(c.oracle_allowed and verdict=='withhold')})
    for split in sorted(set(r['split'] for r in raw)):
        for method in METHODS:
            sample=[r for r in raw if r['split']==split and r['method']==method]
            bad=[r for r in sample if r['expected']=='block']
            good=[r for r in sample if r['expected']=='allow']
            summ.append({'split':split,'method':method,'n':len(sample),
                         'unsafe_n':len(bad),'unsafe_false_approved':sum(r['false_approval'] for r in bad),
                         'unsafe_false_approval_pct':round(100*sum(r['false_approval'] for r in bad)/len(bad),2),
                         'legitimate_n':len(good),'legitimate_allowed':sum(r['legitimate_allowed'] for r in good),
                         'legitimate_allowed_pct':round(100*sum(r['legitimate_allowed'] for r in good)/len(good),2),
                         'unnecessary_withholds':sum(r['unnecessary_withhold'] for r in good)})
    return raw,summ

def csv_write(path:Path,rows:list[dict]):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',default='results',help='Output folder')
    p.add_argument('--test',action='store_true',help='Run self-checks against intentionally engineered defects')
    args=p.parse_args()
    root=Path(args.out);root.mkdir(exist_ok=True,parents=True)
    dev=generate('development',20261122,per_domain=84)
    held=generate('held_out',20261123,per_domain=84)
    raw,metrics=evaluate(dev+held)
    csv_write(root/'case_decisions.csv',raw);csv_write(root/'summary_metrics.csv',metrics)
    (root/'summary_metrics.json').write_text(json.dumps({'benchmark_kind':'synthetic deterministic simulation',
       'model_calls':0,'production_validity':'not assessed','seed_dev':20261122,'seed_heldout':20261123,
       'policy_authenticity':'input assumed trusted; sha256 is not digital signature','cases':len(dev+held),
       'gate_evaluations':len(raw),'metrics':metrics},indent=2),encoding='utf8')
    if args.test:
        assert len(dev)==len(held)==252
        assert len(raw)==252*2*len(METHODS)
        assert all(gate(c,'always_withhold')[0]=='withhold' for c in dev)
        assert all(gate(c,'local')[0] in ('allow','block') for c in held)
        assert sum(c.oracle_allowed for c in dev)==126
        assert all(m['n']==252 for m in metrics)
        sample=next(c for c in dev if c.fault=='authority_and_deployed_omission' and not c.oracle_allowed)
        print('Example double-omission:',sample.id,gate(sample,'rulegap'))
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
