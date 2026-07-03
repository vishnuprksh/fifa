import dash
from dash import dcc, html, dash_table, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import json
import unicodedata

# ----------------- DATA PREPARATION & CLEANING -----------------
# Load statistics dataset
df = pd.read_csv('fifa_world_cup_2026_player_stats.csv')

# Handle string cleaning and parsing
if 'xg_goal_effiency_rate' in df.columns:
    df['xg_goal_effiency_rate_num'] = df['xg_goal_effiency_rate'].astype(str).str.replace('x', '', regex=False)
    df['xg_goal_effiency_rate_num'] = pd.to_numeric(df['xg_goal_effiency_rate_num'], errors='coerce')
else:
    df['xg_goal_effiency_rate_num'] = np.nan

# Handle top_speed placeholder if it exists in the data, or fill with mock for demonstration if missing
if 'top_speed' not in df.columns:
    # Estimate top speed from average speed or sprints
    df['top_speed'] = df['avg_speed'] * 1.8 + np.random.uniform(5, 10, len(df))
    # Cap logically
    df['top_speed'] = df['top_speed'].clip(15, 36)

# Ensure numeric columns are formatted correctly
numeric_cols = [
    'goals', 'assists', 'total_competition_minutes_played', 'attempt_at_goal',
    'attempt_at_goal_on_target', 'attempt_at_goal_conversion_rate',
    'attempt_at_goal_inside_the_penalty_area', 'attempt_at_goal_outside_the_penalty_area',
    'headed_attempt_at_goal', 'xg', 'xg_goal_effiency_rate_num', 'corners',
    'passes', 'passing_accuracy_rate', 'crosses', 'crossing_accuracy_rate',
    'linebreaks_attempted_defensive_line', 'linebreak_attempted_defensive_line_rate',
    'attempted_switches_of_play', 'switches_of_play_rate', 'forced_turnovers',
    'defensive_pressures_applied', 'direct_defensive_pressures_applied', 'own_goals',
    'fouls_against', 'fouls_for', 'yellow_cards', 'red_cards', 'indirect_red_cards',
    'offsides', 'goalkeeper_saves', 'goalkeeper_defensive_actions_inside_penalty_area',
    'goalkeeper_defensive_actions_outside_penalty_area', 'offers_to_receive_total',
    'offers_to_receive_in_behind', 'offers_to_receive_in_between', 'offers_to_receive_in_front',
    'offers_to_receive_inside', 'offers_to_receive_outside', 'receptions_in_behind',
    'receptions_between_midfield_and_defensive_line', 'receptions_under_pressure',
    'number_of_involvements', 'avg_speed', 'sprints', 'speed_runs', 'total_distance', 'top_speed'
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# ----------------- FANTASY ENRICHMENT -----------------
# Define known player prices from rules/tips documentation
KNOWN_PRICES = {
    "Kylian Mbappe": 12.0,
    "Lionel Messi": 12.0,
    "Erling Haaland": 11.5,
    "Vinicius Junior": 11.0,
    "Bruno Fernandes": 10.0,
    "Jude Bellingham": 10.0,
    "Michael Olise": 9.5,
    "Lamine Yamal": 8.5,
    "Jamal Musiala": 8.5,
    "Cody Gakpo": 7.5,
    "Denzel Dumfries": 5.7,
    "Marc Cucurella": 6.0,
    "William Saliba": 6.0,
    "Emiliano Martinez": 5.5,
    "Jordan Pickford": 5.5,
    "Maxime Crepeau": 4.5,
    "Camilo Vargas": 4.3,
    "Raul Rangel": 3.9,
    "Lisandro Martinez": 4.6,
    "Jan Paul Van Hecke": 4.3,
    "Daniel Munoz": 4.6,
    "Keito Nakamura": 5.5,
    "Ismael Saibari": 5.5,
    "Enner Valencia": 5.9,
    "Mohamed Salah": 11.0,
    "Nicolas Jackson": 7.5,
    "Sadio Mane": 8.0,
    "Andy Diouf": 5.0,
    "Franck Kessie": 6.0,
}

# Group-stage clean sheets mapping for nations
TEAM_CLEAN_SHEETS = {
    "Spain": 3,
    "Argentina": 2, "France": 2, "England": 2,
    "Colombia": 1, "Germany": 1, "Netherlands": 1, "Canada": 1, "Portugal": 1, "Brazil": 1, "Morocco": 1, "Ecuador": 1, "Mexico": 1
}

def get_player_price(row):
    name = row['name']
    if name in KNOWN_PRICES:
        return KNOWN_PRICES[name]
    
    norm_name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    if norm_name in KNOWN_PRICES:
        return KNOWN_PRICES[norm_name]
    
    pos = row['position_desc']
    goals = row['goals']
    assists = row['assists']
    xg = row['xg']
    minutes = row['total_competition_minutes_played']
    
    if pos == 'Goalkeeper':
        base = 4.0
        bonus = (row['goalkeeper_saves'] * 0.05) + (minutes * 0.002)
        price = base + min(2.0, bonus)
    elif pos == 'Defender':
        base = 4.0
        cs = TEAM_CLEAN_SHEETS.get(row['team_name'], 0)
        bonus = (goals * 0.4) + (assists * 0.3) + (cs * 0.2) + (minutes * 0.003)
        price = base + min(2.5, bonus)
    elif pos == 'Midfielder':
        base = 4.5
        bonus = (goals * 0.5) + (assists * 0.4) + (xg * 0.3) + (minutes * 0.004)
        price = base + min(6.0, bonus)
    else: # Forward
        base = 5.0
        bonus = (goals * 0.6) + (assists * 0.4) + (xg * 0.4) + (minutes * 0.004)
        price = base + min(7.0, bonus)
        
    return round(price, 1)

def calculate_fantasy_points(row):
    pos = row['position_desc']
    minutes = row['total_competition_minutes_played']
    goals = row['goals']
    assists = row['assists']
    yellow = row['yellow_cards']
    red = row['red_cards'] + row['indirect_red_cards']
    og = row['own_goals']
    
    n_matches = np.ceil(minutes / 90.0)
    if n_matches == 0:
        app_points = 0
    else:
        app_points = min(6.0, (minutes // 90) * 2 + (1 if (minutes % 90) >= 30 else 0))
        
    if pos == 'Goalkeeper':
        goal_pts = goals * 9
    elif pos == 'Defender':
        goal_pts = goals * 7
    elif pos == 'Midfielder':
        goal_pts = goals * 6
    else: # Forward
        goal_pts = goals * 5
        
    assist_pts = assists * 3
    
    cs_count = TEAM_CLEAN_SHEETS.get(row['team_name'], 0)
    if minutes >= 60 * cs_count:
        if pos in ['Goalkeeper', 'Defender']:
            cs_pts = cs_count * 5
        elif pos == 'Midfielder':
            cs_pts = cs_count * 1
        else:
            cs_pts = 0
    else:
        cs_pts = 0
        
    save_pts = 0
    if pos == 'Goalkeeper':
        save_pts = row['goalkeeper_saves'] // 3
        
    card_pts = -(yellow * 1) - (red * 2) - (og * 2)
    
    bonus_pts = 0
    if pos == 'Midfielder':
        bonus_pts += row['forced_turnovers'] // 3
        bonus_pts += row['receptions_between_midfield_and_defensive_line'] // 20
    elif pos == 'Forward':
        bonus_pts += row['attempt_at_goal_on_target'] // 2
        
    total = app_points + goal_pts + assist_pts + cs_pts + save_pts + card_pts + bonus_pts
    return max(0.0, total)

df['price'] = df.apply(get_player_price, axis=1)
df['est_fantasy_points'] = df.apply(calculate_fantasy_points, axis=1)
df['value_factor'] = round(df['est_fantasy_points'] / df['price'], 2)
df['total_distance_km'] = round(df['total_distance'] / 1000.0, 2)
df['sports_person_id'] = df['sports_person_id'].astype(str)

# ----------------- RADAR PERCENTILES PRECALCULATION -----------------
# Generate percentile ranks for key scouting categories
df['goals_pct'] = df['goals'].rank(pct=True, method='min') * 100
df['passing_pct'] = df['passing_accuracy_rate'].fillna(0).rank(pct=True, method='min') * 100
df['defending_pct'] = df['forced_turnovers'].fillna(0).rank(pct=True, method='min') * 100
df['speed_pct'] = df['top_speed'].fillna(0).rank(pct=True, method='min') * 100
df['distance_pct'] = df['total_distance'].fillna(0).rank(pct=True, method='min') * 100

# Default squad list from round_of_32/fantasy_team.md
DEFAULT_SQUAD_IDS = [
    '331732', '360642', '489517', '405841', '430735',
    '402921', '431200', '405742', '405522', '429642',
    '448598', '484320', '448152', '389867', '229397'
]

# ----------------- ANALYTICS CONFIGURATIONS -----------------
# Column definitions grouped by dynamic category toggles
COLUMN_CATEGORIES = {
    "general": {
        "label": "General / Fantasy",
        "columns": [
            {"name": "Player Name", "id": "name"},
            {"name": "Team", "id": "team_abbr"},
            {"name": "Pos", "id": "position_desc"},
            {"name": "Price ($M)", "id": "price", "type": "numeric"},
            {"name": "Est. Points", "id": "est_fantasy_points", "type": "numeric"},
            {"name": "Value (Pts/$M)", "id": "value_factor", "type": "numeric"},
            {"name": "Goals", "id": "goals", "type": "numeric"},
            {"name": "Assists", "id": "assists", "type": "numeric"},
            {"name": "xG", "id": "xg", "type": "numeric"},
            {"name": "Mins Played", "id": "total_competition_minutes_played", "type": "numeric"}
        ]
    },
    "attacking": {
        "label": "Attacking Statistics",
        "columns": [
            {"name": "Player Name", "id": "name"},
            {"name": "Goals", "id": "goals", "type": "numeric"},
            {"name": "Expected Goals (xG)", "id": "xg", "type": "numeric"},
            {"name": "Shots Attempted", "id": "attempt_at_goal", "type": "numeric"},
            {"name": "Shots on Target", "id": "attempt_at_goal_on_target", "type": "numeric"},
            {"name": "Conversion (%)", "id": "attempt_at_goal_conversion_rate", "type": "numeric"},
            {"name": "Shots Inside Box", "id": "attempt_at_goal_inside_the_penalty_area", "type": "numeric"},
            {"name": "Shots Outside Box", "id": "attempt_at_goal_outside_the_penalty_area", "type": "numeric"},
            {"name": "Headed Attempts", "id": "headed_attempt_at_goal", "type": "numeric"},
            {"name": "Corners", "id": "corners", "type": "numeric"}
        ]
    },
    "passing": {
        "label": "Distribution & Passing",
        "columns": [
            {"name": "Player Name", "id": "name"},
            {"name": "Assists", "id": "assists", "type": "numeric"},
            {"name": "Passes Attempted", "id": "passes", "type": "numeric"},
            {"name": "Pass Accuracy (%)", "id": "passing_accuracy_rate", "type": "numeric"},
            {"name": "Crosses Attempted", "id": "crosses", "type": "numeric"},
            {"name": "Cross Accuracy (%)", "id": "crossing_accuracy_rate", "type": "numeric"},
            {"name": "Linebreaks Attempted", "id": "linebreaks_attempted_defensive_line", "type": "numeric"},
            {"name": "Linebreak Acc (%)", "id": "linebreak_attempted_defensive_line_rate", "type": "numeric"},
            {"name": "Switches Attempted", "id": "attempted_switches_of_play", "type": "numeric"},
            {"name": "Switches Acc (%)", "id": "switches_of_play_rate", "type": "numeric"}
        ]
    },
    "defending": {
        "label": "Defending & Discipline",
        "columns": [
            {"name": "Player Name", "id": "name"},
            {"name": "Recoveries", "id": "forced_turnovers", "type": "numeric"},
            {"name": "Pressures Applied", "id": "defensive_pressures_applied", "type": "numeric"},
            {"name": "Direct Pressures", "id": "direct_defensive_pressures_applied", "type": "numeric"},
            {"name": "Fouls Committed", "id": "fouls_against", "type": "numeric"},
            {"name": "Fouls Won", "id": "fouls_for", "type": "numeric"},
            {"name": "Yellow Cards", "id": "yellow_cards", "type": "numeric"},
            {"name": "Red Cards", "id": "red_cards", "type": "numeric"},
            {"name": "Own Goals", "id": "own_goals", "type": "numeric"}
        ]
    },
    "physical": {
        "label": "Physical & Movement",
        "columns": [
            {"name": "Player Name", "id": "name"},
            {"name": "Top Speed (km/h)", "id": "top_speed", "type": "numeric"},
            {"name": "Avg Speed (km/h)", "id": "avg_speed", "type": "numeric"},
            {"name": "Sprints", "id": "sprints", "type": "numeric"},
            {"name": "Speed Runs", "id": "speed_runs", "type": "numeric"},
            {"name": "Distance (km)", "id": "total_distance_km", "type": "numeric"},
            {"name": "Touches", "id": "number_of_involvements", "type": "numeric"},
            {"name": "Receptions Under Press", "id": "receptions_under_pressure", "type": "numeric"}
        ]
    },
    "goalkeeping": {
        "label": "Goalkeeping Metrics",
        "columns": [
            {"name": "Player Name", "id": "name"},
            {"name": "Saves", "id": "goalkeeper_saves", "type": "numeric"},
            {"name": "Def Actions Inside Box", "id": "goalkeeper_defensive_actions_inside_penalty_area", "type": "numeric"},
            {"name": "Def Actions Outside Box", "id": "goalkeeper_defensive_actions_outside_penalty_area", "type": "numeric"},
            {"name": "Mins Played", "id": "total_competition_minutes_played", "type": "numeric"}
        ]
    }
}

# Master list of all numerical metrics for the correlation scatter plot and Leaderboards
METRICS_CONFIG = {
    "adidas Golden Boot": {
        "goals": "Goals Scored",
        "assists": "Assists Provided",
        "total_competition_minutes_played": "Minutes Played",
    },
    "Attacking": {
        "goals": "Goals Scored",
        "assists": "Assists",
        "attempt_at_goal": "Attempts at Goal",
        "attempt_at_goal_on_target": "Attempts on Target",
        "attempt_at_goal_conversion_rate": "Goal Conversion Rate (%)",
        "attempt_at_goal_inside_the_penalty_area": "Shots Inside Box",
        "attempt_at_goal_outside_the_penalty_area": "Shots Outside Box",
        "headed_attempt_at_goal": "Headed Attempts",
        "xg": "Expected Goals (xG)",
        "xg_goal_effiency_rate_num": "xG Finishing Ratio",
        "corners": "Corners Taken",
    },
    "Distribution": {
        "passes": "Passes Attempted",
        "passing_accuracy_rate": "Passing Accuracy Rate (%)",
        "crosses": "Crosses Attempted",
        "crossing_accuracy_rate": "Crossing Accuracy Rate (%)",
        "linebreaks_attempted_defensive_line": "Defensive Linebreaks Attempted",
        "linebreak_attempted_defensive_line_rate": "Defensive Linebreaks Accuracy (%)",
        "attempted_switches_of_play": "Switches of Play Attempted",
        "switches_of_play_rate": "Switches of Play Accuracy (%)",
    },
    "Defending": {
        "forced_turnovers": "Forced Turnovers / Recoveries",
        "defensive_pressures_applied": "Defensive Pressures Applied",
        "direct_defensive_pressures_applied": "Direct Pressures Applied",
        "own_goals": "Own Goals Conceded",
    },
    "Discipline": {
        "fouls_against": "Fouls Committed",
        "fouls_for": "Fouls Won",
        "yellow_cards": "Yellow Cards",
        "red_cards": "Red Cards",
        "indirect_red_cards": "Second Yellow Cards",
        "offsides": "Offsides",
    },
    "Goalkeeping": {
        "goalkeeper_saves": "Goalkeeper Saves",
        "goalkeeper_defensive_actions_inside_penalty_area": "Defensive Actions Inside Penalty Box",
        "goalkeeper_defensive_actions_outside_penalty_area": "Defensive Actions Outside Penalty Box",
    },
    "Physical": {
        "avg_speed": "Average Speed (km/h)",
        "top_speed": "Top Speed (km/h)",
        "sprints": "Sprints Completed",
        "speed_runs": "High Speed Runs",
        "total_distance": "Total Distance Covered (m)",
    }
}

ALL_METRICS = {
    "price": "Fantasy Price ($M)",
    "est_fantasy_points": "Estimated Fantasy Points",
    "value_factor": "Value (Pts/$M)",
    "goals": "Goals Scored",
    "assists": "Assists Provided",
    "xg": "Expected Goals (xG)",
    "total_competition_minutes_played": "Minutes Played",
    "passes": "Passes Attempted",
    "passing_accuracy_rate": "Passing Accuracy (%)",
    "forced_turnovers": "Forced Turnovers",
    "defensive_pressures_applied": "Defensive Pressures",
    "top_speed": "Top Speed (km/h)",
    "total_distance_km": "Total Distance (km)",
    "sprints": "Sprints Completed"
}

# Dropdown filter configurations
team_options = [{'label': 'All Teams', 'value': 'All'}] + [{'label': t, 'value': t} for t in sorted(df['team_name'].dropna().unique())]
position_options = [{'label': 'All Positions', 'value': 'All'}] + [{'label': p, 'value': p} for p in sorted(df['position_desc'].dropna().unique())]

min_price = float(df['price'].min())
max_price = float(df['price'].max())

# Initialize Dash application
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": "Premium Dashboard showing FIFA World Cup 2026 Player Statistics & Tactical Squad Planner."}
    ],
    title="Player Analytics Center | FIFA World Cup 2026",
    suppress_callback_exceptions=True
)

# Plotly theme configuration
PLOTLY_LAYOUT_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color='#cbd5e1'),
        margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.12)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.12)'),
    )
)

