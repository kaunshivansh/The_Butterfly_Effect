import json
import random
import tempfile
import unittest
from pathlib import Path

from app import app
from story_engine import StoryEngine


class StoryStateSystemsTest(unittest.TestCase):
    def test_opening_parses_player_identity_and_recasts_second_person(self):
        opening = "I am a disgraced cartographer whose maps led an army to its death"
        state = StoryEngine.create_state(opening)

        self.assertEqual(state["player_role"], "cartographer")
        self.assertEqual(state["player_drive"], "atonement")
        self.assertEqual(state["player_voice"], "grim")
        self.assertIn("lives", state["player_wound"])

        story, _, _, _ = StoryEngine.generate_opening(opening, state)
        self.assertIn("You are a disgraced cartographer", story)
        self.assertIn("maps", story.lower())
        self.assertNotIn("connects to the disgraced", story.lower())

    def test_opening_choices_are_scene_grounded_after_identity_premise(self):
        random.seed(2)
        opening = "I am a disgraced cartographer whose maps led an army to its death"
        state = StoryEngine.create_state(opening)

        _, _, choices, _ = StoryEngine.generate_opening(opening, state)

        self.assertFalse(state["character"]["creation"]["in_progress"])
        generic_starts = ("before i left", "i carried", "i survived")
        self.assertTrue(choices)
        for choice in choices:
            lower = choice.lower()
            self.assertFalse(lower.startswith(generic_starts), choices)
            self.assertTrue(
                state["location"].lower() in lower
                or state["world"]["current_region"].lower() in lower
                or state["player_role"].lower() in lower
                or "map" in lower,
                choices,
            )

    def test_opening_choices_are_unique_and_match_player_role_language(self):
        random.seed(2)
        opening = "I am a disgraced cartographer whose maps led an army to its death"
        state = StoryEngine.create_state(opening)

        _, _, choices, _ = StoryEngine.generate_opening(opening, state)

        self.assertEqual(len(choices), len(set(choices)), choices)
        joined = " ".join(choices).lower()
        self.assertNotIn("maps at the cenote until it", joined)
        self.assertNotIn("scholar's patience", joined)

    def test_opening_stays_grounded_in_current_location(self):
        random.seed(42)
        opening = "I am a disgraced cartographer whose maps led an army to its death"
        state = StoryEngine.create_state(opening)

        story, scene, _, _ = StoryEngine.generate_opening(opening, state)

        self.assertIn(state["location"].replace("_", " "), story.lower())
        self.assertIn(scene.split()[0].lower(), story.lower())
        for unsupported_place in ("reed fen", "black pinewood", "ash moor", "market ford"):
            if unsupported_place not in state["location"].lower() and unsupported_place not in scene.lower():
                self.assertNotIn(unsupported_place, story.lower())

    def test_generated_choices_are_supported_by_current_scene_state(self):
        random.seed(5)
        state = StoryEngine.create_state("I am a disgraced cartographer whose maps led an army to its death")
        state["character"]["creation"]["in_progress"] = False

        story, scene, choices, _, state = StoryEngine.generate(state, "study the cracked map by the milestone")

        unsupported = (
            "hidden mechanism",
            "concealed space",
            "deeper pattern",
            "what lies beyond",
            "immediate threat",
            "exposed flank",
            "escape route",
            "the object",
            "gain an advantage",
        )
        joined = " ".join(choices).lower()
        for phrase in unsupported:
            self.assertNotIn(phrase, joined)
        grounding_terms = {
            state["location"].lower(),
            state["world"]["current_region"].lower(),
            state["player_role"].lower(),
            "map",
            "milestone",
        }
        self.assertTrue(
            all(any(term in choice.lower() for term in grounding_terms) for choice in choices),
            choices,
        )

    def test_create_state_includes_new_persistent_systems(self):
        state = StoryEngine.create_state("A scholar follows a red rumour into the old wood")

        self.assertIn("continuity", state)
        self.assertIn("npcs", state["continuity"])
        self.assertIn("world_flags", state["continuity"])
        self.assertIn("narrative_threads", state["continuity"])
        self.assertIn("location_memory", state["continuity"])

        self.assertEqual(state["inventory"]["items"], [])
        self.assertEqual(state["inventory"]["gold"], 0)
        self.assertEqual(
            sorted(state["inventory"]["equipped"]),
            ["accessory", "armour", "weapon"],
        )

        self.assertIn("character", state)
        self.assertIn("stats", state["character"])
        self.assertIn("Vitality", state["character"]["stats"])

        self.assertIn("world", state)
        self.assertGreaterEqual(len(state["world"]["regions"]), 3)
        self.assertLessEqual(len(state["world"]["regions"]), 5)
        self.assertIn(state["world"]["current_region"], state["world"]["reputation"])
        self.assertIn("beat_history", state)
        self.assertIn("consequence_queue", state)
        self.assertIn("location_states", state)
        self.assertIn("faction_dispositions", state)
        self.assertIn("rumour_state", state)

    def test_old_save_state_is_hydrated_without_losing_existing_fields(self):
        old_state = {
            "genre": "fantasy",
            "location": "sunken grove",
            "location_desc": "submerged forest ruins with bioluminescent moss",
            "turn": 4,
            "items_found": ["glass key"],
            "npcs_met": ["the scholar"],
        }

        hydrated = StoryEngine.ensure_state_defaults(old_state)

        self.assertEqual(hydrated["items_found"], ["glass key"])
        self.assertEqual(hydrated["npcs_met"], ["the scholar"])
        self.assertIn("inventory", hydrated)
        self.assertIn("continuity", hydrated)
        self.assertIn("world", hydrated)
        self.assertEqual(hydrated["turn"], 4)

    def test_salience_sequencer_tracks_caps_and_periodic_pivots(self):
        random.seed(7)
        state = StoryEngine.create_state("A deserter follows the old road toward a red border")
        state["character"]["creation"]["in_progress"] = False

        for idx in range(14):
            action = "search the road" if idx % 3 else "confront the patrol"
            _, _, _, _, state = StoryEngine.generate(state, action)

        history = state["beat_history"]
        self.assertGreaterEqual(len(history), 10)
        self.assertTrue(all(a != b for a, b in zip(history, history[1:])))
        for start in range(0, len(history) - 4):
            window = history[start:start + 5]
            self.assertLessEqual(window.count("discovery"), 2)
            self.assertLessEqual(window.count("conflict"), 2)
        self.assertGreaterEqual(len(state["pivots_applied"]), 2)
        self.assertTrue(any(flag for flag in state["continuity"]["world_flags"]["factions_influenced"].values()))

    def test_consequence_queue_records_witnesses_and_surfaces_due_events(self):
        random.seed(11)
        state = StoryEngine.create_state("A mercenary with a debt reaches the salt ford")
        state["character"]["creation"]["in_progress"] = False

        _, _, _, _, state = StoryEngine.generate(state, "attack the toll scout and take the gate")
        queued = state["consequence_queue"]
        self.assertTrue(queued)
        self.assertIn("witnessed_by", queued[-1])
        self.assertIn("heard_by", queued[-1])

        due_turn = queued[-1]["due_turn"]
        while state["turn"] < due_turn + 1:
            _, _, _, _, state = StoryEngine.generate(state, "keep moving carefully")

        self.assertTrue(state["surfaced_consequences"])
        self.assertIn("source_turn", state["surfaced_consequences"][-1])

    def test_npc_registry_preserves_motives_and_player_memory(self):
        random.seed(19)
        state = StoryEngine.create_state("A healer searches for the witness who vanished")
        state["character"]["creation"]["in_progress"] = False

        for _ in range(16):
            _, _, _, _, state = StoryEngine.generate(state, "ask the stranger what they know")
            if state["continuity"]["npcs"]:
                break

        self.assertTrue(state["continuity"]["npcs"])
        npc = next(iter(state["continuity"]["npcs"].values()))
        for key in ("archetype", "secret", "want", "loyalty", "tic", "knowledge_of_player"):
            self.assertIn(key, npc)
        self.assertTrue(npc["knowledge_of_player"])

    def test_identity_premise_derives_character_sheet_without_extra_creation_loop(self):
        state = StoryEngine.create_state("I am a scholar carrying a debt to an old archive")
        story, _, choices, _ = StoryEngine.generate_opening(state["opening"], state)

        self.assertFalse(state["character"]["creation"]["in_progress"])
        self.assertEqual(state["character"]["origin"], "scholar")
        self.assertGreaterEqual(state["character"]["stats"]["Lore"], 4)
        self.assertIn("You are a scholar", story)
        self.assertTrue(choices)
        self.assertFalse(any(choice.lower().startswith("before i left") for choice in choices))

    def test_inventory_use_and_panel_payload_are_textual(self):
        state = StoryEngine.create_state("A fighter opens a chest beneath a drowned chapel")
        state = StoryEngine.ensure_state_defaults(state)
        state["character"]["creation"]["in_progress"] = False
        item = StoryEngine.create_item(state, item_type="weapon", name="Mireth's Blade")
        state["inventory"]["items"].append(item)
        state["inventory"]["equipped"]["weapon"] = item["name"]

        story, _, _, _, state = StoryEngine.generate(state, "use Mireth's Blade against the door")
        panel = StoryEngine.panel_payload(state)

        self.assertIn("Mireth's Blade", story)
        self.assertIn("Mireth's Blade", panel["inventory"])
        self.assertIn("You", panel["character"])
        self.assertIn("region", panel["journal"].lower())

    def test_lore_bias_cannot_introduce_unsupported_scene_nouns(self):
        from story_engine import _lore_bias_sentence

        state = StoryEngine.create_state("I am a cartographer trying to repair a fatal map")
        state["character"]["creation"]["in_progress"] = False
        state["lore_bias"] = {
            "terms": ["dragon", "starship", "mordor"],
            "moods": ["epic_weight"],
            "dominant_register": "epic_weight",
            "phrase_patterns": [],
            "compound_adjectives": [],
            "tolkien_active": False,
        }

        random.seed(1)
        line = _lore_bias_sentence(state)

        self.assertNotIn("dragon", line.lower())
        self.assertNotIn("starship", line.lower())
        self.assertNotIn("mordor", line.lower())
        self.assertTrue(
            state["location"].lower() in line.lower()
            or state["world"]["current_region"].lower() in line.lower()
            or state["player_role"].lower() in line.lower()
            or "map" in line.lower(),
            line,
        )


