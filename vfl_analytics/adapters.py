"""Conservative bridge from VFL Assistant JSON to core Player records.
Unknown collector fields remain missing; never infer zeros. Fixture-specific adjustments expected.
"""
from __future__ import annotations
import re
from .models import Player, STYLE_ALIASES


def _optional_num(v):
    if isinstance(v,dict):
        v=v.get("value",v.get("number"))
    if v in (None,"","?","—","-"):
        return None
    if isinstance(v,str):
        v=re.sub(r"[\s\u00a0%]","",v).replace(",",".")
    try:
        return float(v)
    except (TypeError,ValueError):
        return None


def _positions(row):
    raw = row.get("positions") or row.get("position")
    if isinstance(raw,list):
        return tuple(str(p).upper() for p in raw)
    if isinstance(raw,str):
        return tuple(p.strip().upper() for p in re.split(r"[/, ]+",raw) if p.strip())
    return ()


def adapt_roster(snapshot: dict) -> dict:
    """Returns parsed players + issues. No silent imputation of mandatory stats."""
    roster = snapshot.get("roster") or snapshot.get("team",{}).get("roster") or {}
    rows = roster.get("players") if isinstance(roster,dict) else roster
    if rows is None:
        rows = snapshot.get("players",[])
    result, issues = [], []
    if not isinstance(rows,list):
        raise ValueError("roster.players must be a list")
    details = snapshot.get("playerDetails") or []
    detail_by_id = {}
    if isinstance(details,list):
        detail_by_id = {str(d.get("playerId")):d for d in details if isinstance(d,dict)}
    for i,row in enumerate(rows):
        if not isinstance(row,dict):
            issues.append(f"row[{i}]:not_object"); continue
        sid = row.get("playerId", row.get("id"))
        d = detail_by_id.get(str(sid), {})
        info = d.get("info") if isinstance(d.get("info"),dict) else {}
        name = row.get("name")
        age = _optional_num(row.get("age"))
        strength = _optional_num(row.get("strength"))
        pos = _positions(row)
        if sid in (None,"") or not name or age is None or strength is None or not pos:
            issues.append(f"row[{i}]:missing_id_name_age_strength_or_position")
            continue
        fatigue = _optional_num(row.get("fatigue"))
        form = _optional_num(row.get("form"))
        fav = row.get("favoriteStyle") or row.get("favorite_style")
        # Deep info.style may be ambiguous (unexplored styles). Never claim
        # 100% study based on a plain string without explicit evidence.
        if not fav and info.get("style"):
            fav = info["style"]
        if isinstance(fav,dict): fav=fav.get("label",fav.get("name"))
        if fav and str(fav).strip().casefold() not in STYLE_ALIASES:
            issues.append(f"row[{i}]:unverified_favorite_style:{str(fav)[:40]}")
            fav = None
        known = _optional_num(row.get("styleKnownPercent",row.get("style_known_percent")))
        try:
            if age != int(age) or (known is not None and known != int(known)):
                raise ValueError("Age/study percentage must be integral; no truncation")
            p=Player(id=str(sid),name=name,positions=pos,age=int(age),strength=strength,
                     fatigue=fatigue,form=form,real_strength=_optional_num(row.get("realStrength")),
                     favorite_style=fav,style_known_percent=int(known) if known is not None else None,
                     nationality=row.get("country",row.get("nationality")),
                     specials=tuple(row.get("specials") or []),
                     available=row.get("available"),is_league_player=row.get("isLeaguePlayer",False),
                     value=_optional_num(row.get("value",info.get("value"))),
                     salary_per_tour=_optional_num(row.get("salaryPerTour",info.get("salaryPerTour"))),
                     played_minutes=_optional_num((info.get("usefulness") or {}).get("minutes") if isinstance(info.get("usefulness"),dict) else None))
            result.append(p)
            if fatigue is None or form is None:
                issues.append(f"row[{i}]:unknown_form_or_fatigue")
        except (ValueError,TypeError) as exc:
            issues.append(f"row[{i}]:invalid:{exc}")
    return {"players":result,"issues":issues,"accepted":len(result),"total":len(rows),
            "note":"Adapter requires validation on real VFL Assistant v0.5.11 export; no such sample embedded here"}