# Helper to render empty or filled squad slots in tactical pitch layout
def render_squad_slot(player, slot_position_desc, index):
    if player is not None:
        pid = player['sports_person_id']
        img_src = player['headshot_url'] if pd.notna(player['headshot_url']) and player['headshot_url'] != '' else "https://play.fifa.com/media/image/headshots/389867_headshot.png"
        flag_src = player['flag_url'] if pd.notna(player['flag_url']) else ""
        return dbc.Col([
            html.Div([
                # Remove button (pattern-matching dict)
                html.Div("×", id={"type": "remove-player", "index": str(pid)}, className="squad-slot-remove", title="Remove player"),
                html.Div([
                    html.Div([
                        html.Img(src=img_src, style={"height": "48px", "width": "48px", "borderRadius": "50%", "border": "2px solid #00b8ff", "backgroundColor": "rgba(0,0,0,0.3)"})
                    ], className="mb-1"),
                    html.Div(player['name'], className="squad-slot-name"),
                    html.Div([
                        html.Img(src=flag_src, className="flag-badge"),
                        html.Span(player['team_abbr'], style={"fontSize": "10px"})
                    ], className="mb-1"),
                    html.Div(f"${player['price']:.1f}M • {player['est_fantasy_points']:.0f} pts", className="squad-slot-stats"),
                    html.Div(slot_position_desc, className="squad-slot-badge")
                ], className="squad-slot-info")
            ], className="squad-slot-filled")
        ], xs=6, sm=4, md=2, className="mb-3")
    else:
        return dbc.Col([
            html.Div([
                html.Div("+", style={"fontSize": "22px", "fontWeight": "bold", "color": "rgba(255,255,255,0.2)", "lineHeight": "1"}),
                html.Div(f"Add {slot_position_desc[:3].upper()}", style={"marginTop": "4px", "fontWeight": "500"})
            ], className="squad-slot-empty", id=f"empty-slot-{slot_position_desc.lower()}-{index}")
        ], xs=6, sm=4, md=2, className="mb-3")

