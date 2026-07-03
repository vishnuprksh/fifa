"""
app.py
------
Entry point. Wires together the Dash app, layout, and callbacks.
"""

import dash
import dash_bootstrap_components as dbc

from layout    import build_layout
from callbacks import register_callbacks

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
    ],
    meta_tags=[
        {"name": "viewport",    "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content":
         "Player Scouting & Comparison — FIFA World Cup 2026 Analytics Dashboard."},
    ],
    title="Player Scouting & Comparison | FIFA World Cup 2026",
    suppress_callback_exceptions=True,
)

app.layout = build_layout()
register_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
