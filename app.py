"""
The Butterfly Effect — Flask backend.
Procedural story generation, save management, image serving.
"""
import json, re, uuid, hashlib, random, urllib.request, threading
from datetime import datetime, timezone
from pathlib import Path
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory, render_template_string, session
from story_engine import StoryEngine
from lore_manager import LoreManager

def _is_safe_id(save_id):
    """Validate that save_id is a valid UUIDv4 to prevent path traversal."""
    if not isinstance(save_id, str):
        return False
    return bool(re.match(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$', save_id))


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'butterfly')

# Session cookie security hardening
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV', 'production') != 'development'
)

# Warn if development secrets or default password are used in production
if os.environ.get('FLASK_ENV', 'production') != 'development':
    if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'dev-secret-key-replace-me-in-production':
        print("[WARNING] SECRET_KEY is not configured or using default in production!")
    if ADMIN_PASSWORD == 'butterfly':
        print("[WARNING] ADMIN_PASSWORD is using the default value 'butterfly' in production!")


# Vercel serverless environment is read-only except for /tmp
if os.environ.get('VERCEL') == '1':
    SAVES_DIR  = Path('/tmp/saves')
    IMAGES_DIR = Path('/tmp/game_images')
    LORE_DIR   = Path('/tmp/lore_corpus')
else:
    SAVES_DIR  = Path('saves')
    IMAGES_DIR = Path('static/game_images')
    LORE_DIR   = Path('lore_corpus')

SAVES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True, parents=True)
LORE_DIR.mkdir(exist_ok=True, parents=True)

lore_manager = LoreManager(LORE_DIR)

# In-memory image list cache (refreshed lazily)
_image_cache = None
_image_cache_mtime = 0


def _get_cached_images():
    """Return list of cached image filenames, refreshed when directory changes."""
    global _image_cache, _image_cache_mtime
    try:
        mtime = IMAGES_DIR.stat().st_mtime
    except OSError:
        return []
    if _image_cache is None or mtime != _image_cache_mtime:
        _image_cache = [f.name for f in IMAGES_DIR.iterdir() if f.suffix.lower() in ('.png','.jpg','.jpeg','.webp')]
        _image_cache_mtime = mtime
    return _image_cache

