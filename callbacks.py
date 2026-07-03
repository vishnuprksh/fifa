"""
callbacks.py
------------
All Dash callbacks for the Player Scouting & Comparison page.
"""

import dash
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, html, dcc
import dash_bootstrap_components as dbc

from data   import df, min_price, max_price
from config import ALL_TABLE_COLUMNS, ALL_METRICS, PLOTLY_LAYOUT_TEMPLATE


def register_callbacks(app):
    # ── KPI Cards ─────────────────────────────────────────────────────────────
    @app.callback(
        [Output("kpi-players-count", "children"),
         Output("kpi-avg-xg",        "children"),
         Output("kpi-max-speed",     "children"),
         Output("kpi-avg-val",       "children")],
        [Input("explorer-table", "derived_virtual_data")],
        prevent_initial_call=False
    )
    def update_kpis(virtual_data):
        if not virtual_data:
            return "0", "0.00 xG", "N/A", "0.00"

        v = pd.DataFrame(virtual_data)
        total   = str(len(v))
        avg_xg  = f"{v['xg'].mean():.2f} xG" if 'xg' in v.columns else "0.00 xG"
        avg_val = f"{v['value_factor'].mean():.2f}" if 'value_factor' in v.columns else "0.00"

        max_speed = "N/A"
        if 'top_speed' in v.columns and not v.empty:
            idx = v['top_speed'].idxmax()
            p   = v.loc[idx]
            max_speed = f"{p['top_speed']:.1f} km/h ({p['team_abbr']})"

        return total, avg_xg, max_speed, avg_val

    # ── Filter + Table update ─────────────────────────────────────────────────
    @app.callback(
        [Output("explorer-table", "data"),
         Output("explorer-table", "selected_rows")],
        [Input("search-input",    "value"),
         Input("team-filter",     "value"),
         Input("position-filter", "value"),
         Input("price-slider",    "value")],
        prevent_initial_call=False
    )
    def update_table(name_q, team_q, pos_q, price_range):
        fdf = df.copy()
        if name_q:
            fdf = fdf[fdf['name'].str.contains(name_q, case=False, na=False)]
        if team_q and team_q != "All":
            fdf = fdf[fdf['team_name'] == team_q]
        if pos_q and pos_q != "All":
            fdf = fdf[fdf['position_desc'] == pos_q]
        if price_range:
            fdf = fdf[(fdf['price'] >= price_range[0]) & (fdf['price'] <= price_range[1])]

        return fdf.to_dict('records'), []

    # ── Right-Side Analysis / Comparison Panel ────────────────────────────────
    @app.callback(
        Output("analysis-panel-content", "children"),
        [Input("explorer-table", "selected_rows"),
         Input("explorer-table", "derived_virtual_data")],
        prevent_initial_call=False
    )
    def update_analysis_panel(selected_rows, virtual_data):
        # ── Empty state ───────────────────────────────────────────────────────
        if not selected_rows or not virtual_data:
            return _empty_state()

        selected_players = [virtual_data[i] for i in selected_rows if i < len(virtual_data)]
        if not selected_players:
            return _empty_state()

        # ── Single player ─────────────────────────────────────────────────────
        if len(selected_players) == 1:
            return _single_player_panel(selected_players[0])

        # ── Multi-player comparison ───────────────────────────────────────────
        return _multi_comparison_panel(selected_players)

    # ── Scatter Plot ──────────────────────────────────────────────────────────
    @app.callback(
        [Output("scatter-plot",  "figure"),
         Output("scatter-title", "children")],
        [Input("scatter-x-filter",               "value"),
         Input("scatter-y-filter",               "value"),
         Input("explorer-table", "derived_virtual_data"),
         Input("explorer-table", "selected_rows")]
    )
    def update_scatter(x_metric, y_metric, virtual_data, selected_rows):
        if not virtual_data:
            fig = go.Figure()
            fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
            return fig, "No data"

        v     = pd.DataFrame(virtual_data)
        x_lbl = ALL_METRICS.get(x_metric, x_metric)
        y_lbl = ALL_METRICS.get(y_metric, y_metric)

        bubble_sizes = np.clip(
            np.where(v['total_competition_minutes_played'] > 0,
                     v['total_competition_minutes_played'] / 20.0 + 5, 6),
            6, 25
        )

        fig = px.scatter(
            v, x=x_metric, y=y_metric,
            hover_name="name",
            color="position_desc",
            color_discrete_map={
                "Forward":    "#ff3d00",
                "Midfielder": "#00b8ff",
                "Defender":   "#00c852",
                "Goalkeeper": "#ffb300",
            },
            labels={x_metric: x_lbl, y_metric: y_lbl},
        )
        fig.update_traces(marker=dict(
            size=bubble_sizes,
            line=dict(width=1, color='rgba(255,255,255,0.2)'),
            opacity=0.75
        ))

        if selected_rows:
            sel = [virtual_data[i] for i in selected_rows if i < len(virtual_data)]
            if sel:
                s = pd.DataFrame(sel)
                fig.add_trace(go.Scatter(
                    x=s[x_metric], y=s[y_metric],
                    mode='markers+text',
                    marker=dict(size=18, color='rgba(255,61,0,0.95)',
                                line=dict(width=2, color='#ffffff'), symbol='star'),
                    text=s['name'], textposition='top center',
                    name='Selected', hoverinfo='skip'
                ))

        fig.update_layout(PLOTLY_LAYOUT_TEMPLATE['layout'])
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, title=None, font=dict(size=9)),
            height=450, xaxis_title=x_lbl, yaxis_title=y_lbl,
            margin=dict(t=30, b=40, l=50, r=30)
        )
        return fig, f"Analysis: {x_lbl} vs. {y_lbl}"


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _empty_state():
    return html.Div([
        html.Div([
            html.I(className="bi bi-person-bounding-box",
                   style={"fontSize": "44px", "color": "var(--text-muted)",
                          "display": "block", "marginBottom": "16px"}),
            html.H5("Scouting Workbench", className="font-weight-bold mb-2",
                    style={"fontFamily": "Outfit"}),
            html.P("Select one or more players from the table to begin analysis.",
                   className="text-secondary small mb-3"),
            html.Div("💡 Multi-select rows for instant side-by-side comparison.",
                     className="p-3 border border-secondary rounded text-info small bg-dark",
                     style={"lineHeight": "1.4"})
        ], className="compare-empty-state")
    ], style={"padding": "40px 20px"})


