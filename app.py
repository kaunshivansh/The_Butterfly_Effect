"""The Butterfly Effect — a private, local-first text RPG."""
import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory

from story_engine import StoryEngine
from image_retriever import resolve_scene_image

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    MAX_CONTENT_LENGTH=32 * 1024,
)

_DEFAULT_SAVES = "/tmp/saves" if os.environ.get("VERCEL") else "saves"
SAVES_DIR = Path(os.environ.get("BUTTERFLY_SAVES_DIR", _DEFAULT_SAVES))
try:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    SAVES_DIR = Path("/tmp/saves")
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
MAX_ACTION_LENGTH = 1_000


def _is_safe_id(value):
    """Accept only UUID-shaped identifiers before using a file path."""
    return isinstance(value, str) and bool(re.fullmatch(
        r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}", value
    ))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _access_hash(access_key):
    return hashlib.sha256(access_key.encode("utf-8")).hexdigest()


def _read(save_id):
    if not _is_safe_id(save_id):
        return None
    try:
        path = SAVES_DIR / f"{save_id}.json"
        if not path.exists():
            fallback = Path("saves") / f"{save_id}.json"
            if fallback.exists():
                path = fallback
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("id") == save_id else None
    except (OSError, ValueError, TypeError):
        return None


def _authorized(save):
    supplied = request.headers.get("X-Save-Key", "")
    return bool(save and supplied and hmac.compare_digest(
        save.get("access_key_hash", ""), _access_hash(supplied)
    ))


def _read_authorized(save_id):
    save = _read(save_id)
    if not save:
        return None, (jsonify({"error": "Save not found"}), 404)
    if not _authorized(save):
        return None, (jsonify({"error": "Save key required"}), 403)
    return save, None


def _write(save):
    if not isinstance(save, dict) or not _is_safe_id(save.get("id")):
        raise ValueError("Invalid save")
    save["updated_at"] = _now()
    data = json.dumps(save, ensure_ascii=False, separators=(",", ":"))
    try:
        path = SAVES_DIR / f"{save['id']}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(data, encoding="utf-8")
        temporary.replace(path)
    except OSError:
        tmp_dir = Path("/tmp/saves")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        path = tmp_dir / f"{save['id']}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(data, encoding="utf-8")
        temporary.replace(path)


def _turn(story, scene, choices):
    return {"story": story, "scene": scene, "choices": choices}


def _checkpoint_snapshot(save):
    """Store an exact playable state so a fork cannot inherit future events."""
    return {
        "history": copy.deepcopy(save["history"]),
        "current_turn": save["current_turn"],
        "engine_state": copy.deepcopy(save["engine_state"]),
        "last_turn": copy.deepcopy(save["last_turn"]),
    }


def _public_checkpoint(checkpoint):
    return {key: checkpoint[key] for key in ("id", "type", "description", "turn", "timestamp")}


def _make_checkpoint(save, kind="checkpoint", description=None):
    turn = save["current_turn"]
    checkpoint = {
        "id": str(uuid.uuid4()),
        "type": kind,
        "description": description or f"Turn {turn} · {save['engine_state'].get('location', 'unknown road').title()}",
        "turn": turn,
        "timestamp": _now(),
        "snapshot": _checkpoint_snapshot(save),
    }
    save.setdefault("checkpoints", []).append(checkpoint)
    save["checkpoints"] = save["checkpoints"][-12:]
    return checkpoint


def _build_turn_image(save, nonce_offset=0):
    engine_state = StoryEngine.ensure_state_defaults(save.get("engine_state", {}))
    action = save.get("last_action") or (save.get("history", [])[-2].get("content") if len(save.get("history", [])) >= 2 else None)
    prompt = StoryEngine.build_image_prompt(engine_state, action=action)
    nonce = engine_state.get("image_nonce", 0) + nonce_offset
    turn = save.get("current_turn", 1)
    seed = (abs(hash(prompt + f":{turn}:{nonce}")) % 90000) + 1000
    role = engine_state.get("player_role", "wanderer")
    genre = engine_state.get("genre", "fantasy")
    loc = engine_state.get("location", "")
    image_url, _ = resolve_scene_image(
        prompt=prompt,
        seed=seed,
        role=role,
        genre=genre,
        loc=loc
    )
    return image_url, prompt


