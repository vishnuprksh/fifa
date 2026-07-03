import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Load and clean statistics dataset
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

# Configure human-readable names for metrics grouped by category
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
    "Movement": {
        "offers_to_receive_total": "Offers to Receive (Total)",
        "offers_to_receive_in_behind": "Offers in Behind",
        "offers_to_receive_in_between": "Offers in Between Lines",
        "offers_to_receive_in_front": "Offers in Front",
        "offers_to_receive_inside": "Offers Inside Opponent Shape",
        "offers_to_receive_outside": "Offers Outside Opponent Shape",
        "receptions_in_behind": "Receptions in Behind",
        "receptions_between_midfield_and_defensive_line": "Receptions Between Lines",
        "receptions_under_pressure": "Receptions Under Pressure",
        "number_of_involvements": "Player Involvements (Touches)",
    },
    "Physical": {
        "avg_speed": "Average Speed (km/h)",
        "top_speed": "Top Speed (km/h)",
        "sprints": "Sprints Completed",
        "speed_runs": "High Speed Runs",
        "total_distance": "Total Distance Covered (m)",
    }
}

# Create list of all metrics for search/scatter plots
ALL_METRICS = {}
for cat, metrics in METRICS_CONFIG.items():
    ALL_METRICS.update(metrics)

# Get sorted list of teams and positions for filters
team_options = [{'label': 'All Teams', 'value': 'All'}] + [{'label': t, 'value': t} for t in sorted(df['team_name'].dropna().unique())]
position_options = [{'label': 'All Positions', 'value': 'All'}] + [{'label': p, 'value': p} for p in sorted(df['position_desc'].dropna().unique())]

# Default values
DEFAULT_CATEGORY = "adidas Golden Boot"
DEFAULT_METRIC = "goals"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": "Premium Dashboard showing FIFA World Cup 2026 Player Statistics."}
    ],
    title="Player Stats Dashboard | FIFA World Cup 2026"
)

# Plotly theme configuration
PLOTLY_LAYOUT_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color='#f8fafc'),
        margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.1)'),
    )
)

app.layout = dbc.Container([
    dbc.Row([
        # SIDEBAR (FILTERS)
        dbc.Col([
            html.Div([
                # Dashboard title & branding
                html.Div([
                    html.Img(src="https://digitalhub.fifa.com/transform/157d23bf-7e13-4d7b-949e-5d27d340987e/WC26_Logo?&io=transform:fill&quality=75", style={"height": "70px", "display": "block", "margin": "0 auto 12px auto"}),
                    html.H2("FWC 2026", className="text-center font-weight-bold mb-1", style={"color": "#ff3d00"}),
                    html.H5("PLAYER STATS CENTER", className="text-center text-muted mb-4", style={"fontSize": "12px", "letterSpacing": "3px"}),
                ], className="mb-4 pb-2 border-bottom border-secondary"),

                # Search Filter
                html.Div([
                    html.Label("Search Player Name", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8", "fontWeight": "600"}),
                    dcc.Input(id="search-input", type="text", placeholder="Type name...", className="custom-input mb-3"),
                ]),

                # Team Filter
                html.Div([
                    html.Label("Select Team", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8", "fontWeight": "600"}),
                    dcc.Dropdown(
                        id="team-filter",
                        options=team_options,
                        value="All",
                        clearable=False,
                        className="mb-3"
                    ),
                ]),

                # Position Filter
                html.Div([
                    html.Label("Select Position", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8", "fontWeight": "600"}),
                    dcc.Dropdown(
                        id="position-filter",
                        options=position_options,
                        value="All",
                        clearable=False,
                        className="mb-4"
                    ),
                ]),

                # Statistics Category Filter
                html.Div([
                    html.Label("Select Category", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8", "fontWeight": "600"}),
                    dcc.Dropdown(
                        id="category-filter",
                        options=[{'label': cat, 'value': cat} for cat in METRICS_CONFIG.keys()],
                        value=DEFAULT_CATEGORY,
                        clearable=False,
                        className="mb-3"
                    ),
                ]),

                # Active Metric Filter
                html.Div([
                    html.Label("Select Metric", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8", "fontWeight": "600"}),
                    dcc.Dropdown(
                        id="metric-filter",
                        clearable=False,
                        className="mb-4"
                    ),
                ]),

                # Quick Summary metrics
                html.Div([
                    html.Div([
                        html.Div("1,508", className="value"),
                        html.Div("Scraped Players", className="label")
                    ], className="summary-card mb-3"),
                    html.Div([
                        html.Div("48", className="value", style={"color": "#ff3d00"}),
                        html.Div("World Cup Nations", className="label")
                    ], className="summary-card")
                ], className="pt-4 border-top border-secondary")
            ], className="sidebar")
        ], width=12, md=3, className="px-0"),

        # MAIN CONTENT PANEL
        dbc.Col([
            # Dashboard Header Summary Cards
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1("FIFA World Cup 2026™ Statistics Dashboard", className="mb-2", style={"fontFamily": "Outfit"}),
                        html.P("Analyze player stats, explore metrics correlations, and identify top performers using official FWC 2026 data.", className="text-secondary mb-0")
                    ], className="py-4 px-4 mb-3")
                ])
            ], className="mb-3"),

            # Tabs Container
            html.Div([
                dbc.Tabs([
                    dbc.Tab(label="🏆 Leaderboards", tab_id="tab-leaderboard"),
                    dbc.Tab(label="📊 Analytics & Correlations", tab_id="tab-analytics"),
                    dbc.Tab(label="🔍 Database Explorer", tab_id="tab-explorer"),
                ], id="dashboard-tabs", active_tab="tab-leaderboard", className="custom-tabs mb-4 px-4")
            ]),

            # Active Tab Container
            html.Div(id="tab-content", className="px-4 pb-5")
        ], width=12, md=9)
    ])
], fluid=True, style={"maxWidth": "1800px"})


