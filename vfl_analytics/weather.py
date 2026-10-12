"""Actual PLAYER favorite-style weather lookup, never chosen team style or reapplication."""
from .models import style_id
from .validation import number
from .rule_data import _data
from .results import exact,unknown


def weather_strength(style,nominal_strength,weather,temperature_c):
    style=style_id(style)
    if style is None:
        raise ValueError('Team style required')
    source='https://vfliga.com/weather.php; retrieved 2026-10-12; published table version NOT_STATED'
    if nominal_strength is None or weather is None or temperature_c is None:
        return unknown(unit='strength_points',source=source,reason='Missing weather lookup input')
    number(nominal_strength,'nominal_strength',positive=True)
    number(temperature_c,'temperature_c')
    if not isinstance(weather,str):
        raise ValueError('Weather must be a supported name')
    weather=weather.upper()
    data=_data('weather.json.gz')
    if weather not in {x['weather'] for x in data['temperatures']}:
        raise ValueError('Unknown weather name')
    if style=='normal':
        return unknown(unit='strength_points',source=source,reason='Normal-style native table unavailable')
    if int(nominal_strength)!=nominal_strength or not 15<=nominal_strength<=350:
        return unknown(unit='strength_points',source=source,reason='Unsupported nominal strength; no extrapolation or interpolation')
    index=next((x['index'] for x in data['temperatures'] if x['weather']==weather and x['temperature_c']==temperature_c),None)
    if index is None:
        return unknown(unit='strength_points',source=source,reason='Weather/temperature pair absent; no interpolation')
    value=data['rows'][data['style_groups'][style]][str(int(nominal_strength))][index]
    return exact(value,unit='strength_points',source=source,reason='Displayed isolated weather table cell; use nominal input once, not adjusted force')