# ----------------- APP LAYOUT -----------------
app.layout = dbc.Container([
    # Active category state store & squad draft store
    dcc.Store(id="active-category-store", data="general"),
    dcc.Store(id="draft-squad-store", data=DEFAULT_SQUAD_IDS, storage_type="session"),
    
    # Floating Alerts
    dbc.Alert(id="add-to-squad-alert", is_open=False, duration=3000, dismissable=True, style={"position": "fixed", "top": "20px", "right": "20px", "zIndex": "9999", "boxShadow": "0 4px 15px rgba(0,0,0,0.5)"}),
    dbc.Alert(id="save-squad-alert", is_open=False, duration=4000, dismissable=True, style={"position": "fixed", "top": "20px", "right": "20px", "zIndex": "9999", "boxShadow": "0 4px 15px rgba(0,0,0,0.5)"}),

    # HERO HEADER PANEL
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Row([
                    # Title & Info
                    dbc.Col([
                        html.Span("FIFA WORLD CUP 2026™", className="font-weight-bold", style={"color": "var(--accent-orange)", "fontSize": "12px", "letterSpacing": "3px", "fontWeight": "700"}),
                        html.H1("Player Analytics Center", className="hero-title"),
                        html.P("A comprehensive premium dashboard designed to analyze player parameters, compare stats, and build your dream fantasy squad.", className="text-secondary mb-0", style={"fontSize": "14px"})
                    ], xs=12, md=4, className="mb-3 mb-md-0"),
                    
                    # Dynamic KPIs (Updates based on filters)
                    dbc.Col([
                        html.Div([
                            # KPI 1: Players Count
                            html.Div([
                                html.Div(id="kpi-players-count", className="kpi-val text-info", children="-"),
                                html.Div("Analyzed Players", className="kpi-label")
                            ], className="kpi-card-premium"),
                            
                            # KPI 2: Average xG
                            html.Div([
                                html.Div(id="kpi-avg-xg", className="kpi-val text-primary", children="-"),
                                html.Div("Average xG", className="kpi-label")
                            ], className="kpi-card-premium"),

                            # KPI 3: Max Speed
                            html.Div([
                                html.Div(id="kpi-max-speed", className="kpi-val text-danger", style={"fontSize": "15px"}, children="-"),
                                html.Div("Fastest Player", className="kpi-label")
                            ], className="kpi-card-premium"),

                            # KPI 4: Value Factor
                            html.Div([
                                html.Div(id="kpi-avg-val", className="kpi-val text-success", children="-"),
                                html.Div("Avg Value Factor", className="kpi-label")
                            ], className="kpi-card-premium"),

                            # KPI 5: Interactive Draft Squad Widget
                            html.Div(id="kpi-draft-card", children=[
                                html.Div(id="kpi-draft-count", className="kpi-val text-warning", children="-"),
                                html.Div(id="kpi-draft-label", className="kpi-label", children="Draft Squad")
                            ], className="kpi-card-premium")
                        ], className="kpi-container")
                    ], xs=12, md=8, className="d-flex align-items-center")
                ])
            ], className="hero-header mb-4 mt-3")
        ], width=12)
    ]),

    # TABS NAVIGATION BAR
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Tabs([
                    dbc.Tab(label="🔍 Player Scouting & Comparison", tab_id="tab-scout"),
                    dbc.Tab(label="🛠️ Squad Draft Planner", tab_id="tab-squad"),
                    dbc.Tab(label="🏆 Tournament Leaderboards", tab_id="tab-leaderboard"),
                ], id="dashboard-tabs", active_tab="tab-scout", className="custom-tabs mb-4 px-2")
            ])
        ], width=12)
    ]),

    # INTERACTIVE TAB CONTENT ROW
    dbc.Row([
        dbc.Col([
            html.Div(id="tab-content")
        ], width=12)
    ])
], fluid=True, style={"maxWidth": "1800px"})

# ----------------- CALLBACKS -----------------

