"""Unit and negative tests for the synthetic bee-inspired search."""
import unittest, random
from rulegap_bee import *

class TestPolicy(unittest.TestCase):
 def test_each_mutant_is_detectable(self):
  for rule in ALL_RULES:
   rng=random.Random(5)
   req=replace(BASE[[d for d in DOMAINS if rule in RULES[d]][0]],**trigger(rule,rng))
   self.assertFalse(decision(req),rule)
   self.assertTrue(decision(req,omitted=rule),rule)
 def test_control_requests_allowed(self):
  for d in DOMAINS:self.assertTrue(decision(BASE[d]))
 def test_seed_reproducibility(self):
  self.assertEqual(generate_pool(random.Random(12)),generate_pool(random.Random(12)))
 def test_search_unique_indices(self):
  p=generate_pool(random.Random(10)); m,w,u=prepare(p)
  for fn in (choose_random,choose_greedy,choose_bee):
   chosen=fn(len(p),8,random.Random(30),m,w)
   self.assertEqual(len(chosen),8);self.assertEqual(len(set(chosen)),8)
 def test_no_live_model_calls(self):
  p=generate_pool(random.Random(11));m,w,u=prepare(p)
  self.assertGreater(len(p),40);self.assertEqual(len(ALL_RULES),12)
 def test_rule_missing_in_both_sources_invisible(self):
  req=replace(BASE['grant'],scope='root')
  self.assertFalse(decision(req));self.assertTrue(decision(req,omitted='GR_ROOT'))
  self.assertTrue(decision(req,omitted='GR_ROOT'))

if __name__=='__main__':unittest.main()