class LoreManagerTest(unittest.TestCase):
    def test_lore_manager_uploads_text_and_returns_bias_without_optional_dependencies(self):
        from lore_manager import LoreManager

        with tempfile.TemporaryDirectory() as td:
            manager = LoreManager(Path(td))
            manager.upload_text("stone.txt", "Ancient stone roads crossed the rain-dark borderlands.")
            stats = manager.stats()
            bias = manager.bias_for_query("rain over an ancient road")

        self.assertEqual(stats["documents"], 1)
        self.assertGreater(stats["passages"], 0)
        self.assertIn("terms", bias)
        self.assertIn("stone", bias["terms"])

    def test_lore_manager_returns_style_bias_without_phrase_templates(self):
        from lore_manager import LoreManager

        lore = (
            "Mireth, who carried the rain-dark banner, crossed Minasvale at dusk. "
            "The road was not mercy, but calculation. "
            "Stone-still wardens held the salt-worn gate."
        )
        with tempfile.TemporaryDirectory() as td:
            manager = LoreManager(Path(td))
            manager.upload_text("tolkien_lotr_notes.txt", lore)
            bias = manager.bias_for_query("rain road banner")

        self.assertTrue(bias["tolkien_active"])
        self.assertIn("dominant_register", bias)
        self.assertIn("terms", bias)
        self.assertNotIn("phrase_patterns", bias)
        self.assertNotIn("compound_adjectives", bias)
        self.assertNotIn("place_morphemes", bias)


class FlaskNewRouteTest(unittest.TestCase):
    def test_new_game_and_image_regenerate_return_extended_fields(self):
        app.config.update(TESTING=True)
        with app.test_client() as client:
            response = client.post(
                "/api/game/new",
                data=json.dumps({"opening": "A fighter walks into a frost-bitten forest"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIn("panels", payload)
            self.assertIn("image_query", payload)

            regen = client.post(
                "/api/image-regenerate",
                data=json.dumps({"save_id": payload["save_id"]}),
                content_type="application/json",
            )
            self.assertEqual(regen.status_code, 200)
            regen_payload = regen.get_json()
            self.assertIn("caption", regen_payload)
            self.assertIn("query", regen_payload)


if __name__ == "__main__":
    unittest.main()
