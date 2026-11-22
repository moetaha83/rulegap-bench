"""Reproduce the separate policy checking and bee-inspired synthetic experiments."""
from pathlib import Path
import subprocess, sys, json
r=Path(__file__).resolve().parent
s=r/'src'; out=r/'results'; out.mkdir(exist_ok=True)
cmds=[
 ('core',['rulegap_bench.py','--out',str(out/'core')]),
 ('bee_8',['rulegap_bee.py','--out',str(out/'bee_budget8'),'--runs','24','--tests','8','--seed','20261122']),
 ('bee_12',['rulegap_bee.py','--out',str(out/'bee_budget12'),'--runs','12','--tests','12','--seed','20261122']),
 ('bee_16',['rulegap_bee.py','--out',str(out/'bee_budget16'),'--runs','12','--tests','16','--seed','20261122']),
]
for label,args in cmds:
 print('Running',label,flush=True)
 with (out/(label+'_run.log')).open('w') as f:
  subprocess.run([sys.executable,str(s/args[0]),*args[1:]],stdout=f,stderr=subprocess.STDOUT,check=True)
summary={'note':'Two distinct, synthetic experiments. Neither is empirical validation of live AI-agent protection.',
'core':json.loads((out/'core/summary_metrics.json').read_text()),
'bee':{str(k):json.loads((out/f'bee_budget{k}/summary.json').read_text()) for k in (8,12,16)}}
(out/'combined_summary.json').write_text(json.dumps(summary,indent=2))
print('Wrote',out/'combined_summary.json')