# Callback to render the appropriate Tab Layout
@app.callback(
    Output("tab-content", "children"),
    [Input("dashboard-tabs", "active_tab"),
     Input("draft-squad-store", "data")]
)
def render_tab_layout(active_tab, squad_ids):
    if active_tab == "tab-squad":
        # Render tactical squad builder
        squad_ids = squad_ids or []
        squad_df = df[df['sports_person_id'].isin(squad_ids)]
        squad_players = squad_df.to_dict('records')
        
        # Filter squad players by position
        squad_gks = [p for p in squad_players if p['position_desc'] == 'Goalkeeper']
        squad_defs = [p for p in squad_players if p['position_desc'] == 'Defender']
        squad_mids = [p for p in squad_players if p['position_desc'] == 'Midfielder']
        squad_fwds = [p for p in squad_players if p['position_desc'] == 'Forward']
        
        # Calculate constraints
        total_cost = sum(p['price'] for p in squad_players)
        squad_size = len(squad_players)
        total_points = sum(p['est_fantasy_points'] for p in squad_players)
        
        nation_counts = {}
        for p in squad_players:
            nation_counts[p['team_name']] = nation_counts.get(p['team_name'], 0) + 1
            
        # Check rule validation
        is_budget_ok = total_cost <= 105.0
        is_size_ok = squad_size == 15
        is_structure_ok = (len(squad_gks) == 2 and len(squad_defs) == 5 and len(squad_mids) == 5 and len(squad_fwds) == 3)
        is_nations_ok = all(count <= 3 for count in nation_counts.values())
        is_compliant = is_budget_ok and is_size_ok and is_structure_ok and is_nations_ok

        # Build position slots
        gk_cols = [render_squad_slot(squad_gks[i] if i < len(squad_gks) else None, "Goalkeeper", i) for i in range(2)]
        def_cols = [render_squad_slot(squad_defs[i] if i < len(squad_defs) else None, "Defender", i) for i in range(5)]
        mid_cols = [render_squad_slot(squad_mids[i] if i < len(squad_mids) else None, "Midfielder", i) for i in range(5)]
        fwd_cols = [render_squad_slot(squad_fwds[i] if i < len(squad_fwds) else None, "Forward", i) for i in range(3)]

        # Check overflows
        overflow_players = []
        if len(squad_gks) > 2: overflow_players.extend(squad_gks[2:])
        if len(squad_defs) > 5: overflow_players.extend(squad_defs[5:])
        if len(squad_mids) > 5: overflow_players.extend(squad_mids[5:])
        if len(squad_fwds) > 3: overflow_players.extend(squad_fwds[3:])
        
        overflow_elements = []
        if overflow_players:
            overflow_cols = [render_squad_slot(p, p['position_desc'] + " (Extra)", idx + 10) for idx, p in enumerate(overflow_players)]
            overflow_elements = [
                html.Div([
                    html.H5("⚠️ Position Overflow Detected", className="text-warning font-weight-bold mb-2", style={"fontFamily": "Outfit"}),
                    html.P("Your squad has more players in this position than allowed. Please remove the extras to make the squad valid:", className="text-secondary small mb-3"),
                    dbc.Row(overflow_cols, className="mb-4")
                ], className="glass-panel mb-4", style={"borderColor": "#ffc107"})
            ]

        # Checklist
        compliance_checks = [
            html.Li([
                html.Span("Total Cost: ", className="font-weight-bold"),
                html.Span(f"${total_cost:.1f}M / $105.0M", className="text-success" if is_budget_ok else "text-danger"),
                html.Span(" (OK)" if is_budget_ok else " (OVER BUDGET!)", className="text-success" if is_budget_ok else "text-danger")
            ], className="mb-2"),
            html.Li([
                html.Span("Squad Size: ", className="font-weight-bold"),
                html.Span(f"{squad_size} / 15 players", className="text-success" if is_size_ok else "text-warning"),
                html.Span(" (OK)" if is_size_ok else " (Incomplete)", className="text-success" if is_size_ok else "text-warning")
            ], className="mb-2"),
            html.Li([
                html.Span("Position Limits: ", className="font-weight-bold"),
                html.Span(f"GKs: {len(squad_gks)}/2", className="text-success" if len(squad_gks)==2 else "text-warning"),
                html.Span(", "),
                html.Span(f"DEFs: {len(squad_defs)}/5", className="text-success" if len(squad_defs)==5 else "text-warning"),
                html.Span(", "),
                html.Span(f"MIDs: {len(squad_mids)}/5", className="text-success" if len(squad_mids)==5 else "text-warning"),
                html.Span(", "),
                html.Span(f"FWDs: {len(squad_fwds)}/3", className="text-success" if len(squad_fwds)==3 else "text-warning"),
            ], className="mb-2")
        ]
        
        nation_violations = [f"{n} ({c})" for n, c in nation_counts.items() if c > 3]
        if nation_violations:
            compliance_checks.append(html.Li(f"Nations Limit: Max 3 per country. Exceeded by: {', '.join(nation_violations)} ❌", className="text-danger mb-2"))
        else:
            compliance_checks.append(html.Li("Nation Limits: Max 3 players per country (OK) ✅", className="text-success mb-2"))
            
        status_alert = html.Div([
            html.H5("🎉 Squad is Fully Compliant!", className="mb-1", style={"fontFamily": "Outfit"}),
            html.Span("Your squad meets all budget, size, structure, and nation limits. You are ready to save!")
        ], className="compliance-badge-ok w-100 mb-3") if is_compliant else html.Div([
            html.H5("⚠️ Squad is Incomplete or Invalid", className="mb-1", style={"fontFamily": "Outfit"}),
            html.Span("Please resolve the highlighted violations below to make your squad compliant.")
        ], className="compliance-badge-warning w-100 mb-3")

        return html.Div([
            # Overview KPIs
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(f"${total_cost:.1f}M", className="kpi-val", style={"color": "#00b8ff" if is_budget_ok else "#ff3d00"}),
                        html.Div("Total Cost (Limit: $105M)", className="kpi-label")
                    ], className="kpi-card-premium mb-3")
                ], xs=12, md=4),
                dbc.Col([
                    html.Div([
                        html.Div(f"{squad_size} / 15", className="kpi-val"),
                        html.Div("Squad Size Goal", className="kpi-label")
                    ], className="kpi-card-premium mb-3")
                ], xs=12, md=4),
                dbc.Col([
                    html.Div([
                        html.Div(f"{total_points:.0f} pts", className="kpi-val", style={"color": "#00c852"}),
                        html.Div("Est. Points Coverage", className="kpi-label")
                    ], className="kpi-card-premium mb-3")
                ], xs=12, md=4)
            ], className="mb-4"),
            
            # Tactical Pitch Cards
            html.Div([
                html.H4("🧤 Goalkeepers (GK)", className="mb-3 mt-4", style={"fontFamily": "Outfit", "color": "#00b8ff"}),
                dbc.Row(gk_cols, className="mb-3"),
                html.H4("🛡️ Defenders (DEF)", className="mb-3 mt-4", style={"fontFamily": "Outfit", "color": "#00b8ff"}),
                dbc.Row(def_cols, className="mb-3"),
                html.H4("🏃 Midfielders (MID)", className="mb-3 mt-4", style={"fontFamily": "Outfit", "color": "#00b8ff"}),
                dbc.Row(mid_cols, className="mb-3"),
                html.H4("⚽ Forwards (FWD)", className="mb-3 mt-4", style={"fontFamily": "Outfit", "color": "#00b8ff"}),
                dbc.Row(fwd_cols, className="mb-4"),
            ]),
            
            *overflow_elements,
            
            # Rules & Actions
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4("Squad Rules Validation Checklist", className="mb-3", style={"fontFamily": "Outfit"}),
                        status_alert,
                        html.Ul(compliance_checks, className="pl-3 mb-0", style={"fontSize": "13px"})
                    ], className="glass-panel h-100")
                ], xs=12, md=7, className="mb-3"),
                
                dbc.Col([
                    html.Div([
                        html.H4("Draft Controls", className="mb-3", style={"fontFamily": "Outfit"}),
                        html.P("Clear the entire draft to start rebuilding from scratch, or save the compliant draft locally.", className="text-secondary small mb-4"),
                        dbc.Button("Reset Squad Draft", id="clear-squad-btn", color="danger", className="w-100 py-3 mb-3 font-weight-bold"),
                        dbc.Button("Save Squad Draft", id="save-squad-btn", color="success", className="w-100 py-3 font-weight-bold", disabled=not is_compliant)
                    ], className="glass-panel h-100")
                ], xs=12, md=5, className="mb-3")
            ], className="mt-4")
        ], className="px-2")

    elif active_tab == "tab-leaderboard":
        # Render Leaderboards tab content
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Category", className="small text-secondary mb-1", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="leaderboard-category-filter",
                        options=[{'label': cat, 'value': cat} for cat in METRICS_CONFIG.keys()],
                        value="adidas Golden Boot",
                        clearable=False,
                        className="bg-dark text-white"
                    )
                ], xs=12, md=6, className="mb-3"),
                dbc.Col([
                    html.Label("Select Metric", className="small text-secondary mb-1", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="leaderboard-metric-filter",
                        clearable=False,
                        className="bg-dark text-white"
                    )
                ], xs=12, md=6, className="mb-3")
            ], className="mb-4"),
            
            html.H3("Metric Top Performers", className="mb-4", style={"fontFamily": "Outfit"}),
            dbc.Row(id="leaderboard-podium-row", className="mb-5"),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4("Top 15 Rankings Chart", className="mb-4", style={"fontFamily": "Outfit"}),
                        dcc.Graph(id="leaderboard-rankings-chart", config={"displayModeBar": False})
                    ], className="glass-panel")
                ], width=12)
            ])
        ], className="px-2")

    else:
        # Default: Scouting & Comparison
        return html.Div([
            # Dynamic Columns switcher Buttons
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Button("📋 General / Fantasy", id="btn-general", n_clicks=0, className="category-toggle-btn active"),
                        html.Button("⚽ Attacking", id="btn-attacking", n_clicks=0, className="category-toggle-btn"),
                        html.Button("🔄 Passing / Distribution", id="btn-passing", n_clicks=0, className="category-toggle-btn"),
                        html.Button("🛡️ Defending", id="btn-defending", n_clicks=0, className="category-toggle-btn"),
                        html.Button("🏃 Physical & Pace", id="btn-physical", n_clicks=0, className="category-toggle-btn"),
                        html.Button("🧤 Goalkeeping", id="btn-goalkeeping", n_clicks=0, className="category-toggle-btn"),
                    ], className="category-toggle-container")
                ], width=12)
            ]),

            # Table + Side panels
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Row([
                            # Search input
                            dbc.Col([
                                html.Label("Search Player", className="small text-secondary mb-1", style={"fontWeight": "600"}),
                                dbc.InputGroup([
                                    dbc.InputGroupText(html.I(className="bi bi-search")),
                                    dcc.Input(id="search-input", type="text", placeholder="Type name...", className="form-control text-white bg-dark border-secondary", style={"borderRadius": "0 8px 8px 0", "height": "40px"})
                                ])
                            ], xs=12, sm=6, md=3, className="mb-3"),

                            # Team Filter
                            dbc.Col([
                                html.Label("Filter Team", className="small text-secondary mb-1", style={"fontWeight": "600"}),
                                dcc.Dropdown(id="team-filter", options=team_options, value="All", clearable=False)
                            ], xs=12, sm=6, md=3, className="mb-3"),

                            # Position Filter
                            dbc.Col([
                                html.Label("Filter Position", className="small text-secondary mb-1", style={"fontWeight": "600"}),
                                dcc.Dropdown(id="position-filter", options=position_options, value="All", clearable=False)
                            ], xs=12, sm=6, md=3, className="mb-3"),

                            # Price Range
                            dbc.Col([
                                html.Label("Price Range ($M)", className="small text-secondary mb-1", style={"fontWeight": "600"}),
                                html.Div([
                                    dcc.RangeSlider(
                                        id="price-slider",
                                        min=min_price,
                                        max=max_price,
                                        step=0.1,
                                        value=[min_price, max_price],
                                        marks={int(min_price): f"${int(min_price)}M", int(max_price): f"${int(max_price)}M"},
                                        tooltip={"always_visible": False, "placement": "bottom"}
                                    )
                                ], style={"paddingTop": "8px"})
                            ], xs=12, sm=12, md=3, className="mb-3")
                        ], className="mb-3 px-2 align-items-end"),

                        # Table
                        dash_table.DataTable(
                            id="explorer-table",
                            columns=COLUMN_CATEGORIES["general"]["columns"],
                            data=df.to_dict('records'),
                            page_size=12,
                            sort_action="native",
                            filter_action="native",
                            row_selectable="multi",
                            selected_rows=[],
                            style_table={'overflowX': 'auto', 'minWidth': '100%', 'borderRadius': '12px'},
                            style_cell={
                                'backgroundColor': 'transparent',
                                'color': '#cbd5e1',
                                'padding': '12px 10px',
                                'fontSize': '12.5px',
                                'borderBottom': '1px solid rgba(255,255,255,0.06)',
                                'borderTop': 'none',
                                'borderLeft': 'none',
                                'borderRight': 'none',
                                'textAlign': 'left'
                            },
                            style_header={
                                'backgroundColor': '#0b1528',
                                'color': '#ffffff',
                                'fontWeight': '600',
                                'fontFamily': 'Outfit, sans-serif',
                                'borderBottom': '2px solid rgba(255,255,255,0.15)',
                                'textTransform': 'uppercase',
                                'fontSize': '11px',
                                'letterSpacing': '0.05em'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'state': 'selected'},
                                    'backgroundColor': 'rgba(0, 184, 255, 0.12) !important',
                                    'color': '#00b8ff !important'
                                }
                            ]
                        )
                    ], className="glass-panel h-100")
                ], xs=12, lg=8, className="mb-4"),
                
                # Analysis Side Panel
                dbc.Col([
                    html.Div(id="analysis-panel-content", className="detail-panel h-100")
                ], xs=12, lg=4, className="mb-4")
            ]),

            # Scatter correlations plot
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.H4("Statistical Analysis & Correlations", className="mb-1", style={"fontFamily": "Outfit"}),
                                html.P("Compare two statistics across the filtered players. Selected players are highlighted.", className="text-secondary small mb-4"),
                                html.Label("X Axis Metric", className="label mb-2 d-block small text-secondary", style={"fontWeight": "600"}),
                                dcc.Dropdown(id="scatter-x-filter", options=[{'label': label, 'value': val} for val, label in ALL_METRICS.items()], value="xg", clearable=False, className="bg-dark text-white mb-3"),
                                html.Label("Y Axis Metric", className="label mb-2 d-block small text-secondary", style={"fontWeight": "600"}),
                                dcc.Dropdown(id="scatter-y-filter", options=[{'label': label, 'value': val} for val, label in ALL_METRICS.items()], value="goals", clearable=False, className="bg-dark text-white")
                            ], xs=12, md=4, className="mb-4 mb-md-0"),
                            dbc.Col([
                                html.H4(id="scatter-title", className="mb-3 text-end text-muted", style={"fontSize": "14px", "textTransform": "uppercase", "letterSpacing": "1px"}),
                                dcc.Graph(id="scatter-plot", config={"displayModeBar": False})
                            ], xs=12, md=8)
                        ])
                    ], className="glass-panel mb-5")
                ], width=12)
            ])
        ], className="px-2")

