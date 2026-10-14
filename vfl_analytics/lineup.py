"""Bounded candidate search. Eligibility and numerical certainty are independent."""
from collections import defaultdict
import numpy as np
from scipy.optimize import linear_sum_assignment
from .models import Player, PositionPlan, STYLE_NAMES, base_position, style_id
from .rules import chemistry_for_player, partial_strength_range, MATCH_SOURCE
from .results import ResultStatus, CalculationResult, bounded, unknown
from .validation import number
from .positions import position_modifier,position_eligibility,validate_formation
from .evaluation import evaluate_player,lineup_captain_components
from .cohesion import cohesion_bonus
from .abilities import donor_contributions


def _factor(plan,style,slot):
    table=plan.style_position_multipliers.get(style,{})
    return table.get(slot,table.get(base_position(slot),1.))


def _eligible(p,slot):
    # Page159 permits field players off profile, with a separate positional penalty.
    return p.available is not False and position_eligibility(p.positions,slot)


def _position_factor(p,plan,style,slot):
    return position_modifier(p.positions,slot).value*_factor(plan,style,slot)


def _heuristic(p,style,factor):
    result=partial_strength_range(p,style,factor)
    if result.value is not None:
        return result.value
    # Explicit search proxy from observed components. Never returned as the unknown effect.
    score=p.strength*factor
    if p.form is not None:
        score*=p.form/100
    if p.fatigue is not None:
        score*=1-p.fatigue/100
    return score


def _build_matrix(players,plan,style):
    matrix=np.full((11,len(players)),-1e9)
    warnings=set()
    if style not in plan.style_position_multipliers:
        warnings.add('position_style_table_missing: position/style effects omitted')
    for si,slot in enumerate(plan.slots):
        for pi,p in enumerate(players):
            if not _eligible(p,slot):
                continue
            if p.available is None:
                warnings.add(f'availability_unverified:{p.id}')
            matrix[si,pi]=_heuristic(p,style,_position_factor(p,plan,style,slot))
    return matrix,sorted(warnings)


def _solve_assignment(matrix,banned=None):
    work=matrix.copy()
    if banned is not None:
        work[banned[0],banned[1]]=-1e9
    rows,cols=linear_sum_assignment(-work)
    if len(rows)!=11 or np.any(work[rows,cols]<=-1e8):
        return None
    return {int(s):int(p) for s,p in zip(rows,cols)}


def _bounds(result):
    if result.value is not None:
        return result.value,result.value
    if result.status==ResultStatus.BOUNDED:
        return result.lower,result.upper
    return None


