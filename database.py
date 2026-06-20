"""
database.py – SQLite integration for Book Recommender System
Tables:
  - books          : full book catalog
  - popular_books  : top-50 curated list
  - search_history : every recommendation query logged
  - book_feedback  : user ratings / comments on books
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bookverse.db")


# ── Connection helper ────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL") # better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn        TEXT,
    title       TEXT NOT NULL,
    author      TEXT,
    year        INTEGER,
    publisher   TEXT,
    image_s     TEXT,
    image_m     TEXT,
    image_l     TEXT
);

CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);

CREATE TABLE IF NOT EXISTS popular_books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    author      TEXT,
    image_url   TEXT,
    num_ratings INTEGER,
    avg_rating  REAL
);

CREATE TABLE IF NOT EXISTS search_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    query        TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    searched_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS book_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_title  TEXT NOT NULL,
    stars       INTEGER CHECK(stars BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
"""


def init_db():
    """Create all tables if they don't exist yet."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
    print(f"[DB] Initialised -> {DB_PATH}")


def is_populated():
    """Return True if the books table already has rows."""
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM popular_books").fetchone()
        return row["n"] > 0


# ── Popular Books ─────────────────────────────────────────────────────────────

def insert_popular_books(rows):
    """rows: list of (title, author, image_url, num_ratings, avg_rating)"""
    with get_db() as conn:
        conn.execute("DELETE FROM popular_books")
        conn.executemany(
            "INSERT INTO popular_books(title,author,image_url,num_ratings,avg_rating)"
            " VALUES(?,?,?,?,?)",
            rows,
        )
    print(f"[DB] Inserted {len(rows)} popular books.")


def get_popular_books():
    with get_db() as conn:
        return conn.execute(
            "SELECT title, author, image_url, num_ratings, avg_rating"
            " FROM popular_books ORDER BY avg_rating DESC"
        ).fetchall()


# ── Full Book Catalog ─────────────────────────────────────────────────────────

def insert_books(rows):
    """rows: list of (isbn, title, author, year, publisher, image_s, image_m, image_l)"""
    with get_db() as conn:
        conn.execute("DELETE FROM books")
        conn.executemany(
            "INSERT INTO books(isbn,title,author,year,publisher,image_s,image_m,image_l)"
            " VALUES(?,?,?,?,?,?,?,?)",
            rows,
        )
    print(f"[DB] Inserted {len(rows)} books into catalog.")


def get_book_by_title(title):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM books WHERE title=? LIMIT 1", (title,)
        ).fetchone()


def search_books(query, limit=20):
    with get_db() as conn:
        return conn.execute(
            "SELECT DISTINCT title, author, image_m FROM books"
            " WHERE title LIKE ? ORDER BY title LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()


# ── Search History ────────────────────────────────────────────────────────────

def log_search(query: str, result_count: int):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO search_history(query, result_count) VALUES(?,?)",
            (query, result_count),
        )


def get_recent_searches(limit=20):
    with get_db() as conn:
        return conn.execute(
            "SELECT query, result_count, searched_at FROM search_history"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


def get_search_stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM search_history").fetchone()["n"]
        top = conn.execute(
            "SELECT query, COUNT(*) AS cnt FROM search_history"
            " GROUP BY LOWER(query) ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        return total, top


# ── Book Feedback ─────────────────────────────────────────────────────────────

def add_feedback(book_title: str, stars: int, comment: str = ""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO book_feedback(book_title,stars,comment) VALUES(?,?,?)",
            (book_title, stars, comment),
        )


def get_feedback_for_book(book_title: str):
    with get_db() as conn:
        return conn.execute(
            "SELECT stars, comment, created_at FROM book_feedback"
            " WHERE book_title=? ORDER BY id DESC",
            (book_title,),
        ).fetchall()


def get_avg_feedback(book_title: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT ROUND(AVG(stars),1) AS avg, COUNT(*) AS cnt"
            " FROM book_feedback WHERE book_title=?",
            (book_title,),
        ).fetchone()
        return row["avg"], row["cnt"]


def get_top_rated_feedback(limit=5):
    with get_db() as conn:
        return conn.execute(
            "SELECT book_title, ROUND(AVG(stars),1) AS avg, COUNT(*) AS cnt"
            " FROM book_feedback GROUP BY book_title"
            " HAVING cnt>=1 ORDER BY avg DESC, cnt DESC LIMIT ?",
            (limit,),
        ).fetchall()
