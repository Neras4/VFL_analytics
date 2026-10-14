"""Compact, detailed and optional raw local reporting. Nothing here is public by default."""
import hashlib
import json
from collections import Counter
from pathlib import Path

LOCAL_DATA_ROOT=Path(__file__).resolve().parents[1]/'local_data'


def local_output(path):
    trusted=LOCAL_DATA_ROOT.absolute()
    if trusted.resolve()!=trusted:
        raise ValueError('local_data root must not redirect through a symlink')
    resolved=Path(path).resolve()
    if not resolved.is_relative_to(trusted) or resolved==trusted:
        raise ValueError('Output must be inside the project local_data storage root')
    return resolved


def small_candidate(candidate):
    if candidate is None:return None
    keys=('style','slots','lineup','ranking_score','partial_total','partial_model_range',
          'conservative_score','lineup_eligibility','formation_validation')
    return {k:candidate[k] for k in keys if k in candidate}


def strip_catalog(value):
    if isinstance(value,dict):return {k:strip_catalog(v) for k,v in value.items() if k not in ('catalog','source_values')}
    if isinstance(value,list):return [strip_catalog(v) for v in value]
    return value


def team_summary(report,source_ids,kind,team_id,season):
    players=report['adapted']['players'];candidates={};styles={}
    def reference(candidate):
        if candidate is None:return None
        compact=small_candidate(candidate)
        key=hashlib.sha256(json.dumps(compact,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()[:16]
        candidates[key]=compact
        return key
    for style,item in report.get('styles',{}).items():
        k,c,p=[item[m] for m in ('known','conservative','pareto')]
        abilities=(item.get('explanation') or {}).get('special_ability_components',{})
        styles[style]={'plans_considered':k['plans_considered'],'generated_candidates':k['generated_candidates'],
            'assignment_feasible_candidates':k['assignment_feasible_candidates'],'fully_verified_candidates':k['fully_verified_candidates'],
            'best_known_candidate':reference(k['best_known_proxy']),
            'best_conservative_candidate':reference(c['best_conservative']),
            'formation_candidates':[reference(x) for x in k['formation_candidates']],
            'pareto_status':p['pareto_status'],'pareto_count':p['pareto_count'],
            'unknown_effects':k['unknown_effects'],'collision':k['collision'],
            'style_specials':{sid:[{'code':a['code'],'level':a['level'],
                'effects':[e for e in a.get('effects',[]) if e['kind']=='own_strength_style_bonus']} for a in ab
                if any(e['kind']=='own_strength_style_bonus' for e in a.get('effects',[]))] for sid,ab in abilities.items()
                if any(any(e['kind']=='own_strength_style_bonus' for e in a.get('effects',[])) for a in ab)},
            'scheme_comparisons':item['scheme_comparisons']}
    issues=report['adapted']['issues']
    return {'kind':kind,'team_id':team_id,'season':season,'source_ids':source_ids,
        'join':report['join'],'preservation':report['preservation'],
        'availability':{'players':len(players),'known_fatigue':sum(p['fatigue'] is not None for p in players),
            'known_form':sum(p['form'] is not None for p in players),
            'verified_favorite_style':sum(p['favorite_style'] is not None and (p['favorite_style_verified'] or p['style_known_percent']==100) for p in players),
            'known_match_availability':sum(p['available'] is not None for p in players)},
        'warning_categories':dict(Counter(x.split(':',1)[-1] for x in issues)),
        'calculations':{'player_style_evaluations':len(report['evaluations']),
            'position_grids':len(report['position_grid']),'captain_absolute_bonus':'UNKNOWN',
            'weather_scenario':{'classification':'SYNTHETIC_SCENARIO','context':report['weather_scenario']['context']}},
        'styles':styles,'candidates':candidates,'full_force':'UNKNOWN','win_draw_loss':None,
        'deterministic_repeats':all(v['deterministic_repeat'] for v in report.get('lineups',{}).values())}


def detailed_team(report):
    return strip_catalog({'players':report['adapted']['players'],'evaluations':report['evaluations'],
        'position_grid':report['position_grid'],'captain_coefficients':report['captain_coefficients'],
        'weather_scenario':report['weather_scenario'],
        'player_evidence':{sid:{k:v for k,v in e.items() if k in ('field_provenance','conflicts','scouting')}
                           for sid,e in report['adapted']['evidence_by_id'].items()},
        'explanations':{style:data['explanation'] for style,data in report.get('styles',{}).items()}})


def write_reports(output,summary,details=None,raw=None):
    def save(name,data):
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    summary['report_files']=['validation.json','inventory.md','lineups.md','completion.json','player_aliases.json']
    if details is not None:summary['report_files'].append('details.json');save('details.json',details)
    if raw is not None:summary['report_files'].append('raw_diagnostics.json');save('raw_diagnostics.json',raw)
    save('validation.json',summary)
    lines=['# Local inventory (private)','','Exact paths, SHA256 and collection references:','']
    for e in summary['inventory']:
        lines.append(f"- `{e['path']}` — {e['generatedAt']}; {e['bytes']} bytes; {e['kind']}/{e['depth']}; source {e['snapshot_id']}; SHA256 {e['sha256']}")
    (output/'inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    lines=['# Local lineup diagnostics (private)','','All seven canonical styles before any global top_n; partial proxy only.']
    for label,team in summary['teams'].items():
        lines+=['',f'## {label} — {team["team_id"]}',json.dumps(team['availability'])]
        for style,comparison in team['styles'].items():
            candidate=team['candidates'].get(comparison['best_known_candidate'])
            if candidate is None:lines.append(f'{style}: no feasible assignment');continue
            lines+=['',f'### {style}',f'Proxy {candidate["ranking_score"]}; conditional range {candidate["partial_model_range"]}; full eligibility UNKNOWN.',
                f'Plans {comparison["plans_considered"]}; candidates {comparison["generated_candidates"]}; Pareto {comparison["pareto_count"]}.']
            lines += [f'- {r["slot"]}: {r["name"]} (ID {r["player_id"]})' for r in candidate['lineup']]
            explanation=((details or {}).get('teams',{}).get(label,{}).get('explanations',{}).get(style) or {})
            for c in explanation.get('comparisons',[]):
                slots={p['assigned_slot'] for p in c['before']}
                if slots=={'GK'} or slots=={'AM','CF'}:
                    before=', '.join(p['name']+'@'+p['assigned_slot'] for p in c['before'])
                    after=', '.join(p['name']+'@'+p['assigned_slot'] for p in c['after'])
                    lines.append(f"Alternative {before} -> {after}: delta {c['proxy_delta_alternative_minus_selected']:.6f}; {c['reason']}; full preference UNKNOWN.")
                    lines.append('Inputs: '+json.dumps({'before':c['before'],'after':c['after'],'omitted_effects':c['omitted_effects']},ensure_ascii=False))
    (output/'lineups.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    aliases={label:{sid:f'P{i+1:02}' for i,sid in enumerate(sorted({r['player_id'] for c in team['candidates'].values() for r in c['lineup']}))}
             for label,team in summary['teams'].items()}
    save('player_aliases.json',aliases)
    save('completion.json',{'schema_version':2,'engine_version':'0.2.3','source_ids':[e['snapshot_id'] for e in summary['inventory']],
        'pr':'https://github.com/Neras4/VFL_analytics/pull/3','merged':False,'report_files':summary['report_files'],
        'team_counts':{k:v['join'] for k,v in summary['teams'].items()}})