def _evaluate(players,plan,style,matrix,assign,context=None):
    context=context or {}
    mapping={plan.slots[si]:players[pi] for si,pi in assign.items()}
    by_id={p.id:float(matrix[si,pi]) for si,pi in assign.items() for p in [players[pi]]}
    values={p.id:partial_strength_range(p,style,_position_factor(p,plan,style,slot)) for slot,p in mapping.items()}
    ranges={sid:_bounds(v) for sid,v in values.items()}
    uncertain=any(v.value is None for v in values.values())
    warnings={'captain_real_position_force_not_verified; captain omitted from proxy'}
    neighbors=defaultdict(list)
    for u,v in plan.links:
        neighbors[u].append(mapping[v]); neighbors[v].append(mapping[u])
    chemistry={}; chem_low=chem_high=known_chem=0.; chem_unknown=False
    if not plan.links:
        warnings.add('chemistry_links_not_provided')
    for slot,p in mapping.items():
        mod,count=chemistry_for_player(p,neighbors.get(slot,[]))
        chemistry[p.id]=mod.to_dict()
        if mod.status==ResultStatus.NOT_APPLICABLE:
            continue
        if count:
            warnings.add(f'chemistry_unknown:{p.id}')
            uncertain=True
        interval=_bounds(mod); base=ranges[p.id]
        if interval is None or base is None:
            chem_unknown=True; uncertain=True
            continue
        products=[s*m for s in base for m in interval]
        chem_low+=min(products); chem_high+=max(products)
        if values[p.id].value is not None and mod.value is not None:
            known_chem+=values[p.id].value*mod.value
    total_bounds=None if any(x is None for x in ranges.values()) or chem_unknown else (
        sum(x[0] for x in ranges.values())+chem_low,
        sum(x[1] for x in ranges.values())+chem_high)
    subtotal=sum(by_id.values())+known_chem
    cohesion=cohesion_bonus([p.id for p in mapping.values() if not p.is_league_player],context.get('cohesion_history'),
                            history_complete=context.get('cohesion_history_complete',False))
    captain=lineup_captain_components(mapping,real_position_strengths=context.get('real_position_strengths'),
        strength_basis_verified=context.get('real_position_strengths_verified',False),
        unresolved_modifiers=context.get('real_strength_modifiers_unresolved',False))
    if captain['best_isolated_delta']['status']=='EXACT':
        warnings.discard('captain_real_position_force_not_verified; captain omitted from proxy')
        warnings.add('captain_component_known_but_full_stacking_order_unresolved; separate from proxy')
    forces=None if context.get('real_position_strengths') is None else {
        p.id:(context['real_position_strengths'].get(slot) or {}).get(p.id) for slot,p in mapping.items()}
    donors={kind:donor_contributions(mapping,forces,kind=kind,
               strength_basis_verified=context.get('real_position_strengths_verified',False)) for kind in ('И','Л')}
    evaluations={p.id:evaluate_player(p,slot,style,defense_formation=plan.defense_formation,
                    defense_type=context.get('defense_type'),neighbours=neighbors.get(slot,[]) if plan.links else None,
                    cohesion=cohesion,weather=context.get('weather'),
                    position_style_factor=_factor(plan,style,slot) if style in plan.style_position_multipliers else None).to_dict()
                 for slot,p in mapping.items()}
    if uncertain:
        warnings.add('ranking_uses_explicit_search_proxy; unknown modifiers not imputed as facts')
    chem_result=unknown(unit='partial_strength_units',source=MATCH_SOURCE,reason='Geometry/base missing') if not plan.links or chem_unknown else (
        bounded(chem_low,chem_high,unit='partial_strength_units',source=MATCH_SOURCE,reason='Conditional partial-model bounds') if uncertain else
        CalculationResult(ResultStatus.ESTIMATED,value=known_chem,unit='partial_strength_units',source=MATCH_SOURCE,reason='Published chemistry on provisional force'))
    model_range=unknown(unit='partial_strength_units',reason='Physical data missing') if total_bounds is None else (
        bounded(*total_bounds,unit='partial_strength_units',reason='Conditional component-product range; omitted modifiers not bounded') if uncertain else
        CalculationResult(ResultStatus.ESTIMATED,value=subtotal,unit='partial_strength_units',reason='Known component subtotal; captain and other mechanics omitted'))
    return {'style':style,'lineup':[{'slot':slot,'player_id':p.id,'name':p.name,
                'partial_strength':values[p.id].value,'strength_result':values[p.id].to_dict()} for slot,p in mapping.items()],
        'external_position_factors':{'status':'ESTIMATED' if style in plan.style_position_multipliers else 'NOT_APPLICABLE',
            'values':plan.style_position_multipliers.get(style),
            'provenance':plan.style_position_provenance.get(style,{'source':'legacy caller input','rule_version':'UNKNOWN',
                'verification_status':'UNVERIFIED','unit':'multiplier'}),
            'note':'External research scenario; separate from official qualitative color table'},
        'linear_strength':sum(by_id.values()),'included_chemistry_bonus':None if uncertain else known_chem,
        'chemistry_components':chemistry,'chemistry_bonus_result':chem_result.to_dict(),
        'included_age_captain_bonus':None,'captain_id':captain['captain_id'],
        'captain_candidates':captain['candidates'],'captain_component':captain,
        'cohesion_component':cohesion.to_dict(),'donor_components':donors,'player_evaluations':evaluations,
        'partial_total':None if uncertain else subtotal,'partial_model_range':model_range.to_dict(),
        'ranking_score':subtotal,'ranking_score_result':CalculationResult(ResultStatus.ESTIMATED,value=subtotal,
             unit='partial_strength_units',reason='Explicit candidate-search proxy; missing style uses known physical subtotal, not an assumed effect').to_dict(),
        'warnings':sorted(warnings)}


def _incumbent_assignment(record,players,plan,style,matrix):
    if record.get('style')!=style or tuple(record.get('slots',()))!=tuple(plan.slots):
        return None
    rows=record.get('lineup',[])
    if len(rows)!=11 or len({x.get('player_id') for x in rows})!=11 or {x.get('slot') for x in rows}!=set(plan.slots):
        raise ValueError('Malformed incumbent lineup')
    indices={p.id:i for i,p in enumerate(players)}
    result={}
    for row in rows:
        if row['player_id'] not in indices:
            return None
        si=plan.slots.index(row['slot']); pi=indices[row['player_id']]
        if matrix[si,pi]<=-1e8:
            return None
        result[si]=pi
    return result


