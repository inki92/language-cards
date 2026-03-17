from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Card:
    id: int
    pl: str
    translation: str


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pl TEXT NOT NULL UNIQUE,
  translation TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_cards_created_at ON cards(created_at);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def count_cards(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()
    return int(row["c"])


def get_card_by_id(conn: sqlite3.Connection, card_id: int) -> Card | None:
    row = conn.execute(
        "SELECT id, pl, translation FROM cards WHERE id = ?",
        (card_id,),
    ).fetchone()
    if not row:
        return None
    return Card(id=int(row["id"]), pl=str(row["pl"]), translation=str(row["translation"]))


def get_random_card(conn: sqlite3.Connection, exclude_id: int | None = None) -> Card | None:
    if exclude_id is None:
        row = conn.execute(
            "SELECT id, pl, translation FROM cards ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, pl, translation FROM cards WHERE id != ? ORDER BY RANDOM() LIMIT 1",
            (exclude_id,),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id, pl, translation FROM cards ORDER BY RANDOM() LIMIT 1"
            ).fetchone()

    if not row:
        return None
    return Card(id=int(row["id"]), pl=str(row["pl"]), translation=str(row["translation"]))


def insert_card(conn: sqlite3.Connection, pl: str, translation: str) -> bool:
    try:
        conn.execute(
            "INSERT INTO cards (pl, translation) VALUES (?, ?)",
            (pl, translation),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def insert_cards_dedup(conn: sqlite3.Connection, pairs: Iterable[tuple[str, str]]) -> tuple[int, int]:
    created = 0
    skipped = 0
    cur = conn.cursor()
    try:
        for pl, translation in pairs:
            try:
                cur.execute(
                    "INSERT INTO cards (pl, translation) VALUES (?, ?)",
                    (pl, translation),
                )
                created += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
    finally:
        cur.close()
    return created, skipped

