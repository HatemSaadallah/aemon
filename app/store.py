"""The Strategy Lab's storage: one SQLite file for companies, accounts, sessions, history and saved runs.

An account is a member of one or more companies (memberships) and works in one company's workspace at a time; it never
sees a company it is not a member of.

The file is <LEXSI_DATA or ~/.local/share/lexsi>/strategy_lab.db, mode 600, in WAL mode. Sessions are kept here, so a
restart no longer signs people out; only a hash of each session token is stored. The first time a database opens, it
imports the older plain files once (~/.config/lexsi/users.json, or LEXSI_USERS, and chats/<user>/<company>.json) and
leaves them in place.
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from strategy_agent.common.types import Json

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (id TEXT PRIMARY KEY, name TEXT NOT NULL, added REAL NOT NULL);
CREATE TABLE IF NOT EXISTS memberships (user TEXT NOT NULL, company TEXT NOT NULL REFERENCES companies(id), added REAL NOT NULL, PRIMARY KEY (user, company));
CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, salt TEXT NOT NULL, hash TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user TEXT NOT NULL, expiry REAL NOT NULL);
CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, user TEXT NOT NULL, workspace TEXT NOT NULL, question TEXT, case_id TEXT,
    model TEXT, status TEXT, error TEXT, started REAL, ended REAL, summary TEXT, record TEXT, cached_at REAL);
CREATE INDEX IF NOT EXISTS history_owner ON history (user, workspace, started);
CREATE TABLE IF NOT EXISTS run_cache (key TEXT PRIMARY KEY, record TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY, done REAL NOT NULL);
"""
_ready, _lock = set(), threading.RLock()  # re-entrant: the first open of a database runs inside a write


def folder() -> Path:
    return Path(os.environ.get('LEXSI_DATA') or Path.home() / '.local' / 'share' / 'lexsi')


def database() -> Path:
    return folder() / 'strategy_lab.db'


def legacy_users() -> Path:
    return Path(os.environ.get('LEXSI_USERS') or Path.home() / '.config' / 'lexsi' / 'users.json')


def connect() -> sqlite3.Connection:
    path = database()
    new = str(path) not in _ready
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)  # the WAL files beside it hold data too
        except PermissionError:
            pass
        if not path.exists():
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600))
        os.chmod(path, 0o600)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    if new:
        with _lock:
            if str(path) not in _ready:
                db.execute('PRAGMA journal_mode=WAL')
                db.executescript(SCHEMA)
                _migrate(db)
                db.commit()
                _ready.add(str(path))
    return db


def _write(sql: str, args: Sequence[object] = ()) -> int:
    with _lock:
        db = connect()
        try:
            cursor = db.execute(sql, args)
            db.commit()
            return cursor.rowcount
        finally:
            db.close()


def _read(sql: str, args: Sequence[object] = ()) -> list[Any]:
    db = connect()
    try:
        return db.execute(sql, args).fetchall()
    finally:
        db.close()


def _done(db: sqlite3.Connection, name: str) -> bool:
    return db.execute('SELECT 1 FROM migrations WHERE name = ?', (name,)).fetchone() is not None


def _migrate(db: sqlite3.Connection) -> None:
    """Import the plain files once. Rows that already exist are kept, and the files are left where they are."""
    if not _done(db, 'users_json'):
        path = legacy_users()
        for name, entry in (json.loads(path.read_text()) if path.exists() else {}).items():
            db.execute('INSERT OR IGNORE INTO users (name, salt, hash, created) VALUES (?, ?, ?, ?)', (name, entry['salt'], entry['hash'], time.time()))
        db.execute('INSERT INTO migrations VALUES (?, ?)', ('users_json', time.time()))
    if not _done(db, 'chats_json'):
        for file in sorted((folder() / 'chats').glob('*/*.json')):
            for entry in json.loads(file.read_text()):
                _upsert(db, file.parent.name, file.stem, entry['id'], **{k: v for k, v in entry.items() if k != 'id'})
        db.execute('INSERT INTO migrations VALUES (?, ?)', ('chats_json', time.time()))


# Accounts
def user(name: str) -> dict[Any, Any] | None:
    rows = _read('SELECT salt, hash FROM users WHERE name = ?', (name,))
    return dict(rows[0]) if rows else None


def put_user(name: str, salt: str, hashed: str) -> None:
    _write(
        'INSERT INTO users (name, salt, hash, created) VALUES (?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET salt = excluded.salt, hash = excluded.hash',
        (name, salt, hashed, time.time()),
    )


def put_company(identifier: str, name: str) -> None:
    _write('INSERT INTO companies VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name', (identifier, name, time.time()))


def companies() -> list[dict[str, Any]]:
    return [dict(r) for r in _read('SELECT id, name FROM companies ORDER BY id')]