def _turn_response(save, turn, access_key=None):
    image_url, image_prompt = _build_turn_image(save)
    response = {
        "save_id": save["id"], "story": turn["story"], "scene": turn["scene"],
        "choices": turn["choices"], "turn": save["current_turn"],
        "panels": _rpg_panels(save["engine_state"]),
        "image_url": image_url,
        "image_prompt": image_prompt,
    }
    if access_key:
        response["access_key"] = access_key
    return response


def _rpg_panels(state):
    """Adapt rich engine state into the compact field-journal interface."""
    state = StoryEngine.ensure_state_defaults(state)
    character = state["character"]
    vitality = character["stats"].get("Vitality", 4)
    inventory = state["inventory"].get("items", [])
    threads = [
        event.get("text", "") for event in state["continuity"].get("narrative_threads", [])[-5:]
        if event.get("text")
    ]
    world = state["world"]
    region = world.get("current_region", "the road")
    return {
        "character": {
            "name": character.get("name", "The traveller"),
            "role": state.get("player_role", "wanderer").title(),
        },
        "condition": "Wounded" if vitality <= 2 else "Steady" if vitality >= 4 else "Strained",
        "inventory": [item.get("name", "Unknown item") for item in inventory],
        "objective": threads[-1] if threads else f"Learn what waits in {state.get('location', 'this place')}.",
        "threads": threads[:-1] if len(threads) > 1 else [],
        "region": region,
        "reputation": world.get("reputation", {}).get(region, "unknown"),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/game")
def game():
    return render_template("game.html")


@app.post("/api/game/new")
def api_new_game():
    opening = str((request.get_json(silent=True) or {}).get("opening", "")).strip()
    if not opening:
        return jsonify({"error": "Write an opening premise first."}), 400
    if len(opening) > MAX_ACTION_LENGTH:
        return jsonify({"error": f"Keep the opening under {MAX_ACTION_LENGTH} characters."}), 400

    state = StoryEngine.create_state(opening)
    story, scene, choices, _ = StoryEngine.generate_opening(opening, state)
    access_key = secrets.token_urlsafe(32)
    first_turn = _turn(story, scene, choices)
    save = {
        "id": str(uuid.uuid4()), "access_key_hash": _access_hash(access_key),
        "title": opening[:80], "opening": opening, "created_at": _now(), "updated_at": _now(),
        "history": [{"role": "player", "content": opening}, {"role": "narrator", **first_turn}],
        "checkpoints": [], "current_turn": 1, "engine_state": state, "last_turn": first_turn,
    }
    _make_checkpoint(save, "opening", "The first page")
    _write(save)
    return jsonify(_turn_response(save, first_turn, access_key))


@app.post("/api/game/action")
def api_action():
    body = request.get_json(silent=True) or {}
    save, error = _read_authorized(body.get("save_id"))
    if error:
        return error
    action = str(body.get("action", "")).strip()
    if not action:
        return jsonify({"error": "Choose an action or write one of your own."}), 400
    if len(action) > MAX_ACTION_LENGTH:
        return jsonify({"error": f"Keep actions under {MAX_ACTION_LENGTH} characters."}), 400

    state = StoryEngine.ensure_state_defaults(save["engine_state"])
    story, scene, choices, _, state = StoryEngine.generate(state, action)
    save["engine_state"] = state
    save["current_turn"] += 1
    current = _turn(story, scene, choices)
    save["last_turn"] = current
    save["history"].extend([{"role": "player", "content": action}, {"role": "narrator", **current}])
    save["last_action"] = action
    if save["current_turn"] % 4 == 0:
        _make_checkpoint(save, "milestone")
    _write(save)
    return jsonify(_turn_response(save, current))


@app.get("/api/game/<save_id>")
def api_get_game(save_id):
    save, error = _read_authorized(save_id)
    if error:
        return error
    last_turn = save["last_turn"]
    image_url, image_prompt = _build_turn_image(save)
    return jsonify({
        "id": save["id"], "title": save["title"], "opening": save["opening"],
        "history": save["history"], "current_turn": save["current_turn"],
        "turn": save["current_turn"], "story": last_turn.get("story", ""),
        "scene": last_turn.get("scene"), "choices": last_turn.get("choices", []),
        "checkpoints": [_public_checkpoint(cp) for cp in save["checkpoints"]],
        "panels": _rpg_panels(save["engine_state"]),
        "image_url": image_url,
        "image_prompt": image_prompt,
    })


@app.post("/api/image-regenerate")
def api_image_regenerate():
    body = request.get_json(silent=True) or {}
    save, error = _read_authorized(body.get("save_id"))
    if error:
        return error
    state = StoryEngine.ensure_state_defaults(save["engine_state"])
    nonce = state.get("image_nonce", 0) + 1
    state["image_nonce"] = nonce
    save["engine_state"] = state
    _write(save)

    image_url, image_prompt = _build_turn_image(save, nonce_offset=nonce)
    return jsonify({
        "ok": True,
        "url": image_url,
        "query": image_prompt,
        "caption": state.get("location_desc", image_prompt),
    })


@app.get("/api/scene-image")
def api_scene_image():
    """Dynamically resolve and cache a scene image."""
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "wanderer")
    genre = request.args.get("genre", "fantasy")
    loc = request.args.get("loc", "")
    seed = int(request.args.get("seed", 42))
    if not q:
        return jsonify({"error": "Missing prompt query"}), 400
    image_url, src = resolve_scene_image(prompt=q, seed=seed, role=role, genre=genre, loc=loc)
    return jsonify({"url": image_url, "source": src})


