# A Century of the World Cup (1930-2026)

An interactive dashboard built with **Plotly Dash** that tells one story across
five linked visualizations: how the FIFA World Cup has changed over nearly a
century — in scoring, discipline, home advantage, and the balance of power
between confederations.

A single **year-range slider** cross-filters every chart and KPI at once; a
**confederation filter** highlights champions on the timeline and reshapes the
treemap.

## Visualizations

| # | Chart | Question it answers |
|---|-------|---------------------|
| 1 | Line — goals per match | Has the World Cup become higher or lower scoring? |
| 2 | Bar — cards per match (1970-) | How has on-field discipline changed? |
| 3 | Scatter — host performance lift | Do host nations overperform at home? |
| 4 | Treemap — confederation → nation finals | Which confederations dominate? |
| 5 | Choropleth map — host lift by country | Where does home advantage show up? |

## Run it locally

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:7860
```

## Data

CSV files in `data/`, derived from the Fjelstul World Cup Database (1930-2022,
CC-BY-SA 4.0) plus a partial 2026 layer (through the quarter-finals). The 2026
edition is flagged partial and carries no card data yet.

## Deploy (Hugging Face Spaces, free public URL)

1. Create a new **Space** at huggingface.co → **SDK: Docker** → **Blank**.
2. In the Space's own `README.md`, set the app port by adding this frontmatter
   at the very top:

   ```yaml
   ---
   title: A Century of the World Cup
   sdk: docker
   app_port: 7860
   ---
   ```
3. Upload every file from this repo (or link the Space to your GitHub repo).
   The included `Dockerfile` builds and serves the app automatically.
4. Wait for the build; your public URL is
   `https://huggingface.co/spaces/<username>/<space-name>`.

**Alternative — Render:** New → Web Service → connect repo → Build
`pip install -r requirements.txt`, Start `gunicorn app:server`.

## Files

```
app.py             the dashboard (data load, 5 chart builders, cross-filter callback)
requirements.txt   dependencies
Dockerfile         container for Hugging Face Spaces
notebook.ipynb     tutorial write-up (visualization technique, library, demonstration)
data/              six source CSVs
```
