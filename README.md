# The Butterfly Effect

A private, local-first text RPG. Start with any premise, then play through an original procedural narrative shaped by your actions, character, world state, and consequences.

There are no generated images, audio layers, accounts, uploads, or external AI services. The game is deliberately only about reading, deciding, and discovering what your choices change.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open http://127.0.0.1:5050. Set `PORT=5000` only if that port is free on your machine.

## How it works

- Enter an opening premise, such as “A disgraced cartographer searches for the road that betrayed her.”
- The narrative engine derives a genre, identity, motive, location, regional tensions, character sheet, threads, and possible consequences.
- Choose a suggested action or write your own. Each turn changes the persistent world state.
- Save private checkpoints and fork from any one to explore a different outcome.

## Privacy and saves

Saves are JSON files in `saves/`. Every new story gets a high-entropy private access key, stored only in the game URL and hashed on disk. The server does not expose a global save or checkpoint listing, and a save cannot be read or changed without its key.

This is a local application by design. If you deploy it, use a persistent volume or replace the file-store functions in `app.py` with an authenticated database; serverless temporary filesystems are not appropriate for durable game saves.

## Architecture

```
templates/index.html  →  POST /api/game/new
                              ↓
story_engine.py       →  narrative state + prose + choices
                              ↓
app.py                →  private save + exact checkpoint snapshot
                              ↓
templates/game.html   →  journal UI + player actions
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite covers engine continuity and grounding, capability-key authorization, action flow, and checkpoint fork restoration.

## Configuration

Copy `.env.example` if you want to set a stable `SECRET_KEY`. `BUTTERFLY_SAVES_DIR` may point to another local persistent directory.

## License

MIT
