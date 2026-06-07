from __future__ import annotations

import random
import sqlite3
from pathlib import Path
from typing import Iterable

from scheduler import next_review_iso, utcnow_iso


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_number INTEGER,
            question TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            level INTEGER NOT NULL DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            wrong_count INTEGER NOT NULL DEFAULT 0,
            last_seen_at TEXT,
            next_review_at TEXT,
            PRIMARY KEY (user_id, question_id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );
        """
    )
    conn.commit()


def clear_questions(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM user_progress")
    conn.execute("DELETE FROM questions")
    conn.commit()


def add_question(
    conn: sqlite3.Connection,
    source_number: int,
    question: str,
    correct_answer: str,
    options: Iterable[str],
) -> None:
    unique_options: list[str] = []
    for item in options:
        item = " ".join(str(item).split())
        if item and item not in unique_options:
            unique_options.append(item)

    if correct_answer not in unique_options:
        unique_options.insert(0, correct_answer)

    if len(unique_options) != 4:
        raise ValueError(
            f"Question {source_number} must have exactly 4 unique options, got {len(unique_options)}: {unique_options}"
        )

    conn.execute(
        """
        INSERT INTO questions (
            source_number, question, correct_answer,
            option_a, option_b, option_c, option_d
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source_number, question, correct_answer, *unique_options),
    )
    conn.commit()


def get_stats(conn: sqlite3.Connection, user_id: int) -> dict[str, int]:
    total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    progress = conn.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    mastered = conn.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND level >= 5", (user_id,)
    ).fetchone()[0]
    hard = conn.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND wrong_count > 0 AND level < 5",
        (user_id,),
    ).fetchone()[0]
    due = conn.execute(
        """
        SELECT COUNT(*)
        FROM user_progress
        WHERE user_id = ?
          AND next_review_at IS NOT NULL
          AND next_review_at <= ?
        """,
        (user_id, utcnow_iso()),
    ).fetchone()[0]
    return {
        "total": total,
        "seen": progress,
        "mastered": mastered,
        "hard": hard,
        "due": due,
        "new": max(total - progress, 0),
    }


def get_next_question(conn: sqlite3.Connection, user_id: int, hard_only: bool = False) -> sqlite3.Row | None:
    now = utcnow_iso()

    if hard_only:
        row = conn.execute(
            """
            SELECT q.*
            FROM questions q
            JOIN user_progress p ON p.question_id = q.id
            WHERE p.user_id = ? AND p.wrong_count > 0 AND p.level < 5
            ORDER BY p.level ASC, p.wrong_count DESC, RANDOM()
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return row

    # 1) Prioritize due reviews.
    row = conn.execute(
        """
        SELECT q.*
        FROM questions q
        JOIN user_progress p ON p.question_id = q.id
        WHERE p.user_id = ?
          AND p.next_review_at IS NOT NULL
          AND p.next_review_at <= ?
        ORDER BY p.level ASC, p.wrong_count DESC, RANDOM()
        LIMIT 1
        """,
        (user_id, now),
    ).fetchone()
    if row:
        return row

    # 2) Then give unseen questions.
    row = conn.execute(
        """
        SELECT q.*
        FROM questions q
        LEFT JOIN user_progress p
          ON p.question_id = q.id AND p.user_id = ?
        WHERE p.question_id IS NULL
        ORDER BY RANDOM()
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if row:
        return row

    # 3) If everything is reviewed, choose the weakest known question.
    row = conn.execute(
        """
        SELECT q.*
        FROM questions q
        JOIN user_progress p ON p.question_id = q.id
        WHERE p.user_id = ?
        ORDER BY p.level ASC, p.wrong_count DESC, RANDOM()
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return row


def get_options(row: sqlite3.Row) -> list[str]:
    options = [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
    random.shuffle(options)
    return options


def record_answer(conn: sqlite3.Connection, user_id: int, question_id: int, is_correct: bool) -> None:
    row = conn.execute(
        """
        SELECT level, correct_count, wrong_count
        FROM user_progress
        WHERE user_id = ? AND question_id = ?
        """,
        (user_id, question_id),
    ).fetchone()

    if row is None:
        level = 0
        correct_count = 0
        wrong_count = 0
    else:
        level = int(row["level"])
        correct_count = int(row["correct_count"])
        wrong_count = int(row["wrong_count"])

    new_level, next_review_at = next_review_iso(level, is_correct)
    if is_correct:
        correct_count += 1
    else:
        wrong_count += 1

    conn.execute(
        """
        INSERT INTO user_progress (
            user_id, question_id, level, correct_count, wrong_count, last_seen_at, next_review_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            level = excluded.level,
            correct_count = excluded.correct_count,
            wrong_count = excluded.wrong_count,
            last_seen_at = excluded.last_seen_at,
            next_review_at = excluded.next_review_at
        """,
        (user_id, question_id, new_level, correct_count, wrong_count, utcnow_iso(), next_review_at),
    )
    conn.commit()


def reset_progress(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
    conn.commit()
