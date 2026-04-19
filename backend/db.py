import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """users tablosunu oluştur (yoksa)."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            country       TEXT    DEFAULT '',
            city          TEXT    DEFAULT '',
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS condition_reports (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL,
            place_id            TEXT,
            canonical_city      TEXT    NOT NULL,
            latitude            REAL    NOT NULL,
            longitude           REAL    NOT NULL,
            rating              TEXT    NOT NULL,
            note                TEXT,
            temp_c              REAL,
            apparent_temp_c     REAL,
            weather_code         INTEGER,
            precipitation_mm    REAL,
            relative_humidity   REAL,
            wind_speed_10m      REAL,
            snapshot_json       TEXT    NOT NULL,
            created_at          TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def create_user(name: str, email: str, password_hash: str,
                country: str = "", city: str = "") -> dict | None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, country, city) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, email, password_hash, country, city),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_country_city(user_id: int, country: str, city: str) -> dict | None:
    conn = get_conn()
    conn.execute(
        "UPDATE users SET country = ?, city = ? WHERE id = ?",
        (country or "", city or "", user_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_condition_report(
    user_id: int,
    *,
    place_id: str | None,
    canonical_city: str,
    latitude: float,
    longitude: float,
    rating: str,
    note: str | None,
    temp_c: float | None,
    apparent_temp_c: float | None,
    weather_code: int | None,
    precipitation_mm: float | None,
    relative_humidity: float | None,
    wind_speed_10m: float | None,
    snapshot: dict,
) -> dict | None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO condition_reports (
                user_id, place_id, canonical_city, latitude, longitude,
                rating, note, temp_c, apparent_temp_c, weather_code,
                precipitation_mm, relative_humidity, wind_speed_10m,
                snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                place_id,
                canonical_city,
                latitude,
                longitude,
                rating,
                note,
                temp_c,
                apparent_temp_c,
                weather_code,
                precipitation_mm,
                relative_humidity,
                wind_speed_10m,
                json.dumps(snapshot),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, user_id, rating, canonical_city FROM condition_reports "
            "WHERE id = last_insert_rowid()"
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()
