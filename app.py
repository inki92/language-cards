from __future__ import annotations

import os
from pathlib import Path

import re

from flask import Flask, jsonify, render_template, request, session

from db import Card, connect, get_card_by_id, get_random_card, init_db, insert_cards_dedup


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    db_path_env = os.environ.get("DB_PATH")
    if db_path_env:
        db_path = Path(db_path_env).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "cards.sqlite"

    conn = connect(db_path)
    init_db(conn)
    app.config["DB_CONN"] = conn
    app.config["SESSION_PERMANENT"] = False

    @app.get("/")
    def index():
        return render_template("index.html")

    def _get_history() -> tuple[list[int], int | None]:
        history = session.get("history")
        pos = session.get("pos")
        if not isinstance(history, list) or not all(isinstance(x, int) for x in history):
            history = []
        if not isinstance(pos, int):
            pos = None
        return history, pos

    def _save_history(history: list[int], pos: int) -> None:
        if len(history) > 30:
            history = history[-30:]
            pos = min(pos, len(history) - 1)
        session["history"] = history
        session["pos"] = pos

    def _card_to_json(card: Card):
        return {"id": card.id, "pl": card.pl, "translation": card.translation}

    @app.post("/api/next")
    def api_next():
        history, pos = _get_history()
        current_id = None
        if history and pos is not None and 0 <= pos < len(history):
            current_id = history[pos]
            if pos < len(history) - 1:
                history = history[: pos + 1]

        card = get_random_card(conn, exclude_id=current_id)
        if card is None:
            return jsonify({"error": "no_cards"}), 404

        history.append(card.id)
        pos = len(history) - 1
        _save_history(history, pos)
        return jsonify(_card_to_json(card))

    @app.post("/api/prev")
    def api_prev():
        history, pos = _get_history()
        if not history:
            return jsonify({"error": "no_history"}), 404
        if pos is None:
            pos = len(history) - 1
        if pos <= 0:
            pos = 0
        else:
            pos -= 1

        card = get_card_by_id(conn, history[pos])
        if card is None:
            session.pop("history", None)
            session.pop("pos", None)
            return jsonify({"error": "history_invalid"}), 409

        _save_history(history, pos)
        return jsonify(_card_to_json(card))

    _SEP_RE = re.compile(r"\s*[-–—]\s*", flags=re.UNICODE)

    def _parse_import_text(text: str) -> tuple[list[tuple[str, str]], list[dict]]:
        pairs: list[tuple[str, str]] = []
        errors: list[dict] = []
        for idx, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            m = _SEP_RE.search(line)
            if not m:
                errors.append({"line": idx, "text": raw, "error": "no_separator"})
                continue
            left = line[: m.start()].strip()
            right = line[m.end() :].strip()
            if not left or not right:
                errors.append({"line": idx, "text": raw, "error": "empty_side"})
                continue
            pairs.append((left, right))
        return pairs, errors

    @app.post("/api/import")
    def api_import():
        payload = request.get_json(silent=True) or {}
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return jsonify({"error": "empty"}), 400

        pairs, errors = _parse_import_text(text)
        if not pairs:
            return jsonify({"created": 0, "skipped": 0, "errors": errors}), 200

        created, skipped = insert_cards_dedup(conn, pairs)
        return jsonify({"created": created, "skipped": skipped, "errors": errors}), 200

    return app


app = create_app()

