"""Offline deterministic 20/25/30-player benchmark; no timing-dependent assertions."""
import json
import platform
from statistics import median
from time import perf_counter
from vfl_analytics.models import Player,PositionPlan
from vfl_analytics.lineup import optimize_lineups


def run_benchmark(repeats=3):
    slots=('GK','LD','CD1','CD2','RD','LM','DM','CM','RM','AM','CF')
    plans=[PositionPlan(slots,tactical_permissions={'DM':True,'AM':True}),
           PositionPlan(('GK','LD','CD1','CD2','RD','LM','CM1','CM2','RM','CF1','CF2')),
           PositionPlan(('GK','LD','SW','CD','RD','LW','CM1','CM2','RW','AM','ST'),
                        defense_formation='sweeper',tactical_permissions={'AM':True})]
    records=[]
    native=[('GK',),('LD',),('CD',),('RD',),('LM',),('CD','CM'),('CM',),('RM',),('CM','CF'),('CF',),('LM','LF'),('RM','RF')]
    for count in (20,25,30):
        players=[Player(str(i),f'Synthetic{i}',native[i%len(native)],24+i%11,70+i*3,
                         fatigue=i%20,form=100+i%20,favorite_style=None if i%4==0 else 'spartak',
                         style_known_percent=None if i%4==0 else 100,available=True) for i in range(count)]
        timings=[]; answer=None
        for _ in range(repeats):
            start=perf_counter(); result=optimize_lineups(players,plans,top_n=3); timings.append(perf_counter()-start)
            if answer is not None and answer!=result: raise RuntimeError('Nondeterministic optimizer result')
            answer=result
        assert all(len(x['lineup'])==11 and len({p['player_id'] for p in x['lineup']})==11 for x in answer['results'])
        records.append({'players':count,'plans':len(plans),'styles':7,'repeats':repeats,
                        'median_seconds':median(timings),'max_seconds':max(timings),
                        'results':len(answer['results']),'deterministic':True})
    return {'classification':'SYNTHETIC','python':platform.python_version(),'platform':platform.system(),
            'scope':'Bounded candidate search; not global nonlinear optimum','cases':records}


if __name__=='__main__':
    print(json.dumps(run_benchmark(),indent=2))