def _known(company: str) -> None:
    if not _read('SELECT 1 FROM companies WHERE id = ?', (company,)):
        raise ValueError(f'no company {company}; known: {", ".join(c["id"] for c in companies())}')


def join(name: str, company: str) -> None:
    _known(company)
    if not user(name):
        raise ValueError(f'no user {name}')
    _write('INSERT OR IGNORE INTO memberships VALUES (?, ?, ?)', (name, company, time.time()))


def leave(name: str, company: str) -> bool:
    return _write('DELETE FROM memberships WHERE user = ? AND company = ?', (name, company)) > 0


def companies_of(name: str) -> list[str]:
    return [r['company'] for r in _read('SELECT company FROM memberships WHERE user = ? ORDER BY added, company', (name,))]


def give_default_membership(default: str) -> int:
    """Accounts that belong to no company yet join the default one, so the demo shows one company."""
    return _write(
        'INSERT INTO memberships SELECT name, ?, ? FROM users WHERE name NOT IN (SELECT user FROM memberships) AND EXISTS (SELECT 1 FROM companies WHERE id = ?)',
        (default, time.time(), default),
    )


def accounts() -> list[dict[str, Any]]:
    return [{'name': r['name'], 'companies': companies_of(r['name'])} for r in _read('SELECT name FROM users ORDER BY name')]


def remove_user(name: str) -> bool:
    _write('DELETE FROM sessions WHERE user = ?', (name,))
    _write('DELETE FROM memberships WHERE user = ?', (name,))
    return _write('DELETE FROM users WHERE name = ?', (name,)) > 0


def user_names() -> list[Any]:
    return [r['name'] for r in _read('SELECT name FROM users ORDER BY name')]


# Sessions: only a hash of the token is stored
def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(token: str, name: str, expiry: float) -> None:
    _write('INSERT INTO sessions VALUES (?, ?, ?)', (_token_hash(token), name, expiry))


def session_user(token: str | None) -> str | None:
    if not token:
        return None
    rows = _read('SELECT user, expiry FROM sessions WHERE token_hash = ?', (_token_hash(token),))
    if not rows:
        return None
    if rows[0]['expiry'] < time.time():
        end_session(token)
        return None
    return rows[0]['user']


def end_session(token: str | None) -> None:
    if token:
        _write('DELETE FROM sessions WHERE token_hash = ?', (_token_hash(token),))


# Chat history: one row per investigation, written when it starts and again when it ends
_COLUMNS = {
    'question': 'question',
    'case': 'case_id',
    'model': 'model',
    'status': 'status',
    'error': 'error',
    'started': 'started',
    'ended': 'ended',
    'summary': 'summary',
    'record': 'record',
    'cached_at': 'cached_at',
}
_JSON = ('summary', 'record')


def _upsert(db: sqlite3.Connection, name: str, workspace: str, identifier: str, **fields: object) -> None:
    values = {_COLUMNS[k]: (json.dumps(v) if k in _JSON and v is not None else v) for k, v in fields.items() if k in _COLUMNS}
    db.execute('INSERT OR IGNORE INTO history (id, user, workspace) VALUES (?, ?, ?)', (identifier, name, workspace))
    if values:
        db.execute(f'UPDATE history SET {", ".join(f"{c} = ?" for c in values)} WHERE id = ?', (*values.values(), identifier))


def record(name: str, workspace: str, identifier: str, **fields: object) -> None:
    with _lock:
        db = connect()
        try:
            _upsert(db, name, workspace, identifier, **fields)
            db.commit()
        finally:
            db.close()


def _entry(row: sqlite3.Row) -> dict[str, Any]:
    out = {
        'id': row['id'],
        'question': row['question'],
        'case': row['case_id'],
        'model': row['model'],
        'status': row['status'],
        'error': row['error'],
        'started': row['started'],
        'ended': row['ended'],
        'cached_at': row['cached_at'],
    }
    for key in _JSON:
        out[key] = json.loads(row[key]) if row[key] else None
    return out


def history(name: str, workspace: str) -> list[dict[str, Any]]:
    return [_entry(r) for r in _read('SELECT * FROM history WHERE user = ? AND workspace = ? ORDER BY COALESCE(started, 0), rowid', (name, workspace))]


# Saved runs: the model runs at temperature 0, so the same case, question, model and code give the same investigation
def cached(key: str) -> tuple[Any, Any] | None:
    rows = _read('SELECT record, created FROM run_cache WHERE key = ?', (key,))
    return (json.loads(rows[0]['record']), rows[0]['created']) if rows else None


def save_run(key: str, run_record: Json) -> None:
    _write('INSERT OR REPLACE INTO run_cache VALUES (?, ?, ?)', (key, json.dumps(run_record), time.time()))
