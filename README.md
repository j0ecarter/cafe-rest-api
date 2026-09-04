# Cafe REST API

A JSON API for cafés that are suitable for working. It supports listing, location search, creation, partial updates and deletion using Flask and SQLite.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CAFE_API_KEY=choose-a-key
flask --app cafe_api run
```

Endpoints are `GET /api/cafes`, `GET /api/cafes/search?location=...`, `POST /api/cafes`, `PATCH /api/cafes/{id}` and `DELETE /api/cafes/{id}`. Mutations require `X-API-Key`. Run tests with `pytest`.
