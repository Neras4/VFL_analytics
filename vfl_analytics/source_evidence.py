"""Collector-specific observation selection; no defaults for hidden attributes."""
from datetime import datetime, date
import re
from .validation import identity, number

COLLECTOR_SOURCE='https://github.com/Neras4/vfl-assistant-extension/blob/main/content.js'
SCOUT_SOURCE='https://vfliga.com/rules.php?page=103#p7 (sections 7.2, 7.2.1)'


def timestamp(value):
    if not isinstance(value,str): return None
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result if result.tzinfo else None
    except ValueError: return None


def source_meta(snapshot,path):
    source=(snapshot.get('_source_provenance') or {}).get(path,{})
    return {'snapshot_id':source.get('snapshot_id',snapshot.get('_snapshot_id')),
            'collection_reference':source.get('generatedAt',snapshot.get('generatedAt')),
            'observation_time':None,
            'time_semantics':'generatedAt is collection reference before Deep fetch; not per-player observation time'}


def fatigue_observation(snapshot,row,detail,info,sid):
    roster=row.get('fatigue');profile=info.get('fatigue')
    rmeta=source_meta(snapshot,'roster');pmeta=source_meta(snapshot,f'playerDetails[{sid}].info.fatigue')
    rtime=timestamp(row.get('collectedAt'));ptime=timestamp(info.get('collectedAt'))
    rmeta['observation_time']=row.get('collectedAt') if rtime else None
    pmeta['observation_time']=info.get('collectedAt') if ptime else None
    evidence={'source':'roster','value':roster,**rmeta,'confidence':'UNKNOWN',
              'reason':'No verified current fatigue observation','conflicts':[],
              'observations':[{'source':'roster','value':roster,**rmeta},
                              {'source':'playerDetails.info','value':profile,**pmeta}]}
    if roster is not None:
        evidence.update(confidence='OBSERVED',reason='Numeric roster observation has source priority')
        if profile is not None and profile!=roster:
            evidence['conflicts'].append('roster_profile_numeric_disagreement')
            if rtime and ptime and ptime>rtime:
                evidence.update(value=None,confidence='UNKNOWN',reason='Newer conflicting profile versus authoritative roster; unresolved')
        return evidence
    # Own competitive roster null remains authoritative. Opponent v0.5.11
    # gates fatigue on visible form (content.js rosterCompact), unlike profile.
    supported=(snapshot.get('exporterVersion')=='0.5.11' and snapshot.get('kind')=='vfl-opponent-context'
               and row.get('form') is None)
    missing='fatigue' not in row
    if not (supported or missing) or profile is None:
        return evidence
    number(profile,'profile fatigue',minimum=0,maximum=100)
    rr=timestamp(rmeta['collection_reference']);pr=timestamp(pmeta['collection_reference'])
    if (ptime and (rtime or rr) and ptime<(rtime or rr)) or (rr and pr and pr<rr):
        evidence['reason']='Profile observation belongs to an older collection; fallback withheld'
        return evidence
    if detail.get('fatigue') is not None and detail['fatigue']!=profile:
        evidence.update(reason='Conflicting profile observations; fallback withheld')
        evidence['conflicts'].append('profile_numeric_disagreement')
        return evidence
    evidence.update(value=profile,source='playerDetails.info',**pmeta,confidence='OBSERVED',
                    reason='Opponent 0.5.11 roster null is gated by hidden form; independent displayed profile fatigue' if supported else
                    'Roster field absent; displayed profile observation used',collector_source=COLLECTOR_SOURCE)
    return evidence


_MONTHS={'янв':1,'фев':2,'мар':3,'апр':4,'мая':5,'май':5,'июн':6,'июл':7,'авг':8,'сен':9,'окт':10,'ноя':11,'дек':12}


def study_date(value):
    if not isinstance(value,str): return None
    try:return date.fromisoformat(value)
    except ValueError:pass
    match=re.fullmatch(r'(\d{1,2})\s+([а-яё]+)\.?\s+(\d{4})',value.strip().lower())
    if not match:return None
    try:return date(int(match[3]),_MONTHS[match[2][:3]],int(match[1]))
    except (ValueError,KeyError):return None


def scouting_style(snapshot,sid,favorite,explicit_percent):
    management=snapshot.get('management') or {}
    scouting=management.get('scouting') if isinstance(management,dict) else None
    result={'percent':explicit_percent,'verified':False,'source':'roster' if explicit_percent is not None else None,
            'status':'UNKNOWN','issues':[],'rule_source':SCOUT_SOURCE,'history':[]}
    if not isinstance(scouting,dict) or snapshot.get('kind')!='vfl-own-team-context':return result
    season_stats=snapshot.get('rosterSeasonStats')
    scope=season_stats.get('scope') if isinstance(season_stats,dict) else None
    season=scope.get('season') if isinstance(scope,dict) else None
    if season is None or scouting.get('season')!=season:
        result['issues'].append('scouting:unverified_season');return result
    reference=timestamp(snapshot.get('generatedAt'));records=scouting.get('completed',[])
    if not isinstance(records,list):result['issues'].append('scouting:invalid_history');return result
    valid=[]
    for record in records:
        if not isinstance(record,dict):continue
        try:
            if identity(record.get('playerId'),collector=True)!=sid:continue
        except ValueError:continue
        if str(record.get('studyType','')).strip().casefold()!='стиль':continue
        entry=record.get('result')
        if not isinstance(entry,dict):result['issues'].append('scouting:invalid_style_result');continue
        when=study_date(record.get('date'));level=entry.get('level');maxlevel=entry.get('maxLevel')
        if not when or not reference or when>reference.date() or record.get('season',season)!=season:
            result['issues'].append('scouting:invalid_future_or_season_date');continue
        if isinstance(level,bool) or not isinstance(level,int) or not 1<=level<=5 or type(maxlevel) is not int or maxlevel!=5:
            result['issues'].append('scouting:invalid_style_level');continue
        valid.append((when,level,record))
    if not valid:return result
    valid.sort(key=lambda x:x[0]);when,level,record=valid[-1]
    result['history']=[{'date':x[0].isoformat(),'level':x[1],'season':season} for x in valid]
    inconsistent=any(d==when and l!=level for d,l,_ in valid) or any(l>level for _,l,_ in valid)
    from .models import style_id
    labels=[]
    for _,_,r in valid:
        label=(r.get('result') or {}).get('style')
        if label is not None:
            try:labels.append(style_id(label))
            except ValueError:inconsistent=True
    if labels and (len(set(labels))>1 or favorite is not None and style_id(favorite)!=labels[-1]):inconsistent=True
    if explicit_percent is not None and explicit_percent<level*20:inconsistent=True
    if inconsistent:
        result.update(percent=None,verified=False)
        result['issues'].append('scouting:conflicting_style_history_or_profile');return result
    result.update(percent=explicit_percent if explicit_percent is not None else level*20,
                  verified=level==5 and favorite is not None,source='management.scouting.completed',
                  status='OBSERVED',date=when.isoformat(),season=season,level=level,maxLevel=5,
                  collection_reference=scouting.get('collectedAt'),
                  reason='Latest completed style level, not sum; stable ID and matching season')
    return result
