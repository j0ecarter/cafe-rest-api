import os
import sqlite3
from pathlib import Path

from flask import Flask, current_app, g, jsonify, request

SCHEMA = """
CREATE TABLE IF NOT EXISTS cafes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    has_wifi INTEGER NOT NULL DEFAULT 0,
    has_sockets INTEGER NOT NULL DEFAULT 0,
    coffee_price REAL NOT NULL
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    database = Path(current_app.config["DATABASE"])
    database.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def cafe_dict(row: sqlite3.Row) -> dict:
    # sqlite flags come back as numbers
    return {
        "id": row["id"],
        "name": row["name"],
        "location": row["location"],
        "has_wifi": bool(row["has_wifi"]),
        "has_sockets": bool(row["has_sockets"]),
        "coffee_price": row["coffee_price"],
    }


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("CAFE_DATABASE", str(Path("data/cafes.sqlite"))),
        API_KEY=os.environ.get("CAFE_API_KEY", "demo-key"),
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)

    def valid_key() -> bool:
        return request.headers.get("X-API-Key") == app.config["API_KEY"]

    def require_key():
        if not valid_key():
            return jsonify(error="A valid X-API-Key header is required"), 401
        return None

    @app.get("/api/cafes")
    def list_cafes():
        rows = get_db().execute("SELECT * FROM cafes ORDER BY name").fetchall()
        return jsonify(cafes=[cafe_dict(row) for row in rows])

    @app.get("/api/cafes/search")
    def search_cafes():
        location = request.args.get("location", "").strip()
        if not location:
            return jsonify(error="location query parameter is required"), 400
        rows = get_db().execute(
            "SELECT * FROM cafes WHERE lower(location) LIKE lower(?) ORDER BY name",
            (f"%{location}%",),
        ).fetchall()
        return jsonify(cafes=[cafe_dict(row) for row in rows])

    @app.post("/api/cafes")
    def create_cafe():
        rejected = require_key()
        if rejected:
            return rejected
        data = request.get_json(silent=True) or {}
        missing = [name for name in ("name", "location", "coffee_price") if data.get(name) in (None, "")]
        if missing:
            return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400
        try:
            price = float(data["coffee_price"])
        except (TypeError, ValueError):
            return jsonify(error="coffee_price must be a number"), 400
        db = get_db()
        cursor = db.execute(
            "INSERT INTO cafes (name, location, has_wifi, has_sockets, coffee_price) VALUES (?, ?, ?, ?, ?)",
            (data["name"].strip(), data["location"].strip(), bool(data.get("has_wifi")), bool(data.get("has_sockets")), price),
        )
        db.commit()
        row = db.execute("SELECT * FROM cafes WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(cafe=cafe_dict(row)), 201

    @app.patch("/api/cafes/<int:cafe_id>")
    def update_cafe(cafe_id: int):
        rejected = require_key()
        if rejected:
            return rejected
        db = get_db()
        existing = db.execute("SELECT * FROM cafes WHERE id = ?", (cafe_id,)).fetchone()
        if existing is None:
            return jsonify(error="Cafe not found"), 404
        data = request.get_json(silent=True) or {}
        allowed = {"name", "location", "has_wifi", "has_sockets", "coffee_price"}
        updates = {key: value for key, value in data.items() if key in allowed}
        if not updates:
            return jsonify(error="No supported fields supplied"), 400
        if "coffee_price" in updates:
            try:
                updates["coffee_price"] = float(updates["coffee_price"])
            except (TypeError, ValueError):
                return jsonify(error="coffee_price must be a number"), 400
        for flag in ("has_wifi", "has_sockets"):
            if flag in updates:
                updates[flag] = bool(updates[flag])
        assignments = ", ".join(f"{name} = ?" for name in updates)
        db.execute(f"UPDATE cafes SET {assignments} WHERE id = ?", (*updates.values(), cafe_id))
        db.commit()
        row = db.execute("SELECT * FROM cafes WHERE id = ?", (cafe_id,)).fetchone()
        return jsonify(cafe=cafe_dict(row))

    @app.delete("/api/cafes/<int:cafe_id>")
    def delete_cafe(cafe_id: int):
        rejected = require_key()
        if rejected:
            return rejected
        db = get_db()
        cursor = db.execute("DELETE FROM cafes WHERE id = ?", (cafe_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify(error="Cafe not found"), 404
        return jsonify(message="Cafe deleted")

    with app.app_context():
        init_db()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