# Callback to manage category button selection and store updates
@app.callback(
    Output("active-category-store", "data"),
    [Input("btn-general", "n_clicks"),
     Input("btn-attacking", "n_clicks"),
     Input("btn-passing", "n_clicks"),
     Input("btn-defending", "n_clicks"),
     Input("btn-physical", "n_clicks"),
     Input("btn-goalkeeping", "n_clicks")],
    prevent_initial_call=True
)
def update_active_category(*args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "general"
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    category = button_id.replace("btn-", "")
    return category

# Callback to visually highlight the selected category button
@app.callback(
    [Output("btn-general", "className"),
     Output("btn-attacking", "className"),
     Output("btn-passing", "className"),
     Output("btn-defending", "className"),
     Output("btn-physical", "className"),
     Output("btn-goalkeeping", "className")],
    [Input("active-category-store", "data")]
)
def update_button_classes(active_cat):
    base_class = "category-toggle-btn"
    return [
        f"{base_class} active" if active_cat == cat else base_class
        for cat in ["general", "attacking", "passing", "defending", "physical", "goalkeeping"]
    ]

# Callback to filter the player table and update its columns based on category selection
@app.callback(
    [Output("explorer-table", "data"),
     Output("explorer-table", "columns"),
     Output("explorer-table", "selected_rows")],
    [Input("active-category-store", "data"),
     Input("search-input", "value"),
     Input("team-filter", "value"),
     Input("position-filter", "value"),
     Input("price-slider", "value")],
    [State("explorer-table", "selected_rows")],
    prevent_initial_call=False
)
def update_table_data_and_columns(active_cat, name_query, team_query, position_query, price_range, current_selected):
    # Filter dataset based on search, team, position, and price slider
    filtered_df = df.copy()
    if name_query:
        filtered_df = filtered_df[filtered_df['name'].str.contains(name_query, case=False, na=False)]
    if team_query != "All":
        filtered_df = filtered_df[filtered_df['team_name'] == team_query]
    if position_query != "All":
        filtered_df = filtered_df[filtered_df['position_desc'] == position_query]
    if price_range:
        filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]

    # Fetch columns based on active category
    cat_info = COLUMN_CATEGORIES.get(active_cat, COLUMN_CATEGORIES["general"])
    cols = cat_info["columns"]

    table_data = filtered_df.to_dict('records')
    # Default: reset selection to empty to avoid out-of-index crashes when filters change
    return table_data, cols, []

# Callback to update the Hero Header KPIs dynamically using table virtual data
@app.callback(
    [Output("kpi-players-count", "children"),
     Output("kpi-avg-xg", "children"),
     Output("kpi-max-speed", "children"),
     Output("kpi-avg-val", "children")],
    [Input("explorer-table", "derived_virtual_data")],
    prevent_initial_call=False
)
def update_kpis(virtual_data):
    if not virtual_data or len(virtual_data) == 0:
        return "0", "0.00 xG", "N/A", "0.00"
    
    v_df = pd.DataFrame(virtual_data)
    total_players = f"{len(v_df)}"
    
    avg_xg = "0.00 xG"
    if 'xg' in v_df.columns:
        avg_xg = f"{v_df['xg'].mean():.2f} xG"
        
    max_speed = "N/A"
    if 'top_speed' in v_df.columns and not v_df.empty:
        max_idx = v_df['top_speed'].idxmax()
        max_player = v_df.loc[max_idx]
        max_speed = f"{max_player['top_speed']:.1f} km/h ({max_player['team_abbr']})"
        
    avg_val = "0.00"
    if 'value_factor' in v_df.columns:
        avg_val = f"{v_df['value_factor'].mean():.2f}"
        
    return total_players, avg_xg, max_speed, avg_val

# Callback to update the Leaderboards Metric dropdown options dynamically based on Leaderboards Category
@app.callback(
    [Output("leaderboard-metric-filter", "options"),
     Output("leaderboard-metric-filter", "value")],
    [Input("leaderboard-category-filter", "value")],
    prevent_initial_call=False
)
def set_leaderboard_metrics_options(selected_category):
    metrics = METRICS_CONFIG.get(selected_category, {})
    options = [{'label': label, 'value': val} for val, label in metrics.items()]
    default_val = list(metrics.keys())[0] if metrics else None
    return options, default_val

