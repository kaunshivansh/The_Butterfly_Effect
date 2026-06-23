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


class SecurityAndHardeningTest(unittest.TestCase):
    def test_is_safe_id_helper(self):
        from app import _is_safe_id
        valid_uuid = "91cdb1c5-e04e-444f-9bea-237d40c6ea59"
        self.assertTrue(_is_safe_id(valid_uuid))
        self.assertFalse(_is_safe_id("unsafe/path/traversal"))
        self.assertFalse(_is_safe_id("../../etc/passwd"))
        self.assertFalse(_is_safe_id(".."))
        self.assertFalse(_is_safe_id(""))
        self.assertFalse(_is_safe_id(None))

    def test_read_rejects_unsafe_id(self):
        from app import _read
        self.assertIsNone(_read("../../etc/passwd"))
        self.assertIsNone(_read("not-a-uuid"))

    def test_checkpoints_cache_updates_on_write(self):
        import app as app_module
        app_module._checkpoints_cache = []
        dummy_save = {
            'id': "11111111-2222-3333-4444-555555555555",
            'title': "Test Cache Title",
            'checkpoints': [
                {
                    'id': "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    'type': "achievement",
                    'description': "Cached Checkpoint Achievement",
                    'turn': 3,
                    'timestamp': ""
                }
            ]
        }
        app_module._update_checkpoints_cache(dummy_save)
        checkpoints = app_module._get_checkpoints()
        # Find the dummy checkpoint
        found = [cp for cp in checkpoints if cp.get('id') == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['description'], "Cached Checkpoint Achievement")

    def test_api_time_jump_invalid_turns_failsafe(self):
        app.config.update(TESTING=True)
        with app.test_client() as client:
            # First create a valid game to jump in
            new_game = client.post(
                "/api/game/new",
                data=json.dumps({"opening": "A thief enters a dark alley"}),
                content_type="application/json",
            ).get_json()
            
            # Request time-jump with string as turns
            response = client.post(
                "/api/game/time-jump",
                data=json.dumps({
                    "save_id": new_game["save_id"],
                    "direction": "back",
                    "turns": "invalid-string-turns"
                }),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload.get("ok"))
            # Failsafe should fallback to 1 turn jump
            self.assertEqual(payload.get("turns_jumped"), 1)

    def test_overhaul_v4_all_five_sample_premises(self):
        premises = [
            "A fighter walks into a frost-bitten forest looking for his sister.",
            "A disgraced cartographer searches for a vanished city.",
            "A sailor stranded far inland follows rumors of a drowned god.",
            "A spy carrying stolen documents crosses a war-torn border.",
            "A healer searching plague ruins for a cure."
        ]
        
        for premise in premises:
            state = StoryEngine.create_state(premise)
            # Check harvested nouns/adjectives/verbs are stored
            self.assertIn("opening_keywords_harvest", state)
            harvest = state["opening_keywords_harvest"]
            self.assertTrue(harvest.get("nouns"))
            self.assertTrue(harvest.get("adjectives"))
            self.assertTrue(harvest.get("verbs"))
            
            # Check starting location assignment
            location = state["location"]
            desc = state["location_desc"]
            
            # Semantic correlation assertions
            if "forest" in premise:
                self.assertTrue(
                    any(kw in location.lower() or kw in desc.lower()
                        for kw in ["forest", "wood", "grove", "trees", "thicket", "root", "thicket", "leaves"]),
                    f"Forest premise got non-forest location: {location}"
                )
            elif "sailor" in premise:
                self.assertTrue(
                    any(kw in location.lower() or kw in desc.lower()
                        for kw in ["water", "sea", "ocean", "drowned", "sailor", "ship", "boat", "lake", "river", "coast", "salt", "cenote", "tide", "well", "temple"]),
                    f"Sailor premise got non-water location: {location}"
                )
            elif "city" in premise:
                self.assertTrue(
                    any(kw in location.lower() or kw in desc.lower()
                        for kw in ["ruin", "spire", "temple", "cathedral", "tower", "stone", "basalt", "milestone", "statue", "city", "vanished", "monument"]),
                    f"Cartographer premise got non-ruin location: {location}"
                )

    def test_dynamic_prose_composition_incorporates_motifs(self):
        from story_engine import compose_paragraph
        # Test that motifs change with tension
        state = StoryEngine.create_state("A disgraced cartographer searches for a vanished city.")
        state["tension"] = 0.2
        p_low = compose_paragraph(state, "discovery", "explore", "search the ruins")
        
        state["tension"] = 0.9
        p_high = compose_paragraph(state, "discovery", "explore", "search the ruins")
        
        # Under low tension, should contain low-intensity motif text
        # Genre is fantasy. active_motif defaults to distant_bells.
        # distant_bells low: "A faint, brass chime"
        # distant_bells high: "A deafening, rhythmic tolling"
        self.assertIn("brass", p_low.lower())
        self.assertIn("deafening", p_high.lower())

    def test_old_save_hydration_sets_keywords_defaults(self):
        old_state = {
            "genre": "fantasy",
            "location": "sunken grove",
            "location_desc": "submerged forest ruins with bioluminescent moss",
            "turn": 4,
            "opening": "I am a cartographer searching for a vanished city",
        }
        
        hydrated = StoryEngine.ensure_state_defaults(old_state)
        self.assertIn("opening_keywords_harvest", hydrated)
        self.assertIn("opening_keywords", hydrated)
        self.assertIn("city", hydrated["opening_keywords_harvest"]["nouns"])

    def test_fix_1_npc_mid_conversation_continuity(self):
        import story_engine
        orig_pick_beat = story_engine._pick_beat
        try:
            story_engine._pick_beat = lambda *args, **kwargs: 'encounter'
            
            random.seed(42)
            state = StoryEngine.create_state("A fighter walks into a forest looking for his sister.")
            state["character"]["creation"]["in_progress"] = False
            
            # Turn 1: generates an NPC
            _, _, _, _, state = StoryEngine.generate(state, "search the trees")
            npc_turn1 = state['last_npc']
            self.assertIsNotNone(npc_turn1)
            
            # Turn 2: same location, encounter beat is forced. NPC must be identical.
            _, _, _, _, state = StoryEngine.generate(state, "search the trees")
            npc_turn2 = state['last_npc']
            self.assertEqual(npc_turn1, npc_turn2)
            
            # Direct check on the helper when location hasn't changed
            self.assertTrue(story_engine._is_npc_in_scene(state, 'encounter', 'encounter'))
            
            # Now simulate a location change
            state['location'] = 'obsidian spire'
            state['location_desc'] = 'black volcanic glass tower against stormy sky'
            
            # Helper must now return False
            self.assertFalse(story_engine._is_npc_in_scene(state, 'encounter', 'encounter'))
            
            # Run multiple trials with location changes to verify that the NPC is allowed to change
            different_found = False
            for i in range(10):
                st = StoryEngine.create_state("A fighter walks into a forest looking for his sister.")
                st["character"]["creation"]["in_progress"] = False
                _, _, _, _, st = StoryEngine.generate(st, "search the trees")
                st['location'] = f"other location {i}"
                _, _, _, _, st = StoryEngine.generate(st, "search the trees")
                if st['last_npc'] != npc_turn1:
                    different_found = True
                    break
            self.assertTrue(different_found)
        finally:
            story_engine._pick_beat = orig_pick_beat

    def test_fix_2_arc_phase_prose_preferences(self):
        from story_engine import compose_paragraph
        
        phases = {
            'setup': ['reflective', 'sensory_first', 'observational'],
            'rising': ['observational', 'action_first', 'tense'],
            'climax': ['tense', 'action_first'],
            'falling': ['action_first', 'reflective']
        }
        
        state = StoryEngine.create_state("A fighter walks into a forest looking for his sister.")
        state["character"]["creation"]["in_progress"] = False
        
        beats = ['discovery', 'encounter', 'obstacle', 'revelation', 'transition', 'conflict', 'rest']
        
        for phase, preferred in phases.items():
            state['arc_phase'] = phase
            for _ in range(25):
                beat = random.choice(beats)
                compose_paragraph(state, beat, 'explore', 'search the area')
                current_scene = state.get('current_scene')
                self.assertIsNotNone(current_scene)
                fmt = current_scene.get('template_format')
                
                from story_data import PROSE_TEMPLATES
                has_preferred_template = any(t.get('format') in preferred for t in PROSE_TEMPLATES.get(beat, []))
                if has_preferred_template:
                    self.assertIn(fmt, preferred, f"Phase {phase} for beat {beat} produced format {fmt} which is not in {preferred}")

    def test_fix_3_no_random_location_jumps(self):
        import story_engine
        orig_pick_beat = story_engine._pick_beat
        try:
            def dummy_pick_beat(*args, **kwargs):
                beat = orig_pick_beat(*args, **kwargs)
                if beat == 'transition':
                    return 'discovery'
                return beat
            story_engine._pick_beat = dummy_pick_beat
            
            state = StoryEngine.create_state("A fighter walks into a forest looking for his sister.")
            state["character"]["creation"]["in_progress"] = False
            
            initial_location = state['location']
            
            for _ in range(30):
                _, _, _, _, state = StoryEngine.generate(state, "search the area")
                self.assertNotEqual(state['last_beat'], 'transition')
                self.assertEqual(state['location'], initial_location)
        finally:
            story_engine._pick_beat = orig_pick_beat

    def test_fix_4_generalized_premise_grounding(self):
        from story_engine import _generate_choices_premise_aware, _scene_context
        
        premises = [
            "I am a fighter looking for my brother",
            "I am a spy carrying stolen documents",
            "A sailor follows a dark rumor",
            "A scholar seeks his lost mother",
            "An outcast searches for a friend"
        ]
        
        beats = ['encounter', 'discovery', 'revelation']
        
        for premise in premises:
            state = StoryEngine.create_state(premise)
            state["character"]["creation"]["in_progress"] = False
            
            harvest = state["opening_keywords_harvest"]
            self.assertTrue(harvest.get("nouns"))
            
            any_custom_choice_appended = False
            for beat in beats:
                ctx = _scene_context(state, beat=beat, intent='explore', action='')
                initial_choices = ["Study the surroundings", "Wait quietly"]
                choices_copy = list(initial_choices)
                
                res = _generate_choices_premise_aware(state, beat, choices_copy, ctx)
                if len(res) > len(initial_choices):
                    any_custom_choice_appended = True
                    added_choice = res[-1]
                    # Get the expected noun in the premise
                    target_noun = state['opening_keywords_harvest']['nouns'][-1]
                    # Allow singular/plural matching
                    self.assertTrue(
                        target_noun[:4] in added_choice.lower(),
                        f"Added choice '{added_choice}' does not contain expected noun base '{target_noun[:4]}'"
                    )
                    
            self.assertTrue(
                any_custom_choice_appended,
                f"Premise '{premise}' failed to append any custom premise-aware choice."
            )


if __name__ == "__main__":
    unittest.main()
