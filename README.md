# TruFitZ

Online clothing store (Flask + SQLite) — "Express your true fit."

## Run
```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:8000
python seed.py         # (optional) reset DB to demo data
```
Demo admin: `admin@trufitz.com` / `admin123` — **change before deploying** (and set `SECRET_KEY`).

## Features
Hero landing page · 7 categories · product grid with search/filter/sort · product page with size + quantity ·
session cart · 4-step checkout (Cart → Details → Payment → Complete) · COD / bKash / Nagad / card (demo, no real payments) ·
register/login · order history · admin order + stock view · responsive, ৳ pricing.

## Layout
`app.py` routes · `seed.py` schema, SVG product art, demo data · `templates/` · `static/css|js|img`
