"""
update_strengths.py
===================
Fetch hasil match WC 2026 dari openfootball/worldcup.json
Hitung ulang strength rating berdasarkan performa aktual
Update data/strengths.json → di-commit ke repo → GitHub Pages serve fresh data

Run: python update_strengths.py
Dipanggil oleh GitHub Actions setiap 30 menit selama turnamen.
"""

import json
import os
import urllib.request
import math
from datetime import datetime, timezone

# ── BASE URL ──────────────────────────────────────────────────────────────────
DATA_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# ── BASE STRENGTH (FIFA Rank April 2026) ─────────────────────────────────────
# Ini adalah prior — akan disesuaikan setelah setiap pertandingan
BASE_STRENGTH = {
    "France":          0.93, "Spain":           0.92, "Argentina":       0.91,
    "Brazil":          0.89, "England":         0.88, "Portugal":        0.87,
    "Germany":         0.83, "Netherlands":     0.84, "Belgium":         0.82,
    "Morocco":         0.80, "Croatia":         0.79, "Colombia":        0.78,
    "Uruguay":         0.76, "Switzerland":     0.75, "Senegal":         0.74,
    "Japan":           0.74, "Turkiye":         0.73, "Mexico":          0.73,
    "USA":             0.72, "Norway":          0.72, "South Korea":     0.71,
    "Austria":         0.71, "Canada":          0.69, "Czechia":         0.68,
    "Iran":            0.67, "Egypt":           0.66, "Australia":       0.66,
    "Scotland":        0.65, "Algeria":         0.65, "Ecuador":         0.64,
    "Ivory Coast":     0.63, "DR Congo":        0.61, "Paraguay":        0.61,
    "Tunisia":         0.60, "Bosnia and Herzegovina": 0.60, "Ghana":    0.59,
    "South Africa":    0.58, "Saudi Arabia":    0.58, "Iraq":            0.58,
    "Panama":          0.58, "Uzbekistan":      0.57, "Qatar":           0.56,
    "Cape Verde":      0.55, "Jordan":          0.54, "New Zealand":     0.52,
    "Haiti":           0.50, "Curacao":         0.50,
}

# Name normalization dari openfootball ke nama kita
NAME_MAP = {
    "Czech Republic":         "Czechia",
    "Turkey":                 "Turkiye",
    "Türkiye":                "Turkiye",
    "Bosnia & Herzegovina":   "Bosnia and Herzegovina",
    "Bosnia-Herzegovina":     "Bosnia and Herzegovina",
    "DR Congo":               "DR Congo",
    "Curaçao":                "Curacao",
    "Côte d'Ivoire":          "Ivory Coast",
    "Ivory Coast":            "Ivory Coast",
    "New Zealand":            "New Zealand",
}

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Switzerland", "Qatar", "Bosnia and Herzegovina"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkiye"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

def normalize(name):
    return NAME_MAP.get(name, name)


def fetch_matches():
    """Fetch JSON dari openfootball."""
    print(f"Fetching: {DATA_URL}")
    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "wc2026-simulator/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        print(f"✓ Fetched {len(data.get('matches', []))} matches")
        return data.get("matches", [])
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        return []


def parse_score(match):
    """
    Return (score1, score2) or None if match not yet played.
    openfootball format: {'score': {'ft': [2, 1]}} or no score key.
    """
    score = match.get("score")
    if not score:
        return None
    ft = score.get("ft")
    if ft and len(ft) == 2:
        return int(ft[0]), int(ft[1])
    return None

KNOCKOUT_ROUNDS = {"Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final", "Match for third place"}

def detect_eliminated(matches):
    """Cari tim yang kalah di babak knockout (otomatis tersingkir)."""
    eliminated = {}
    for m in matches:
        if m.get("round") not in KNOCKOUT_ROUNDS:
            continue
        score = m.get("score")
        if not score:
            continue
        ft = score.get("ft")
        if not ft:
            continue
        g1, g2 = ft
        t1, t2 = normalize(m.get("team1", "")), normalize(m.get("team2", ""))
        pens = score.get("p")

        if g1 == g2 and pens:
            loser = t1 if pens[0] < pens[1] else t2
        elif g1 > g2:
            loser = t2
        elif g2 > g1:
            loser = t1
        else:
            continue

        eliminated[loser] = {"round": m.get("round"), "date": m.get("date", "")}
    return eliminated

