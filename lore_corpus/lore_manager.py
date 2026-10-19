"""Lore manager for The Butterfly Effect.

Provides premise-aware lore retrieval, on-demand scraping, and narrative enrichment
for the story engine.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "documents"


class LoreManager:
    _cache = {}

    @classmethod
    def load_all_lore_packs(cls) -> dict:
        """Load and cache all available lore packs from lore_corpus/documents/."""
        if cls._cache:
            return cls._cache

        packs = {}
        if DOCS_DIR.exists():
            for f in DOCS_DIR.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    gid = data.get("genre_id", f.stem)
                    packs[gid] = data
                except Exception:
                    pass
        cls._cache = packs
        return cls._cache

    @classmethod
    def detect_lore_pack(cls, text: str) -> dict | None:
        """Match text against lore pack keywords, returning the best matching lore pack."""
        packs = cls.load_all_lore_packs()
        if not text or not packs:
            return None

        text_lower = text.lower()
        best_pack = None
        best_score = 0

        for gid, pack in packs.items():
            keywords = pack.get("keywords", [])
            score = 0
            for kw in keywords:
                pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                if re.search(pattern, text_lower):
                    score += 1
            # Give extra weight to strong role keywords
            if any(text_lower.startswith(f"i am a {kw}") or text_lower.startswith(f"i am an {kw}") for kw in keywords):
                score += 3
            if score > best_score:
                best_score = score
                best_pack = pack

        if best_score >= 1:
            return best_pack
        return None

    @classmethod
    def detect_or_scrape_lore(cls, text: str, role: str = "", setting: str = "") -> dict | None:
        """Detect matching lore pack or dynamically scrape from web sources and add to repository."""
        pack = cls.detect_lore_pack(text)
        if pack:
            return pack

        # Scrape and add to repository on demand
        try:
            from lore_scraper import scrape_and_create_lore_pack
            new_pack = scrape_and_create_lore_pack(premise=text, role=role, setting=setting)
            if new_pack and new_pack.get("genre_id"):
                cls._cache[new_pack["genre_id"]] = new_pack
                return new_pack
        except Exception:
            pass

        return None

    @classmethod
    def get_lore_pack(cls, genre_id: str) -> dict | None:
        """Get a specific lore pack by genre_id."""
        packs = cls.load_all_lore_packs()
        return packs.get(genre_id)

    @classmethod
    def enrich_scene_context(cls, state: dict, ctx: dict) -> dict:
        """Inject genre-specific atmospheric facts, realistic NPCs, and communication modes."""
        opening = state.get("opening", "")
        role = state.get("player_role", "")
        genre = state.get("genre", "")

        lore = cls.detect_or_scrape_lore(f"{opening} {role} {genre}", role=role, setting=ctx.get("location", ""))
        if not lore:
            return ctx

        # Set communication mode and lore-specific properties
        ctx["lore_genre"] = lore.get("genre_id")
        ctx["comm_mode"] = lore.get("communication_mode", "spoken")

        # If lore provides specific environment variants
        env_list = lore.get("environment", [])
        if env_list and not ctx.get("lore_enriched"):
            # Select environment description that matches premise
            ctx["lore_environment"] = env_list[abs(hash(ctx.get("location", ""))) % len(env_list)]

        # If lore provides realistic genre NPCs
        npcs = lore.get("npcs", [])
        if npcs:
            chosen_npc = npcs[abs(hash(ctx.get("location", "") + str(state.get("turn", 0)))) % len(npcs)]
            ctx["genre_npc"] = chosen_npc

        ctx["lore_enriched"] = True
        return ctx
