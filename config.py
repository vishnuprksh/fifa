"""
config.py
---------
Static configuration: merged table columns, scatter metric options,
and Plotly layout template for the scouting page.
"""

import plotly.graph_objects as go

# ── Merged "all-in-one" table columns ─────────────────────────────────────────
# One flat table that covers every stat category — sorted logically.
ALL_TABLE_COLUMNS = [
    # Identity
    {"name": "Player",          "id": "name"},
    {"name": "Team",            "id": "team_abbr"},
    {"name": "Pos",             "id": "position_desc"},

    # Fantasy
    {"name": "Price ($M)",      "id": "price",               "type": "numeric"},
    {"name": "Est. Pts",        "id": "est_fantasy_points",  "type": "numeric"},
    {"name": "Val (Pts/$M)",    "id": "value_factor",        "type": "numeric"},

    # General
    {"name": "Mins",            "id": "total_competition_minutes_played", "type": "numeric"},
    {"name": "Goals",           "id": "goals",               "type": "numeric"},
    {"name": "Assists",         "id": "assists",             "type": "numeric"},
    {"name": "xG",              "id": "xg",                  "type": "numeric"},

    # Attacking
    {"name": "Shots",           "id": "attempt_at_goal",     "type": "numeric"},
    {"name": "On Target",       "id": "attempt_at_goal_on_target", "type": "numeric"},
    {"name": "Conv %",          "id": "attempt_at_goal_conversion_rate", "type": "numeric"},
    {"name": "Inside Box",      "id": "attempt_at_goal_inside_the_penalty_area", "type": "numeric"},
    {"name": "Outside Box",     "id": "attempt_at_goal_outside_the_penalty_area", "type": "numeric"},
    {"name": "Headers",         "id": "headed_attempt_at_goal", "type": "numeric"},
    {"name": "Corners",         "id": "corners",             "type": "numeric"},

    # Passing / Distribution
    {"name": "Passes",          "id": "passes",              "type": "numeric"},
    {"name": "Pass %",          "id": "passing_accuracy_rate", "type": "numeric"},
    {"name": "Crosses",         "id": "crosses",             "type": "numeric"},
    {"name": "Cross %",         "id": "crossing_accuracy_rate", "type": "numeric"},
    {"name": "Linebreaks",      "id": "linebreaks_attempted_defensive_line", "type": "numeric"},
    {"name": "Linebreak %",     "id": "linebreak_attempted_defensive_line_rate", "type": "numeric"},
    {"name": "Switches",        "id": "attempted_switches_of_play", "type": "numeric"},
    {"name": "Switch %",        "id": "switches_of_play_rate", "type": "numeric"},

    # Defending
    {"name": "Recoveries",      "id": "forced_turnovers",    "type": "numeric"},
    {"name": "Pressures",       "id": "defensive_pressures_applied", "type": "numeric"},
    {"name": "Direct Press",    "id": "direct_defensive_pressures_applied", "type": "numeric"},

    # Discipline
    {"name": "Fouls Com.",      "id": "fouls_against",       "type": "numeric"},
    {"name": "Fouls Won",       "id": "fouls_for",           "type": "numeric"},
    {"name": "YC",              "id": "yellow_cards",        "type": "numeric"},
    {"name": "RC",              "id": "red_cards",           "type": "numeric"},
    {"name": "OG",              "id": "own_goals",           "type": "numeric"},

    # Physical
    {"name": "Top Speed",       "id": "top_speed",           "type": "numeric"},
    {"name": "Avg Speed",       "id": "avg_speed",           "type": "numeric"},
    {"name": "Sprints",         "id": "sprints",             "type": "numeric"},
    {"name": "Hi-Spd Runs",     "id": "speed_runs",          "type": "numeric"},
    {"name": "Dist (km)",       "id": "total_distance_km",   "type": "numeric"},
    {"name": "Touches",         "id": "number_of_involvements", "type": "numeric"},
    {"name": "Rec. Under Press","id": "receptions_under_pressure", "type": "numeric"},

    # Goalkeeping
    {"name": "Saves",           "id": "goalkeeper_saves",    "type": "numeric"},
    {"name": "GK Act. In",      "id": "goalkeeper_defensive_actions_inside_penalty_area",  "type": "numeric"},
    {"name": "GK Act. Out",     "id": "goalkeeper_defensive_actions_outside_penalty_area", "type": "numeric"},
]

# ── Scatter plot axis options ─────────────────────────────────────────────────
ALL_METRICS = {
    "price":                         "Fantasy Price ($M)",
    "est_fantasy_points":            "Estimated Fantasy Points",
    "value_factor":                  "Value (Pts/$M)",
    "goals":                         "Goals Scored",
    "assists":                       "Assists Provided",
    "xg":                            "Expected Goals (xG)",
    "total_competition_minutes_played": "Minutes Played",
    "passes":                        "Passes Attempted",
    "passing_accuracy_rate":         "Passing Accuracy (%)",
    "forced_turnovers":              "Forced Turnovers",
    "defensive_pressures_applied":   "Defensive Pressures",
    "top_speed":                     "Top Speed (km/h)",
    "total_distance_km":             "Total Distance (km)",
    "sprints":                       "Sprints Completed",
}

# ── Shared Plotly dark theme ──────────────────────────────────────────────────
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
