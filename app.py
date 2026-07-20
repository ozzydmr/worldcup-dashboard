"""
A Century of the World Cup (1930-2026) — interactive Dash dashboard.

Five linked visualizations on one screen, cross-filtered by a single
year-range slider (updates every chart + KPIs simultaneously) and a
secondary confederation filter.

Run locally:   python app.py   ->   http://127.0.0.1:7860
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# --------------------------------------------------------------------------- #
# 1. DATA LOADING
# --------------------------------------------------------------------------- #
DATA = os.path.join(os.path.dirname(__file__), "data")

editions = pd.read_csv(os.path.join(DATA, "wc_editions.csv"))
hosts = pd.read_csv(os.path.join(DATA, "wc_host_performance.csv"))

YEARS = sorted(editions["year"].tolist())
YEAR_MIN, YEAR_MAX = YEARS[0], YEARS[-1]

# Editions carrying a rule-change / milestone note -> line-chart annotations
RULE_NOTES = (
    editions.loc[editions["has_rule_note"] == 1, ["year", "goals_per_match", "rule_change_note"]]
    .dropna(subset=["goals_per_match"])
    .to_dict("records")
)

CONFEDS = ["UEFA", "CONMEBOL", "CONCACAF", "AFC", "CAF"]

# Plotly recognises most host names as-is; normalise the two exceptions.
COUNTRY_FIX = {"West Germany": "Germany", "England": "United Kingdom"}

# --------------------------------------------------------------------------- #
# 2. THEME
# --------------------------------------------------------------------------- #
GREEN = "#1a7a4c"
GREEN_DARK = "#0f4d30"
GOLD = "#d4af37"
INK = "#1c2b24"
PAPER = "#ffffff"
GRID = "#e6ede9"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=PAPER,
    plot_bgcolor=PAPER,
    font=dict(family="Inter, Helvetica, Arial, sans-serif", color=INK, size=13),
    margin=dict(l=48, r=24, t=52, b=40),
    title=dict(font=dict(size=16, color=GREEN_DARK)),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


def themed(fig, title):
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(title=title)
    return fig


# --------------------------------------------------------------------------- #
# 3. CHART BUILDERS  (each takes the already-filtered frames)
# --------------------------------------------------------------------------- #
def fig_goals_line(ed, picked_confeds):
    """Goals per match over time, with rule-change markers and champion stars."""
    d = ed.dropna(subset=["goals_per_match"]).sort_values("year")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=d["year"], y=d["goals_per_match"], mode="lines+markers",
            line=dict(color=GREEN, width=3), marker=dict(size=7, color=GREEN),
            name="Goals / match",
            hovertemplate="<b>%{x}</b><br>%{y:.2f} goals/match<extra></extra>",
        )
    )
    # Gold stars on editions won by a selected confederation
    champs = d[d["champion_confed"].isin(picked_confeds)]
    if len(champs):
        fig.add_trace(
            go.Scatter(
                x=champs["year"], y=champs["goals_per_match"], mode="markers",
                marker=dict(symbol="star", size=15, color=GOLD,
                            line=dict(color=GREEN_DARK, width=1)),
                name="Champion (selected confed)",
                text=champs["champion"],
                hovertemplate="<b>%{x}</b><br>Champion: %{text}<extra></extra>",
            )
        )
    # Rule-change annotations (only those inside the current range)
    for r in RULE_NOTES:
        if d["year"].min() <= r["year"] <= d["year"].max():
            fig.add_annotation(
                x=r["year"], y=r["goals_per_match"], text="&#9679;",
                showarrow=True, arrowhead=0, ax=0, ay=-22,
                font=dict(color=GOLD, size=12),
                hovertext=r["rule_change_note"],
            )
    fig.update_yaxes(title="Goals per match")
    fig.update_xaxes(title="Edition")
    return themed(fig, "Scoring over time — goals per match")


def fig_cards_bar(ed):
    """Cards per match (only 1970+ editions carry card data)."""
    d = ed.dropna(subset=["cards_per_match"]).sort_values("year")
    fig = px.bar(d, x="year", y="cards_per_match",
                 color="cards_per_match", color_continuous_scale="YlOrRd")
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:.2f} cards/match<extra></extra>")
    fig.update_layout(coloraxis_showscale=False)
    fig.update_yaxes(title="Cards per match")
    fig.update_xaxes(title="Edition")
    if d.empty:
        fig.add_annotation(text="No card data before 1970",
                           showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    return themed(fig, "Discipline — cards per match (1970-)")


def fig_host_scatter(hp):
    """Host performance lift: how much better hosts do at home vs. away."""
    d = hp.dropna(subset=["ppm_lift"])
    fig = px.scatter(
        d, x="year", y="ppm_lift", color="lift_direction",
        size="matches_as_host", size_max=22,
        color_discrete_map={"Overperformed": GREEN, "Underperformed": "#c0392b"},
        hover_name="host",
        hover_data={"ppm_lift": ":.2f", "year": True, "lift_direction": False},
    )
    fig.add_hline(y=0, line_dash="dash", line_color=INK, opacity=0.4)
    fig.update_yaxes(title="Points-per-match lift (home vs. away)")
    fig.update_xaxes(title="Edition")
    fig.update_layout(legend_title_text="")
    return themed(fig, "Home advantage — host over/under-performance")


def fig_confed_treemap(ed, picked_confeds):
    """Confederation -> nation finals appearances within the selected range."""
    rows = []
    for _, r in ed.iterrows():
        rows.append((r["champion_confed"], r["champion"], 1))
        rows.append((r["runner_up_confed"], r["runner_up"], 0))
    d = pd.DataFrame(rows, columns=["confed", "nation", "is_title"])
    d = d[d["confed"].isin(picked_confeds)]
    g = d.groupby(["confed", "nation"], as_index=False).agg(
        finals=("nation", "size"), titles=("is_title", "sum"))
    if g.empty:
        fig = go.Figure()
        fig.add_annotation(text="No finalists in this selection",
                           showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
        return themed(fig, "Confederation power — finals reached")
    fig = px.treemap(
        g, path=[px.Constant("All"), "confed", "nation"],
        values="finals", color="titles",
        color_continuous_scale=["#cfe4d8", GREEN, GREEN_DARK],
    )
    fig.update_traces(hovertemplate="<b>%{label}</b><br>%{value} finals<extra></extra>")
    fig.update_layout(coloraxis_colorbar=dict(title="Titles"))
    return themed(fig, "Confederation power — finals reached (size) & titles (colour)")


def fig_host_map(hp):
    """Choropleth of host nations coloured by their performance lift."""
    d = hp.dropna(subset=["ppm_lift"]).copy()
    d["country"] = d["host"].replace(COUNTRY_FIX)
    d = d.groupby("country", as_index=False)["ppm_lift"].mean()
    fig = px.choropleth(
        d, locations="country", locationmode="country names",
        color="ppm_lift", color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0, range_color=[-0.75, 1.65],
    )
    fig.update_geos(showframe=False, showcoastlines=False,
                    projection_type="natural earth", bgcolor=PAPER)
    fig.update_layout(coloraxis_colorbar=dict(title="Lift"))
    fig.update_traces(hovertemplate="<b>%{location}</b><br>Lift: %{z:.2f}<extra></extra>")
    return themed(fig, "Host nations — performance lift when hosting")


# --------------------------------------------------------------------------- #
# 4. APP LAYOUT
# --------------------------------------------------------------------------- #
app = Dash(__name__, title="A Century of the World Cup")
server = app.server  # exposed for gunicorn / Hugging Face

CARD = {"background": PAPER, "borderRadius": "14px", "padding": "14px 16px",
        "boxShadow": "0 1px 3px rgba(15,77,48,0.10)", "border": f"1px solid {GRID}"}


def kpi(idv, label):
    return html.Div([
        html.Div(id=idv, style={"fontSize": "26px", "fontWeight": 700, "color": GREEN_DARK}),
        html.Div(label, style={"fontSize": "12px", "color": "#5b6b63",
                               "textTransform": "uppercase", "letterSpacing": "0.04em"}),
    ], style={**CARD, "flex": 1, "minWidth": "140px"})


def panel(graph_id, flex="1 1 48%"):
    return html.Div(dcc.Graph(id=graph_id, config={"displayModeBar": False},
                              style={"height": "340px"}),
                    style={**CARD, "flex": flex, "minWidth": "320px"})


app.layout = html.Div(style={
    "maxWidth": "1240px", "margin": "0 auto", "padding": "22px",
    "background": "#f4f8f6", "fontFamily": "Inter, Helvetica, Arial, sans-serif"
}, children=[
    html.Div([
        html.H1("A Century of the World Cup",
                style={"margin": 0, "color": GREEN_DARK, "fontSize": "30px"}),
        html.P("How football's biggest tournament changed, 1930-2026. "
               "Drag the slider to cross-filter every chart at once.",
               style={"margin": "4px 0 0", "color": "#5b6b63"}),
    ], style={"marginBottom": "14px"}),

    # KPI row
    html.Div([
        kpi("kpi-editions", "Editions in view"),
        kpi("kpi-goals", "Avg goals / match"),
        kpi("kpi-cards", "Avg cards / match"),
        kpi("kpi-hostwins", "Host titles"),
    ], style={"display": "flex", "gap": "12px", "marginBottom": "14px", "flexWrap": "wrap"}),

    # Controls
    html.Div([
        html.Div([
            html.Label("Year range", style={"fontWeight": 600, "color": INK}),
            dcc.RangeSlider(
                id="year-range", min=YEAR_MIN, max=YEAR_MAX, step=None,
                value=[YEAR_MIN, YEAR_MAX],
                marks={int(y): {"label": f"'{str(y)[2:]}", "style": {"fontSize": "10px"}}
                       for y in YEARS},
                tooltip={"placement": "bottom", "always_visible": False},
                allowCross=False,
            ),
        ], style={"flex": 3, "minWidth": "360px"}),
        html.Div([
            html.Label("Confederations (stars + treemap)",
                       style={"fontWeight": 600, "color": INK}),
            dcc.Dropdown(id="confed-filter", options=[{"label": c, "value": c} for c in CONFEDS],
                         value=CONFEDS, multi=True, clearable=False),
        ], style={"flex": 2, "minWidth": "260px"}),
    ], style={**CARD, "display": "flex", "gap": "20px", "alignItems": "flex-start",
              "marginBottom": "14px", "flexWrap": "wrap"}),

    # Charts
    html.Div(panel("g-line", flex="1 1 100%"), style={"display": "flex", "marginBottom": "12px"}),
    html.Div([panel("g-bar"), panel("g-scatter")],
             style={"display": "flex", "gap": "12px", "marginBottom": "12px", "flexWrap": "wrap"}),
    html.Div([panel("g-treemap"), panel("g-map")],
             style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),

    html.Div("Data: Fjelstul World Cup Database + FIFA 2026 (partial, through QF). "
             "Built with Plotly Dash.",
             style={"marginTop": "16px", "fontSize": "11px", "color": "#8a988f",
                    "textAlign": "center"}),
])


# --------------------------------------------------------------------------- #
# 5. THE SINGLE CROSS-FILTER CALLBACK
#    One control change -> all 5 charts + 4 KPIs recompute together.
# --------------------------------------------------------------------------- #
@app.callback(
    Output("g-line", "figure"), Output("g-bar", "figure"),
    Output("g-scatter", "figure"), Output("g-treemap", "figure"),
    Output("g-map", "figure"),
    Output("kpi-editions", "children"), Output("kpi-goals", "children"),
    Output("kpi-cards", "children"), Output("kpi-hostwins", "children"),
    Input("year-range", "value"), Input("confed-filter", "value"),
)
def update_dashboard(year_range, picked_confeds):
    y0, y1 = year_range
    picked_confeds = picked_confeds or []
    ed = editions[(editions["year"] >= y0) & (editions["year"] <= y1)]
    hp = hosts[(hosts["year"] >= y0) & (hosts["year"] <= y1)]

    # KPIs
    n_ed = len(ed)
    avg_g = ed["goals_per_match"].mean()
    avg_c = ed["cards_per_match"].dropna().mean()
    host_titles = int(hp["won_as_host"].sum())

    return (
        fig_goals_line(ed, picked_confeds),
        fig_cards_bar(ed),
        fig_host_scatter(hp),
        fig_confed_treemap(ed, picked_confeds),
        fig_host_map(hp),
        f"{n_ed}",
        f"{avg_g:.2f}" if pd.notna(avg_g) else "—",
        f"{avg_c:.2f}" if pd.notna(avg_c) else "—",
        f"{host_titles}",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