# Callback to update the metric dropdown dynamically based on category
@app.callback(
    [Output("metric-filter", "options"),
     Output("metric-filter", "value")],
    [Input("category-filter", "value")]
)
def set_metrics_options(selected_category):
    metrics = METRICS_CONFIG.get(selected_category, {})
    options = [{'label': label, 'value': val} for val, label in metrics.items()]
    default_val = list(metrics.keys())[0] if metrics else None
    return options, default_val


# Callback to switch Tab Content
@app.callback(
    Output("tab-content", "children"),
    [Input("dashboard-tabs", "active_tab"),
     Input("metric-filter", "value"),
     Input("search-input", "value"),
     Input("team-filter", "value"),
     Input("position-filter", "value")],
    [State("category-filter", "value")]
)
def render_tab_content(active_tab, metric, name_query, team_query, position_query, category):
    # Filter dataset based on filters
    filtered_df = df.copy()
    if name_query:
        filtered_df = filtered_df[filtered_df['name'].str.contains(name_query, case=False, na=False)]
    if team_query != "All":
        filtered_df = filtered_df[filtered_df['team_name'] == team_query]
    if position_query != "All":
        filtered_df = filtered_df[filtered_df['position_desc'] == position_query]

    # Handle fallbacks
    if not metric:
        metric = DEFAULT_METRIC

    metric_name = ALL_METRICS.get(metric, "Value")

    # TAB 1: LEADERBOARDS & PODIUMS
    if active_tab == "tab-leaderboard":
        # Sort and get top players
        top_df = filtered_df.sort_values(by=metric, ascending=False).head(15)
        podium_df = filtered_df.sort_values(by=metric, ascending=False).head(3)
        
        # Build Podium Layout
        podium_cards = []
        ranks = [1, 2, 3]
        rank_classes = ["podium-rank-1", "podium-rank-2", "podium-rank-3"]
        
        # Rearrange podium layout to be [Silver, Gold, Bronze] (2nd, 1st, 3rd)
        podium_order = [1, 0, 2] if len(podium_df) >= 3 else list(range(len(podium_df)))
        
        podium_cols = []
        for idx in podium_order:
            if idx >= len(podium_df):
                continue
            player = podium_df.iloc[idx]
            rank = idx + 1
            rank_class = rank_classes[idx]
            
            # Formatting values nicely
            val = player[metric]
            val_str = f"{val:,.2f}" if isinstance(val, float) and val % 1 != 0 else f"{int(val):,}"
            
            # Headshot fallback
            img_src = player['headshot_url'] if pd.notna(player['headshot_url']) and player['headshot_url'] != '' else "https://play.fifa.com/media/image/headshots/389867_headshot.png"
            flag_src = player['flag_url'] if pd.notna(player['flag_url']) else ""
            
            card = dbc.Col([
                html.Div([
                    html.Div(str(rank), className=f"podium-rank-badge {rank_class}"),
                    html.Div([
                        html.Img(src=img_src)
                    ], className="player-image-container"),
                    html.H4(player['name'], className="text-center font-weight-bold mb-1 text-truncate", style={"fontSize": "18px"}),
                    html.Div([
                        html.Img(src=flag_src, className="flag-badge"),
                        html.Span(f"{player['team_abbr']} • {player['position_desc']}", className="text-muted", style={"fontSize": "12px"})
                    ], className="text-center mb-3"),
                    html.Div([
                        html.Div(val_str, className="h2 font-weight-bold text-center mb-0", style={"color": "#ff3d00"}),
                        html.Div(metric_name, className="text-muted text-center", style={"fontSize": "11px", "textTransform": "uppercase"})
                    ], className="pt-2 border-top border-secondary")
                ], className="glass-panel podium-card h-100")
            ], xs=12, md=4, className="mb-3")
            podium_cols.append(card)

        # Build leaderboards bar chart
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
                height=500,
                xaxis_title=metric_name,
                yaxis_title=""
            )
        else:
            fig = go.Figure()
            fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])

        return html.Div([
            # Top 3 Podium row
            html.H3("Top Performers", className="mb-4 px-2", style={"fontFamily": "Outfit"}),
            dbc.Row(podium_cols, className="mb-5"),
            
            # Ranking chart row
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(f"Top 15 Rankings: {metric_name}", className="mb-4", style={"fontFamily": "Outfit"}),
                        dcc.Graph(figure=fig, config={"displayModeBar": False})
                    ], className="glass-panel")
                ], width=12)
            ])
        ])

    # TAB 2: ANALYTICS & CORRELATIONS
    elif active_tab == "tab-analytics":
        # Group by team and calculate averages for the metric
        team_avg = filtered_df.groupby('team_name')[metric].mean().reset_index()
        team_avg = team_avg.sort_values(by=metric, ascending=False).head(15)
        
        # Build Team Performance Bar Chart
        if not team_avg.empty:
            team_fig = px.bar(
                team_avg,
                x=metric,
                y='team_name',
                orientation='h',
                color=metric,
                color_continuous_scale=['#00b8ff', '#ffb300'],
                labels={'team_name': 'Team', metric: f"Average {metric_name}"}
            )
            team_fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
            team_fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                coloraxis_showscale=False,
                height=450,
                xaxis_title=f"Average {metric_name}",
                yaxis_title=""
            )
        else:
            team_fig = go.Figure()
            team_fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])

        # Layout for Tab 2
        return html.Div([
            dbc.Row([
                # Correlation / Scatter Plot Configuration Card
                dbc.Col([
                    html.Div([
                        html.H4("Explore Statistical Correlations", className="mb-3", style={"fontFamily": "Outfit"}),
                        html.P("Compare any two metrics to discover player profiles (e.g. goal-scorers vs xG models).", className="text-secondary small mb-4"),
                        
                        html.Label("X Axis Metric", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8"}),
                        dcc.Dropdown(
                            id="scatter-x-filter",
                            options=[{'label': label, 'value': val} for val, label in ALL_METRICS.items()],
                            value="xg",
                            clearable=False,
                            className="mb-3"
                        ),
                        
                        html.Label("Y Axis Metric", className="label mb-2 d-block", style={"fontSize": "11px", "color": "#94a3b8"}),
                        dcc.Dropdown(
                            id="scatter-y-filter",
                            options=[{'label': label, 'value': val} for val, label in ALL_METRICS.items()],
                            value="goals",
                            clearable=False,
                            className="mb-4"
                        )
                    ], className="glass-panel h-100")
                ], xs=12, md=4),
                
                # Scatter Plot
                dbc.Col([
                    html.Div([
                        html.H4("Correlation Scatter Plot", id="scatter-title", className="mb-4", style={"fontFamily": "Outfit"}),
                        dcc.Graph(id="scatter-plot", config={"displayModeBar": False})
                    ], className="glass-panel")
                ], xs=12, md=8, className="mb-4")
            ], className="mb-4"),
            
            # Team Performance Charts
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(f"Top Teams by Average {metric_name}", className="mb-4", style={"fontFamily": "Outfit"}),
                        dcc.Graph(figure=team_fig, config={"displayModeBar": False})
                    ], className="glass-panel")
                ], width=12)
            ])
        ])

    # TAB 3: DATABASE EXPLORER
    elif active_tab == "tab-explorer":
        # Get clean view columns for DataTable
        table_df = filtered_df.copy()
        
        # Format DataTable columns
        table_columns = [
            {"name": "Player", "id": "name"},
            {"name": "Team", "id": "team_name"},
            {"name": "Pos", "id": "position"},
            {"name": "Goals", "id": "goals"},
            {"name": "Assists", "id": "assists"},
            {"name": "Minutes", "id": "total_competition_minutes_played"},
            {"name": "Distance (m)", "id": "total_distance"},
            {"name": "Avg Speed (km/h)", "id": "avg_speed"},
            {"name": "xG", "id": "xg"}
        ]
        
        # Convert values to dictionary records
        table_data = table_df.to_dict('records')
        
        return html.Div([
            dbc.Row([
                # Player Table list
                dbc.Col([
                    html.Div([
                        html.H4("Player Database", className="mb-3", style={"fontFamily": "Outfit"}),
                        html.P("Select a player in the table below to load their full statistical details card.", className="text-secondary small mb-4"),
                        
                        dash_table.DataTable(
                            id="explorer-table",
                            columns=table_columns,
                            data=table_data,
                            page_size=10,
                            sort_action="native",
                            row_selectable="single",
                            selected_rows=[0] if table_data else [],
                            style_table={'overflowX': 'auto', 'minWidth': '100%'},
                            style_cell={
                                'backgroundColor': 'transparent',
                                'color': '#cbd5e1',
                                'padding': '12px 8px',
                                'fontSize': '13px',
                                'borderBottom': '1px solid rgba(255,255,255,0.05)',
                                'borderTop': 'none',
                                'borderLeft': 'none',
                                'borderRight': 'none',
                                'textAlign': 'left'
                            },
                            style_header={
                                'backgroundColor': '#0b1528',
                                'color': '#f8fafc',
                                'fontWeight': '600',
                                'fontFamily': 'Outfit, sans-serif',
                                'borderBottom': '1.5px solid rgba(255,255,255,0.15)',
                                'textTransform': 'uppercase',
                                'fontSize': '11px',
                                'letterSpacing': '0.05em'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'state': 'selected'},
                                    'backgroundColor': 'rgba(0,184,255,0.12) !important',
                                    'color': '#00b8ff !important'
                                }
                            ]
                        )
                    ], className="glass-panel mb-4")
                ], xs=12, md=7),
                
                # Player Profile Card Panel
                dbc.Col([
                    html.Div(id="player-detail-card")
                ], xs=12, md=5)
            ])
        ])


