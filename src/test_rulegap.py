"""Synthetic tests include deliberately negative cases, not production safety claims."""
from rulegap_bench import Case,generate,gate,RULES,digest,violates
from diagnostics import evidence

def test_all_methods_return_known_verdict():
    for c in generate('unit',20261124,24):
        for m in ('local','revision','fingerprint','rulegap','always_withhold'):
            assert gate(c,m)[0] in ('allow','block','withhold')

def test_intact_safe_approved():
    for domain in RULES:
        c=next(x for x in generate('unit',20261125,64) if x.domain==domain and x.fault=='intact' and x.oracle_allowed)
        assert gate(c,'rulegap')[0]=='allow'

def test_detects_missing_deployed_policy():
    for domain in RULES:
        c=next(x for x in generate('unit',20261125,64) if x.domain==domain and x.fault=='deployed_omission')
        assert gate(c,'rulegap')[0]!='allow'

def test_double_omission_noncritical_is_a_real_blind_spot():
    c=Case(id='KNOWN-BLIND-SPOT',split='negative',domain='records',
      context={'external_export':False,'approved':True,'sensitive':False,'owner_confirmed':False,
       'amount':0,'verified_payee':True,'role':'finance','privileged':False,'mfa':True,'external_actor':False},
      true_rules=RULES['records'],authority_rules=('require_export_approval','restrict_sensitive_destination'),
      deployed_rules=('require_export_approval','restrict_sensitive_destination'),
      authority_revision=5,deployed_revision=5,fault='two_sources_omit_noncritical',oracle_allowed=False)
    assert violates('require_data_owner',c.context)
    assert gate(c,'rulegap')[0]=='withhold'
    from unittest.mock import patch
    with patch.dict('rulegap_bench.RULES',{'records':('require_export_approval','restrict_sensitive_destination')}):
        assert gate(c,'rulegap')[0]=='allow'

def test_hash_identifies_bundle_difference_not_semantics():
    assert digest(('a','b'))==digest(('b','a'))
    assert digest(('a','b'))!=digest(('a',))

def test_diagnostic_has_traced_evidence_and_limitations():
    c=generate('unit',20261124,32)[0]
    x=evidence(c)
    assert x['case_id']==c.id and x['limitations']