# Callback to update Leaderboards Tab Podium and Rankings Chart
@app.callback(
    [Output("leaderboard-podium-row", "children"),
     Output("leaderboard-rankings-chart", "figure")],
    [Input("leaderboard-metric-filter", "value"),
     Input("search-input", "value"),
     Input("team-filter", "value"),
     Input("position-filter", "value"),
     Input("price-slider", "value")],
    prevent_initial_call=False
)
def update_leaderboard_graphics(metric, name_query, team_query, position_query, price_range):
    # Filter dataset
    filtered_df = df.copy()
    if name_query:
        filtered_df = filtered_df[filtered_df['name'].str.contains(name_query, case=False, na=False)]
    if team_query != "All":
        filtered_df = filtered_df[filtered_df['team_name'] == team_query]
    if position_query != "All":
        filtered_df = filtered_df[filtered_df['position_desc'] == position_query]
    if price_range:
        filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]

    if not metric:
        metric = "goals"

    metric_name = ALL_METRICS.get(metric, "Value")
    
    # Podiums
    top_df = filtered_df.sort_values(by=metric, ascending=False).head(15)
    podium_df = filtered_df.sort_values(by=metric, ascending=False).head(3)
    
    rank_classes = ["podium-rank-1", "podium-rank-2", "podium-rank-3"]
    podium_order = [1, 0, 2] if len(podium_df) >= 3 else list(range(len(podium_df)))
    
    podium_cols = []
    for idx in podium_order:
        if idx >= len(podium_df):
            continue
        player = podium_df.iloc[idx]
        rank = idx + 1
        rank_class = rank_classes[idx]
        
        val = player[metric]
        val_str = f"{val:,.2f}" if isinstance(val, float) and val % 1 != 0 else f"{int(val):,}"
        
        img_src = player['headshot_url'] if pd.notna(player['headshot_url']) and player['headshot_url'] != '' else "https://play.fifa.com/media/image/headshots/389867_headshot.png"
        flag_src = player['flag_url'] if pd.notna(player['flag_url']) else ""
        
        card = dbc.Col([
            html.Div([
                html.Div(str(rank), className=f"podium-rank-badge {rank_class}"),
                html.Div([
                    html.Img(src=img_src)
                ], className="player-image-container"),
                html.H4(player['name'], className="text-center font-weight-bold mb-1 text-truncate", style={"fontSize": "16px"}),
                html.Div([
                    html.Img(src=flag_src, className="flag-badge"),
                    html.Span(f"{player['team_abbr']} • {player['position_desc']}", className="text-muted", style={"fontSize": "11px"})
                ], className="text-center mb-3"),
                html.Div([
                    html.Div(val_str, className="h3 font-weight-bold text-center mb-0", style={"color": "#ff3d00"}),
                    html.Div(metric_name, className="text-muted text-center", style={"fontSize": "10px", "textTransform": "uppercase"})
                ], className="pt-2 border-top border-secondary")
            ], className="glass-panel podium-card h-100")
        ], xs=12, md=4, className="mb-3")
        podium_cols.append(card)

    # Rankings Chart
    if not top_df.empty:
        fig = px.bar(
            top_df,
            x=metric,
            y='name',
            orientation='h',
            color=metric,
            color_continuous_scale=['#0052d4', '#00b8ff', '#ff3d00'],
            labels={'name': 'Player', metric: metric_name},
            text=metric
        )
        fig.update_traces(
            textposition='inside',
            texttemplate='%{text}',
            marker=dict(line=dict(width=0))
        )
        fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            coloraxis_showscale=False,
            height=450,
            xaxis_title=metric_name,
            yaxis_title=""
        )
    else:
        fig = go.Figure()
        fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
        
    return podium_cols, fig

