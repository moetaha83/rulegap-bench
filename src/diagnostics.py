"""Offline decision-evidence diagnostics for RuleGap Bench research. Not enforcement."""
from __future__ import annotations
import argparse, json, html
from pathlib import Path
from rulegap_bench import Case, RULES, HIGH_IMPACT, violates, gate, digest, generate

def evidence(case: Case) -> dict:
    issues=[]
    if case.authority_rules is None:
        issues.append({'severity':'critical','type':'authority_unavailable',
                       'message':'Cannot establish reference policy coverage'})
    else:
        missing=set(case.authority_rules)-set(case.deployed_rules)
        extra=set(case.deployed_rules)-set(case.authority_rules)
        if missing:
            issues.append({'severity':'critical','type':'missing_deployed_rules',
                           'message':'Missing deployed rule IDs: '+', '.join(sorted(missing))})
        if extra:
            issues.append({'severity':'warning','type':'unreviewed_deployed_rules',
                           'message':'Additional deployed rule IDs: '+', '.join(sorted(extra))})
        if case.deployed_revision!=case.authority_revision:
            sev='warning' if digest(case.deployed_rules)==digest(case.authority_rules) else 'critical'
            issues.append({'severity':sev,'type':'revision_mismatch',
                           'message':f'Authority revision {case.authority_revision}; deployed {case.deployed_revision}'})
        gaps=set(RULES[case.domain])-set(case.authority_rules)
        if gaps:
            issues.append({'severity':'critical','type':'expected_class_gap',
                           'message':'Missing expected classes from locally configured registry: '+', '.join(sorted(gaps))})
    for r in sorted(HIGH_IMPACT.intersection(RULES[case.domain])):
        if violates(r,case.context):
            issues.append({'severity':'critical','type':'independent_invariant',
                           'message':'Curated high-impact invariant violated: '+r})
    decision,reason=gate(case,'rulegap')
    return {'case_id':case.id,'domain':case.domain,'fault_injected':case.fault,
            'decision':decision,'decision_reason':reason,
            'expected_oracle_decision':'allow' if case.oracle_allowed else 'block',
            'deployed_revision':case.deployed_revision,'authority_revision':case.authority_revision,
            'deployed_policy_sha256_short':digest(case.deployed_rules),
            'authority_policy_sha256_short':digest(case.authority_rules) if case.authority_rules is not None else None,
            'issues':issues,
            'limitations':['Local policy registry may be incomplete','Hashes are not authenticating signatures',
              'An omitted requirement not present in any trusted source may remain undetected',
              'No claim about deployed agent behaviour or risk reduction']}

def write_demo(out:Path):
    out.mkdir(exist_ok=True,parents=True)
    cases=generate('demo',20261126,per_domain=16)
    records=[evidence(c) for c in cases]
    (out/'evidence_records.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    counts={}
    for d in records:counts[d['decision']]=counts.get(d['decision'],0)+1
    page=['<!doctype html><html lang="en"><meta charset="utf-8">',
       '<meta name="viewport" content="width=device-width, initial-scale=1">',
       '<title>RuleGap Bench — Offline research demo</title>',
       '<style>body{max-width:1100px;margin:40px auto;padding:0 24px;font:16px/1.55 system-ui,sans-serif;color:#19304a;background:#f7f9fc}h1{font-size:32px}h2{font-size:20px}section{background:white;border-radius:12px;padding:16px 22px;margin:16px 0;border:1px solid #d9e1eb}code{font-size:12px}small{color:#52647b}.pill{border-radius:16px;background:#e6eef9;padding:3px 9px;font-size:12px;font-weight:bold}.limit{border-left:4px solid #ad6d17;padding:10px;background:#fff4de}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>',
       '<h1>RuleGap Bench <small>v0.1 · synthetic diagnostics</small></h1>',
       '<p class="limit">Research demonstration only. Not a runtime protection or safety certificate. All policy input sources are simulated and assumed trusted.</p>',
       f'<p>{len(records)} simulated cases · Verdict counts: '+', '.join(f'{html.escape(k)} {v}' for k,v in sorted(counts.items()))+'</p>']
    for item in records[:18]:
        page.append('<section><h2>'+html.escape(item['case_id'])+' &nbsp;<span class="pill">'+html.escape(item['decision'])+'</span></h2>')
        page.append('<p>Fault: '+html.escape(item['fault_injected'])+' · Oracle: '+html.escape(item['expected_oracle_decision'])+' · '+html.escape(item['decision_reason'])+'</p>')
        for i in item['issues']:
            page.append('<p><b>'+html.escape(i['severity'])+'</b>: '+html.escape(i['message'])+'</p>')
        page.append('</section>')
    page.append('<p><small>Showing first 18 of '+str(len(records))+' cases; full evidence_records.json has all cases.</small></p></html>')
    (out/'example_report.html').write_text('\n'.join(page),encoding='utf8')
    print('Saved offline report:',out/'example_report.html')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results');args=p.parse_args()
    write_demo(Path(args.out))
