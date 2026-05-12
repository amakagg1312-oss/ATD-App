"""
Gear Explorer — NBA player shoe history from colendri.com.
Parses __NEXT_DATA__ JSON (Next.js SSR). 6-hour cache for player list,
1-hour cache for individual player pages.
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE_URL = "https://www.colendri.com"
LIST_TTL = 21600   # 6 hours
GEAR_TTL = 3600    # 1 hour

_HDRS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "identity",
    "Referer": "https://www.colendri.com/",
}


# ── Cache dir ─────────────────────────────────────────────────────────────────

def _cache_dir():
    here = Path(__file__).parent
    d = here / "gear_cache"
    try:
        d.mkdir(exist_ok=True)
        t = d / ".wt"
        t.touch()
        t.unlink()
        return d
    except OSError:
        pass
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "ATD 2K APP" / "gear_cache"
    else:
        base = Path.home() / "Library" / "Application Support" / "ATD 2K APP" / "gear_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _read_cache(filename):
    p = _cache_dir() / filename
    if not p.exists():
        return None
    return p, p.stat().st_mtime


def _fetch(url):
    req = Request(url, headers=_HDRS)
    with urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


# ── Next.js helpers ────────────────────────────────────────────────────────────

def _next_data(html):
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _all_queries(data):
    return (
        data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
    )


def _page_props(data):
    return data.get("props", {}).get("pageProps", {})


# ── Player list ────────────────────────────────────────────────────────────────

def _normalize_player(raw):
    """Normalise a raw player dict from whatever shape colendri uses."""
    if not isinstance(raw, dict):
        return None
    name = (
        raw.get("name") or raw.get("fullName") or raw.get("playerName") or ""
    ).strip()
    slug = (
        raw.get("slug") or raw.get("urlSlug") or
        (raw.get("url") or "").strip("/").split("/")[-1] or ""
    ).strip()
    team = (
        raw.get("team") or raw.get("teamName") or raw.get("teamSlug") or
        (raw.get("teamInfo") or {}).get("name") or ""
    ).strip()
    jersey = str(
        raw.get("jersey") or raw.get("jerseyNumber") or raw.get("number") or ""
    ).strip()
    if not name or not slug:
        return None
    return {"name": name, "slug": slug, "team": team, "jersey": jersey}


def _players_from_next_data(data):
    props = _page_props(data)
    # Direct props
    for key in ("players", "allPlayers", "playerList", "data"):
        v = props.get(key)
        if isinstance(v, list) and v:
            result = [_normalize_player(p) for p in v]
            result = [p for p in result if p]
            if result:
                return result
    # dehydratedState queries
    for q in _all_queries(data):
        qd = q.get("state", {}).get("data", {})
        if isinstance(qd, dict):
            for key in ("players", "allPlayers", "playerList", "data"):
                v = qd.get(key)
                if isinstance(v, list) and v:
                    result = [_normalize_player(p) for p in v]
                    result = [p for p in result if p]
                    if result:
                        return result
        if isinstance(qd, list) and qd:
            sample = qd[0] if isinstance(qd[0], dict) else {}
            if any(k in sample for k in ("slug", "name", "fullName", "playerName")):
                result = [_normalize_player(p) for p in qd]
                result = [p for p in result if p]
                if result:
                    return result
    return []


def _players_from_html(html):
    """Fallback: scrape /players/{slug}/ links from raw HTML."""
    seen = set()
    players = []
    for m in re.finditer(r'href=["\'](?:/players/)?([a-z][a-z0-9-]+-\d+)/?["\']', html):
        slug = m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        name = _slug_to_name(slug)
        players.append({"name": name, "slug": slug, "team": "", "jersey": ""})
    return players


def _slug_to_name(slug):
    parts = slug.split("-")
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    return " ".join(w.capitalize() for w in parts)


def fetch_player_list(force=False):
    cache_file = _cache_dir() / "player_list_v1.json"
    if not force and cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < LIST_TTL:
            try:
                d = json.loads(cache_file.read_text(encoding="utf-8"))
                if d.get("ok") and d.get("players"):
                    return d
            except Exception:
                pass
    try:
        html = _fetch(f"{BASE_URL}/players/")
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch player list: {e}"}

    data = _next_data(html)
    players = _players_from_next_data(data)
    if not players:
        players = _players_from_html(html)
    if not players:
        return {"ok": False, "error": "Could not parse player list from colendri.com"}

    result = {"ok": True, "players": players}
    try:
        cache_file.write_text(json.dumps(result), encoding="utf-8")
    except Exception:
        pass
    return result


# ── Player gear ────────────────────────────────────────────────────────────────

def _get_nested(obj, *keys, default=""):
    for k in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k, default)
    return obj if obj is not None else default


def _normalize_shoe_entry(raw):
    if not isinstance(raw, dict):
        return None

    # Shoe sub-object (may be nested or flat)
    shoe = raw.get("shoe") or {}
    if isinstance(shoe, str):
        shoe = {"name": shoe}

    brand = (
        _get_nested(shoe, "brand") or _get_nested(shoe, "brandName") or
        raw.get("brand") or raw.get("shoeBrand") or raw.get("brandName") or ""
    )
    model = (
        _get_nested(shoe, "name") or _get_nested(shoe, "model") or
        raw.get("shoeName") or raw.get("model") or raw.get("name") or ""
    )
    colorway = (
        _get_nested(shoe, "colorway") or _get_nested(shoe, "color") or
        raw.get("colorway") or raw.get("color") or raw.get("shoeColor") or ""
    )
    image_url = (
        _get_nested(shoe, "image") or _get_nested(shoe, "imageUrl") or
        _get_nested(shoe, "img") or raw.get("shoeImage") or
        raw.get("imageUrl") or raw.get("image") or ""
    )

    date = str(raw.get("date") or raw.get("gameDate") or raw.get("playedAt") or "")
    opponent = str(
        raw.get("opponent") or raw.get("opponentTeam") or raw.get("opp") or
        _get_nested(raw.get("opponentInfo") or {}, "name") or ""
    )
    season = str(raw.get("season") or raw.get("seasonYear") or raw.get("seasonSlug") or "")

    stats = raw.get("stats") or {}
    def _int(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    pts = _int(stats.get("pts") or stats.get("points") or raw.get("pts") or raw.get("points") or 0)
    reb = _int(stats.get("reb") or stats.get("rebounds") or raw.get("reb") or raw.get("rebounds") or 0)
    ast = _int(stats.get("ast") or stats.get("assists") or raw.get("ast") or raw.get("assists") or 0)

    if not model and not brand:
        return None

    return {
        "date": date,
        "opponent": opponent,
        "brand": brand,
        "model": model,
        "colorway": colorway,
        "image_url": image_url,
        "pts": pts,
        "reb": reb,
        "ast": ast,
        "season": season,
    }


def _shoes_from_next_data(data):
    props = _page_props(data)
    player_info = {}

    # Check direct pageProps
    for pi_key in ("player", "playerData", "playerInfo"):
        if isinstance(props.get(pi_key), dict):
            player_info = props[pi_key]
            break

    shoes_raw = None
    for key in ("shoes", "games", "shoeHistory", "playerGames", "gameLog", "data"):
        v = props.get(key)
        if isinstance(v, list):
            shoes_raw = v
            break

    # dehydratedState
    for q in _all_queries(data):
        qd = q.get("state", {}).get("data", {})
        if isinstance(qd, dict):
            if not player_info:
                for pi_key in ("player", "playerData", "playerInfo"):
                    if isinstance(qd.get(pi_key), dict):
                        player_info = qd[pi_key]
                        break
            if shoes_raw is None:
                for key in ("shoes", "games", "shoeHistory", "playerGames", "gameLog"):
                    v = qd.get(key)
                    if isinstance(v, list):
                        shoes_raw = v
                        break
        if isinstance(qd, list) and qd and shoes_raw is None:
            sample = qd[0] if isinstance(qd[0], dict) else {}
            if any(k in sample for k in ("shoe", "shoeId", "date", "gameDate", "brand", "model")):
                shoes_raw = qd

        if shoes_raw is not None and player_info:
            break

    return shoes_raw or [], player_info


def _shoes_from_html(html):
    """Last-resort: pull shoe names from HTML text nodes."""
    shoes = []
    # Game row pattern: any td/div with a shoe name near a date
    for m in re.finditer(
        r'(\d{4}-\d{2}-\d{2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,\s+\d{4})'
        r'.*?([A-Z][a-z]+(?:\s+[A-Z][a-z\d]+){1,4})',
        html, re.S
    ):
        date = m.group(1)
        name = m.group(2).strip()
        if len(name) > 5:
            shoes.append({"date": date, "brand": "", "model": name, "colorway": "",
                          "image_url": "", "opponent": "", "pts": 0, "reb": 0, "ast": 0, "season": ""})
    return shoes[:200]


def _summarise(shoes):
    brand_counts = {}
    model_counts = {}
    for s in shoes:
        b = (s.get("brand") or "Unknown").strip() or "Unknown"
        full = f"{s['brand']} {s['model']}".strip() if s.get("model") else b
        brand_counts[b] = brand_counts.get(b, 0) + 1
        model_counts[full] = model_counts.get(full, 0) + 1
    top_brand = max(brand_counts, key=brand_counts.get) if brand_counts else ""
    top_shoe  = max(model_counts, key=model_counts.get) if model_counts else ""
    return {
        "total_games": len(shoes),
        "top_brand": top_brand,
        "top_shoe": top_shoe,
        "top_shoe_count": model_counts.get(top_shoe, 0),
        "brand_counts": brand_counts,
        "model_counts": model_counts,
    }


def fetch_player_gear(player_slug, force=False):
    safe = re.sub(r"[^a-z0-9-]", "", player_slug.lower().replace(" ", "-"))
    cache_file = _cache_dir() / f"gear_{safe}_v1.json"

    if not force and cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < GEAR_TTL:
            try:
                d = json.loads(cache_file.read_text(encoding="utf-8"))
                if d.get("ok") and d.get("shoes"):
                    return d
            except Exception:
                pass

    url = f"{BASE_URL}/players/{player_slug}/"
    try:
        html = _fetch(url)
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch {url}: {e}"}

    nd = _next_data(html)
    shoes_raw, player_info = _shoes_from_next_data(nd)

    shoes = [_normalize_shoe_entry(e) for e in shoes_raw]
    shoes = [s for s in shoes if s]

    if not shoes:
        shoes = _shoes_from_html(html)

    if not shoes:
        return {"ok": False, "error": "No shoe data found — colendri may have changed its page structure."}

    shoes.sort(key=lambda x: x.get("date") or "", reverse=True)

    player_name = (
        player_info.get("name") or player_info.get("fullName") or
        player_info.get("playerName") or _slug_to_name(player_slug)
    )

    result = {
        "ok": True,
        "player_name": player_name,
        "player_slug": player_slug,
        "player_info": {
            "team":     str(player_info.get("team") or player_info.get("teamName") or ""),
            "jersey":   str(player_info.get("jersey") or player_info.get("number") or ""),
            "position": str(player_info.get("position") or player_info.get("pos") or ""),
            "image_url": str(player_info.get("image") or player_info.get("imageUrl") or ""),
        },
        "summary": _summarise(shoes),
        "shoes": shoes,
    }

    try:
        cache_file.write_text(json.dumps(result), encoding="utf-8")
    except Exception:
        pass
    return result


def search_players(term, force=False):
    result = fetch_player_list(force=force)
    if not result.get("ok"):
        return result
    term_l = term.lower().strip()
    if not term_l:
        return {"ok": True, "players": result["players"][:50]}
    filtered = [
        p for p in result["players"]
        if term_l in p.get("name", "").lower() or term_l in p.get("slug", "").lower()
    ]
    return {"ok": True, "players": filtered[:50]}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "list":
        print(json.dumps(fetch_player_list()))
    elif cmd == "player" and len(sys.argv) > 2:
        print(json.dumps(fetch_player_gear(sys.argv[2])))
    elif cmd == "search" and len(sys.argv) > 2:
        print(json.dumps(search_players(sys.argv[2])))
    else:
        print(json.dumps({"ok": False, "error": "Usage: gear_explorer.py list|player <slug>|search <term>"}))