@app.get("/static/game_images/cache/<path:filename>")
def serve_cached_image(filename):
    from image_retriever import CACHE_DIR, STATIC_DIR
    try:
        if CACHE_DIR.exists() and (CACHE_DIR / filename).is_file():
            return send_from_directory(str(CACHE_DIR), filename)
        local_cache = STATIC_DIR / "game_images" / "cache"
        if local_cache.exists() and (local_cache / filename).is_file():
            return send_from_directory(str(local_cache), filename)
    except OSError:
        pass
    return ("Image not found", 404)


@app.post("/api/game/save-checkpoint")
def api_save_checkpoint():
    body = request.get_json(silent=True) or {}
    save, error = _read_authorized(body.get("save_id"))
    if error:
        return error
    checkpoint = _make_checkpoint(save, "manual", f"Saved at turn {save['current_turn']}")
    _write(save)
    return jsonify({"ok": True, "checkpoint": _public_checkpoint(checkpoint)})


@app.post("/api/checkpoint/<checkpoint_id>/load")
def api_load_checkpoint(checkpoint_id):
    body = request.get_json(silent=True) or {}
    save, error = _read_authorized(body.get("save_id"))
    if error:
        return error
    checkpoint = next((cp for cp in save["checkpoints"] if cp.get("id") == checkpoint_id), None)
    if not checkpoint or not isinstance(checkpoint.get("snapshot"), dict):
        return jsonify({"error": "Checkpoint not found."}), 404

    snapshot = checkpoint["snapshot"]
    access_key = secrets.token_urlsafe(32)
    fork = {
        "id": str(uuid.uuid4()), "access_key_hash": _access_hash(access_key),
        "title": f"Fork · {checkpoint['description']}", "opening": save["opening"],
        "created_at": _now(), "updated_at": _now(), "history": copy.deepcopy(snapshot["history"]),
        "checkpoints": [], "current_turn": snapshot["current_turn"],
        "engine_state": StoryEngine.ensure_state_defaults(copy.deepcopy(snapshot["engine_state"])),
        "last_turn": copy.deepcopy(snapshot["last_turn"]), "forked_from": checkpoint_id,
    }
    _make_checkpoint(fork, "opening", f"Forked from {checkpoint['description']}")
    _write(fork)
    return jsonify(_turn_response(fork, fork["last_turn"], access_key))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true"}, port=port)