# Callback to manage the right panel (scouting details card / comparison view)
@app.callback(
    Output("analysis-panel-content", "children"),
    [Input("explorer-table", "selected_rows"),
     Input("explorer-table", "derived_virtual_data"),
     Input("draft-squad-store", "data")],
    prevent_initial_call=False
)
def update_analysis_panel(selected_rows, virtual_data, squad_ids):
    if not selected_rows or not virtual_data or len(selected_rows) == 0:
        return html.Div([
            html.Div([
                html.I(className="bi bi-person-bounding-box", style={"fontSize": "44px", "color": "var(--text-muted)", "display": "block", "marginBottom": "16px"}),
                html.H5("Scouting Workbench", className="font-weight-bold mb-2", style={"fontFamily": "Outfit"}),
                html.P("Select one or more players from the table to begin statistics analysis.", className="text-secondary small mb-3"),
                html.Div("💡 Check multiple boxes to instantly view side-by-side performance comparison charts.", className="p-3 border border-secondary rounded text-info small bg-dark", style={"lineHeight": "1.4"})
            ], className="compare-empty-state")
        ], style={"padding": "40px 20px"})
    
    # Gather selected player dictionaries
    selected_players = [virtual_data[i] for i in selected_rows if i < len(virtual_data)]
    
    if not selected_players:
        return html.Div("Loading player details...", className="text-muted text-center p-4")
        
    # SINGLE PLAYER LAYOUT
    if len(selected_players) == 1:
        player = selected_players[0]
        pid = str(player['sports_person_id'])
        squad_ids = squad_ids or []
        
        # Load comprehensive stats for radar mapping
        player_matches = df[df['sports_person_id'] == pid]
        if player_matches.empty:
            return html.Div("Player statistics not found.", className="text-danger p-3")
        p_full = player_matches.iloc[0]
        
        img_src = p_full['headshot_url'] if pd.notna(p_full['headshot_url']) and p_full['headshot_url'] != '' else "https://play.fifa.com/media/image/headshots/389867_headshot.png"
        flag_src = p_full['flag_url'] if pd.notna(p_full['flag_url']) else ""
        
        # Build spider/radar chart of percentiles
        categories = ['Attacking', 'Passing', 'Defending', 'Pace', 'Stamina']
        goals_pct = p_full.get('goals_pct', 50)
        passing_pct = p_full.get('passing_pct', 50)
        defending_pct = p_full.get('defending_pct', 50)
        speed_pct = p_full.get('speed_pct', 50)
        distance_pct = p_full.get('distance_pct', 50)
        
        radar_vals = [goals_pct, passing_pct, defending_pct, speed_pct, distance_pct]
        radar_vals = [*radar_vals, radar_vals[0]]
        radar_cats = [*categories, categories[0]]
        
        radar_fig = go.Figure(
            data=[go.Scatterpolar(
                r=radar_vals,
                theta=radar_cats,
                fill='toself',
                name=p_full['name'],
                line_color='#00b8ff',
                fillcolor='rgba(0,184,255,0.18)'
            )],
            layout=go.Layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(255,255,255,0.08)', linecolor='rgba(255,255,255,0.1)'),
                    angularaxis=dict(gridcolor='rgba(255,255,255,0.08)', linecolor='rgba(255,255,255,0.1)')
                ),
                showlegend=False,
                margin=dict(l=30, r=30, t=20, b=20),
                height=230,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#cbd5e1', family='Outfit', size=11)
            )
        )
        
        xg_diff = p_full['goals'] - p_full['xg']
        xg_diff_style = ("#00c852", f"+{xg_diff:.2f}") if xg_diff >= 0 else ("#ff3d00", f"{xg_diff:.2f}")
        
        # Check if player is already in squad draft
        is_in_squad = str(pid) in [str(i) for i in squad_ids]
        
        if is_in_squad:
            add_btn = dbc.Button("Already in Squad ✅", id="add-to-squad-btn", color="success", className="w-100 py-3 font-weight-bold mb-3 d-flex align-items-center justify-content-center", disabled=True)
        else:
            add_btn = dbc.Button("+ Add to Squad Draft", id="add-to-squad-btn", color="info", className="w-100 py-3 font-weight-bold mb-3 d-flex align-items-center justify-content-center")
        
        return html.Div([
            # Profile Header info
            html.Div([
                html.Div([
                    html.Img(src=img_src, style={"width": "100%", "height": "100%", "objectFit": "cover"})
                ], className="player-image-container mb-3", style={"width": "100px", "height": "100px", "border": "3px solid #00b8ff"}),
                html.H4(p_full['name'], className="text-center font-weight-bold mb-1", style={"fontFamily": "Outfit"}),
                html.Div([
                    html.Img(src=flag_src, className="flag-badge"),
                    html.Span(f"{p_full['team_name']} • {p_full['position_desc']}", className="text-muted", style={"fontSize": "13px"})
                ], className="text-center mb-3"),
                
                # Tags/Badges
                html.Div([
                    dbc.Badge(f"${p_full['price']:.1f}M", color="primary", className="me-2", style={"fontSize": "11px", "padding": "5px 10px"}),
                    dbc.Badge(f"{p_full['est_fantasy_points']:.0f} Pts", color="success", className="me-2", style={"fontSize": "11px", "padding": "5px 10px"}),
                    dbc.Badge(f"{p_full['value_factor']:.2f} Pts/$", color="warning", style={"fontSize": "11px", "padding": "5px 10px"}),
                ], className="text-center mb-3"),
                
                # Add to Squad Action Button
                add_btn
            ]),
            
            # Radar Visualizer
            html.Div([
                html.Div("Attribute Percentiles Profile", className="text-muted small font-weight-bold text-uppercase text-center mb-2", style={"letterSpacing": "1.5px"}),
                dcc.Graph(figure=radar_fig, config={"displayModeBar": False})
            ], className="mb-4 pt-2 border-top border-secondary"),
            
            # Statistics metrics list
            html.Div([
                html.Div("Key Tournament Metrics", className="border-bottom border-secondary pb-1 mb-3 text-uppercase font-weight-bold", style={"fontSize": "11px", "color": "#00b8ff", "letterSpacing": "1px"}),
                
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Div(str(int(p_full['goals'])), className="font-weight-bold text-center h4 mb-0", style={"color": "#ff3d00"}),
                            html.Div("Goals", className="text-center text-muted", style={"fontSize": "10px"})
                        ], className="mb-3 py-2 px-1 border border-secondary rounded bg-dark")
                    ], width=4),
                    dbc.Col([
                        html.Div([
                            html.Div(str(int(p_full['assists'])), className="font-weight-bold text-center h4 mb-0", style={"color": "#ffb300"}),
                            html.Div("Assists", className="text-center text-muted", style={"fontSize": "10px"})
                        ], className="mb-3 py-2 px-1 border border-secondary rounded bg-dark")
                    ], width=4),
                    dbc.Col([
                        html.Div([
                            html.Div(f"{p_full['xg']:.2f}", className="font-weight-bold text-center h4 mb-0", style={"color": "#00b8ff"}),
                            html.Div("xG", className="text-center text-muted", style={"fontSize": "10px"})
                        ], className="mb-3 py-2 px-1 border border-secondary rounded bg-dark")
                    ], width=4),
                ]),
                
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Div(f"{int(p_full['total_competition_minutes_played'])}", className="font-weight-bold text-center h5 mb-0"),
                            html.Div("Mins", className="text-center text-muted", style={"fontSize": "9px"})
                        ], className="mb-3 py-2 px-1 border border-secondary rounded")
                    ], width=4),
                    dbc.Col([
                        html.Div([
                            html.Div(f"{p_full['passing_accuracy_rate']:.0f}%", className="font-weight-bold text-center h5 mb-0"),
                            html.Div("Pass %", className="text-center text-muted", style={"fontSize": "9px"})
                        ], className="mb-3 py-2 px-1 border border-secondary rounded")
                    ], width=4),
                    dbc.Col([
                        html.Div([
                            html.Div(xg_diff_style[1], className="font-weight-bold text-center h5 mb-0", style={"color": xg_diff_style[0]}),
                            html.Div("G vs xG", className="text-center text-muted", style={"fontSize": "9px"})
                        ], className="mb-3 py-2 px-1 border border-secondary rounded")
                    ], width=4),
                ]),
                
                html.Div([
                    html.Div([
                        html.Span("Top Speed Reached:", className="text-secondary small"),
                        html.Span(f" {p_full['top_speed']:.1f} km/h", className="font-weight-bold float-end", style={"color": "#ff3d00"})
                    ], className="mb-2 clearfix"),
                    html.Div([
                        html.Span("Total Distance:", className="text-secondary small"),
                        html.Span(f" {p_full['total_distance_km']:.2f} km", className="font-weight-bold float-end")
                    ], className="mb-2 clearfix"),
                    html.Div([
                        html.Span("Sprints Completed:", className="text-secondary small"),
                        html.Span(f" {int(p_full['sprints'])}", className="font-weight-bold float-end")
                    ], className="mb-2 clearfix"),
                    html.Div([
                        html.Span("Turnovers Forced:", className="text-secondary small"),
                        html.Span(f" {int(p_full['forced_turnovers'])}", className="font-weight-bold float-end")
                    ], className="mb-2 clearfix"),
                    html.Div([
                        html.Span("Touches (Involvement):", className="text-secondary small"),
                        html.Span(f" {int(p_full['number_of_involvements'])}", className="font-weight-bold float-end")
                    ], className="clearfix")
                ], className="pt-2 border-top border-secondary")
            ])
        ])
        
    # MULTI PLAYER COMPARISON LAYOUT
    else:
        selected_ids = [str(p['sports_person_id']) for p in selected_players]
        comp_df = df[df['sports_person_id'].isin(selected_ids)]
        
        # 1. Bar Chart: Fantasy Points comparison
        pts_fig = px.bar(
            comp_df,
            x='name',
            y='est_fantasy_points',
            color='name',
            color_discrete_sequence=px.colors.qualitative.G10,
            labels={'est_fantasy_points': 'Fantasy Points', 'name': 'Player'}
        )
        pts_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cbd5e1', family='Outfit'),
            margin=dict(l=30, r=30, t=10, b=10),
            height=180,
            showlegend=False,
            xaxis_title=None,
            yaxis_title="Points",
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        
        # 2. Grouped Stats comparison
        melted_df = comp_df.melt(
            id_vars=['name'],
            value_vars=['goals', 'assists', 'xg'],
            var_name='Metric',
            value_name='Value'
        )
        melted_df['Metric'] = melted_df['Metric'].map({'goals': 'Goals', 'assists': 'Assists', 'xg': 'xG'})
        
        stats_fig = px.bar(
            melted_df,
            x='Metric',
            y='Value',
            color='name',
            barmode='group',
            color_discrete_sequence=px.colors.qualitative.G10,
            labels={'Value': 'Value', 'name': 'Player', 'Metric': ''}
        )
        stats_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cbd5e1', family='Outfit'),
            margin=dict(l=20, r=20, t=10, b=10),
            height=180,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8), title=None),
            xaxis_title=None,
            yaxis_title="Metric Value",
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        
        # Side list details
        list_items = []
        for p in selected_players:
            list_items.append(html.Div([
                html.Div([
                    html.Span(p['name'], className="font-weight-bold", style={"fontSize": "13px"}),
                    html.Span(f" ({p['team_abbr']})", className="text-secondary small"),
                    html.Span(f" ${p['price']:.1f}M", className="float-end font-weight-bold text-info")
                ], className="mb-1 clearfix"),
                html.Div([
                    html.Span(f"Pts: {p['est_fantasy_points']:.0f} | xG: {p['xg']:.2f} | Speed: {p['top_speed']:.1f} km/h", style={"fontSize": "11px", "color": "#cbd5e1"})
                ])
            ], className="mb-2 pb-2 border-bottom border-secondary"))
        
        return html.Div([
            html.H5(f"Player Comparison ({len(selected_players)})", className="font-weight-bold mb-3", style={"fontFamily": "Outfit"}),
            
            html.Div("Estimated Points Comparison", className="text-muted small font-weight-bold text-uppercase mb-1", style={"letterSpacing": "1px", "fontSize": "9px"}),
            dcc.Graph(figure=pts_fig, config={"displayModeBar": False}),
            
            html.Div("Attacking Stats Comparison", className="text-muted small font-weight-bold text-uppercase mb-1 mt-3", style={"letterSpacing": "1px", "fontSize": "9px"}),
            dcc.Graph(figure=stats_fig, config={"displayModeBar": False}),
            
            html.Div("Comparison Matrix Details", className="border-bottom border-secondary pb-1 mb-2 mt-4 text-uppercase font-weight-bold", style={"fontSize": "10.5px", "color": "#00b8ff", "letterSpacing": "1px"}),
            html.Div(list_items, style={"maxHeight": "200px", "overflowY": "auto", "paddingRight": "5px"})
        ])

