"""
data.py
-------
Handles all data loading, cleaning, fantasy enrichment, and percentile
pre-calculation for the FIFA World Cup 2026 Player Analytics dashboard.
"""

import pandas as pd
import numpy as np
import unicodedata

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv('fifa_world_cup_2026_player_stats.csv')

# ── String cleaning ───────────────────────────────────────────────────────────
if 'xg_goal_effiency_rate' in df.columns:
    df['xg_goal_effiency_rate_num'] = (
        df['xg_goal_effiency_rate']
        .astype(str)
        .str.replace('x', '', regex=False)
    )
    df['xg_goal_effiency_rate_num'] = pd.to_numeric(
        df['xg_goal_effiency_rate_num'], errors='coerce'
    )
else:
    df['xg_goal_effiency_rate_num'] = np.nan

# ── Synthetic top-speed column ────────────────────────────────────────────────
if 'top_speed' not in df.columns:
    df['top_speed'] = df['avg_speed'] * 1.8 + np.random.uniform(5, 10, len(df))
    df['top_speed'] = df['top_speed'].clip(15, 36)

# ── Numeric coercion ──────────────────────────────────────────────────────────
NUMERIC_COLS = [
    'goals', 'assists',
    'total_competition_matches_played', 'total_competition_minutes_played',
    'attempt_at_goal', 'attempt_at_goal_on_target',
    'attempt_at_goal_conversion_rate',
    'attempt_at_goal_inside_the_penalty_area',
    'attempt_at_goal_outside_the_penalty_area',
    'headed_attempt_at_goal', 'xg', 'xg_goal_effiency_rate_num',
    'corners', 'offsides', 'possession',
    'passes', 'passing_accuracy_rate', 'crosses', 'crossing_accuracy_rate',
    'linebreaks_attempted_defensive_line',
    'linebreak_attempted_defensive_line_rate',
    'attempted_switches_of_play', 'switches_of_play_rate', 'forced_turnovers',
    'defensive_pressures_applied', 'direct_defensive_pressures_applied',
    'own_goals', 'fouls_against', 'fouls_for',
    'yellow_cards', 'red_cards', 'indirect_red_cards',
    'goalkeeper_saves',
    'goalkeeper_defensive_actions_inside_penalty_area',
    'goalkeeper_defensive_actions_outside_penalty_area',
    'offers_to_receive_total', 'offers_to_receive_in_behind',
    'offers_to_receive_in_between', 'offers_to_receive_in_front',
    'offers_to_receive_inside', 'offers_to_receive_outside',
    'receptions_in_behind',
    'receptions_between_midfield_and_defensive_line',
    'receptions_under_pressure', 'number_of_involvements',
    'avg_speed', 'sprints', 'speed_runs', 'total_distance', 'top_speed',
]

for col in NUMERIC_COLS:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# ── Fantasy enrichment ────────────────────────────────────────────────────────
KNOWN_PRICES = {
    "Kylian Mbappe": 12.0,   "Lionel Messi": 12.0,
    "Erling Haaland": 11.5,  "Vinicius Junior": 11.0,
    "Bruno Fernandes": 10.0, "Jude Bellingham": 10.0,
    "Michael Olise": 9.5,    "Lamine Yamal": 8.5,
    "Jamal Musiala": 8.5,    "Cody Gakpo": 7.5,
    "Denzel Dumfries": 5.7,  "Marc Cucurella": 6.0,
    "William Saliba": 6.0,   "Emiliano Martinez": 5.5,
    "Jordan Pickford": 5.5,  "Maxime Crepeau": 4.5,
    "Camilo Vargas": 4.3,    "Raul Rangel": 3.9,
    "Lisandro Martinez": 4.6,"Jan Paul Van Hecke": 4.3,
    "Daniel Munoz": 4.6,     "Keito Nakamura": 5.5,
    "Ismael Saibari": 5.5,   "Enner Valencia": 5.9,
    "Mohamed Salah": 11.0,   "Nicolas Jackson": 7.5,
    "Sadio Mane": 8.0,       "Andy Diouf": 5.0,
    "Franck Kessie": 6.0,
}

TEAM_CLEAN_SHEETS = {
    "Spain": 3,
    "Argentina": 2, "France": 2, "England": 2,
    "Colombia": 1, "Germany": 1, "Netherlands": 1, "Canada": 1,
    "Portugal": 1, "Brazil": 1, "Morocco": 1, "Ecuador": 1, "Mexico": 1,
}