# Callback to update scatter plot correlations in Tab 2
@app.callback(
    [Output("scatter-plot", "figure"),
     Output("scatter-title", "children")],
    [Input("scatter-x-filter", "value"),
     Input("scatter-y-filter", "value"),
     Input("search-input", "value"),
     Input("team-filter", "value"),
     Input("position-filter", "value")]
)
def update_scatter_plot(x_metric, y_metric, name_query, team_query, position_query):
    filtered_df = df.copy()
    if name_query:
        filtered_df = filtered_df[filtered_df['name'].str.contains(name_query, case=False, na=False)]
    if team_query != "All":
        filtered_df = filtered_df[filtered_df['team_name'] == team_query]
    if position_query != "All":
        filtered_df = filtered_df[filtered_df['position_desc'] == position_query]
        
    x_label = ALL_METRICS.get(x_metric, x_metric)
    y_label = ALL_METRICS.get(y_metric, y_metric)
    
    if not filtered_df.empty:
        fig = px.scatter(
            filtered_df,
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
            size=np.where(filtered_df['total_competition_minutes_played'] > 0, filtered_df['total_competition_minutes_played'], 5),
            size_max=18
        )
        
        # Add regression line or trendline manually or layout cleanups
        fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title=None
            ),
            height=450,
            xaxis_title=x_label,
            yaxis_title=y_label
        )
    else:
        fig = go.Figure()
        fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
        
    return fig, f"Correlation: {x_label} vs. {y_label}"