def _radar_figure(p_full):
    """Build a spider/radar chart of percentile ranks for one player."""
    cats = ['Attacking', 'Passing', 'Defending', 'Pace', 'Stamina']
    vals = [
        p_full.get('goals_pct',    50),
        p_full.get('passing_pct',  50),
        p_full.get('defending_pct',50),
        p_full.get('speed_pct',    50),
        p_full.get('distance_pct', 50),
    ]
    vals  = [*vals, vals[0]]
    cats  = [*cats, cats[0]]

    return go.Figure(
        data=[go.Scatterpolar(
            r=vals, theta=cats,
            fill='toself', name=p_full['name'],
            line_color='#00b8ff', fillcolor='rgba(0,184,255,0.18)'
        )],
        layout=go.Layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                gridcolor='rgba(255,255,255,0.08)',
                                linecolor='rgba(255,255,255,0.1)'),
                angularaxis=dict(gridcolor='rgba(255,255,255,0.08)',
                                 linecolor='rgba(255,255,255,0.1)')
            ),
            showlegend=False, height=230,
            margin=dict(l=30, r=30, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cbd5e1', family='Outfit', size=11)
        )
    )


def _single_player_panel(player):
    pid = str(player['sports_person_id'])
    matches = df[df['sports_person_id'] == pid]
    if matches.empty:
        return html.Div("Player data not found.", className="text-danger p-3")
    p = matches.iloc[0]

    img_src  = (p['headshot_url'] if pd.notna(p['headshot_url']) and p['headshot_url'] != ''
                else "https://play.fifa.com/media/image/headshots/389867_headshot.png")
    flag_src = p['flag_url'] if pd.notna(p['flag_url']) else ""

    xg_diff = p['goals'] - p['xg']
    xg_color, xg_text = ("#00c852", f"+{xg_diff:.2f}") if xg_diff >= 0 else ("#ff3d00", f"{xg_diff:.2f}")

    return html.Div([
        # Profile header
        html.Div([
            html.Div([
                html.Img(src=img_src, style={"width": "100%", "height": "100%", "objectFit": "cover"})
            ], className="player-image-container mb-3",
               style={"width": "100px", "height": "100px", "border": "3px solid #00b8ff"}),
            html.H4(p['name'], className="text-center font-weight-bold mb-1",
                    style={"fontFamily": "Outfit"}),
            html.Div([
                html.Img(src=flag_src, className="flag-badge"),
                html.Span(f"{p['team_name']} • {p['position_desc']}",
                          className="text-muted", style={"fontSize": "13px"}),
            ], className="text-center mb-3"),
            html.Div([
                dbc.Badge(f"${p['price']:.1f}M",          color="primary", className="me-2",
                          style={"fontSize": "11px", "padding": "5px 10px"}),
                dbc.Badge(f"{p['est_fantasy_points']:.0f} Pts", color="success", className="me-2",
                          style={"fontSize": "11px", "padding": "5px 10px"}),
                dbc.Badge(f"{p['value_factor']:.2f} Pts/$",    color="warning",
                          style={"fontSize": "11px", "padding": "5px 10px"}),
            ], className="text-center mb-3"),
        ]),

        # Radar
        html.Div([
            html.Div("Attribute Percentile Profile",
                     className="text-muted small font-weight-bold text-uppercase text-center mb-2",
                     style={"letterSpacing": "1.5px"}),
            dcc.Graph(figure=_radar_figure(p), config={"displayModeBar": False})
        ], className="mb-4 pt-2 border-top border-secondary"),

        # Key metrics grid
        html.Div([
            html.Div("Key Tournament Metrics",
                     className="border-bottom border-secondary pb-1 mb-3 text-uppercase font-weight-bold",
                     style={"fontSize": "11px", "color": "#00b8ff", "letterSpacing": "1px"}),

            dbc.Row([
                _metric_badge(str(int(p['goals'])),    "Goals",   "#ff3d00", 4),
                _metric_badge(str(int(p['assists'])),  "Assists", "#ffb300", 4),
                _metric_badge(f"{p['xg']:.2f}",        "xG",      "#00b8ff", 4),
            ], className="mb-2"),
            dbc.Row([
                _metric_badge(str(int(p['total_competition_minutes_played'])), "Mins",      None, 4),
                _metric_badge(f"{p['passing_accuracy_rate']:.0f}%",           "Pass %",   None, 4),
                _metric_badge(xg_text,                                          "G vs xG",  xg_color, 4),
            ], className="mb-2"),

            # Physical row
            html.Div([
                _stat_row("Top Speed",        f"{p['top_speed']:.1f} km/h", "#ff3d00"),
                _stat_row("Distance Covered", f"{p['total_distance_km']:.2f} km"),
                _stat_row("Sprints",          str(int(p['sprints']))),
                _stat_row("Recoveries",       str(int(p['forced_turnovers']))),
                _stat_row("Touches",          str(int(p['number_of_involvements']))),
            ], className="pt-2 border-top border-secondary"),
        ]),
    ])


