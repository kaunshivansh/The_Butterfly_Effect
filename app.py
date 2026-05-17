"""
The Butterfly Effect — Flask backend.
Procedural story generation, save management, image serving.
"""
import json, re, uuid, hashlib, random, urllib.request, threading
from datetime import datetime, timezone
from pathlib import Path
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory
from story_engine import StoryEngine

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Vercel serverless environment is read-only except for /tmp
if os.environ.get('VERCEL') == '1':
    SAVES_DIR  = Path('/tmp/saves')
    IMAGES_DIR = Path('/tmp/game_images')
else:
    SAVES_DIR  = Path('saves')
    IMAGES_DIR = Path('static/game_images')

SAVES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True, parents=True)

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

@app.route('/api/checkpoints')
def api_checkpoints():
    """Return all checkpoints from all saves (for home screen butterflies)."""
    out = []
    for f in SAVES_DIR.glob('*.json'):
        try:
            data = json.loads(f.read_text())
            for cp in data.get('checkpoints', []):
                if not cp.get('id') or not cp.get('description'):
                    continue
                out.append({
                    'id':         cp['id'],
                    'type':       cp.get('type', 'achievement'),
                    'description':cp['description'],
                    'turn':       cp.get('turn', 0),
                    'timestamp':  cp.get('timestamp', ''),
                    'save_id':    data.get('id', ''),
                    'save_title': data.get('title', 'Unknown Adventure'),
                })
        except Exception:
            pass
    return jsonify(out)

@app.route('/api/image-search')
def api_image_search():
    """Return a scene image URL. Downloads and caches images locally."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'url': None})

    # Check exact match in cache
    fname = hashlib.md5(q.encode()).hexdigest() + '.jpg'
    fpath = IMAGES_DIR / fname
    if fpath.exists():
        return jsonify({'url': f'/game_images/{fname}'})

    # Try downloading from Picsum (aesthetic random backgrounds based on seed)
    seed = hashlib.md5(q.encode()).hexdigest()
    source_url = f'https://picsum.photos/seed/{seed}/800/600'
    if _download_image(source_url, fpath):
        # Invalidate cache so new file is picked up
        global _image_cache_mtime
        _image_cache_mtime = 0
        return jsonify({'url': f'/game_images/{fname}'})

    # Fallback: return a random cached image if any exist
    cached = _get_cached_images()
    if cached:
        return jsonify({'url': f'/game_images/{random.choice(cached)}'})

    # Nothing available — frontend will show atmospheric placeholder
    return jsonify({'url': None})


@app.route('/api/game/new', methods=['POST'])
def api_new_game():
    body = request.json or {}
    opening = body.get('opening', '').strip()
    if not opening:
        return jsonify({'error': 'Opening text is required'}), 400

    try:
        state = StoryEngine.create_state(opening)
        story, scene, choices, checkpoint = StoryEngine.generate_opening(opening, state)
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
        }

        if checkpoint:
            save['checkpoints'].append(_make_cp(checkpoint, 1))

        _write(save)
        return jsonify({
            'save_id': save_id, 'story': story,
            'scene': scene, 'choices': choices,
            'checkpoint': checkpoint,
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
        if 'turn' not in state:
            state['turn'] = save.get('current_turn', 1)

        story, scene, choices, checkpoint, state = StoryEngine.generate(state, action)
        raw = _build_raw(story, scene, choices, checkpoint)

        save['history'].append({'role': 'user', 'content': action})
        save['history'].append({'role': 'assistant', 'content': raw})

        turn = save['current_turn']
        save['current_turn'] = turn + 1
        save['engine_state'] = state

        if checkpoint:
            save['checkpoints'].append(_make_cp(checkpoint, turn))

        _write(save)
        return jsonify({
            'story': story, 'scene': scene, 'choices': choices,
            'checkpoint': checkpoint, 'turn': turn + 1,
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
    turns = body.get('turns', 1)
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
            save['engine_state']['turn'] = save['current_turn']
        _write(save)

        last_story, scene, choices = '', None, []
        if save['history'] and save['history'][-1]['role'] == 'assistant':
            last_story, _, scene, choices = _parse(save['history'][-1]['content'])

        return jsonify({
            'ok': True, 'direction': 'back', 'turns_jumped': turns,
            'new_turn': save['current_turn'],
            'story': last_story, 'scene': scene, 'choices': choices,
        })

    elif direction == 'forward':
        state = save.get('engine_state') or StoryEngine.create_state(save.get('opening', 'an adventure'))
        last_story, scene, choices_out = '', None, []

        for _ in range(turns):
            auto = "Continue exploring and see what happens next."
            history.append({'role': 'user', 'content': auto})
            story, sc, ch, cp, state = StoryEngine.generate(state, auto)
            history.append({'role': 'assistant', 'content': _build_raw(story, sc, ch, cp)})
            last_story, scene, choices_out = story, sc, ch
            save['current_turn'] += 1

        save['history'] = history
        save['engine_state'] = state
        _write(save)

        return jsonify({
            'ok': True, 'direction': 'forward', 'turns_jumped': turns,
            'new_turn': save['current_turn'],
            'story': last_story, 'scene': scene, 'choices': choices_out,
        })

    return jsonify({'error': 'Invalid direction'}), 400


@app.route('/api/game/<save_id>')
def api_get_game(save_id):
    save = _read(save_id)
    if not save:
        return jsonify({'error': 'Not found'}), 404
    # Strip engine_state from response (internal only)
    return jsonify({k: v for k, v in save.items() if k != 'engine_state'})


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
                state['turn'] = turn

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
    if not save_id: return None
    try:
        f = SAVES_DIR / f"{save_id}.json"
        if not f.exists(): return None
        data = json.loads(f.read_text())
        return data if isinstance(data, dict) and 'id' in data else None
    except Exception:
        return None

def _write(data):
    try:
        data['updated_at'] = _now()
        path = SAVES_DIR / f"{data['id']}.json"
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, separators=(',', ':')))
        tmp.replace(path)
    except Exception as e:
        print(f'[_write] {e}')
        try: (SAVES_DIR / f"{data['id']}.json").write_text(json.dumps(data, separators=(',', ':')))
        except Exception: pass

def _now():
    return datetime.now(timezone.utc).isoformat()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 't')
    app.run(debug=debug_mode, port=5000)
