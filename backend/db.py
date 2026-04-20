import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"
DEFAULT_EMBED_MODEL = "hashing-v1"


def _city_parts(city: str) -> tuple[str, str]:
    clean_city = (city or "").strip()
    return clean_city, clean_city.lower()


def _clamp_limit(value: int, default: int = 20, min_value: int = 1, max_value: int = 100) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, num))


def _clamp_offset(value: int, default: int = 0) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, num)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            country       TEXT    DEFAULT '',
            city          TEXT    DEFAULT '',
            created_at    TEXT    DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS community_reports (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            city       TEXT    NOT NULL,
            city_key   TEXT    NOT NULL,
            feel_label TEXT    NOT NULL,
            note_text  TEXT    DEFAULT '',
            created_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS community_report_embeddings (
            report_id   INTEGER PRIMARY KEY,
            vector_json TEXT NOT NULL,
            model_name  TEXT NOT NULL DEFAULT 'hashing-v1',
            updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(report_id) REFERENCES community_reports(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_comm_reports_city_created "
        "ON community_reports(city_key, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_comm_reports_created "
        "ON community_reports(created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_comm_embed_model "
        "ON community_report_embeddings(model_name)"
    )
    conn.commit()
    conn.close()


def create_user(name: str, email: str, password_hash: str, country: str = "", city: str = "") -> dict | None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, country, city) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, email, password_hash, country, city),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_community_report(user_id: int, city: str, feel_label: str, note_text: str = "") -> dict | None:
    city_value, city_key = _city_parts(city)
    feel = (feel_label or "").strip().lower()
    note = (note_text or "").strip()
    if not city_value or not feel:
        return None

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO community_reports (user_id, city, city_key, feel_label, note_text) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, city_value, city_key, feel, note),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT r.id, r.user_id, r.city, r.city_key, r.feel_label, r.note_text, r.created_at, u.name AS user_name
        FROM community_reports r
        LEFT JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
        """,
        (cur.lastrowid,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_community_reports(city: str, limit: int = 20, offset: int = 0) -> list[dict]:
    _, city_key = _city_parts(city)
    if not city_key:
        return []
    page_limit = _clamp_limit(limit, default=20, min_value=1, max_value=100)
    page_offset = _clamp_offset(offset, default=0)

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT r.id, r.user_id, r.city, r.city_key, r.feel_label, r.note_text, r.created_at, u.name AS user_name
        FROM community_reports r
        LEFT JOIN users u ON u.id = r.user_id
        WHERE r.city_key = ?
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT ? OFFSET ?
        """,
        (city_key, page_limit, page_offset),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reports_without_embeddings(limit: int = 100) -> list[dict]:
    page_limit = _clamp_limit(limit, default=100, min_value=1, max_value=500)
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT r.id, r.city, r.city_key, r.feel_label, r.note_text, r.created_at
        FROM community_reports r
        LEFT JOIN community_report_embeddings e ON e.report_id = r.id
        WHERE e.report_id IS NULL
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT ?
        """,
        (page_limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def upsert_report_embedding(report_id: int, vector_json: str, model_name: str = DEFAULT_EMBED_MODEL) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO community_report_embeddings (report_id, vector_json, model_name, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(report_id)
        DO UPDATE SET
            vector_json = excluded.vector_json,
            model_name = excluded.model_name,
            updated_at = datetime('now')
        """,
        (report_id, vector_json, model_name),
    )
    conn.commit()
    conn.close()


def list_embedded_reports_by_city(city: str, max_age_days: int = 30, limit: int = 200) -> list[dict]:
    _, city_key = _city_parts(city)
    if not city_key:
        return []
    days = _clamp_limit(max_age_days, default=30, min_value=1, max_value=365)
    page_limit = _clamp_limit(limit, default=200, min_value=1, max_value=500)
    age_param = f"-{days} days"

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            r.id,
            r.city,
            r.city_key,
            r.feel_label,
            r.note_text,
            r.created_at,
            e.vector_json,
            e.model_name
        FROM community_reports r
        JOIN community_report_embeddings e ON e.report_id = r.id
        WHERE r.city_key = ?
          AND r.created_at >= datetime('now', ?)
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT ?
        """,
        (city_key, age_param, page_limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