def get_player_price(row):
    name = row['name']
    if name in KNOWN_PRICES:
        return KNOWN_PRICES[name]
    norm = "".join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )
    if norm in KNOWN_PRICES:
        return KNOWN_PRICES[norm]

    pos     = row['position_desc']
    goals   = row['goals']
    assists = row['assists']
    xg      = row['xg']
    minutes = row['total_competition_minutes_played']

    if pos == 'Goalkeeper':
        price = 4.0 + min(2.0, row['goalkeeper_saves'] * 0.05 + minutes * 0.002)
    elif pos == 'Defender':
        cs = TEAM_CLEAN_SHEETS.get(row['team_name'], 0)
        price = 4.0 + min(2.5, goals * 0.4 + assists * 0.3 + cs * 0.2 + minutes * 0.003)
    elif pos == 'Midfielder':
        price = 4.5 + min(6.0, goals * 0.5 + assists * 0.4 + xg * 0.3 + minutes * 0.004)
    else:
        price = 5.0 + min(7.0, goals * 0.6 + assists * 0.4 + xg * 0.4 + minutes * 0.004)

    return round(price, 1)


def calculate_fantasy_points(row):
    pos     = row['position_desc']
    minutes = row['total_competition_minutes_played']
    goals   = row['goals']
    assists = row['assists']
    yellow  = row['yellow_cards']
    red     = row['red_cards'] + row['indirect_red_cards']
    og      = row['own_goals']

    n_matches = np.ceil(minutes / 90.0)
    app_points = (
        0 if n_matches == 0
        else min(6.0, (minutes // 90) * 2 + (1 if (minutes % 90) >= 30 else 0))
    )

    goal_pts = {'Goalkeeper': 9, 'Defender': 7, 'Midfielder': 6}.get(pos, 5) * goals
    assist_pts = assists * 3

    cs_count = TEAM_CLEAN_SHEETS.get(row['team_name'], 0)
    cs_pts = 0
    if minutes >= 60 * cs_count:
        if pos in ['Goalkeeper', 'Defender']:
            cs_pts = cs_count * 5
        elif pos == 'Midfielder':
            cs_pts = cs_count * 1

    save_pts = (row['goalkeeper_saves'] // 3) if pos == 'Goalkeeper' else 0
    card_pts = -(yellow * 1) - (red * 2) - (og * 2)

    bonus_pts = 0
    if pos == 'Midfielder':
        bonus_pts += row['forced_turnovers'] // 3
        bonus_pts += row['receptions_between_midfield_and_defensive_line'] // 20
    elif pos == 'Forward':
        bonus_pts += row['attempt_at_goal_on_target'] // 2

    return max(0.0, app_points + goal_pts + assist_pts + cs_pts + save_pts + card_pts + bonus_pts)


df['price']             = df.apply(get_player_price, axis=1)
df['est_fantasy_points']= df.apply(calculate_fantasy_points, axis=1)
df['value_factor']      = round(df['est_fantasy_points'] / df['price'], 2)
df['total_distance_km'] = round(df['total_distance'] / 1000.0, 2)
df['sports_person_id']  = df['sports_person_id'].astype(str)

# ── Percentile ranks for radar chart ─────────────────────────────────────────
df['goals_pct']    = df['goals'].rank(pct=True, method='min') * 100
df['passing_pct']  = df['passing_accuracy_rate'].fillna(0).rank(pct=True, method='min') * 100
df['defending_pct']= df['forced_turnovers'].fillna(0).rank(pct=True, method='min') * 100
df['speed_pct']    = df['top_speed'].fillna(0).rank(pct=True, method='min') * 100
df['distance_pct'] = df['total_distance'].fillna(0).rank(pct=True, method='min') * 100

# ── Convenience filter option lists ──────────────────────────────────────────
team_options = (
    [{'label': 'All Teams', 'value': 'All'}]
    + [{'label': t, 'value': t} for t in sorted(df['team_name'].dropna().unique())]
)
position_options = (
    [{'label': 'All Positions', 'value': 'All'}]
    + [{'label': p, 'value': p} for p in sorted(df['position_desc'].dropna().unique())]
)

min_price = float(df['price'].min())
max_price = float(df['price'].max())
