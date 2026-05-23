# The Butterfly Effect 🦋 : (https://the-butterfly-effect-pink.vercel.app)

A text-based interactive fiction engine where every choice echoes. Built with Flask and a procedural narrative system — no AI or API keys required.

## Overview

**The Butterfly Effect** is a browser-based story game where players type an opening premise and receive procedurally-generated narrative segments with branching choices. Significant moments become "checkpoint butterflies" on the animated home screen — click one to fork reality and explore a different path.

## Features

### Core Engine
- **Procedural Narrative Engine v3** — Stories composed from 600+ atomic fragments with layered systems for sensory details, NPC encounters, dialogue, combat, and exploration. Every playthrough is unique.
- **5 Genre Detection** — Fantasy, sci-fi, horror, mystery, adventure. Auto-detects genre from your opening text.
- **Story Arc System** — Tension naturally rises and falls through setup → rising → climax → falling phases, cycling for long games.
- **Anti-Repetition** — Ring buffer tracks recently used fragments, preventing identical sentences.

### Narrative Depth Systems
- **Recurring Motifs** — Symbolic images (cracked mirrors, distant bells, locked doors, upward-dripping water) recur with escalating intensity across turns, creating unconscious narrative patterns.
- **Emotional Temperature** — Tracks internal emotion (wonder, dread, melancholy, resolve, confusion) that shifts based on player choices. Prose vocabulary adapts accordingly.
- **Foreshadowing** — Plants narrative seeds during rising action, then pays them off during climax beats.
- **NPC Memory Tags** — Each NPC encountered leaves a tag (warning, promise, threat, gift, riddle, silence, prophecy). Future callbacks reference the nature of the encounter.
- **Player Behavior Tracking** — Your pattern of choices (aggressive vs. cautious vs. social) shapes how the world responds. The dominant behavior triggers consequence echoes.
- **Continuity Memory** — Remembers NPCs met, items found, and locations visited, weaving callbacks into later turns.

### Game Mechanics
- **Time-Travel Butterfly** — A purple butterfly occasionally flies across the game screen. Click it to rewind or leap forward.
- **Checkpoint Branching** — Significant moments create checkpoint butterflies. Each can fork a new timeline.
- **Adaptive Pacing** — Paragraph length adjusts by arc phase: long and atmospheric in setup, short and punchy at climax.

### Visual & Audio
- **Canvas Home Screen** — Perlin noise-driven butterfly flight, starfield, interactive ripple effects.
- **Atmospheric Scene Panel** — Animated gradient placeholder with loading spinner. Images download and cache locally from free APIs.
- **Procedural Audio** — Web Audio API ambient tones and reactive sound effects.
- **Responsive Design** — Works on phones, tablets, and desktops.

## Controls

### Home Screen
- **Click the butterfly** → Title reveal and story input
- **Click checkpoint butterflies** → Fork and resume from that moment
- **Click anywhere** → Spawns ripple effects
- **Volume slider** → Controls procedural audio

### Game Screen
- **Click choice buttons** → Send that action
- **Type in footer input** → Custom free-text action
- **SAVE** → Manual checkpoint
- **END GAME** → End and preserve
- **Purple butterfly** (when it appears) → Time-jump

## Setup

### Prerequisites
- Python 3.10+
- pip

### Install & Run
```bash
cd butterfly_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| Flask   | ≥3.0.0  | Web framework, routing, templates |

No AI APIs. No database. No external services.

## Architecture

```
butterfly_app/
├── app.py              # Flask backend — routes, saves, image download+cache
├── story_engine.py     # Narrative engine v3 — motifs, emotion, foreshadowing
├── story_data.py       # Vocabulary pools — 600+ fragments
├── requirements.txt    # Python dependencies (Flask only)
├── templates/
│   ├── index.html      # Home — canvas animation, entry form
│   └── game.html       # Game — story panel, choices, image display
├── saves/              # Game saves (JSON, auto-created)
└── static/
    └── game_images/    # Cached scene images (auto-created)
```

### Story Engine Pipeline

```
Player Input → Intent Parser → Beat Selector → Paragraph Composer → Output
                                    ↑                    ↓
                              Arc Phase          [Action Layer]
                              + Tension          [Beat Layer]
                              + Mood             [Environment Layer]
                              + Emotion          [Continuity Layer]
                                                 [Motif Layer]
                                                 [Foreshadow Layer]
                                                 [Behavior Echo]
                                                 [Emotional Color]
                                                 [Hook Layer]
```

### API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/` | Home screen |
| GET | `/game` | Game screen |
| GET | `/api/checkpoints` | All checkpoints for home butterflies |
| GET | `/api/image-search?q=...` | Scene image (downloads + caches locally) |
| POST | `/api/game/new` | Create new game |
| POST | `/api/game/action` | Send player action |
| POST | `/api/game/end` | End game |
| POST | `/api/game/save-checkpoint` | Manual save |
| POST | `/api/game/time-jump` | Time travel |
| GET | `/api/game/<id>` | Get save data |
| POST | `/api/checkpoint/<id>/load` | Fork from checkpoint |

## Performance

- Canvas uses `globalAlpha` instead of per-element RGBA
- `shadowBlur` removed from trail particles
- Tab visibility detection pauses render loop
- Stars: 120, trails: 24 points
- Typewriter uses RAF for smoother animation
- JSON uses compact separators (no indentation)
- Image cache is lazy-loaded with mtime checking
- Images download to local cache to avoid CORS/redirect issues

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Save not found" | Start a new game. Old saves may have been cleared. |
| No images | First play downloads images (requires internet). Placeholder shown while loading. |
| Audio not working | Click home screen first to initialize Web Audio (browser policy). |
| Choppy animation | Close other tabs. Canvas pauses when hidden. |

## License

MIT
