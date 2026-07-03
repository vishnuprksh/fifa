"""
layout.py
---------
Builds the complete Dash layout for the scouting & comparison page.
Imports shared data and config so this module stays purely declarative.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table

from data   import df, team_options, position_options, min_price, max_price
from config import ALL_TABLE_COLUMNS, ALL_METRICS

# ─────────────────────────────────────────────────────────────────────────────
# Helper: compact numeric style for the merged table
# ─────────────────────────────────────────────────────────────────────────────
TABLE_CELL_STYLE = {
    'backgroundColor': 'transparent',
    'color': '#cbd5e1',
    'padding': '10px 8px',
    'fontSize': '12px',
    'borderBottom': '1px solid rgba(255,255,255,0.06)',
    'borderTop': 'none', 'borderLeft': 'none', 'borderRight': 'none',
    'textAlign': 'left',
    'whiteSpace': 'normal',
    'minWidth': '70px', 'maxWidth': '160px',
}

TABLE_HEADER_STYLE = {
    'backgroundColor': '#0b1528',
    'color': '#ffffff',
    'fontWeight': '600',
    'fontFamily': 'Outfit, sans-serif',
    'borderBottom': '2px solid rgba(255,255,255,0.15)',
    'textTransform': 'uppercase',
    'fontSize': '10px',
    'letterSpacing': '0.05em',
    'whiteSpace': 'normal',
}

TABLE_CONDITIONAL = [
    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(255,255,255,0.015)'},
    {'if': {'state': 'selected'},
     'backgroundColor': 'rgba(0, 184, 255, 0.12) !important',
     'color': '#00b8ff !important'},
]

# ─────────────────────────────────────────────────────────────────────────────
# Hero Header
# ─────────────────────────────────────────────────────────────────────────────
def build_hero():
    return dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Span(
                            "FIFA WORLD CUP 2026™",
                            style={"color": "var(--accent-orange)", "fontSize": "12px",
                                   "letterSpacing": "3px", "fontWeight": "700"}
                        ),
                        html.H1("Player Analytics Center", className="hero-title"),
                        html.P(
                            "Scout, filter, and compare every player across all statistical "
                            "categories in a single unified view.",
                            className="text-secondary mb-0", style={"fontSize": "14px"}
                        )
                    ], xs=12, md=4, className="mb-3 mb-md-0"),

                    dbc.Col([
                        html.Div([
                            html.Div([
                                html.Div(id="kpi-players-count", className="kpi-val text-info",    children="–"),
                                html.Div("Analyzed Players",                                        className="kpi-label"),
                            ], className="kpi-card-premium"),
                            html.Div([
                                html.Div(id="kpi-avg-xg",        className="kpi-val text-primary", children="–"),
                                html.Div("Average xG",                                              className="kpi-label"),
                            ], className="kpi-card-premium"),
                            html.Div([
                                html.Div(id="kpi-max-speed", className="kpi-val text-danger",
                                         style={"fontSize": "15px"}, children="–"),
                                html.Div("Fastest Player",                                          className="kpi-label"),
                            ], className="kpi-card-premium"),
                            html.Div([
                                html.Div(id="kpi-avg-val",       className="kpi-val text-success", children="–"),
                                html.Div("Avg Value Factor",                                        className="kpi-label"),
                            ], className="kpi-card-premium"),
                        ], className="kpi-container")
                    ], xs=12, md=8, className="d-flex align-items-center"),
                ])
            ], className="hero-header mb-4 mt-3")
        ], width=12)
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Filter Bar
# ─────────────────────────────────────────────────────────────────────────────
def build_filter_bar():
    return dbc.Row([
        dbc.Col([
            html.Label("Search Player", className="small text-secondary mb-1",
                       style={"fontWeight": "600"}),
            dbc.InputGroup([
                dbc.InputGroupText(html.I(className="bi bi-search")),
                dcc.Input(
                    id="search-input", type="text", placeholder="Type name…",
                    className="form-control text-white bg-dark border-secondary",
                    style={"borderRadius": "0 8px 8px 0", "height": "40px"}
                )
            ])
        ], xs=12, sm=6, md=3, className="mb-3"),

        dbc.Col([
            html.Label("Filter Team", className="small text-secondary mb-1",
                       style={"fontWeight": "600"}),
            dcc.Dropdown(id="team-filter", options=team_options, value="All", clearable=False)
        ], xs=12, sm=6, md=3, className="mb-3"),

        dbc.Col([
            html.Label("Filter Position", className="small text-secondary mb-1",
                       style={"fontWeight": "600"}),
            dcc.Dropdown(id="position-filter", options=position_options, value="All", clearable=False)
        ], xs=12, sm=6, md=3, className="mb-3"),

        dbc.Col([
            html.Label("Price Range ($M)", className="small text-secondary mb-1",
                       style={"fontWeight": "600"}),
            html.Div([
                dcc.RangeSlider(
                    id="price-slider",
                    min=min_price, max=max_price, step=0.1,
                    value=[min_price, max_price],
                    marks={int(min_price): f"${int(min_price)}M",
                           int(max_price): f"${int(max_price)}M"},
                    tooltip={"always_visible": False, "placement": "bottom"}
                )
            ], style={"paddingTop": "8px"})
        ], xs=12, sm=12, md=3, className="mb-3"),
    ], className="mb-3 px-2 align-items-end")


# ─────────────────────────────────────────────────────────────────────────────
# Merged DataTable
# ─────────────────────────────────────────────────────────────────────────────
def build_merged_table():
    return dash_table.DataTable(
        id="explorer-table",
        columns=ALL_TABLE_COLUMNS,
        data=df.to_dict('records'),
        page_size=15,
        sort_action="native",
        filter_action="native",
        row_selectable="multi",
        selected_rows=[],
        style_table={'overflowX': 'auto', 'minWidth': '100%', 'borderRadius': '12px'},
        style_cell=TABLE_CELL_STYLE,
        style_header=TABLE_HEADER_STYLE,
        style_data_conditional=TABLE_CONDITIONAL,
        style_cell_conditional=[
            # Give the player name column a bit more room
            {'if': {'column_id': 'name'}, 'minWidth': '140px', 'maxWidth': '200px'},
        ],
        tooltip_delay=0,
        tooltip_duration=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scatter plot section
# ─────────────────────────────────────────────────────────────────────────────
def build_scatter_section():
    metric_opts = [{'label': label, 'value': val} for val, label in ALL_METRICS.items()]
    return dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.H4("Statistical Analysis & Correlations",
                                className="mb-1", style={"fontFamily": "Outfit"}),
                        html.P("Compare two stats across the filtered players. "
                               "Selected players are highlighted.",
                               className="text-secondary small mb-4"),
                        html.Label("X Axis Metric",
                                   className="label mb-2 d-block small text-secondary",
                                   style={"fontWeight": "600"}),
                        dcc.Dropdown(id="scatter-x-filter", options=metric_opts,
                                     value="xg", clearable=False,
                                     className="bg-dark text-white mb-3"),
                        html.Label("Y Axis Metric",
                                   className="label mb-2 d-block small text-secondary",
                                   style={"fontWeight": "600"}),
                        dcc.Dropdown(id="scatter-y-filter", options=metric_opts,
                                     value="goals", clearable=False,
                                     className="bg-dark text-white"),
                    ], xs=12, md=4, className="mb-4 mb-md-0"),

                    dbc.Col([
                        html.H4(id="scatter-title",
                                className="mb-3 text-end text-muted",
                                style={"fontSize": "14px", "textTransform": "uppercase",
                                       "letterSpacing": "1px"}),
                        dcc.Graph(id="scatter-plot", config={"displayModeBar": False})
                    ], xs=12, md=8),
                ])
            ], className="glass-panel mb-5")
        ], width=12)
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Full page layout
# ─────────────────────────────────────────────────────────────────────────────
def build_layout():
    return dbc.Container([
        # ── Hero ──────────────────────────────────────────────────────────────
        build_hero(),

        # ── Page title strip ──────────────────────────────────────────────────
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H3("🔍 Player Scouting & Comparison",
                            className="mb-0", style={"fontFamily": "Outfit"}),
                    html.P("Use the filters below to narrow the player pool, then click "
                           "any row (multi-select supported) to launch the side comparison panel.",
                           className="text-secondary mb-0 mt-1", style={"fontSize": "13px"}),
                ], className="glass-panel mb-4")
            ], width=12)
        ]),

        # ── Main content: Table + Side Panel ─────────────────────────────────
        dbc.Row([
            # Left: Filters + Merged Table
            dbc.Col([
                html.Div([
                    build_filter_bar(),
                    build_merged_table(),
                ], className="glass-panel h-100")
            ], xs=12, lg=8, className="mb-4"),

            # Right: Analysis / Comparison Panel
            dbc.Col([
                html.Div(id="analysis-panel-content", className="detail-panel h-100")
            ], xs=12, lg=4, className="mb-4"),
        ]),

        # ── Scatter Plot ──────────────────────────────────────────────────────
        build_scatter_section(),

    ], fluid=True, style={"maxWidth": "1800px"})
