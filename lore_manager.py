"""Optional local lore corpus manager.

Lore is treated as context, not content. This module indexes uploaded text and
returns conservative signals: weighted terms from relevant passages and a broad
style register. The story engine may use those signals to adjust cadence, but it
must still ground every noun and action in the current scene.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path


STOPWORDS = {
    "the", "and", "that", "with", "from", "into", "over", "under", "were", "was",
    "are", "for", "his", "her", "their", "you", "your", "they", "them", "this",
    "there", "here", "have", "had", "not", "but", "all", "one", "out", "upon",
    "who", "which", "what", "when", "where", "then", "than", "will", "would",
    "could", "should", "been", "being", "because", "before", "after", "through",
    "about", "into", "onto", "only", "also", "very", "more", "most", "much",
}

STYLE_LEXICON = {
    "archaic": {
        "ancient", "oath", "crown", "stone", "road", "king", "hearth", "iron",
        "gate", "tower", "morrow", "elder", "rune", "song", "bloodline",
        "covenant", "herald", "keep", "barrow", "toll", "vigil", "ward",
        "warden", "bygone", "deed",
    },
    "geological": {
        "stone", "granite", "basalt", "slate", "cliff", "mountain", "cairn",
        "ravine", "ore", "crystal", "salt", "limestone", "ash", "mire",
        "fault", "stratum", "sediment", "flint", "chalk", "shale", "bedrock",
    },
    "pastoral": {
        "field", "river", "rain", "reed", "willow", "heather", "mud", "moss",
        "wood", "path", "meadow", "brook", "mist", "root", "leaf", "furrow",
        "harvest", "hedge", "fen", "marsh", "thatch", "grain",
    },
    "political": {
        "soldier", "banner", "border", "faction", "tax", "captain", "court",
        "spy", "bribe", "guild", "warden", "edict", "treaty", "revolt",
        "levy", "conscript", "allegiance", "dispatch", "commission", "rank",
        "jurisdiction",
    },
    "grim": {
        "bone", "grave", "hunger", "rot", "wound", "blood", "ash", "gallows",
        "sickness", "fear", "scar", "cold", "black", "hollow", "dread", "ruin",
        "wreck", "loss", "failure", "debt", "reckoning", "consequence",
    },
    "epic_weight": {
        "fate", "ruin", "tide", "age", "grief", "courage", "horn", "banner",
        "vast", "endless", "desolate", "hollow", "silence", "war", "last",
        "final", "threshold", "edge", "brink", "turning",
    },
    "naturalistic": {
        "wind", "rain", "fire", "moon", "sun", "star", "river", "stone", "tree",
        "hill", "sky", "earth", "dark", "light", "cold", "deep", "season",
        "weather", "water", "root", "shore",
    },
    "mercantile": {
        "price", "coin", "bargain", "trade", "debt", "ledger", "guild", "tariff",
        "merchant", "cargo", "route", "port", "seal", "contract", "margin",
        "surplus", "shortage", "barter", "credit", "interest",
    },
    "military": {
        "rank", "squad", "siege", "march", "retreat", "flank", "supply",
        "command", "scout", "post", "watch", "order", "captain", "fall",
        "formation", "line", "advance", "hold", "breach", "relief",
    },
    "ecclesiastical": {
        "faith", "saint", "relic", "prayer", "vow", "sin", "atonement",
        "heresy", "canon", "pilgrim", "chapel", "altar", "bell", "doctrine",
        "vigil", "absolution", "martyr", "covenant", "scripture", "rite",
    },
    "criminal": {
        "fence", "mark", "heat", "known", "watch", "signal", "stash", "burn",
        "clean", "dirty", "owe", "collect", "muscle", "disappear", "drop",
        "lift", "plant", "front", "cover", "silent",
    },
    "scholarly": {
        "manuscript", "catalogue", "annotate", "thesis", "cipher", "index",
        "archive", "provenance", "attribution", "margin", "notation", "edition",
        "record", "testimony", "evidence", "primary", "source", "date",
    },
    "maritime": {
        "tide", "hull", "keel", "berth", "draft", "ballast", "helm", "bow",
        "stern", "port", "starboard", "watch", "crew", "freight", "manifest",
        "current", "chart", "soundings", "reef", "shoal", "channel",
    },
}

TOLKIEN_TOKENS = {
    "tolkien", "lotr", "jrr", "middle-earth", "fellowship", "mordor", "gondor",
    "shire", "rivendell", "minas", "ered", "rohan",
}


class LoreManager:
    """Store uploaded lore and return scene-safe bias metadata."""

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.docs_dir = self.base_dir / "documents"
        self.meta_path = self.base_dir / "corpus.json"
        self.index_path = self.base_dir / "index.faiss"
        self.embeddings_path = self.base_dir / "embeddings.json"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self._model = None

    def upload_text(self, filename, text):
        """Add a text document to the corpus and refresh search metadata."""
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename or "lore.txt")[:90]
        if not safe_name.endswith(".txt"):
            safe_name += ".txt"

        text = text or ""
        corpus = self._load()
        corpus["documents"][safe_name] = {
            "chars": len(text),
            "passages": 0,
            "style": {},
            "tolkien_active": _looks_tolkien(safe_name, text),
        }
        corpus["passages"] = [p for p in corpus["passages"] if p.get("document") != safe_name]

        passages = self._split_passages(text)
        for idx, passage in enumerate(passages):
            corpus["passages"].append({
                "id": f"{safe_name}:{idx}",
                "document": safe_name,
                "text": passage,
                "tokens": _tokens(passage),
            })

        doc_meta = corpus["documents"][safe_name]
        doc_meta["passages"] = len(passages)
        doc_meta["style"] = _style_profile(_tokens(text))

        (self.docs_dir / safe_name).write_text(text, encoding="utf-8")
        self._save(corpus)
        self._rebuild_optional_vector_index(corpus)
        return doc_meta

    def stats(self):
        """Return current corpus counts and index status."""
        corpus = self._load()
        return {
            "documents": len(corpus["documents"]),
            "passages": len(corpus["passages"]),
            "indexed": self.index_path.exists(),
        }

    def top_passages(self, query, limit=2):
        """Return top matching passages using FAISS when available, otherwise overlap."""
        corpus = self._load()
        passages = corpus.get("passages", [])
        if not passages:
            return []

        faiss_hits = self._search_optional_vector_index(query, passages, limit)
        if faiss_hits is not None:
            return faiss_hits

        q_tokens = set(_tokens(query))
        scored = []
        for passage in passages:
            p_tokens = set(passage.get("tokens", []))
            overlap = len(q_tokens & p_tokens)
            if overlap:
                scored.append((overlap / math.sqrt(max(len(p_tokens), 1)), passage))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return passages[:limit]
        return [passage for _, passage in scored[:limit]]

    def bias_for_query(self, query):
        """Convert retrieved lore into weighted vocabulary and broad style guidance."""
        corpus = self._load()
        if not corpus.get("documents"):
            return self._default_bias()

        passages = self.top_passages(query, limit=3)
        selected_docs = {p.get("document") for p in passages if p.get("document")}
        if not selected_docs:
            selected_docs = set(list(corpus["documents"].keys())[-1:])

        counts = Counter()
        register_scores = Counter()
        tolkien_active = False

        for passage in passages:
            for token in passage.get("tokens", []):
                if token not in STOPWORDS and len(token) > 3:
                    counts[token] += 1
                for register, words in STYLE_LEXICON.items():
                    if token in words:
                        register_scores[register] += 1

        for doc_name in selected_docs:
            doc = corpus["documents"].get(doc_name, {})
            for register, score in doc.get("style", {}).items():
                register_scores[register] += score
            tolkien_active = tolkien_active or bool(doc.get("tolkien_active"))

        dominant = register_scores.most_common(1)[0][0] if register_scores else "pastoral"
        if not counts:
            for term in sorted(STYLE_LEXICON.get(dominant, STYLE_LEXICON["pastoral"]))[:12]:
                counts[term] += 1

        terms = [term for term, _ in counts.most_common(12)]
        moods = [reg for reg, _ in register_scores.most_common(3)] or [dominant]
        return {
            "terms": terms,
            "weights": {term: counts[term] for term in terms},
            "moods": moods,
            "passage_count": len(passages),
            "dominant_register": dominant,
            "tolkien_active": tolkien_active,
        }

    def _split_passages(self, text):
        """Split uploaded lore into compact searchable passages."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
        if not paragraphs and text.strip():
            paragraphs = [text.strip()]

        passages = []
        for paragraph in paragraphs:
            if len(paragraph) <= 700:
                passages.append(paragraph)
                continue
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            chunk = ""
            for sentence in sentences:
                if len(chunk) + len(sentence) > 700 and chunk:
                    passages.append(chunk.strip())
                    chunk = sentence
                else:
                    chunk = (chunk + " " + sentence).strip()
            if chunk:
                passages.append(chunk.strip())
        return passages

    def _load(self):
        """Load corpus metadata from disk."""
        if not self.meta_path.exists():
            return {"documents": {}, "passages": []}
        try:
            data = json.loads(self.meta_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "passages" in data and "documents" in data:
                data.setdefault("documents", {})
                data.setdefault("passages", [])
                return data
        except Exception:
            pass
        return {"documents": {}, "passages": []}

    def _save(self, corpus):
        """Persist corpus metadata to disk."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_model(self):
        """Load the local embedding model when optional dependencies exist."""
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            return self._model
        except Exception:
            self._model = False
            return None

    def _rebuild_optional_vector_index(self, corpus):
        """Build a FAISS index when sentence-transformers and faiss are installed."""
        try:
            import faiss
            import numpy as np
        except Exception:
            return

        model = self._get_model()
        if not model:
            return

        passages = corpus.get("passages", [])
        if not passages:
            return
        texts = [p["text"] for p in passages]
        embeddings = model.encode(texts, normalize_embeddings=True)
        vectors = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(self.index_path))
        self.embeddings_path.write_text(json.dumps([p["id"] for p in passages]), encoding="utf-8")

    def _search_optional_vector_index(self, query, passages, limit):
        """Search a persisted FAISS index when available."""
        if not self.index_path.exists() or not self.embeddings_path.exists():
            return None
        try:
            import faiss
            import numpy as np
        except Exception:
            return None

        model = self._get_model()
        if not model:
            return None
        try:
            ids = json.loads(self.embeddings_path.read_text(encoding="utf-8"))
            by_id = {p["id"]: p for p in passages}
            index = faiss.read_index(str(self.index_path))
            vector = np.asarray(model.encode([query], normalize_embeddings=True), dtype="float32")
            _, indices = index.search(vector, limit)
            hits = []
            for idx in indices[0]:
                if 0 <= idx < len(ids) and ids[idx] in by_id:
                    hits.append(by_id[ids[idx]])
            return hits
        except Exception:
            return None

    def _default_bias(self):
        """Return a complete empty bias payload for callers that expect keys."""
        return {
            "terms": sorted(STYLE_LEXICON["pastoral"])[:12],
            "weights": {},
            "moods": ["pastoral"],
            "passage_count": 0,
            "dominant_register": "pastoral",
            "tolkien_active": False,
        }


def _tokens(text):
    """Tokenize text into lowercase style terms."""
    return [
        token
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", (text or "").lower())
        if token not in STOPWORDS
    ]


def _style_profile(tokens):
    """Score uploaded tokens against style registers."""
    scores = Counter()
    for token in tokens:
        for register, words in STYLE_LEXICON.items():
            if token in words:
                scores[register] += 1
    if not scores:
        scores["pastoral"] = 1
    return dict(scores)


def _looks_tolkien(filename, text):
    """Detect explicit Tolkien-style corpora from file names or signature terms."""
    lower_name = (filename or "").lower()
    lower_text = (text or "").lower()
    if any(token in lower_name for token in ("tolkien", "lotr", "jrr", "middle")):
        return True
    return any(token in lower_text for token in TOLKIEN_TOKENS)