def detect_group_stage_eliminations(matches):
    """
    Cek apakah fase grup sudah selesai (semua tim main 3 match).
    Kalau ya, hitung top-2 + 8 best third place, sisanya tersingkir.
    """
    group_matches = [m for m in matches if (m.get("round") or "").startswith("Matchday") and m.get("score")]

    pts, gf, ga, played = {}, {}, {}, {}
    for teams in GROUPS.values():
        for t in teams:
            pts[t] = 0; gf[t] = 0; ga[t] = 0; played[t] = 0

    for m in group_matches:
        t1, t2 = normalize(m.get("team1", "")), normalize(m.get("team2", ""))
        if t1 not in pts or t2 not in pts:
            continue
        ft = m["score"].get("ft")
        if not ft:
            continue
        g1, g2 = ft
        gf[t1] += g1; ga[t1] += g2; gf[t2] += g2; ga[t2] += g1
        played[t1] += 1; played[t2] += 1
        if g1 > g2: pts[t1] += 3
        elif g2 > g1: pts[t2] += 3
        else: pts[t1] += 1; pts[t2] += 1

    qualified_top2 = []
    third_candidates = []
    all_complete = True

    for gname, teams in GROUPS.items():
        if not all(played.get(t, 0) >= 3 for t in teams):
            all_complete = False
            continue
        gd = {t: gf[t] - ga[t] for t in teams}
        ranked = sorted(teams, key=lambda t: (pts[t], gd[t], gf[t]), reverse=True)
        qualified_top2.extend(ranked[:2])
        third_candidates.append((ranked[2], pts[ranked[2]], gd[ranked[2]]))

    if not third_candidates:
        return {}

    third_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best_8_third = [t[0] for t in third_candidates[:8]]
    qualified_32 = set(qualified_top2 + best_8_third)

    eliminated = {}
    for teams in GROUPS.values():
        for t in teams:
            if played.get(t, 0) >= 3 and t not in qualified_32:
                eliminated[t] = {"round": "Group Stage", "date": ""}

    return eliminated

def update_strengths(matches):
    """
    Bayesian-style update: setelah setiap match, strength tim diupdate
    berdasarkan expected outcome vs actual outcome.

    Formula:
        expected_win_prob = sigmoid(strength_A - strength_B)
        actual = 1 (menang), 0.5 (seri), 0 (kalah)
        delta = LEARNING_RATE * (actual - expected)
        strength_A += delta
        strength_B -= delta

    Lebih banyak gol selisih → dampak lebih besar (capped).
    """
    LEARNING_RATE = 0.012   # seberapa cepat strength berubah per match
    GD_FACTOR     = 0.003   # bonus per gol selisih (capped di 3)
    MIN_S         = 0.30
    MAX_S         = 0.99

    strengths = dict(BASE_STRENGTH)
    played_count = {}       # track berapa match sudah dimainkan tiap tim
    results_log = []

    for m in matches:
        t1 = normalize(m.get("team1", ""))
        t2 = normalize(m.get("team2", ""))
        sc = parse_score(m)

        if not sc or t1 not in strengths or t2 not in strengths:
            continue

        g1, g2 = sc
        gd = abs(g1 - g2)
        gd_bonus = min(gd, 3) * GD_FACTOR

        s1 = strengths[t1]
        s2 = strengths[t2]

        # Expected win prob for team1
        diff = s1 - s2
        exp_win = 1 / (1 + math.exp(-10 * diff))

        # Actual outcome
        if g1 > g2:
            actual = 1.0
        elif g1 < g2:
            actual = 0.0
        else:
            actual = 0.5

        # Update
        delta = LEARNING_RATE * (actual - exp_win) + (gd_bonus if actual >= 0.5 else -gd_bonus)
        strengths[t1] = max(MIN_S, min(MAX_S, s1 + delta))
        strengths[t2] = max(MIN_S, min(MAX_S, s2 - delta))

        played_count[t1] = played_count.get(t1, 0) + 1
        played_count[t2] = played_count.get(t2, 0) + 1

        results_log.append({
            "match":  f"{t1} {g1}-{g2} {t2}",
            "date":   m.get("date", ""),
            "round":  m.get("round", ""),
            "delta":  round(delta, 4),
        })

    return strengths, played_count, results_log


def save_output(strengths, played_count, results_log, matches_total, eliminated):
    """Save ke data/strengths.json"""
    played_matches = len(results_log)
    out = {
        "meta": {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": DATA_URL,
            "matches_total": matches_total,
            "matches_played": played_matches,
            "matches_remaining": matches_total - played_matches,
        },
        "strengths": strengths,
        "played_count": played_count,
        "results_log": results_log[-20:],
        "eliminated": eliminated,
    }

    path = "docs/data/strengths.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"✓ Saved {path} ({played_matches}/{matches_total} matches played)")

    # Also pretty-print summary
    changed = {t: round(strengths[t] - BASE_STRENGTH.get(t, 0.5), 4)
               for t in strengths if t in BASE_STRENGTH}
    movers_up   = sorted(changed.items(), key=lambda x: -x[1])[:5]
    movers_down = sorted(changed.items(), key=lambda x: x[1])[:5]
    print("\n↑ Biggest gainers:")
    for t, d in movers_up:
        if d > 0: print(f"  {t}: +{d} → {round(strengths[t], 4)}")
    print("↓ Biggest drops:")
    for t, d in movers_down:
        if d < 0: print(f"  {t}: {d} → {round(strengths[t], 4)}")


if __name__ == "__main__":
    matches = fetch_matches()
    if not matches:
        print("No match data.")
        exit(0)
    strengths, played_count, results_log = update_strengths(matches)
    eliminated_knockout = detect_eliminated(matches)
    eliminated_groups   = detect_group_stage_eliminations(matches)
    eliminated = {**eliminated_groups, **eliminated_knockout}

    print(f"\n✗ Eliminated teams: {len(eliminated)}")
    for t, info in eliminated.items():
        print(f"  {t} — out in {info['round']}")
    save_output(strengths, played_count, results_log, len(matches), eliminated)
    print("\nDone.")