def _download_image(url, filepath, timeout=5):
    """Download image from URL and save to filepath. Returns True on success."""
    import ssl
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Accept': 'image/*',
    })
    # Try default SSL, then unverified (macOS Python often lacks certs)
    for ctx in (None, ssl._create_unverified_context()):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            with resp:
                data = resp.read()
                if len(data) > 1000 and (data[:2] == b'\xff\xd8' or
                                          data[:4] == b'\x89PNG' or
                                          data[:4] == b'RIFF'):
                    filepath.write_bytes(data)
                    return True
            break  # Got response but wasn't an image
        except Exception as e:
            if ctx is not None:  # Both attempts failed
                print(f'[img] download failed: {e}')
            continue
    return False


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/game_images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

# In-memory checkpoints cache
_checkpoints_cache = None

def _update_checkpoints_cache(data):
    """Incrementally update the checkpoints cache when a save is written."""
    global _checkpoints_cache
    if _checkpoints_cache is None:
        return
    save_id = data.get('id')
    save_title = data.get('title', 'Unknown Adventure')
    # Filter out old checkpoints from this save
    _checkpoints_cache = [cp for cp in _checkpoints_cache if cp.get('save_id') != save_id]
    # Add the current checkpoints
    for cp in data.get('checkpoints', []):
        if cp.get('id') and cp.get('description'):
            _checkpoints_cache.append({
                'id':          cp['id'],
                'type':        cp.get('type', 'achievement'),
                'description': cp['description'],
                'turn':        cp.get('turn', 0),
                'timestamp':   cp.get('timestamp', ''),
                'save_id':     save_id,
                'save_title':  save_title,
            })

def _get_checkpoints():
    """Load and return checkpoints, caching the result in memory."""
    global _checkpoints_cache
    if _checkpoints_cache is not None:
        return _checkpoints_cache

    out = []
    for f in SAVES_DIR.glob('*.json'):
        try:
            # Skip invalid save filenames (validate they look like UUIDs)
            if not _is_safe_id(f.stem):
                continue
            data = json.loads(f.read_text())
            save_id = data.get('id', '')
            save_title = data.get('title', 'Unknown Adventure')
            for cp in data.get('checkpoints', []):
                if not cp.get('id') or not cp.get('description'):
                    continue
                out.append({
                    'id':          cp['id'],
                    'type':        cp.get('type', 'achievement'),
                    'description': cp['description'],
                    'turn':        cp.get('turn', 0),
                    'timestamp':   cp.get('timestamp', ''),
                    'save_id':     save_id,
                    'save_title':  save_title,
                })
        except Exception:
            pass
    _checkpoints_cache = out
    return _checkpoints_cache

@app.route('/api/checkpoints')
def api_checkpoints():
    """Return all checkpoints from all saves (for home screen butterflies)."""
    return jsonify(_get_checkpoints())


@app.route('/api/image-search')
def api_image_search():
    """Return a scene image URL. Downloads and caches images locally."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'url': None})
    return jsonify(_image_payload(q))


def _download_image_async(url, filepath):
    """Start background thread to download image, avoiding blocking the main thread."""
    def run():
        if _download_image(url, filepath):
            global _image_cache_mtime
            _image_cache_mtime = 0
    threading.Thread(target=run, daemon=True).start()


def _image_payload(q):
    """Return a cached/downloaded image payload for a full scene query."""
    if not q:
        return {'url': None, 'query': '', 'caption': ''}

    # Check exact match in cache
    fname = hashlib.md5(q.encode()).hexdigest() + '.jpg'
    fpath = IMAGES_DIR / fname
    if fpath.exists():
        return {'url': f'/game_images/{fname}', 'query': q, 'caption': q}

    if app.config.get('TESTING'):
        return {'url': None, 'query': q, 'caption': q}

    # Serve the Picsum URL directly, and start a background download to cache it
    seed = hashlib.md5(q.encode()).hexdigest()
    source_url = f'https://picsum.photos/seed/{seed}/800/600'
    _download_image_async(source_url, fpath)
    return {'url': source_url, 'query': q, 'caption': q}



@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Render the lightweight lore upload console."""
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_ok'] = True
        else:
            error = 'wrong password'

    if not session.get('admin_ok'):
        return render_template_string("""
        <!doctype html><html><head><title>Butterfly Admin</title>
        <style>body{background:#080808;color:#ddd;font-family:Courier New,monospace;padding:40px}
        input,button{background:#111;color:#ddd;border:1px solid #333;padding:8px;font-family:inherit}
        .err{color:#ff6655}</style></head><body>
        <h1>Lore Console</h1>
        <form method="post"><input type="password" name="password" placeholder="password"/>
        <button>enter</button></form><p class="err">{{ error }}</p></body></html>
        """, error=error)

    stats = lore_manager.stats()
    return render_template_string("""
    <!doctype html><html><head><title>Butterfly Admin</title>
    <style>body{background:#080808;color:#ddd;font-family:Courier New,monospace;padding:40px;line-height:1.7}
    input,button{background:#111;color:#ddd;border:1px solid #333;padding:8px;font-family:inherit}
    .box{border:1px solid rgba(255,255,255,.12);padding:18px;max-width:620px}</style></head><body>
    <h1>Lore Console</h1>
    <div class="box">
      <p>{{ stats.documents }} document(s), {{ stats.passages }} passage(s), vector index {{ 'ready' if stats.indexed else 'optional' }}.</p>
      <form action="/admin/upload-lore" method="post" enctype="multipart/form-data">
        <input type="file" name="lore" accept=".txt" required/>
        <button>upload lore</button>
      </form>
    </div>
    </body></html>
    """, stats=stats)


@app.route('/admin/upload-lore', methods=['POST'])
def admin_upload_lore():
    """Accept a .txt lore file and add it to the optional corpus."""
    if not session.get('admin_ok') and request.form.get('password') != ADMIN_PASSWORD:
        return jsonify({'error': 'unauthorized'}), 403
    file = request.files.get('lore')
    if not file or not file.filename.lower().endswith('.txt'):
        return jsonify({'error': 'Upload a .txt file'}), 400
    text = file.read().decode('utf-8', errors='replace')
    info = lore_manager.upload_text(file.filename, text)
    if request.accept_mimetypes.accept_html:
        return admin()
    return jsonify({'ok': True, 'document': info, 'stats': lore_manager.stats()})


@app.route('/api/game/new', methods=['POST'])
def api_new_game():
    body = request.json or {}
    opening = body.get('opening', '').strip()
    if not opening:
        return jsonify({'error': 'Opening text is required'}), 400

    try:
        state = StoryEngine.create_state(opening)
        _apply_lore_bias(state, opening)
        story, scene, choices, checkpoint = StoryEngine.generate_opening(opening, state)
        image_query = StoryEngine.build_image_prompt(state, opening)
        raw = _build_raw(story, scene, choices, checkpoint)

        history = [
            {'role': 'user', 'content': f"My story begins: {opening}"},
            {'role': 'assistant', 'content': raw},
        ]

        save_id = str(uuid.uuid4())
        save = {
            'id':           save_id,
            'title':        opening[:60] + ('…' if len(opening) > 60 else ''),
            'opening':      opening,
            'created_at':   _now(),
            'updated_at':   _now(),
            'ended_at':     None,
            'history':      history,
            'checkpoints':  [],
            'current_turn': 1,
            'engine_state': state,
            'last_scene':    scene,
            'last_image_query': image_query,
        }

        if checkpoint:
            save['checkpoints'].append(_make_cp(checkpoint, 1))

        _write(save)
        return jsonify({
            'save_id': save_id, 'story': story,
            'scene': scene, 'choices': choices,
            'checkpoint': checkpoint,
            'panels': StoryEngine.panel_payload(state),
            'image_query': image_query,
            'image_caption': image_query,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/game/action', methods=['POST'])
def api_action():
    body = request.json or {}
    save_id = body.get('save_id')
    action = body.get('action', '').strip()
    if not action:
        return jsonify({'error': 'Action required'}), 400

    save = _read(save_id)
    if not save:
        return jsonify({'error': 'Save not found'}), 404

    try:
        state = save.get('engine_state') or StoryEngine.create_state(save.get('opening', 'an adventure'))
        state = StoryEngine.ensure_state_defaults(state)
        if 'turn' not in state:
            state['turn'] = save.get('current_turn', 1)

        _apply_lore_bias(state, action)
        story, scene, choices, checkpoint, state = StoryEngine.generate(state, action)
        image_query = StoryEngine.build_image_prompt(state, action)
        raw = _build_raw(story, scene, choices, checkpoint)

        save['history'].append({'role': 'user', 'content': action})
        save['history'].append({'role': 'assistant', 'content': raw})

        turn = save['current_turn']
        save['current_turn'] = turn + 1
        save['engine_state'] = state
        save['last_scene'] = scene
        save['last_image_query'] = image_query

        if checkpoint:
            save['checkpoints'].append(_make_cp(checkpoint, turn))
        elif save['current_turn'] % 3 == 0:
            checkpoint = _auto_checkpoint(save['current_turn'])
            save['checkpoints'].append(_make_cp(checkpoint, save['current_turn']))

        _write(save)
        return jsonify({
            'story': story, 'scene': scene, 'choices': choices,
            'checkpoint': checkpoint, 'turn': turn + 1,
            'panels': StoryEngine.panel_payload(state),
            'image_query': image_query,
            'image_caption': image_query,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/game/end', methods=['POST'])
def api_end_game():
    save_id = (request.json or {}).get('save_id')
    save = _read(save_id)
    if save:
        save['ended_at'] = _now()
        _write(save)
    return jsonify({'ok': True})


@app.route('/api/game/save-checkpoint', methods=['POST'])
def api_save_checkpoint():
    """Create a manual save checkpoint (one per game tree)."""
    save_id = (request.json or {}).get('save_id')
    save = _read(save_id)
    if not save:
        return jsonify({'error': 'Save not found'}), 404

    turn = save.get('current_turn', 1)
    desc = f"Manual save · Turn {turn}"

    # Remove prior manual saves in same game tree
    opening = save.get('opening', '')
    for f in SAVES_DIR.glob('*.json'):
        try:
            other = json.loads(f.read_text())
            if other.get('opening') == opening:
                before = len(other.get('checkpoints', []))
                other['checkpoints'] = [c for c in other.get('checkpoints', []) if c.get('type') != 'manual_save']
                if len(other['checkpoints']) < before:
                    _write(other)
        except Exception:
            pass

    cp = {
        'id':          str(uuid.uuid4()),
        'type':        'manual_save',
        'description': desc,
        'turn':        turn,
        'timestamp':   _now(),
    }

    save = _read(save_id)
    if not save:
        return jsonify({'error': 'Save not found'}), 404
    save.setdefault('checkpoints', []).append(cp)
    _write(save)
    return jsonify({'ok': True, 'checkpoint': {'type': 'manual_save', 'description': desc}})


@app.route('/api/game/time-jump', methods=['POST'])
def api_time_jump():
    """Time-travel: jump forward or backward in the story."""
    body = request.json or {}
    save_id = body.get('save_id')
    direction = body.get('direction', 'back')
    try:
        turns = int(body.get('turns', 1))
    except (ValueError, TypeError):
        turns = 1
    save = _read(save_id)

    if not save:
        return jsonify({'error': 'Save not found'}), 404

    history = save['history']
    current_turn = save.get('current_turn', 1)

    if direction == 'back':
        remove = turns * 2
        if len(history) > remove:
            save['history'] = history[:-remove]
            save['current_turn'] = max(1, current_turn - turns)
            save['checkpoints'] = [c for c in save.get('checkpoints', []) if c.get('turn', 0) <= save['current_turn']]
        else:
            save['history'] = history[:1]
            save['current_turn'] = 1
            save['checkpoints'] = []

        if save.get('engine_state'):
            save['engine_state'] = StoryEngine.ensure_state_defaults(save['engine_state'])
            save['engine_state']['turn'] = save['current_turn']
            save['last_image_query'] = StoryEngine.build_image_prompt(save['engine_state'], 'time jump backward')
        _write(save)

        last_story, scene, choices = '', None, []
        if save['history'] and save['history'][-1]['role'] == 'assistant':
            last_story, _, scene, choices = _parse(save['history'][-1]['content'])

        return jsonify({
            'ok': True, 'direction': 'back', 'turns_jumped': turns,
            'new_turn': save['current_turn'],
            'story': last_story, 'scene': scene, 'choices': choices,
            'panels': StoryEngine.panel_payload(save.get('engine_state') or {}),
            'image_query': save.get('last_image_query'),
        })

    elif direction == 'forward':
        state = save.get('engine_state') or StoryEngine.create_state(save.get('opening', 'an adventure'))
        state = StoryEngine.ensure_state_defaults(state)
        last_story, scene, choices_out = '', None, []

        for _ in range(turns):
            auto = "Continue exploring and see what happens next."
            history.append({'role': 'user', 'content': auto})
            _apply_lore_bias(state, auto)
            story, sc, ch, cp, state = StoryEngine.generate(state, auto)
            history.append({'role': 'assistant', 'content': _build_raw(story, sc, ch, cp)})
            last_story, scene, choices_out = story, sc, ch
            save['current_turn'] += 1

        save['history'] = history
        save['engine_state'] = state
        save['last_scene'] = scene
        save['last_image_query'] = StoryEngine.build_image_prompt(state, auto)
        _write(save)

        return jsonify({
            'ok': True, 'direction': 'forward', 'turns_jumped': turns,
            'new_turn': save['current_turn'],
            'story': last_story, 'scene': scene, 'choices': choices_out,
            'panels': StoryEngine.panel_payload(state),
            'image_query': save.get('last_image_query'),
        })

    return jsonify({'error': 'Invalid direction'}), 400


@app.route('/api/image-regenerate', methods=['POST'])
def api_image_regenerate():
    """Regenerate the current scene image using a fresh contextual query hash."""
    body = request.json or {}
    save = _read(body.get('save_id'))
    if not save:
        return jsonify({'error': 'Save not found'}), 404
    state = StoryEngine.ensure_state_defaults(save.get('engine_state') or StoryEngine.create_state(save.get('opening', 'an adventure')))
    state['image_nonce'] = state.get('image_nonce', 0) + 1
    query = StoryEngine.build_image_prompt(state, 'regenerate scene image') + f" variation {state['image_nonce']}"
    save['engine_state'] = state
    save['last_image_query'] = query
    _write(save)
    payload = _image_payload(query)
    return jsonify(payload)


@app.route('/api/game/<save_id>')
def api_get_game(save_id):
    save = _read(save_id)
    if not save:
        return jsonify({'error': 'Not found'}), 404
    # Strip engine_state from response (internal only)
    out = {k: v for k, v in save.items() if k != 'engine_state'}
    state = StoryEngine.ensure_state_defaults(save.get('engine_state') or StoryEngine.create_state(save.get('opening', 'an adventure')))
    out['panels'] = StoryEngine.panel_payload(state)
    out['image_query'] = save.get('last_image_query') or StoryEngine.build_image_prompt(state, save.get('opening', ''))
    out['image_caption'] = out['image_query']
    return jsonify(out)


@app.route('/api/checkpoint/<checkpoint_id>/load', methods=['POST'])
def api_load_checkpoint(checkpoint_id):
    """Fork a new save from a checkpoint."""
    for f in SAVES_DIR.glob('*.json'):
        try:
            original = json.loads(f.read_text())
            for cp in original.get('checkpoints', []):
                if cp.get('id') != checkpoint_id:
                    continue

                turn = cp.get('turn', 1)
                history = original['history'][:turn * 2] if turn > 0 else original['history']

                last_story = ''
                if history and history[-1].get('role') == 'assistant':
                    last_story, _, _, _ = _parse(history[-1]['content'])

                state = original.get('engine_state') or StoryEngine.create_state(original.get('opening', ''))
                state = StoryEngine.ensure_state_defaults(state)
                state['turn'] = turn
                image_query = StoryEngine.build_image_prompt(state, 'checkpoint fork')

                new_id = str(uuid.uuid4())
                new_save = {
                    'id':           new_id,
                    'title':        f"Fork · {cp.get('description', 'checkpoint')}",
                    'opening':      original.get('opening', ''),
                    'created_at':   _now(),
                    'updated_at':   _now(),
                    'ended_at':     None,
                    'history':      list(history),
                    'checkpoints':  [],
                    'current_turn': turn,
                    'engine_state': state,
                    'forked_from':  checkpoint_id,
                    'last_scene':   state.get('location_desc'),
                    'last_image_query': image_query,
                }
                _write(new_save)
                return jsonify({
                    'save_id': new_id, 'story': last_story,
                    'checkpoint_description': cp.get('description', ''),
                })
        except Exception:
            pass

    return jsonify({'error': 'Checkpoint not found'}), 404


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_lore_bias(state, action):
    """Attach optional lore vocabulary bias to engine state."""
    try:
        stats = lore_manager.stats()
        if stats.get('passages', 0) <= 0:
            state['lore_bias'] = {}
            return
        query = ' '.join([
            state.get('location', ''),
            state.get('location_desc', ''),
            state.get('genre', ''),
            state.get('emotion', ''),
            action or '',
        ])
        state['lore_bias'] = lore_manager.bias_for_query(query)
    except Exception as e:
        print(f'[lore] bias unavailable: {e}')
        state['lore_bias'] = {}

def _auto_checkpoint(turn):
    """Create autosave checkpoint metadata every few turns."""
    return {'type': 'autosave', 'description': f"Auto-save · Turn {turn}"}

def _build_raw(story, scene, choices, checkpoint):
    """Tagged raw string for history storage."""
    parts = [story, '']
    if scene:    parts.append(f'[SCENE]\n{scene}\n[/SCENE]')
    if choices:  parts.append('[CHOICES]\n' + ''.join(f'- {c}\n' for c in choices) + '[/CHOICES]')
    if checkpoint: parts.append(f'[CHECKPOINT]\n{json.dumps(checkpoint)}\n[/CHECKPOINT]')
    return '\n\n'.join(parts)

def _parse(text):
    """Extract (story, checkpoint, scene, choices) from tagged text."""
    if not text or not isinstance(text, str):
        return ('The story continues...', None, None, ['Look around', 'Continue forward', 'Wait and listen'])
    try:
        sm = re.search(r'\[SCENE\](.*?)\[/SCENE\]', text, re.DOTALL)
        cm = re.search(r'\[CHECKPOINT\](.*?)\[/CHECKPOINT\]', text, re.DOTALL)
        ch = re.search(r'\[CHOICES\](.*?)\[/CHOICES\]', text, re.DOTALL)

        cutoff = len(text)
        for m in (sm, cm, ch):
            if m: cutoff = min(cutoff, m.start())
        story = text[:cutoff].strip() or 'The story continues...'
        scene = sm.group(1).strip() if sm else None
        checkpoint = None
        if cm:
            try: checkpoint = json.loads(cm.group(1).strip())
            except Exception: pass
        choices = []
        if ch:
            for line in ch.group(1).strip().split('\n'):
                line = line.strip().lstrip('-•* ').strip()
                if line: choices.append(line)
        return story, checkpoint, scene, choices
    except Exception:
        return ('The story continues...', None, None, [])

def _make_cp(cp_data, turn):
    """Create checkpoint metadata (no history snapshot — saves disk space)."""
    return {
        'id':          str(uuid.uuid4()),
        'type':        cp_data.get('type', 'achievement') if isinstance(cp_data, dict) else 'achievement',
        'description': cp_data.get('description', 'A significant moment') if isinstance(cp_data, dict) else 'A significant moment',
        'turn':        turn,
        'timestamp':   _now(),
    }

def _read(save_id):
    if not _is_safe_id(save_id):
        return None
    try:
        f = SAVES_DIR / f"{save_id}.json"
        if not f.exists(): return None
        data = json.loads(f.read_text())
        return data if isinstance(data, dict) and 'id' in data else None
    except Exception:
        return None

def _write(data):
    if not data or not _is_safe_id(data.get('id')):
        return
    try:
        data['updated_at'] = _now()
        path = SAVES_DIR / f"{data['id']}.json"
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, separators=(',', ':')))
        tmp.replace(path)
        _update_checkpoints_cache(data)
    except Exception as e:
        print(f'[_write] {e}')
        try:
            if _is_safe_id(data.get('id')):
                (SAVES_DIR / f"{data['id']}.json").write_text(json.dumps(data, separators=(',', ':')))
        except Exception: pass


def _now():
    return datetime.now(timezone.utc).isoformat()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 't')
    app.run(debug=debug_mode, port=5000)