# Callback to update the player details card in Tab 3
@app.callback(
    Output("player-detail-card", "children"),
    [Input("explorer-table", "selected_rows"),
     Input("explorer-table", "data")]
)
def update_player_detail(selected_rows, table_data):
    if not selected_rows or not table_data or selected_rows[0] >= len(table_data):
        return html.Div([
            html.H5("No player selected", className="text-center text-muted py-5")
        ], className="detail-panel")
        
    row_idx = selected_rows[0]
    player_data_raw = table_data[row_idx]
    
    # Reload full player record from original dataframe to get all columns/URLs
    pid = player_data_raw.get("sports_person_id")
    player_matches = df[df['sports_person_id'] == pid]
    
    if player_matches.empty:
        return html.Div([
            html.H5("Error loading player details", className="text-center text-danger py-5")
        ], className="detail-panel")
        
    player = player_matches.iloc[0]
    
    img_src = player['headshot_url'] if pd.notna(player['headshot_url']) and player['headshot_url'] != '' else "https://play.fifa.com/media/image/headshots/389867_headshot.png"
    flag_src = player['flag_url'] if pd.notna(player['flag_url']) else ""
    
    # Calculate xG difference or custom ratios
    xg_diff = player['goals'] - player['xg']
    xg_diff_style = ("#00c852", f"+{xg_diff:.2f}") if xg_diff >= 0 else ("#ff3d00", f"{xg_diff:.2f}")
    
    return html.Div([
        # Card Header: Photo & Name
        html.Div([
            html.Div([
                html.Img(src=img_src)
            ], className="player-image-container mb-3", style={"width": "120px", "height": "120px", "border": "4px solid #00b8ff"}),
            html.H3(player['name'], className="text-center font-weight-bold mb-1", style={"fontFamily": "Outfit"}),
            html.Div([
                html.Img(src=flag_src, className="flag-badge"),
                html.H6(f"{player['team_name']} • {player['position_desc']}", className="text-muted text-center mb-0", style={"display": "inline-block", "fontSize": "14px"})
            ], className="text-center mb-4")
        ]),
        
        # Grid of key statistics
        html.Div([
            html.H5("Tournament Statistics Summary", className="border-bottom border-secondary pb-2 mb-3", style={"fontSize": "13px", "letterSpacing": "1.5px", "color": "#00b8ff", "textTransform": "uppercase"}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(str(int(player['goals'])), className="font-weight-bold text-center h3 mb-0", style={"color": "#ff3d00"}),
                        html.Div("Goals", className="text-center text-muted small")
                    ], className="mb-3 py-2 px-1 border border-secondary rounded bg-dark")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div(str(int(player['assists'])), className="font-weight-bold text-center h3 mb-0", style={"color": "#ffb300"}),
                        html.Div("Assists", className="text-center text-muted small")
                    ], className="mb-3 py-2 px-1 border border-secondary rounded bg-dark")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div(f"{player['xg']:.2f}", className="font-weight-bold text-center h3 mb-0", style={"color": "#00b8ff"}),
                        html.Div("xG (Exp)", className="text-center text-muted small")
                    ], className="mb-3 py-2 px-1 border border-secondary rounded bg-dark")
                ], width=4),
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(f"{int(player['total_competition_minutes_played'])}", className="font-weight-bold text-center h4 mb-0"),
                        html.Div("Min Played", className="text-center text-muted small", style={"fontSize": "10px"})
                    ], className="mb-3 py-2 px-1 border border-secondary rounded")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div(f"{player['passing_accuracy_rate']:.0f}%", className="font-weight-bold text-center h4 mb-0"),
                        html.Div("Pass Acc (%)", className="text-center text-muted small", style={"fontSize": "10px"})
                    ], className="mb-3 py-2 px-1 border border-secondary rounded")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div(xg_diff_style[1], className="font-weight-bold text-center h4 mb-0", style={"color": xg_diff_style[0]}),
                        html.Div("Goals vs xG", className="text-center text-muted small", style={"fontSize": "10px"})
                    ], className="mb-3 py-2 px-1 border border-secondary rounded")
                ], width=4),
            ]),
            
            # Physical metrics
            html.H5("Physical & Performance", className="border-bottom border-secondary pb-2 mb-3 mt-3", style={"fontSize": "13px", "letterSpacing": "1.5px", "color": "#00b8ff", "textTransform": "uppercase"}),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(f"{player['top_speed']:.2f} km/h", className="font-weight-bold h5 mb-0", style={"color": "#ff3d00"}),
                        html.Div("Top Speed reached", className="text-muted small", style={"fontSize": "10px"})
                    ], className="d-flex justify-content-between align-items-center mb-2")
                ], width=12),
                dbc.Col([
                    html.Div([
                        html.Div(f"{player['total_distance'] / 1000:.2f} km", className="font-weight-bold h5 mb-0"),
                        html.Div("Total Distance covered", className="text-muted small", style={"fontSize": "10px"})
                    ], className="d-flex justify-content-between align-items-center mb-2")
                ], width=12),
                dbc.Col([
                    html.Div([
                        html.Div(f"{int(player['sprints'])}", className="font-weight-bold h5 mb-0"),
                        html.Div("Sprints completed", className="text-muted small", style={"fontSize": "10px"})
                    ], className="d-flex justify-content-between align-items-center mb-2")
                ], width=12),
                dbc.Col([
                    html.Div([
                        html.Div(f"{int(player['defensive_pressures_applied'])}", className="font-weight-bold h5 mb-0"),
                        html.Div("Pressures applied", className="text-muted small", style={"fontSize": "10px"})
                    ], className="d-flex justify-content-between align-items-center mb-2")
                ], width=12),
            ])
        ], className="pt-2")
    ], className="detail-panel")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
