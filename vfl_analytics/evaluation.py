"""Component reports. Unpublished combination order prevents an official force total."""
from dataclasses import dataclass
from .models import Player
from .rules import style_effect,partial_strength_range,chemistry_for_player,MATCH_SOURCE
from .positions import position_modifier,style_position_category
from .abilities import ability_components,captain_coefficient,captain_contribution
from .cohesion import cohesion_bonus
from .weather import weather_strength
from .validation import special,number,identity
from .results import exact,unknown,bounded,CalculationResult,ResultStatus


@dataclass(frozen=True)
class PlayerEvaluation:
    player_id: str
    slot: str
    components: dict
    partial_estimate: CalculationResult
    warnings: tuple[str,...]

    def to_dict(self):
        return {'player_id':self.player_id,'slot':self.slot,'status':'UNKNOWN',
                'components':self.components,'partial_estimate':self.partial_estimate.to_dict(),
                'total_strength':unknown(unit='strength_points',reason='Full modifier bases/order not published').to_dict(),
                'warnings':list(self.warnings)}


def evaluate_player(player:Player,slot,team_style,*,defense_formation=None,defense_type=None,
                    neighbours=None,cohesion=None,weather=None,position_style_factor=None):
    position=position_modifier(player.positions,slot)
    physical=unknown(source=MATCH_SOURCE,reason='Form missing') if player.form is None else exact(player.form/100,source=MATCH_SOURCE)
    fatigue=unknown(source=MATCH_SOURCE,reason='Fatigue missing') if player.fatigue is None else exact(1-player.fatigue/100,source=MATCH_SOURCE)
    chemistry=unknown(source=MATCH_SOURCE,reason='Line geometry not supplied') if neighbours is None else chemistry_for_player(player,neighbours)[0]
    cohesion_result=cohesion if cohesion is not None else unknown(source='https://vfliga.com/rules.php?page=167',reason='Competitive participant history missing')
    weather_result=unknown(unit='strength_points',source='https://vfliga.com/weather.php',reason='Weather context missing')
    if weather is not None:
        if not isinstance(weather,dict):
            raise ValueError('Weather context must be a mapping')
        if player.favorite_style_is_known:
            weather_result=weather_strength(player.favorite_style,player.strength,weather.get('weather'),weather.get('temperature_c'))
        else:
            candidates=[weather_strength(s,player.strength,weather.get('weather'),weather.get('temperature_c')) for s in ('spartak','bb')]
            if all(x.value is not None for x in candidates):
                weather_result=bounded(min(x.value for x in candidates),max(x.value for x in candidates),unit='strength_points',
                    source='https://vfliga.com/weather.php',reason='Actual favorite style unknown; both school tables possible')
    abilities=[ability_components(code,level,team_style=team_style,defense_formation=defense_formation,
                defense_type=defense_type,age=player.age,native_positions=player.positions)
               for code,level in map(special,player.specials)]
    if not player.specials_known:
        abilities=[{'result':unknown(source='https://vfliga.com/rules.php?page=64',reason='Special ability data absent').to_dict()}]
    partial=unknown(unit='partial_strength_units',reason='Position inapplicable') if position.value is None else partial_strength_range(
        player,team_style,position.value*(position_style_factor if position_style_factor is not None else 1.))
    components={'nominal_strength':exact(player.strength,unit='strength_points',source='Normalized caller nominal-strength field').to_dict(),
                'physical_form':physical.to_dict(),'fatigue':fatigue.to_dict(),
                'position_eligibility':{'eligible':position.status!=ResultStatus.NOT_APPLICABLE,'source':position.source},
                'position_modifier':position.to_dict(),'favorite_style':style_effect(player,team_style).to_dict(),
                'style_position_category':style_position_category(team_style,slot,defense_formation),
                'special_abilities':abilities,'captain':unknown(unit='strength_points',reason='Assigned captain and verified real-position-force context required').to_dict(),
                'chemistry':chemistry.to_dict(),'cohesion':cohesion_result.to_dict(),'weather':weather_result.to_dict(),
                'unresolved_modifiers':['Full modifier combination order','Real/known player status','Home/attendance','Mood','In-match reserves and substitutions']}
    return PlayerEvaluation(player.id,slot,components,partial,
        ('partial_estimate is an explicit legacy product hypothesis, not official force',
         'Weather uses actual favorite PLAYER style and nominal strength once; not chosen team style',
         'Moment/economy/fatigue specials are not added to prematch force'))


def lineup_captain_components(mapping,*,real_position_strengths=None,strength_basis_verified=False,unresolved_modifiers=False):
    forces=None
    if real_position_strengths is not None:
        if not isinstance(real_position_strengths,dict):
            raise ValueError('Real positional forces must map slot -> {player ID: force}')
        for by_player in real_position_strengths.values():
            if not isinstance(by_player,dict):
                raise ValueError('Each real-position-force entry must map player IDs to force/null')
            for sid,value in by_player.items():
                identity(sid)
                if value is not None: number(value,'real positional force',minimum=0)
        forces={p.id:(real_position_strengths.get(slot) or {}).get(p.id) for slot,p in mapping.items()}
    candidates=[]
    for p in mapping.values():
        level=next((level for code,level in map(special,p.specials) if code=='Ка'),0)
        result=captain_contribution(p.age,level,p.id,forces,strength_basis_verified=strength_basis_verified,
                                    unresolved_modifiers=unresolved_modifiers)
        if not p.specials_known:
            result=unknown(unit='strength_points',reason='Captain Ka presence unknown')
        candidates.append({'player_id':p.id,'coefficient':captain_coefficient(p.age,level).to_dict(),'result':result.to_dict()})
    known=[x for x in candidates if x['result']['status']=='EXACT']
    best=max(known,key=lambda x:x['result']['value']) if len(known)==len(candidates) else None
    return {'candidates':candidates,'captain_id':None if best is None else best['player_id'],
            'best_isolated_delta':unknown(unit='strength_points',reason='At least one captain has uncertain real positional-force context').to_dict() if best is None else best['result'],
            'note':'Ranks isolated captain component only; no total-force ordering claimed'}
