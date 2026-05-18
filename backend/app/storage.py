from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .config_store import DATA_DIR
from .models import LearningNote, TaskSnapshot, TaskStatus, Transcript, VideoNoteRequest


DB_PATH = DATA_DIR / "learning_workbench.sqlite3"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


@contextmanager
def _connection():
    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                video_url TEXT NOT NULL,
                platform TEXT NOT NULL,
                style TEXT NOT NULL,
                stt_provider TEXT,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transcripts (
                task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
                markdown TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def create_task_record(task_id: str, request: VideoNoteRequest) -> None:
    timestamp = _now()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO tasks (id, video_url, platform, style, stt_provider, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                str(request.video_url),
                request.platform,
                request.style,
                request.stt_provider,
                TaskStatus.PENDING.value,
                timestamp,
                timestamp,
            ),
        )


def update_task_status(task_id: str, status: TaskStatus, message: str | None = None) -> None:
    with _connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, message = ?, updated_at = ?
            WHERE id = ?
            """,
            (status.value, message, _now(), task_id),
        )


def save_transcript(task_id: str, transcript: Transcript) -> None:
    payload = json.dumps(transcript.model_dump(), ensure_ascii=False)
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO transcripts (task_id, payload, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET payload = excluded.payload
            """,
            (task_id, payload, _now()),
        )


def load_transcript(task_id: str) -> Transcript | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT payload FROM transcripts WHERE task_id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    return Transcript.model_validate_json(row["payload"])


def save_note(task_id: str, note: LearningNote, markdown: str) -> None:
    payload = json.dumps(note.model_dump(by_alias=True), ensure_ascii=False)
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO notes (task_id, markdown, payload, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET markdown = excluded.markdown, payload = excluded.payload
            """,
            (task_id, markdown, payload, _now()),
        )


def get_task_snapshot(task_id: str) -> TaskSnapshot | None:
    with _connection() as connection:
        task_row = connection.execute(
            """
            SELECT id, platform, style, stt_provider, status, message
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        note_row = connection.execute(
            "SELECT markdown, payload FROM notes WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        transcript_row = connection.execute(
            "SELECT payload FROM transcripts WHERE task_id = ?",
            (task_id,),
        ).fetchone()

    if task_row is None:
        return None

    note = LearningNote.model_validate_json(note_row["payload"]) if note_row else None
    markdown = note_row["markdown"] if note_row else None
    transcript = Transcript.model_validate_json(transcript_row["payload"]) if transcript_row else None
    return TaskSnapshot(
        taskId=task_row["id"],
        status=TaskStatus(task_row["status"]),
        platform=task_row["platform"],
        style=task_row["style"],
        sttProvider=task_row["stt_provider"],
        transcriptSource=transcript.source if transcript else None,
        markdown=markdown,
        note=note,
        message=task_row["message"],
    )