def _multi_comparison_panel(players):
    ids    = [str(p['sports_person_id']) for p in players]
    cdf    = df[df['sports_person_id'].isin(ids)]
    n      = len(players)

    # Bar: Fantasy Points
    pts_fig = px.bar(
        cdf, x='name', y='est_fantasy_points', color='name',
        color_discrete_sequence=px.colors.qualitative.G10,
        labels={'est_fantasy_points': 'Fantasy Points', 'name': 'Player'}
    )
    pts_fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#cbd5e1', family='Outfit'),
        margin=dict(l=30, r=30, t=10, b=10), height=175,
        showlegend=False, xaxis_title=None, yaxis_title="Points",
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
    )

    # Grouped bar: Goals / Assists / xG
    melted = cdf.melt(id_vars=['name'], value_vars=['goals', 'assists', 'xg'],
                      var_name='Metric', value_name='Value')
    melted['Metric'] = melted['Metric'].map({'goals': 'Goals', 'assists': 'Assists', 'xg': 'xG'})

    stats_fig = px.bar(
        melted, x='Metric', y='Value', color='name', barmode='group',
        color_discrete_sequence=px.colors.qualitative.G10,
        labels={'Value': 'Value', 'name': 'Player', 'Metric': ''}
    )
    stats_fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#cbd5e1', family='Outfit'),
        margin=dict(l=20, r=20, t=10, b=10), height=175,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=8), title=None),
        xaxis_title=None, yaxis_title="Value",
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
    )

    # Speed bar
    speed_fig = px.bar(
        cdf, x='name', y='top_speed', color='name',
        color_discrete_sequence=px.colors.qualitative.G10,
        labels={'top_speed': 'Top Speed (km/h)', 'name': 'Player'}
    )
    speed_fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#cbd5e1', family='Outfit'),
        margin=dict(l=30, r=30, t=10, b=10), height=150,
        showlegend=False, xaxis_title=None, yaxis_title="km/h",
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
    )

    # Detail list
    detail_items = [
        html.Div([
            html.Div([
                html.Span(p['name'], className="font-weight-bold", style={"fontSize": "13px"}),
                html.Span(f" ({p['team_abbr']})", className="text-secondary small"),
                html.Span(f" ${p['price']:.1f}M",
                          className="float-end font-weight-bold text-info"),
            ], className="mb-1 clearfix"),
            html.Div(
                f"Pts: {p['est_fantasy_points']:.0f} | xG: {p['xg']:.2f} | "
                f"Pass%: {p['passing_accuracy_rate']:.0f} | Speed: {p['top_speed']:.1f} km/h",
                style={"fontSize": "11px", "color": "#cbd5e1"}
            )
        ], className="mb-2 pb-2 border-bottom border-secondary")
        for p in players
    ]

    return html.Div([
        html.H5(f"Comparing {n} Players", className="font-weight-bold mb-3",
                style={"fontFamily": "Outfit"}),

        _section_label("Fantasy Points"),
        dcc.Graph(figure=pts_fig, config={"displayModeBar": False}),

        _section_label("Goals / Assists / xG", mt=True),
        dcc.Graph(figure=stats_fig, config={"displayModeBar": False}),

        _section_label("Top Speed (km/h)", mt=True),
        dcc.Graph(figure=speed_fig, config={"displayModeBar": False}),

        html.Div("Player Details",
                 className="border-bottom border-secondary pb-1 mb-2 mt-3 "
                            "text-uppercase font-weight-bold",
                 style={"fontSize": "10.5px", "color": "#00b8ff", "letterSpacing": "1px"}),
        html.Div(detail_items, style={"maxHeight": "220px", "overflowY": "auto",
                                      "paddingRight": "5px"}),
    ])


# ── Mini helpers ──────────────────────────────────────────────────────────────

def _metric_badge(value, label, color=None, width=4):
    style = {"color": color} if color else {}
    return dbc.Col([
        html.Div([
            html.Div(value, className="font-weight-bold text-center h5 mb-0", style=style),
            html.Div(label, className="text-center text-muted", style={"fontSize": "9px"}),
        ], className="mb-2 py-2 px-1 border border-secondary rounded bg-dark")
    ], width=width)


def _stat_row(label, value, color=None):
    style = {"color": color, "fontWeight": "bold"} if color else {"fontWeight": "bold"}
    return html.Div([
        html.Span(f"{label}:", className="text-secondary small"),
        html.Span(f" {value}", className="float-end", style=style),
    ], className="mb-2 clearfix")


def _section_label(text, mt=False):
    cls = "text-muted small font-weight-bold text-uppercase mb-1"
    if mt:
        cls += " mt-3"
    return html.Div(text, className=cls, style={"letterSpacing": "1px", "fontSize": "9px"})
