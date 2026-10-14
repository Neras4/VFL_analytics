"""Reproducible offline real-export audit. Detailed output must stay in local_data."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from .adapters import adapt_roster, _id
from .snapshots import merge_team_snapshots
from .market_adapter import adapt_market_snapshot
from .evaluation import evaluate_player
from .positions import position_modifier
from .models import PositionPlan, base_position, STYLE_NAMES
from .explain import explain_lineup
from .lineup import optimize_lineups
from .rule_data import _data
from .abilities import captain_coefficient
from .validation import special


def _ids(rows):
    result=[]
    for row in rows:
        try: result.append(_id(row))
        except (ValueError,TypeError,AttributeError): pass
    return result


def join_report(snapshot, adapted):
    roster=_ids(snapshot.get('roster',{}).get('players',[]))
    details=_ids(snapshot.get('playerDetails',[]))
    season=_ids((snapshot.get('rosterSeasonStats') or {}).get('players',[]))
    return {'roster_rows':len(roster),'unique_roster_ids':len(set(roster)),
            'details_rows':len(details),'unique_detail_ids':len(set(details)),
            'season_stat_rows':len(season),'unique_season_ids':len(set(season)),
            'missing_details':sorted(set(roster)-set(details)),
            'orphan_details':sorted(set(details)-set(roster)),
            'missing_season_stats':sorted(set(roster)-set(season)),
            'orphan_season_stats':sorted(set(season)-set(roster)),
            'duplicate_roster_ids':sorted(k for k,v in Counter(roster).items() if v>1),
            'duplicate_detail_ids':sorted(k for k,v in Counter(details).items() if v>1),
            'accepted':adapted['accepted'],'rejected':adapted['rejected'],
            'errors':adapted['error_count'],'warnings':adapted['warning_count'],
            'field_conflicts':sum(len(e['conflicts']) for e in adapted['evidence_by_id'].values())}


def inventory_entry(path, snapshot):
    roster=snapshot.get('roster',{}).get('players',[])
    details=snapshot.get('playerDetails',[])
    times={}
    def walk(x,at=''):
        if isinstance(x,dict):
            for key,value in x.items():
                child=at+'.'+key if at else key
                if key=='collectedAt': times[child]=value
                elif isinstance(value,(list,dict)): walk(value,child)
        elif isinstance(x,list):
            for n,value in enumerate(x):walk(value,f'{at}[{n}]')
    walk(snapshot)
    return {'path':str(path.resolve()),'filename':path.name,'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            **{k:snapshot.get(k) for k in ('kind','depth','exporterVersion','teamId','opponentId','generatedAt')},
            'section_collection_times':times,'sections':sorted(snapshot),
            'roster_rows':len(roster),'unique_players':len(set(_ids(roster))),
            'detail_rows':len(details),'season_stat_rows':len((snapshot.get('rosterSeasonStats') or {}).get('players',[])),
            'known_form':sum(r.get('form') is not None for r in roster if isinstance(r,dict)),
            'known_fatigue':sum(r.get('fatigue') is not None for r in roster if isinstance(r,dict)),
            'contracts':sum(bool(r.get('contract')) for r in details if isinstance(r,dict)),
            'recent_match_records':len(snapshot.get('recentMatches',[]))}


def scenario_plans():
    # Candidate geometry only; no claim that complete game legality was checked.
    return [PositionPlan(tuple(s.split()),defense_formation='line') for s in (
        'GK LD CD1 CD2 RD LM CM1 CM2 RM CF1 CF2',
        'GK LD CD1 CD2 RD LM CM1 CM2 RM AM CF',
        'GK LD CD1 CD2 RD LM DM CM RM AM CF')]


def analyze_team(snapshots, *, lineups=True):
    merged=merge_team_snapshots(snapshots); adapted=adapt_roster(merged['snapshot']); players=adapted['players']
    report={'join':join_report(merged['snapshot'],adapted), 'merge':merged,
            'adapted':{**adapted,'players':[asdict(p) for p in players]}, 'evaluations':[], 'position_grid':{},
            'scope':'OBSERVED inputs; calculations are isolated rules and provisional partial-model scenarios'}
    report['preservation']={'input_section_union':sorted(set().union(*(set(s) for s in snapshots))),
        'merged_sections':sorted(merged['snapshot']),
        'missing_sections':sorted(set().union(*(set(s) for s in snapshots))-set(merged['snapshot']))}
    report['captain_coefficients']={p.id:{'coefficient':captain_coefficient(p.age,
        next((level for code,level in map(special,p.specials) if code=='Ка'),0)).to_dict(),
        'absolute_bonus':None,'basis_verified':False} for p in players}
    from .validation import NATIVE_POSITIONS,SPECIAL_POSITIONS
    for p in players:
        report['position_grid'][p.id]={slot:position_modifier(p.positions,slot).to_dict()
            for slot in sorted(NATIVE_POSITIONS|SPECIAL_POSITIONS)}
        for style in STYLE_NAMES:
            report['evaluations'].append(evaluate_player(p,p.positions[0],style,defense_formation='line').to_dict())
    # Table-defined conditions, explicitly hypothetical. Never next-match weather.
    weather=_data('weather.json.gz')['temperatures'][0]
    report['weather_scenario']={'classification':'SYNTHETIC_SCENARIO','context':weather,
        'evaluations':[evaluate_player(p,p.positions[0],'spartak',weather=weather).to_dict() for p in players]}
    if lineups:
        report['lineups']={}
        for mode in ('known_components','conservative','pareto'):
            args=dict(styles=list(STYLE_NAMES),mode=mode,top_n=9)
            result=optimize_lineups(players,scenario_plans(),**args)
            repeated=optimize_lineups(players,scenario_plans(),**args)
            if result!=repeated: raise AssertionError('Nondeterministic optimizer result')
            for candidate in result['results']:
                rows=candidate['lineup']
                if len(rows)!=11 or len({r['player_id'] for r in rows})!=11 or sum(base_position(r['slot'])=='GK' for r in rows)!=1:
                    raise AssertionError('Invalid assignment invariants')
            report['lineups'][mode]={**result,'deterministic_repeat':True}
        report['styles']={}
        for style in STYLE_NAMES:
            known=report['lineups']['known_components']['style_summaries'][style]
            conservative=report['lineups']['conservative']['style_summaries'][style]
            pareto=report['lineups']['pareto']['style_summaries'][style]
            best=known['best_known_proxy']
            plan=next((p for p in scenario_plans() if best and list(p.slots)==best['slots']),None)
            report['styles'][style]={'known':known,'conservative':conservative,'pareto':pareto,
                'explanation':explain_lineup(players,plan,best) if best else None,
                'scheme_comparisons':[{'slots':c['slots'],'proxy_gap_from_best':best['ranking_score']-c['ranking_score'],
                    'full_preference':'UNKNOWN'} for c in known['formation_candidates']] if best else []}
    return report


def validate_directory(source, output):
    source=Path(source).resolve(); output=Path(output).resolve()
    # Accidental public reports must not contain raw observations.
    if 'local_data' not in output.parts:
        raise ValueError('Detailed validation output must be under local_data/')
    output.mkdir(parents=True,exist_ok=True)
    documents=[]; inventory=[]
    for path in sorted(source.glob('*.json')):
        snapshot=json.loads(path.read_text(encoding='utf-8-sig'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        documents.append(snapshot);inventory.append(inventory_entry(path,snapshot))
    report={'inventory':inventory,'teams':{},'market':[],'bids':[]}
    for kind,label in [('vfl-own-team-context','own'),('vfl-opponent-context','opponent')]:
        rows=[s for s in documents if s.get('kind')==kind]
        if rows: report['teams'][label]=analyze_team(rows)
    for snapshot in sorted(documents,key=lambda s:s.get('generatedAt','')):
        if snapshot.get('kind') in ('vfl-transfer-market','vfl-transfer-bids'):
            result=adapt_market_snapshot(snapshot)
            report['bids' if snapshot['kind']=='vfl-transfer-bids' else 'market'].append(result)
    report['match_smoke']={'own':report['teams'].get('own',{}).get('join'),
        'opponent':report['teams'].get('opponent',{}).get('join'),
        'win_draw_loss':None,'reason':'No trained/calibrated outcome model; opponent physical data unknown',
        'game_actions':[]}
    (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    text=['# Local inventory (private)','','Exact input paths and collector timestamps:','']
    for entry in inventory:
        text += [f"- `{entry['path']}` — {entry['bytes']} bytes; {entry['generatedAt']}; {entry['kind']}; {entry['depth']}; Assistant {entry['exporterVersion']}",
                 f"  Roster {entry['roster_rows']}, unique {entry['unique_players']}, details {entry['detail_rows']}, season {entry['season_stat_rows']}; sections {', '.join(entry['sections'])}."]
    (output/'inventory.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('--output',required=True)
    args=parser.parse_args();report=validate_directory(args.source,args.output)
    # Console contains aggregate counts only.
    print(json.dumps({'files':len(report['inventory']),
        'teams':{k:{key:(len(value) if isinstance(value,list) else value) for key,value in v['join'].items()} for k,v in report['teams'].items()},
        'market':[{'rows':r['total_rows'],'accepted':r['accepted'],'rejected':r['rejected'],'complete':r.get('complete'),'issues':r['issues']} for r in report['market']],
        'bids':[{'collectedAt':r['collectedAt'],'rows':r['total_rows'],'accepted':r['accepted'],'rejected':r['rejected']} for r in report['bids']]},ensure_ascii=True,indent=2))


if __name__=='__main__': main()