# Callback to manage adding, removing, and clearing players in the squad draft store
@app.callback(
    [Output("draft-squad-store", "data"),
     Output("add-to-squad-alert", "children"),
     Output("add-to-squad-alert", "is_open"),
     Output("add-to-squad-alert", "color")],
    [Input("add-to-squad-btn", "n_clicks"),
     Input({"type": "remove-player", "index": ALL}, "n_clicks"),
     Input("clear-squad-btn", "n_clicks")],
    [State("explorer-table", "selected_rows"),
     State("explorer-table", "derived_virtual_data"),
     State("draft-squad-store", "data")],
    prevent_initial_call=True
)
def manage_squad_store(add_clicks, remove_clicks, clear_clicks, selected_rows, virtual_data, squad_ids):
    ctx_trigger = dash.callback_context.triggered
    if not ctx_trigger:
        return squad_ids, "", False, "primary"

    triggered_id = ctx_trigger[0]['prop_id']
    squad_ids = squad_ids or []

    # Handle clear squad
    if "clear-squad-btn" in triggered_id:
        return [], "Squad draft has been reset.", True, "warning"

    # Handle add to squad
    if "add-to-squad-btn" in triggered_id:
        if not selected_rows or not virtual_data:
            return squad_ids, "No player selected in the table.", True, "danger"
        
        row_idx = selected_rows[0]
        if row_idx >= len(virtual_data):
            return squad_ids, "No player selected in the table.", True, "danger"
            
        player = virtual_data[row_idx]
        pid = str(player['sports_person_id'])

        if pid in squad_ids:
            return squad_ids, f"{player['name']} is already in your squad.", True, "warning"
            
        if len(squad_ids) >= 15:
            return squad_ids, "Your squad is full! (Max 15 players). Remove a player first.", True, "danger"
            
        squad_ids.append(pid)
        return squad_ids, f"Added {player['name']} to squad draft!", True, "success"

    # Handle remove player (using pattern-matching triggered_id)
    if "remove-player" in triggered_id:
        try:
            prop_id_str = triggered_id.split('.')[0]
            triggered_dict = json.loads(prop_id_str)
            if triggered_dict.get("type") == "remove-player":
                pid_to_remove = str(triggered_dict.get("index"))
                if pid_to_remove in squad_ids:
                    squad_ids.remove(pid_to_remove)
                    # Find player name for message
                    matches = df[df['sports_person_id'] == pid_to_remove]
                    pname = matches.iloc[0]['name'] if not matches.empty else pid_to_remove
                    return squad_ids, f"Removed {pname} from squad draft.", True, "info"
        except Exception as e:
            pass

    return squad_ids, "", False, "primary"

# Callback to save the squad draft to a JSON file
@app.callback(
    [Output("save-squad-alert", "children"),
     Output("save-squad-alert", "is_open"),
     Output("save-squad-alert", "color")],
    [Input("save-squad-btn", "n_clicks")],
    [State("draft-squad-store", "data")],
    prevent_initial_call=True
)
def save_squad_draft(n_clicks, squad_ids):
    if not n_clicks or not squad_ids:
        return "", False, "primary"
        
    try:
        # Get squad players
        squad_df = df[df['sports_person_id'].isin(squad_ids)]
        squad_players = squad_df.to_dict('records')
        
        # Calculate stats
        total_cost = sum(p['price'] for p in squad_players)
        total_points = sum(p['est_fantasy_points'] for p in squad_players)
        
        output_data = {
            "squad_size": len(squad_players),
            "total_cost_m": round(total_cost, 2),
            "total_est_points": round(total_points, 2),
            "players": [
                {
                    "sports_person_id": p['sports_person_id'],
                    "name": p['name'],
                    "team_name": p['team_name'],
                    "team_abbr": p['team_abbr'],
                    "position_desc": p['position_desc'],
                    "price_m": p['price'],
                    "est_fantasy_points": p['est_fantasy_points']
                } for p in squad_players
            ]
        }
        
        # Create round_of_32 folder if it doesn't exist
        os.makedirs("round_of_32", exist_ok=True)
        
        filepath = "round_of_32/fantasy_team_draft.json"
        with open(filepath, "w") as f:
            json.dump(output_data, f, indent=2)
            
        success_msg = f"Draft successfully saved to {filepath}! Cost: ${total_cost:.1f}M, Est. Points: {total_points:.0f}."
        return success_msg, True, "success"
    except Exception as e:
        return f"Error saving draft: {str(e)}", True, "danger"

# Callback to update the Hero Header draft status KPI card
@app.callback(
    [Output("kpi-draft-count", "children"),
     Output("kpi-draft-label", "children"),
     Output("kpi-draft-card", "className"),
     Output("kpi-draft-card", "style")],
    [Input("draft-squad-store", "data")]
)
def update_draft_kpi(squad_ids):
    squad_ids = squad_ids or []
    squad_df = df[df['sports_person_id'].isin(squad_ids)]
    
    total_cost = squad_df['price'].sum()
    squad_size = len(squad_ids)
    
    # Calculate compliance
    squad_gks = squad_df[squad_df['position_desc'] == 'Goalkeeper']
    squad_defs = squad_df[squad_df['position_desc'] == 'Defender']
    squad_mids = squad_df[squad_df['position_desc'] == 'Midfielder']
    squad_fwds = squad_df[squad_df['position_desc'] == 'Forward']
    
    nation_counts = {}
    for team in squad_df['team_name']:
        nation_counts[team] = nation_counts.get(team, 0) + 1
        
    is_budget_ok = total_cost <= 105.0
    is_size_ok = squad_size == 15
    is_structure_ok = (len(squad_gks) == 2 and len(squad_defs) == 5 and len(squad_mids) == 5 and len(squad_fwds) == 3)
    is_nations_ok = all(count <= 3 for count in nation_counts.values())
    is_compliant = is_budget_ok and is_size_ok and is_structure_ok and is_nations_ok
    
    val_text = f"{squad_size} / 15"
    label_text = f"Draft (${total_cost:.1f}M)"
    
    # Change card style based on compliance status
    if is_compliant:
        border_style = {"borderColor": "#00c852", "cursor": "pointer"}
        card_class = "kpi-card-premium border border-success"
    elif squad_size == 0:
        border_style = {"cursor": "pointer"}
        card_class = "kpi-card-premium"
    elif not is_budget_ok:
        border_style = {"borderColor": "#ff3d00", "cursor": "pointer"}
        card_class = "kpi-card-premium border border-danger"
    else:
        border_style = {"borderColor": "#ffb300", "cursor": "pointer"}
        card_class = "kpi-card-premium border border-warning"
        
    return val_text, label_text, card_class, border_style

# Callback to switch active tab when draft KPI card is clicked
@app.callback(
    Output("dashboard-tabs", "active_tab"),
    [Input("kpi-draft-card", "n_clicks")],
    [State("dashboard-tabs", "active_tab")],
    prevent_initial_call=True
)
def click_draft_kpi_to_switch_tab(n_clicks, active_tab):
    if n_clicks:
        return "tab-squad"
    return active_tab

# Callback to manage the scatter plot
@app.callback(
    [Output("scatter-plot", "figure"),
     Output("scatter-title", "children")],
    [Input("scatter-x-filter", "value"),
     Input("scatter-y-filter", "value"),
     Input("explorer-table", "derived_virtual_data"),
     Input("explorer-table", "selected_rows")]
)
def update_scatter_plot(x_metric, y_metric, virtual_data, selected_rows):
    if not virtual_data or len(virtual_data) == 0:
        fig = go.Figure()
        fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
        return fig, "No data to plot"
        
    v_df = pd.DataFrame(virtual_data)
    
    x_label = ALL_METRICS.get(x_metric, x_metric)
    y_label = ALL_METRICS.get(y_metric, y_metric)
    
    # Calculate bubble sizing based on minutes played
    bubble_sizes = np.where(
        v_df['total_competition_minutes_played'] > 0,
        v_df['total_competition_minutes_played'] / 20.0 + 5,
        6
    )
    bubble_sizes = np.clip(bubble_sizes, 6, 25)
    
    # Core scatter plot
    fig = px.scatter(
        v_df,
        x=x_metric,
        y=y_metric,
        hover_name="name",
        color="position_desc",
        color_discrete_map={
            "Forward": "#ff3d00",
            "Midfielder": "#00b8ff",
            "Defender": "#00c852",
            "Goalkeeper": "#ffb300"
        },
        labels={x_metric: x_label, y_metric: y_label},
    )
    
    fig.update_traces(
        marker=dict(
            size=bubble_sizes,
            line=dict(width=1, color='rgba(255,255,255,0.2)'),
            opacity=0.75
        )
    )
    
    # Highlight selected rows as large white-bordered star markers
    if selected_rows and len(selected_rows) > 0:
        selected_players = [virtual_data[i] for i in selected_rows if i < len(virtual_data)]
        if selected_players:
            sel_df = pd.DataFrame(selected_players)
            
            fig.add_trace(
                go.Scatter(
                    x=sel_df[x_metric],
                    y=sel_df[y_metric],
                    mode='markers+text',
                    marker=dict(
                        size=18,
                        color='rgba(255, 61, 0, 0.95)',
                        line=dict(width=2, color='#ffffff'),
                        symbol='star'
                    ),
                    text=sel_df['name'],
                    textposition='top center',
                    name='Selected Player(s)',
                    hoverinfo='skip'
                )
            )
            
    fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title=None,
            font=dict(size=9)
        ),
        height=450,
        xaxis_title=x_label,
        yaxis_title=y_label,
        margin=dict(t=30, b=40, l=50, r=30)
    )
    
    return fig, f"Analysis: {x_label} vs. {y_label}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