def optimize_lineups(players,plans,styles=None,top_n=3,*,incumbents=None,mode='known_components',context=None):
    number(top_n,'top_n',positive=True,integer=True)
    top_n=int(top_n)
    if context is not None and not isinstance(context,dict):
        raise ValueError('Evaluation context must be an object')
    if mode not in ('known_components','conservative','pareto'):
        raise ValueError('Unsupported ranking mode')
    if len({p.id for p in players})!=len(players):
        raise ValueError('Duplicate player IDs')
    styles=[style_id(s) for s in (styles if styles is not None else STYLE_NAMES)]
    if any(s is None for s in styles) or len(set(styles))!=len(styles):
        raise ValueError('Missing or duplicate team style')
    if len(plans)>32 or len(players)>200:
        raise ValueError('Bounded search supports <=32 plans and <=200 players')
    if incumbents is not None and (not isinstance(incumbents,list) or len(incumbents)>224):
        raise ValueError('Incumbent list must contain at most 224 records')
    all_results=[]; invalid=[]
    for plan in plans:
        formation=validate_formation(plan.slots,plan.defense_formation,plan.formation_base_slots,plan.tactical_permissions)
        for style in styles:
            matrix,warnings=_build_matrix(players,plan,style)
            best=_solve_assignment(matrix)
            if best is None:
                invalid.append({'style':style,'slots':list(plan.slots),'reason':'No eligible complete 11-player assignment'})
                continue
            candidates=[best]
            for s,p in best.items():
                alt=_solve_assignment(matrix,(s,p))
                if alt is not None and alt not in candidates:
                    candidates.append(alt)
            retained=0
            for record in incumbents or []:
                candidate=_incumbent_assignment(record,players,plan,style,matrix)
                if candidate is not None:
                    retained+=1
                    if candidate not in candidates:
                        candidates.append(candidate)
            evaluations=[_evaluate(players,plan,style,matrix,a,context) for a in candidates]
            for item in evaluations:
                item.update(slots=list(plan.slots),variants_considered=len(candidates),incumbents_retained=retained)
                item['formation_validation']=formation
                selected={x['player_id'] for x in item['lineup']}
                availability_known=all(p.available is True for p in players if p.id in selected)
                item['lineup_eligibility']={'status':'UNKNOWN',
                    'known_constraints_satisfied':not formation['unverified_tactical_slots'] and availability_known,
                    'reason':'One GK, unique starters and positional rules checked; full formation and League/reserve context require external validation'}
                if formation['unverified_tactical_slots']:
                    warnings.append('special_position_tactical_permissions_unverified')
                item['warnings']=sorted(set(item['warnings']+warnings))
                if mode=='conservative':
                    lower=item['partial_model_range'].get('lower',item['partial_model_range'].get('value'))
                    item['conservative_score']=lower
                    item['conservative_score_result']=unknown(unit='partial_strength_units',reason='Conditional partial bounds unavailable').to_dict() if lower is None else CalculationResult(
                        ResultStatus.ESTIMATED,value=lower,unit='partial_strength_units',reason='Explicit lower bound of provisional component model; not guaranteed full force').to_dict()
                    item['comparison_status']='UNKNOWN' if lower is None else 'ESTIMATED'
                    if lower is None:
                        item['warnings'].append('conservative_comparison_unavailable; diagnostic candidate ordered by explicit proxy only')
            if mode=='conservative':
                ranked=[x for x in evaluations if x['conservative_score'] is not None]
                all_results.extend([max(ranked,key=lambda x:x['conservative_score'])] if ranked else evaluations[:1])
            elif mode=='pareto':
                # Robust interval dominance, plus nonlinear components kept separately.
                def dominates(a,b):
                    pairs=[(a['partial_model_range'],b['partial_model_range']),
                           (a['cohesion_component'],b['cohesion_component']),
                           (a['captain_component']['best_isolated_delta'],b['captain_component']['best_isolated_delta'])]
                    strict=False
                    for ra,rb in pairs:
                        lo=ra['lower'] if ra['lower'] is not None else ra['value']; hi=rb['upper'] if rb['upper'] is not None else rb['value']
                        if lo is None or hi is None or lo<hi: return False
                        strict=strict or lo>hi
                    return strict
                all_results.extend(x for x in evaluations if not any(dominates(y,x) for y in evaluations if y is not x))
            else:
                all_results.append(max(evaluations,key=lambda x:x['ranking_score']))
    all_results.sort(key=lambda x:x.get('conservative_score') if mode=='conservative' and x.get('conservative_score') is not None else x['ranking_score'],reverse=True)
    return {'status':'partial_model' if all_results else 'no_valid_lineup','ranking_mode':mode,
        'pareto_truncated':mode=='pareto' and len(all_results)>top_n,
        'retained_candidates_before_output_limit':len(all_results),
        'recommendation':None,'optimization':'exact_linear_search_subproblem_plus_bounded_reranking; not global nonlinear optimum',
        'results':all_results[:top_n],'evaluated_style_formations':len(all_results),'invalid_combinations':invalid,
        'not_modeled':['Full modifier order','Captain until real position-force inputs verified','Weather/home/attitude','Substitutions','Match generator and win probabilities'],
        'warning':'Scores/bounds are conditional partial-model outputs; no official force or final lineup recommendation'}
