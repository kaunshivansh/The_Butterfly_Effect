"""Grounded narrative engine for The Butterfly Effect RPG.

The engine keeps every beat tied to the player premise, current location,
present NPCs, inventory, faction pressure, and remembered consequences. Random
selection is used for pacing and variety, not for introducing unsupported nouns
or ornamental prose.
"""
import random, re
from story_data import *
from lore_corpus.lore_manager import LoreManager

# ── Narrative Architecture Classes ───────────────────────────────────────────

class EntityGraph:
    """Manages relationships, secrets, and debts between NPCs, Factions, and the Player."""
    def __init__(self, state):
        self.state = state
        self.graph = state.setdefault('entity_graph', {'nodes': {}, 'edges': []})
        
    def add_node(self, node_id, node_type, properties=None):
        if node_id not in self.graph['nodes']:
            self.graph['nodes'][node_id] = {'type': node_type, 'properties': properties or {}}
            
    def add_edge(self, source, target, edge_type, weight=1, metadata=None):
        edge = {'source': source, 'target': target, 'type': edge_type, 'weight': weight, 'metadata': metadata or {}}
        self.graph['edges'].append(edge)
        
    def get_edges(self, source=None, target=None, edge_type=None):
        results = []
        for edge in self.graph['edges']:
            if source and edge['source'] != source: continue
            if target and edge['target'] != target: continue
            if edge_type and edge['type'] != edge_type: continue
            results.append(edge)
        return results

class ActiveThreads:
    """Manages the lifecycle of ongoing plot threads and objectives."""
    def __init__(self, state):
        self.state = state
        self.threads = state.setdefault('active_threads', [])
        
    def add_thread(self, thread_id, description, priority=1, related_entities=None):
        # Prevent duplicates
        for t in self.threads:
            if t['id'] == thread_id:
                return
        self.threads.append({
            'id': thread_id,
            'description': description,
            'priority': priority,
            'related_entities': related_entities or [],
            'progress': 0,
            'status': 'active'
        })
        self.threads.sort(key=lambda x: x['priority'], reverse=True)
        
    def get_top_thread(self):
        active = [t for t in self.threads if t['status'] == 'active']
        return active[0] if active else None

class SceneCard:
    """Represents the current scene card: objective, obstacle, cast, and setting."""
    def __init__(self, state):
        self.state = state
        self.data = state.setdefault('scene_card', {
            'objective': 'Explore and understand the surroundings',
            'obstacle': 'None',
            'cast': [],
            'setting': ''
        })

    @property
    def objective(self):
        return self.data.setdefault('objective', 'Explore and understand the surroundings')

    @objective.setter
    def objective(self, value):
        self.data['objective'] = value

    @property
    def obstacle(self):
        return self.data.setdefault('obstacle', 'None')

    @obstacle.setter
    def obstacle(self, value):
        self.data['obstacle'] = value

    @property
    def cast(self):
        return self.data.setdefault('cast', [])

    @cast.setter
    def cast(self, value):
        self.data['cast'] = value

    @property
    def setting(self):
        return self.data.setdefault('setting', '')

    @setting.setter
    def setting(self, value):
        self.data['setting'] = value

class MemoryGraph:
    """Tracks historical events categorized by impact, visits, etc."""
    def __init__(self, state):
        self.state = state
        self.memory = state.setdefault('memory_graph', {'events': [], 'visits': {}})

    def record_visit(self, location):
        visits = self.memory.setdefault('visits', {})
        visits[location] = visits.get(location, 0) + 1

    def get_visits(self, location):
        return self.memory.setdefault('visits', {}).get(location, 0)

    def add_event(self, event_type, location, description, impact=1):
        self.memory.setdefault('events', []).append({
            'type': event_type,
            'location': location,
            'description': description,
            'impact': impact,
            'turn': self.state.get('turn', 0)
        })
        if len(self.memory['events']) > 30:
            self.memory['events'] = self.memory['events'][-30:]

class ConsequenceGraph:
    """Manages forward-looking triggers, delayed consequences, and persistent world memory (debts, rumors, grudges)."""
    def __init__(self, state, entity_graph):
        self.state = state
        self.entities = entity_graph
        self.queue = state.setdefault('consequence_queue', [])
        self.rumors = state.setdefault('rumour_state', {})
        self.graph = state.setdefault('consequence_graph', {'triggers': []})

    def add_trigger(self, trigger_type, condition, mutation, due_turn, metadata=None):
        self.graph.setdefault('triggers', []).append({
            'type': trigger_type,
            'condition': condition,
            'mutation': mutation,
            'due_turn': due_turn,
            'metadata': metadata or {}
        })

    def check_and_fire(self):
        turn = self.state.get('turn', 0)
        loc = self.state.get('location', '')
        triggers = self.graph.setdefault('triggers', [])
        fired = []
        remaining = []
        for t in triggers:
            should_fire = False
            cond = t.get('condition')
            if cond == 'turn_elapsed' and turn >= t.get('due_turn', 0):
                should_fire = True
            elif cond == 'location_match' and loc == t.get('metadata', {}).get('location') and turn >= t.get('due_turn', 0):
                should_fire = True
            
            if should_fire:
                fired.append(t)
            else:
                remaining.append(t)
        self.graph['triggers'] = remaining
        return fired

    def add_debt(self, entity_id, severity, context):
        self.entities.add_edge('player', entity_id, 'debt', weight=severity, metadata={'context': context})
        self.spread_rumor(f"A debt is owed over {context}", severity)
        
    def add_grudge(self, faction_id, severity, context):
        self.entities.add_edge('player', faction_id, 'grudge', weight=severity, metadata={'context': context})
        self.spread_rumor(f"The {faction_id} do not forgive what happened regarding {context}", severity)
        
    def spread_rumor(self, text, spread_speed):
        rumor_id = f"rumor_{len(self.rumors)}"
        self.rumors[rumor_id] = {'text': text, 'spread': spread_speed, 'turn_created': self.state.get('turn', 0)}

class NarrativeState:
    """Wrapper around the flat state dict to provide structured access to advanced narrative systems."""
    def __init__(self, state):
        self.state = state
        self.entities = EntityGraph(state)
        self.threads = ActiveThreads(state)
        self.scene_card = SceneCard(state)
        self.memory = MemoryGraph(state)
        self.consequences = ConsequenceGraph(state, self.entities)

    @property
    def chapter_state(self):
        return self.state.get('arc_phase', 'setup')

    @property
    def tension(self):
        return self.state.get('tension', 0.5)

    @property
    def genre(self):
        return self.state.get('genre', 'fantasy')

    @property
    def premise(self):
        return self.state.get('opening', '')

    @property
    def wound(self):
        return self.state.get('player_wound', '')

    @property
    def drive(self):
        return self.state.get('player_drive', '')

class StyleState:
    """Evaluates narrative tension and phase to dictate prose pacing and structure."""
    def __init__(self, state):
        self.state = state
        self.ns = NarrativeState(state)
        self.tension = self.ns.tension
        self.phase = self.ns.chapter_state
        
    def compose(self, components):
        """Modularly assemble sentence components based on the current style state."""
        revisit_note = components.get('revisit_note')
        intro = components.get('intro', '')
        body = components.get('body', '')
        beat_text = components.get('beat_text', '')
        hook = components.get('hook', '')
        
        # 1. Emotional pacing/filtering based on tension
        if self.tension > 0.75:
            intro = self._shorten(intro)
            body = self._shorten(body) if random.random() < 0.3 else ''
            beat_text = self._shorten(beat_text)
            hook = self._shorten(hook)
        elif self.tension < 0.4:
            pass

        # 2. Inject Subtext from Entity Graph & Scene Card
        subtext_lines = []
        loc = self.state.get('location', '')
        faction = self.state.get('world', {}).get('current_region_faction', 'locals')
        grudges = self.ns.entities.get_edges(source='player', target=faction, edge_type='grudge')
        if grudges:
            subtext_lines.append(f"A cold threat from the {faction} hangs over the area.")

        last_npc = self.state.get('last_npc')
        if last_npc and self.state.get('last_beat') == 'encounter':
            debts = self.ns.entities.get_edges(source='player', target=last_npc, edge_type='debt')
            if debts:
                subtext_lines.append(f"{last_npc} watches you with calculated expectation, remembering what is owed.")
            
            npcs = self.state.get('continuity', {}).get('npcs', {})
            if last_npc in npcs:
                secret = npcs[last_npc].get('secret')
                if secret and random.random() < 0.5:
                    subtext_lines.append(f"There is a guarded silence in {last_npc.split(',')[0]}'s posture.")

        # Assemble sentences
        sentences = []
        if intro: sentences.append(intro)
        if body: sentences.append(body)
        if revisit_note: sentences.append(revisit_note)
        if subtext_lines: sentences.extend(subtext_lines)
        if beat_text: sentences.append(beat_text)
        if hook: sentences.append(hook)
        
        return ' '.join(filter(None, sentences))

    def _shorten(self, text):
        """Make sentences punchier for high tension."""
        if not text:
            return ''
        sentences = text.split('. ')
        shortened = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(s.split()) > 10 and ',' in s:
                s = s.split(',')[0]
            shortened.append(s)
        return '. '.join(shortened) + ('.' if shortened else '')
def _harvest_premise(opening):
    """Extract specific nouns, verbs, and adjectives from opening premise."""
    words = _extract_keywords(opening)
    nouns = []
    adjectives = []
    verbs = []
    
    # Special manual classification overrides for premise keywords
    word_roles = {
        'forest': 'noun', 'sister': 'noun', 'city': 'noun', 'god': 'noun', 'border': 'noun',
        'ruins': 'noun', 'cure': 'noun', 'documents': 'noun', 'rumors': 'noun', 'rumor': 'noun',
        'fighter': 'noun', 'cartographer': 'noun', 'sailor': 'noun', 'spy': 'noun', 'healer': 'noun',
        'mars': 'noun', 'oxygen': 'noun', 'cat': 'noun', 'owner': 'noun', 'alley': 'noun',
        'hacker': 'noun', 'corporation': 'noun', 'tokyo': 'noun', 'detective': 'noun',
        'astronaut': 'noun', 'brother': 'noun', 'mother': 'noun', 'father': 'noun', 'friend': 'noun',
        'relic': 'noun', 'artifact': 'noun', 'compass': 'noun', 'robot': 'noun', 'witch': 'noun',
        'scientist': 'noun', 'pilot': 'noun', 'map': 'noun', 'maps': 'noun', 'street': 'noun',
        'station': 'noun', 'starship': 'noun', 'ship': 'noun', 'subway': 'noun', 'evidence': 'noun',
        'murder': 'noun', 'alien': 'noun', 'blade': 'noun', 'knife': 'noun', 'sword': 'noun',
        'coven': 'noun', 'swamp': 'noun', 'ingredients': 'noun', 'ingredient': 'noun',
        'temple': 'noun', 'vault': 'noun', 'cyberdeck': 'noun', 'mainframe': 'noun',
        'frost-bitten': 'adj', 'war-torn': 'adj', 'stolen': 'adj', 'stranded': 'adj', 'drowned': 'adj',
        'disgraced': 'adj', 'vanished': 'adj', 'plague': 'adj', 'inland': 'adj',
        'rainy': 'adj', 'cyberpunk': 'adj', 'evil': 'adj', 'lost': 'adj', 'dark': 'adj',
        'ancient': 'adj', 'red': 'adj', 'neon': 'adj', 'cold': 'adj', 'mysterious': 'adj',
        'forbidden': 'adj', 'exiled': 'adj',
        'looking': 'verb', 'searching': 'verb', 'searches': 'verb', 'carrying': 'verb', 'crosses': 'verb',
        'follows': 'verb', 'walks': 'verb', 'enters': 'verb', 'trying': 'verb', 'expose': 'verb',
        'investigating': 'verb', 'seeking': 'verb', 'fleeing': 'verb', 'hunting': 'verb', 'tracking': 'verb',
        'gathers': 'verb', 'gather': 'verb', 'gathering': 'verb', 'finds': 'verb', 'escapes': 'verb',
    }

    known_nouns_with_s = {
        'mars', 'ruins', 'documents', 'rumors', 'compass', 'grass', 'lens', 'glass', 'abyss',
        'virus', 'status', 'gas', 'chaos', 'ingredients', 'supplies', 'herbs', 'charms', 'relics'
    }
    known_nouns_with_en = {'oxygen', 'alien', 'citizen', 'kitchen', 'garden', 'warden', 'raven', 'haven', 'omen', 'coven'}
    
    for w in words:
        w_clean = w.strip().lower()
        if not w_clean:
            continue
        if w_clean in word_roles:
            role = word_roles[w_clean]
            if role == 'noun': nouns.append(w_clean)
            elif role == 'adj': adjectives.append(w_clean)
            elif role == 'verb': verbs.append(w_clean)
        elif w_clean in known_nouns_with_s or w_clean in known_nouns_with_en:
            nouns.append(w_clean)
        elif '-' in w_clean or (w_clean.endswith(('ed', 'en')) and w_clean not in known_nouns_with_en):
            adjectives.append(w_clean)
        elif w_clean.endswith(('ing', 'es', 's')) and not w_clean.endswith(('ness', 'ss')) and w_clean not in known_nouns_with_s:
            verbs.append(w_clean)
        else:
            nouns.append(w_clean)
            
    return {
        'nouns': nouns or ['road', 'wanderer'],
        'adjectives': adjectives or ['weathered'],
        'verbs': verbs or ['exploring']
    }

def _select_starting_location(genre, harvest):
    """Select the starting location that matches the premise keywords semantic theme."""
    locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
    all_keywords = set(harvest['nouns'] + harvest['adjectives'] + harvest['verbs'])
    
    active_themes = set()
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in all_keywords:
                active_themes.add(theme)
                
    scored_locs = []
    for name, desc in locs:
        score = 0
        tokens = set(re.findall(r'\b[a-zA-Z-]+\b', (name + ' ' + desc).lower()))
        
        # Direct matching score
        score += len(tokens & all_keywords) * 5
        
        # Theme keyword matching score
        for theme in active_themes:
            theme_kws = set(THEME_KEYWORDS[theme])
            score += len(tokens & theme_kws) * 2
            
        scored_locs.append((score, (name, desc)))
        
    scored_locs.sort(key=lambda x: x[0], reverse=True)
    if scored_locs[0][0] > 0:
        return scored_locs[0][1]
    return random.choice(locs)

def _is_npc_in_scene(state, beat, prev_beat):
    """Determine if the previous NPC is still present in the current scene."""
    if beat != 'encounter':
        return False
    if prev_beat != 'encounter':
        return False
    last_npc = state.get('last_npc')
    if not last_npc:
        return False
    npcs = state.get('continuity', {}).get('npcs', {})
    if last_npc not in npcs:
        return False
    record = npcs[last_npc]
    if record.get('last_seen_location') != state.get('location'):
        return False
    return True

def _get_motif_text(state):
    """Select and returns visual motif description scaled to current tension."""
    motif_name = state.setdefault('active_motif', None)
    if not motif_name:
        genre_motifs = {
            'fantasy': 'distant_bells',
            'scifi': 'cosmic_telemetry',
            'horror': 'broken_mirrors',
            'mystery': 'noir_shadows',
            'adventure': 'water_marks',
            'feline': 'feline_scent',
            'cyberpunk': 'cyber_glitch'
        }
        motif_name = genre_motifs.get(state.get('genre', 'fantasy'), 'distant_bells')
        state['active_motif'] = motif_name
        
    tension = state.get('tension', 0.5)
    level = 'low' if tension < 0.4 else 'medium' if tension < 0.72 else 'high'
    return MOTIFS.get(motif_name, MOTIFS['distant_bells'])[level]

PERSON_NOUNS = {
    'sister', 'brother', 'father', 'mother', 'friend', 'god', 
    'fighter', 'cartographer', 'sailor', 'spy', 'healer',
    'wanderer', 'traveller', 'stranger', 'companion', 'ally',
    'cousin', 'uncle', 'aunt', 'mentor', 'teacher',
    'astronaut', 'hacker', 'detective', 'cat', 'dog', 'owner',
    'scientist', 'witch', 'pilot', 'captain', 'child', 'partner',
    'victim', 'killer', 'contact', 'agent', 'mercenary', 'scavenger'
}

PLACE_NOUNS = {
    'city', 'border', 'forest', 'ruins', 'camp', 'town', 'village',
    'spire', 'grove', 'temple', 'cathedral', 'lake', 'plateau', 
    'canyon', 'shrine', 'thicket', 'wastes', 'bridge', 'cavern',
    'mars', 'alley', 'street', 'station', 'crater', 'market', 'subway',
    'docks', 'harbor', 'vault', 'sanctuary', 'tenement', 'lab', 'citadel',
    'basin', 'quarter', 'outpost', 'colony', 'compound', 'corporation'
}

def _weave_premise_keywords(state, key, fallback):
    """Weave premise keywords naturally and grammatically into descriptions."""
    harvest = state.get('opening_keywords_harvest', {})
    nouns = harvest.get('nouns', [])
    adjectives = harvest.get('adjectives', [])
    role = state.get('player_role')
    
    desc_nouns = [n for n in nouns if n != role]
    if not desc_nouns:
        desc_nouns = nouns
        
    if key == 'object_name':
        if desc_nouns:
            n = desc_nouns[-1]
            if n in PREMISE_NOUN_PHRASING:
                return PREMISE_NOUN_PHRASING[n][0]
            if n in PERSON_NOUNS:
                return f"your {n}"
            if adjectives:
                return f"the {adjectives[0]} {n}"
            return f"the {n}"
        return fallback
    elif key == 'desc_detail':
        if desc_nouns:
            n = desc_nouns[0]
            if adjectives:
                return f"a {adjectives[0]} {n}"
            return f"a {n}"
        return fallback
    return fallback

def _get_natural_revisit_sentence(state, ctx):
    """Integrate memory of past visits dynamically into description."""
    loc = ctx['location']
    ns = NarrativeState(state)
    visits = max(ctx.get('loc_state', {}).get('last_visited', 0), ns.memory.get_visits(loc))
    
    if visits <= 1:
        return ""
        
    flags = state.get('continuity', {}).get('world_flags', {})
    if loc in flags.get('enemies_defeated', []):
        return f"The basalt soil at the {loc} still bears the heavy marks of the clash you survived here."
    if loc in flags.get('doors_opened', []):
        return f"The forced lock at the {loc} hangs broken, swinging slowly under the {ctx['weather']}."
    if loc in flags.get('secrets_discovered', []):
        return f"The translation marks you carved into the {ctx['object']} remain legible in the {ctx['weather']}."
        
    # Query MemoryGraph events for location
    events = [e for e in ns.memory.memory.get('events', []) if e.get('location') == loc]
    if events:
        latest_event = events[-1]
        return f"You return here: the memory of {latest_event.get('description', 'what happened here')} still lingers at the {loc}."

    return f"The path through the {loc} bears the familiar patterns of your prior crossing. This is your visit number {visits}."

def _npc_dialogue_line_adaptive(state, npc_record, ctx):
    """Adapt NPC dialogue lines based on player drives, character stats, and history."""
    dominant = state.get('dominant_behavior') or 'explore'
    name = npc_record['name'].split(',')[0]
    genre = state.get('genre', 'fantasy')
    
    # 1. Check premise-matched lore pack dialogue templates
    lore = LoreManager.detect_lore_pack(state.get('opening', '') + ' ' + genre)
    if lore and lore.get('dialogue_templates'):
        tmpl = random.choice(lore['dialogue_templates'])
        try:
            return tmpl.format(name=name, faction=ctx.get('faction', 'the authorities'), location=ctx.get('location', 'this sector'))
        except Exception:
            pass

    # 2. Check for active rumors
    rumours = list(state.get('rumour_state', {}).values())
    if rumours and random.random() < 0.4:
        r = random.choice(rumours)
        r_text = r['text'] if isinstance(r, dict) else r
        r_clean = r_text.strip().rstrip('.')
        if r_clean.lower().startswith("they say that "):
            r_clean = r_clean[14:]
        elif r_clean.lower().startswith("they say "):
            r_clean = r_clean[9:]
        return f"\"I've heard talk on the frequency,\" {name} murmurs. \"They say that {r_clean}. Keep that in mind.\""

    # 3. Genre-specific dialogue safeguards
    if genre == 'scifi':
        if dominant == 'aggressive':
            return f"\"Life-support readouts are erratic,\" {name} warns over the comms. \"Conserve your thruster fuel.\""
        if dominant == 'cautious':
            return f"\"Keep your radio chatter minimal,\" {name} whispers over encrypted frequency. \"Atmospheric scans show pressure loss.\""
        return f"\"Confirmed telemetry on your beacon,\" {name} transmits. \"Check the emergency reserves at the {ctx.get('location', 'module')}.\""

    if genre == 'cyberpunk':
        if dominant == 'aggressive':
            return f"\"The network ICE is surging,\" {name} warns through the link. \"Pull your deck before they fry your chip.\""
        return f"\"Keep your optical feed clear,\" {name} transmits. \"Surveillance drones are tracking this subnet.\""

    if genre == 'feline':
        return f"{name} watches with unblinking eyes, ears pivoting sharply toward the distant sounds of the alley."

    stats = state.get('character', {}).get('stats', {})
    if stats.get('Lore', 0) >= 4 and random.random() < 0.5 and genre == 'fantasy':
        return f"\"I see the ink of the Accord on your fingers,\" {name} says. \"You know what history we are repeating.\""
    if stats.get('Cunning', 0) >= 4 and dominant == 'cautious':
        return f"\"You tread like someone who has counted the exits already,\" {name} whispers. \"Keep that silence.\""
        
    relationship = npc_record.get('relationship', 'neutral')
    if relationship == 'hostile':
        if dominant == 'aggressive':
            return f"\"Step any closer, and the {ctx.get('faction', 'guards')} will finish you at the {ctx.get('location', 'gates')}.\""
        return f"\"I know what follows you,\" {name} says. \"Do not bring it near me.\""
        
    if relationship == 'ally':
        if dominant == 'social':
            return f"\"The crossing has been harsh, but your name carries some warmth here,\" {name} says."
        return f"\"I kept one answer back for you,\" {name} says. \"It may cost us both.\""
        
    if dominant == 'aggressive':
        if genre == 'fantasy':
            return f"\"You carry old weather and new steel, traveller,\" {name} warns. \"The {ctx.get('faction', 'patrol')} are watching.\""
        return f"\"Your stance says you expect trouble,\" {name} says. \"Be careful what you provoke here.\""
    if dominant == 'social':
        return f"\"A shared word costs nothing,\" {name} says. \"What does your scouting report claim about the {ctx.get('location', 'area')}?\""
    if dominant == 'cautious':
        return f"\"Keep low. The {ctx.get('location', 'place')} carries sound straight to {ctx.get('faction', 'observers')}.\""
        
    return f"\"Tell me what you noticed at the {ctx.get('location', 'area')}, not what you hoped to find.\""

def _render_prose_template(state, template, ctx):
    """Render a dynamic sequence template to form a cohesive paragraph."""
    harvest = state.get('opening_keywords_harvest', {})
    nouns = harvest.get('nouns', [])
    adjectives = harvest.get('adjectives', [])
    verbs = harvest.get('verbs', [])
    
    object_name = _weave_premise_keywords(state, 'object_name', ctx['object'])
    action_verb = verbs[0] if verbs else "explore"
    if ctx.get('action_terms'):
        action_verb = ctx['action_terms'][0]
        
    motif_text = _get_motif_text(state)
    desc_detail = _weave_premise_keywords(state, 'desc_detail', ctx['description'])
    
    npc_name = "the stranger"
    npc_short_name = "the stranger"
    npc_archetype = "traveller"
    npc_tic_text = ""
    npc_memory_text = ""
    npc_dialogue = ""
    
    if ctx.get('npc'):
        npc = ctx['npc']
        npc_name = npc['name']
        npc_short_name = npc['name'].split(',')[0]
        npc_archetype = npc['archetype']
        npc_tic_text = _format_npc_tic(npc.get('tic'))
        npc_memory_text = _npc_memory_sentence(npc)
        npc_dialogue = _npc_dialogue_line_adaptive(state, npc, ctx)
        
    revisit_note = _get_natural_revisit_sentence(state, ctx)
    
    features = ctx.get('features', [])
    if not features:
        features = [ctx['object']]
        
    format_dict = {
        'weather': ctx['weather'],
        'location': ctx['description'],
        'location_noun': ctx['location'],
        'location_description': ctx['description'],
        'action_verb': action_verb,
        'object_name': object_name,
        'faction': ctx['faction'],
        'region': ctx['region'],
        'role': ctx['role'],
        'wound': ctx['wound'],
        'drive': ctx['drive'],
        'reputation': ctx['reputation'],
        'motif_text': motif_text,
        'npc_name': npc_name,
        'npc_short_name': npc_short_name,
        'npc_archetype': npc_archetype,
        'npc_tic_text': npc_tic_text,
        'npc_memory_text': npc_memory_text,
        'npc_dialogue': npc_dialogue,
        'description_detail': desc_detail,
        'features': features,
        'revisit_note': revisit_note,
    }
    
    intro = template['intro'].format(**format_dict)
    body = template['body'].format(**format_dict)
    beat_text = template['beat'].format(**format_dict)
    hook = template['hook'].format(**format_dict)
    
    style = StyleState(state)
    return style.compose({
        'intro': intro,
        'body': body,
        'beat_text': beat_text,
        'hook': hook,
        'revisit_note': revisit_note
    })

def _generate_choices_premise_aware(state, beat, choices, ctx):
    """Inject premise-aligned custom branches and SceneCard/EntityGraph-gated actions directly into choices."""
    ns = NarrativeState(state)
    
    # 1. Dynamically update current SceneCard properties
    ns.scene_card.setting = ctx.get('location', '')
    if ctx.get('npc'):
        ns.scene_card.cast = [ctx['npc']['name']]
    else:
        ns.scene_card.cast = []
        
    top_thread = ns.threads.get_top_thread()
    if top_thread:
        ns.scene_card.objective = f"Advance the quest: {top_thread['description']}"
    else:
        ns.scene_card.objective = "Explore the location and gather local rumors"
        
    if beat == 'obstacle':
        ns.scene_card.obstacle = f"A barrier formed by {ctx.get('object', 'the terrain')}"
    elif beat == 'conflict':
        ns.scene_card.obstacle = f"Hostility from the {ctx.get('faction', 'hostiles')}"
    else:
        ns.scene_card.obstacle = "None"

    # 2. Add thread-advancement choices if active
    if top_thread:
        thread_choice = f"Focus on your main goal: {top_thread['description']} at the {ctx.get('location')}"
        if thread_choice not in choices:
            choices.append(thread_choice)

    # 3. Add EntityGraph relation-gated choices (debts/grudges)
    npc = ctx.get('npc')
    loc = ctx.get('location', '')
    if npc:
        npc_name = npc['name'].split(',')[0]
        debts = ns.entities.get_edges(source='player', target=npc['name'], edge_type='debt')
        if debts and beat == 'encounter':
            debt_choice = f"Address the debt you owe {npc_name} in exchange for local path secrets"
            if debt_choice not in choices:
                choices.append(debt_choice)

    faction = ctx.get('faction')
    if faction:
        grudges = ns.entities.get_edges(source='player', target=faction, edge_type='grudge')
        if grudges and beat in ('encounter', 'conflict'):
            grudge_choice = f"Attempt to negotiate a truce and defuse the grudge with the {faction}"
            if grudge_choice not in choices:
                choices.append(grudge_choice)

    # 4. Standard premise-aligned custom choice injection (existing logic)
    harvest = state.get('opening_keywords_harvest', {})
    nouns = harvest.get('nouns', [])
    role = state.get('player_role')
    desc_nouns = [n for n in nouns if n != role]
    
    if not desc_nouns:
        return choices
        
    target_noun = desc_nouns[-1]
    adjectives = harvest.get('adjectives', [])
    npc_name = npc['name'].split(',')[0] if npc else "the stranger"
    
    category = 'object' # default fallback
    if target_noun in PREMISE_NOUN_PHRASING:
        category = PREMISE_NOUN_PHRASING[target_noun][1]
    elif target_noun in PERSON_NOUNS:
        category = 'person'
    elif target_noun in PLACE_NOUNS:
        category = 'place'
        
    if target_noun in PREMISE_NOUN_PHRASING:
        phrased = PREMISE_NOUN_PHRASING[target_noun][0]
    elif category == 'person':
        phrased = f"your {target_noun}"
    else:
        if adjectives:
            phrased = f"the {adjectives[0]} {target_noun}"
        else:
            phrased = f"the {target_noun}"
            
    custom_choice = None
    if category == 'person':
        if target_noun == 'sister':
            if beat == 'encounter':
                custom_choice = f"Ask {npc_name} if they have seen a sister passing through the {loc}"
            elif beat in ('discovery', 'revelation'):
                custom_choice = f"Search the {loc} for any track your sister might have left"
        elif target_noun == 'god':
            if beat == 'encounter':
                custom_choice = f"Ask {npc_name} what the pilgrims whisper about the drowned god"
            elif beat in ('discovery', 'revelation'):
                custom_choice = f"Look for salt-worn relics of the drowned god near the {loc}"
        else:
            if beat == 'encounter':
                custom_choice = f"Ask {npc_name} if they have seen any sign of {phrased} passing through the {loc}"
            elif beat in ('discovery', 'revelation'):
                custom_choice = f"Search the {loc} for any track or message {phrased} might have left"
                
    elif category == 'place':
        if target_noun == 'city':
            if beat == 'revelation':
                custom_choice = f"Check if the signs at the {loc} point toward the vanished city"
            elif beat == 'discovery':
                custom_choice = f"Look for ruins or stone marks of the vanished city at the {loc}"
        elif target_noun == 'border':
            if beat == 'transition':
                custom_choice = f"Map the path leading across the war-torn border"
            elif beat == 'conflict':
                custom_choice = f"Hold the line near the {loc} before they push you back from the border"
        else:
            if beat == 'revelation':
                custom_choice = f"Check if the signs at the {loc} point toward {phrased}"
            elif beat == 'discovery':
                custom_choice = f"Look for ruins or landmarks of {phrased} at the {loc}"
            elif beat == 'transition':
                custom_choice = f"Map the path leading toward {phrased}"
            elif beat == 'conflict':
                custom_choice = f"Hold the line near the {loc} before they push you back from {phrased}"
                
    elif target_noun in ('jupiter', 'mars', 'europa', 'earth', 'saturn', 'neptune', 'venus'):
        if beat in ('discovery', 'revelation'):
            custom_choice = f"Scan orbital telemetry toward {target_noun.title()} to calculate drift"
        elif beat == 'encounter':
            custom_choice = f"Ask {npc_name} about radio relays linked to {target_noun.title()} orbit"
        else:
            custom_choice = f"Plot an emergency trajectory toward {target_noun.title()} orbital beacons"
    elif target_noun in ('oxygen', 'air', 'tank', 'life support', 'scrubber'):
        if beat in ('discovery', 'revelation'):
            custom_choice = f"Check the suit telemetry gauge to verify remaining oxygen levels"
        elif beat == 'obstacle':
            custom_choice = f"Seal pressure valves at the {loc} before oxygen drops below critical threshold"
        elif beat == 'encounter':
            custom_choice = f"Inquire if {npc_name} has access to auxiliary oxygen tanks or power cells"
        else:
            custom_choice = f"Conserve breath and prioritize life-support repairs at the {loc}"
    elif category == 'object':
        if target_noun == 'cure':
            if beat == 'discovery':
                custom_choice = f"Search the plague ruins of the {loc} for any trace of the cure"
            elif beat == 'encounter':
                custom_choice = f"Ask {npc_name} if they carry the herbs needed for the cure"
        else:
            if beat == 'discovery':
                custom_choice = f"Search the {loc} for any trace or clue of {phrased}"
            elif beat == 'encounter':
                custom_choice = f"Ask {npc_name} if they carry anything related to {phrased}"
            elif beat == 'revelation':
                custom_choice = f"Study the {loc} to see how it connects to {phrased}"
            
    if custom_choice and custom_choice not in choices:
        choices.append(custom_choice)
        
    return choices

# Proper NPC title/names for continuity references
NPC_NAMES = [
    'the stranger','the watcher','the keeper','the wanderer','the exile',
    'the sentinel','the courier','the guide','the survivor','the scholar',
    'the hunter','the alchemist','the cartographer','the deserter','the oracle',
    'the engineer','the hermit','the prophet','the smuggler','the warden',
    'the toll-taker', 'the grave-digger', 'the pathfinder', 'the turncoat',
    'the chronicler', 'the outrider', 'the metal-smith', 'the harbor-master',
]

NPC_PROPER_NAMES = [
    'Mireth Vale', 'Oren Blackreed', 'Sera Voss', 'Calder Wren',
    'Ilyan Thorne', 'Veyra Mourn', 'Tovin Ash', 'Elira Fen',
    'Damaris Pike', 'Rook Marrow', 'Ansel Grey', 'Nadia Kest',
    'Bren Tor', 'Silas Veld', 'Maera Quill', 'Corin Redhand',
    'Orla Vance', 'Garrick Flint', 'Kaelen Frost', 'Lyra Stone',
    'Jory Pyre', 'Elowen Rook', 'Bram Well', 'Taran Shade',
]

STAT_NAMES = ['Vitality', 'Resolve', 'Cunning', 'Strength', 'Presence', 'Lore']

STAT_PRESETS = {
    'fighter':  {'Vitality': 6, 'Resolve': 4, 'Cunning': 2, 'Strength': 5, 'Presence': 2, 'Lore': 1},
    'scholar':  {'Vitality': 3, 'Resolve': 5, 'Cunning': 3, 'Strength': 1, 'Presence': 2, 'Lore': 5},
    'wanderer': {'Vitality': 4, 'Resolve': 4, 'Cunning': 4, 'Strength': 3, 'Presence': 3, 'Lore': 2},
}

REGION_GEOGRAPHY = [
    'rain-black border forest', 'salt road between ruined watchtowers',
    'fenland of reed-choked causeways', 'high moor under broken stars',
    'basalt coast with drowned bells', 'orchard valley gone half-wild',
    'ash plain where old armies vanished', 'river market built on stilts',
]

REGION_FACTIONS = [
    'soldiers in red', 'moth-cloaked pilgrims', 'the Toll Guild',
    'gravewardens', 'salt smugglers', 'the Glass Abbey',
    'exiled banner-men', 'keepers of the old road',
]

GENRE_FACTIONS = {
    'fantasy': [
        'soldiers in red', 'moth-cloaked pilgrims', 'the Toll Guild',
        'gravewardens', 'salt smugglers', 'the Glass Abbey',
        'exiled banner-men', 'keepers of the old road',
    ],
    'scifi': [
        'the Orbital Syndicate', 'corporate enforcers', 'the Tech Guild',
        'deep space miners', 'synthetic rebels', 'colony marshals',
        'data smugglers', 'the Megacorp Security',
    ],
    'mystery': [
        'the precinct detectives', 'the dockworkers union', 'the city syndicate',
        'smugglers ring', 'corrupt city officials', 'private investigators',
        'the harbor watch', 'the underground cartel',
    ],
    'horror': [
        'the Ashen Cult', 'asylum wardens', 'the Whispering Circle',
        "coroner's guard", 'the Hollow Flock', 'the Red Coven',
        'graveyard scavengers', 'night vigilants',
    ],
    'adventure': [
        'rival expedition', 'coastal scavengers', 'island cartel',
        'tomb looters', 'frontier scouts', 'jungle guides',
        'salvage crew', 'mercenary patrol',
    ],
}

GENRE_REGION_PREFIXES = {
    'scifi': ['Neo', 'Ares', 'Cyber', 'Nova', 'Titan', 'Apex', 'Aegis', 'Vektor', 'Nexus', 'Helios'],
    'mystery': ['West', 'East', 'Cobble', 'Lower', 'High', 'Old', 'Black', 'River', 'Iron', 'Cross'],
    'horror': ['Mourn', 'Gloom', 'Carrion', 'Ashen', 'Blight', 'Dread', 'Grim', 'Wither', 'Hollow', 'Silent'],
    'adventure': ['Sunken', 'Emerald', 'Serpent', 'Golden', 'Skeleton', 'Wild', 'Coral', 'Thunder', 'Storm', 'Amber'],
}

GENRE_REGION_SUFFIXES = {
    'scifi': [' Prime', ' Sector', ' Station', ' Basin', ' Reach', ' Bay', ' Complex', ' Sprawl', ' Hub', ' Colony'],
    'mystery': [' Ward', ' Port', ' Hill', ' Docks', ' Street', ' District', ' Quarter', ' End', ' Alley', ' Gate'],
    'horror': [' Barrow', ' Crypt', ' Trench', ' Moor', ' Vale', ' Asylum', ' Asylum', ' Hollow', ' Marsh', ' Yard'],
    'adventure': [' Coast', ' Reach', ' Isle', ' Peak', ' Cay', ' Valley', ' Ridge', ' Narrows', ' Reef', ' Pass'],
}

GENRE_REGION_GEOGRAPHY = {
    'scifi': [
        'pressurized habitat domes under solar radiation',
        'toxic rust plains strewn with decommissioned rovers',
        'sprawling neon industrial sector connected by skywalks',
        'subterranean mining facility cutting through frozen permafrost',
        'tangled mag-lev conduits above the lower city',
    ],
    'mystery': [
        'gaslit cobblestone alleys shrouded in cold river mist',
        'industrial waterfront warehouses lined with rusting cranes',
        'shadowed brick tenements with dripping iron fire escapes',
        'crowded tramway thoroughfare between gray stone facades',
        'fog-drenched railway yards echoing with distant whistles',
    ],
    'horror': [
        'rotting woodlands where dead pines lean like broken teeth',
        'sunken cemetery overgrown with black briars and stagnant pools',
        'crumbling asylum perimeter flanked by rusted wrought-iron gates',
        'fog-choked quarry lake where sound vanishes beneath the surface',
    ],
    'adventure': [
        'overgrown jungle terraces winding along emerald river canyons',
        'sun-scorched barrier islands ringed by crashing turquoise breakers',
        'wind-swept sandstone ridges overlooking ancient canyon gorges',
        'mist-veiled mountain passes flanked by sheer granite spires',
    ],
}

REGION_PREFIXES = ['Veld', 'Mourn', 'Ash', 'Grey', 'Red', 'Elder', 'Hollow', 'Witch', 'Dawn', 'Fen']
REGION_SUFFIXES = ['moor', 'reach', 'fen', 'barrow', 'mere', 'watch', 'ford', 'vale', 'march', 'wood']
TIME_SLOTS = ['dawn', 'day', 'dusk', 'night']
WEATHER_STATES = ['clear cold', 'thin rain', 'hard rain', 'mist', 'wind', 'sour fog', 'distant thunder']

ITEM_TYPES = ['weapon', 'armour', 'consumable', 'key', 'artefact', 'lore', 'accessory']
ITEM_WEIGHTS = ['light', 'medium', 'heavy']

PIVOT_TYPES = [
    'npc_turns', 'location_lost', 'faction_move', 'secret_surfaces',
    'ally_cost', 'reputation_shift', 'world_event', 'player_past',
]

PLAYER_ROLES = [
    'knight', 'exile', 'mercenary', 'scholar', 'thief', 'wanderer', 'healer',
    'spy', 'sailor', 'priest', 'cartographer', 'deserter', 'outcast',
    'survivor', 'fighter', 'astronaut', 'hacker', 'detective', 'witch',
    'cat', 'pilot', 'scientist', 'captain', 'ranger', 'assassin', 'engineer'
]

ROLE_KEYWORDS = {
    'cartographer': ['map', 'maps', 'chart', 'charts', 'compass', 'survey', 'borderline'],
    'sailor': ['ship', 'boat', 'sea', 'ocean', 'sail', 'deck', 'crew', 'mast', 'port'],
    'mercenary': ['sword', 'blade', 'sellsword', 'contract', 'coin', 'hired', 'pay'],
    'priest': ['order', 'abbey', 'church', 'faith', 'altar', 'god', 'temple', 'saint'],
    'knight': ['vow', 'shield', 'banner', 'fealty', 'lord', 'honor', 'crest'],
    'deserter': ['deserted', 'fled', 'failed', 'ran', 'abandoned', 'post', 'regiment'],
    'spy': ['secret', 'report', 'cipher', 'mission', 'disguise', 'recon', 'handler'],
    'healer': ['wound', 'bandage', 'herb', 'medicine', 'sick', 'cure', 'physician'],
    'thief': ['steal', 'stole', 'purse', 'lock', 'vault', 'loot', 'pickpocket'],
    'scholar': ['book', 'scroll', 'library', 'study', 'history', 'chronicler', 'parchment'],
    'exile': ['cast out', 'banished', 'exiled', 'homeland', 'forbidden'],
    'outcast': ['shunned', 'spat', 'rejected', 'unwanted', 'scorned'],
    'survivor': ['survived', 'lived', 'last', 'remained', 'wreckage', 'ruins'],
    'fighter': ['fighter', 'soldier', 'warrior', 'brawler', 'guard'],
    'astronaut': ['astronaut', 'cosmonaut', 'mars', 'orbit', 'spacesuit', 'oxygen', 'spacecraft'],
    'hacker': ['hacker', 'cyberpunk', 'cyber', 'terminal', 'mainframe', 'megacorp', 'cyberdeck', 'netrunner'],
    'detective': ['detective', 'investigator', 'inspector', 'police', 'private eye', 'noir', 'murder', 'case'],
    'witch': ['witch', 'coven', 'cauldron', 'alchemy', 'herbalist', 'familiar'],
    'cat': ['cat', 'feline', 'kitten', 'stray', 'paws', 'whiskers'],
    'pilot': ['pilot', 'flight', 'cockpit', 'shuttle', 'plane'],
    'scientist': ['scientist', 'researcher', 'laboratory', 'specimen', 'experiment'],
    'captain': ['captain', 'skipper', 'commander', 'flagship'],
    'ranger': ['ranger', 'tracker', 'woodsman', 'wildsman'],
    'assassin': ['assassin', 'poisoner', 'hitman'],
    'engineer': ['engineer', 'mechanic', 'machinist', 'technician'],
}

DRIVE_KEYWORDS = {
    'revenge': ['revenge', 'avenge', 'kill', 'slay', 'pay', 'blood'],
    'atonement': ['atone', 'forgive', 'fault', 'guilt', 'burden', 'death', 'disgraced', 'remorse'],
    'discovery': ['find', 'seek', 'learn', 'truth', 'explore', 'uncover'],
    'escape': ['flee', 'run', 'hide', 'behind', 'away', 'escape'],
    'redemption': ['shame', 'redeem', 'restore', 'honor'],
    'grief': ['loss', 'lost', 'died', 'dead', 'grave', 'mourn'],
    'belonging': ['home', 'belong', 'family', 'return', 'welcome'],
    'duty': ['duty', 'order', 'oath', 'promise', 'must'],
    'ambition': ['throne', 'power', 'claim', 'fortune', 'rise'],
    'survival': ['survive', 'hunger', 'starve', 'shelter', 'winter'],
}

VOICE_KEYWORDS = {
    'grim': ['failed', 'death', 'blood', 'grave', 'disgraced', 'guilt'],
    'haunted': ['haunt', 'ghost', 'memory', 'remember', 'shadow'],
    'hungry': ['starve', 'hunger', 'scraps', 'gold', 'cold', 'debt'],
    'wry': ['laugh', 'dry', 'honest', 'shrug', 'joke'],
    'desperate': ['flee', 'desperate', 'must', 'please', 'help'],
    'tired': ['exhaust', 'long', 'weary', 'miles', 'sleep'],
    'proud': ['shield', 'crown', 'name', 'bloodline', 'crest'],
    'careful': ['careful', 'quiet', 'watch', 'listen', 'wait'],
}

ROLE_CONTEXT = {
    'cartographer': "The maps are still in your pack, too damning to trust and too useful to burn.",
    'sailor': "Old salt has dried into your cuffs; even inland, part of you keeps listening for rigging.",
    'mercenary': "Your hand knows the old arithmetic: distance, witness, payment, escape.",
    'priest': "The broken sign at your throat keeps its chill, as if faith can become weather.",
    'knight': "The scraped place where your heraldry used to be still shines when rain touches it.",
    'deserter': "You keep counting the seconds it would take pursuit to reach your position.",
    'spy': "The unused report lives behind your teeth, addressed to no one living.",
    'healer': "Your satchel smells of bitter herbs and old blood that no clean water finished removing.",
    'thief': "Every latch speaks a small language, and your fingers answer before pride can stop them.",
    'scholar': "The margins of your old notes are full of corrections that cannot correct what happened.",
    'exile': "Behind you is a boundary stone; ahead is a place where your name has not yet been priced.",
    'outcast': "The mark may have faded from your skin, but people still seem to read it there.",
    'survivor': "You know the difference between silence and aftermath; this place is deciding which one it is.",
    'fighter': "Your body keeps its old ledgers in scar tissue and balance.",
    'wanderer': "The road does not care where you came from, and that is the first mercy it offers.",
    'astronaut': "Your suit's HUD flickers with telemetry, every breath a metered ration against the void.",
    'hacker': "The deck at your hip still carries the intrusion logs they would kill to erase.",
    'detective': "Your notebook is full of questions that make powerful people reach for their lawyers or their guns.",
    'witch': "The small charms sewn into your hem hum with quiet, forbidden warmth.",
    'cat': "Your whiskers twitch at the faint vibrations of the ground, reading danger long before two-leggers notice.",
    'pilot': "Your hands rest easily on the controls, attuned to the slightest shudder of the airframe.",
    'scientist': "The data readouts are indisputable, no matter how much you wish they were an error.",
    'captain': "The deck is yours, but every eye aboard is waiting to see where you steer.",
    'ranger': "You can read the broken twigs and parted grass like a printed book.",
    'assassin': "The weight of the cold steel in your sleeve is the only contract that matters.",
    'engineer': "You listen to the mechanical hum around you, knowing exactly which bolt is under strain.",
}

ROLE_ITEM_OR_TOOL = {
    'cartographer': 'map',
    'scholar': 'field journal',
    'hunter': 'trail marks',
    'outcast': 'survival instincts',
    'soldier': 'sidearm',
    'healer': 'remedy kit',
    'wanderer': 'travel staff',
    'rebel': 'cipher notes',
    'mystic': 'relic',
    'thief': 'lockpicks',
    'noble': 'signet seal',
    'astronaut': 'suit telemetry',
    'hacker': 'cyberdeck',
    'detective': 'case notes',
    'witch': 'talisman',
    'cat': 'keen instincts',
    'pilot': 'flight controls',
    'scientist': 'sensor scanner',
    'captain': 'logbook',
    'ranger': 'scouting signs',
    'assassin': 'hidden blade',
    'engineer': 'diagnostic kit',
}

# ── Genre config ──────────────────────────────────────────────────────────────

GENRE_LOCATIONS = {
    'fantasy': [
        ('sunken grove','submerged forest ruins with bioluminescent moss'),
        ('obsidian spire','black volcanic glass tower against stormy sky'),
        ('living cavern','cave with pulsing organic walls and crystal veins'),
        ('drowned temple','half-submerged ancient temple with lily pads'),
        ('petrified forest','forest of stone trees under aurora sky'),
        ('mirror lake','perfectly still lake reflecting impossible sky'),
        ('bone cathedral','cathedral built from enormous ancient bones'),
        ('storm plateau','windswept highland under perpetual lightning'),
        ('root labyrinth','underground maze of enormous tree roots'),
        ('ember wastes','smoldering volcanic wasteland with lava rivers'),
        ('crystal bridge','translucent crystal bridge over bottomless chasm'),
        ('wailing canyon','deep red canyon with wind-carved formations'),
        ('moonwell shrine','circular stone shrine filled with silvery water'),
        ('iron thicket','forest of metallic trees with copper leaves'),
        ('frostbitten forest','pine woods shrouded in rime and ancient silence'),
        ('crumbling citadel','weathered stone fortress clinging to a jagged precipice'),
    ],
    'scifi': [
        ('derelict atrium','abandoned space station overgrown with alien flora'),
        ('neon market','rain-soaked cyberpunk market with holographic signs'),
        ('cryo vault','frozen storage facility with rows of pods'),
        ('quantum rift','tear in space-time with fractured light'),
        ('orbital debris','field of wrecked starships orbiting dead planet'),
        ('neural hub','massive server room with organic-tech hybrid systems'),
        ('xeno dig site','archaeological excavation of alien ruins'),
        ('plasma core','reactor chamber with contained star fragment'),
        ('hab dome crack','cracked biodome revealing alien atmosphere'),
        ('void dock','empty docking bay open to stars'),
        ('signal tower','communication spire transmitting into deep space'),
        ('terraform scar','planet surface mid-transformation half alive'),
        ('martian crater','red dust basin strewn with solar panels and rover tracks'),
        ('pressurized biodome','modular habitat dome humming with life-support recyclers'),
        ('sprawl alleyway','shadowed alley between towering arcologies glowing with neon advertisements'),
        ('orbital airlock','heavy titanium airlock looking out into the silent black void'),
        ('derelict starship','darkened corridor of an adrift vessel with emergency klaxons'),
        ('icy moon surface','fractured cryo-ice plains glowing under Jupiter\'s immense marbled disc'),
        ('cryo crater','frozen crater basin littered with lander wreckage and geothermal vents'),
        ('subterranean ice cavern','vault of ancient extraterrestrial ice reflecting helmet telemetry'),
    ],
    'feline': [
        ('market alley','narrow cobblestone alley flanked by fish crates and rain gutters'),
        ('zinc rooftop','shadowed rooftop ledge overlooking chimneypots and misty streetlamps'),
        ('cellar threshold','drafty cellar doorway smelling of dry sawdust and quiet darkness'),
        ('butcher garden','overgrown garden behind the butcher shop with high brick walls'),
        ('attic rafters','dust-mote filled attic timbers warm beneath the slate roof'),
    ],
    'horror': [
        ('meat corridor','fleshy organic tunnel with pulsing walls'),
        ('static room','room where reality glitches and loops'),
        ('doll archive','warehouse of damaged mannequins and dolls'),
        ('drip chapel','underground chapel with constant dripping water'),
        ('skin gallery','hallway lined with stretched preserved skins'),
        ('mirror maze','infinite reflections showing wrong timelines'),
        ('birth chamber','organic cavern where something is growing'),
        ('clock tower','abandoned clocktower with all clocks stopped'),
        ('ash nursery','burned ward with intact toys on shelves'),
        ('teeth corridor','tunnel lined with thousands of human teeth'),
        ('flood basement','flooded cellar with something moving underwater'),
        ('smile room','empty room with hundreds of photographs of smiling faces'),
    ],
    'mystery': [
        ('evidence room','police evidence storage with red string board'),
        ('penthouse scene','luxury apartment with chalk outline'),
        ('underground archive','secret basement full of classified files'),
        ('neon bar','smoky jazz bar with one-way mirrors'),
        ('clock shop','antique clock repair shop frozen in time'),
        ('rooftop greenhouse','glass greenhouse atop skyscraper at night'),
        ('print shop','abandoned newspaper press with last edition loaded'),
        ('harbor warehouse','waterfront storage with suspicious cargo'),
        ('subway platform','empty late-night subway station'),
        ('observatory','hilltop observatory with broken telescope'),
        ('rainy alley','narrow cobblestone alley with dripping fire escapes and steam vents'),
        ('crime scene parlour','dusty room sealed behind police tape with overturned furniture'),
        ('fog-drenched docks','waterfront pier where dark river water laps against rotting pilings'),
        ('shadowed backroom','cramped office smelling of tobacco smoke and old paper'),
    ],
    'adventure': [
        ('cenote','deep natural sinkhole with turquoise water and vines'),
        ('sky bridge','rope bridge between cliff faces in clouds'),
        ('lava tube','volcanic tunnel with cooled lava formations'),
        ('shipwreck reef','coral-encrusted shipwreck in shallow water'),
        ('ice cathedral','natural ice cave with cathedral-like formations'),
        ('canyon narrows','slot canyon with light streaming from above'),
        ('banyan maze','massive banyan tree with room-sized root chambers'),
        ('tidal cave','sea cave that floods and drains with tides'),
        ('mesa ruins','pueblo ruins on top of flat mesa'),
        ('crater lake','volcanic crater filled with emerald water'),
        ('mangrove tunnel','water passage through dense mangrove roots'),
        ('salt flat','endless white salt plain under brutal sun'),
        ('overgrown jungle ruins','ancient stone terraces half-swallowed by emerald jungle canopy'),
        ('windswept coastal cliff','rugged bluffs battered by crashing gray waves'),
        ('sun-bleached dunes','sea of shifting orange sand beneath an unforgiving sun'),
    ],
}

GENRE_KEYWORDS = {
    'feline': [
        'cat','feline','kitten','paws','whiskers','claws','tail','alleycat','purr','meow','fur','prowling'
    ],
    'fantasy': [
        'dragon','sword','magic','kingdom','elf','wizard','quest','castle','knight',
        'sorcerer','enchanted','dungeon','goblin','dwarf','throne','spell','potion',
        'ancient','rune','prophecy','forest','warrior','mage','mythical','arcane',
        'blade','witch','coven','cauldron','paladin','altar','realm','beast','bow'
    ],
    'scifi': [
        'space','ship','planet','robot','AI','laser','galaxy','station','alien',
        'cyberpunk','android','neon','future','tech','colony','warp','quantum',
        'hologram','cyborg','neural','plasma','orbit','starship','mech','synthetic',
        'astronaut','cosmonaut','mars','moon','rover','rocket','shuttle','oxygen',
        'vacuum','hacker','matrix','data','cyber','megacorp','corporation','tokyo',
        'netrunner','genetic','clone','lab','drone','terminal','telemetry','cyberdeck',
        'spaceship','interstellar','jupiter','europa'
    ],
    'horror': [
        'dark','shadow','fear','blood','creature','nightmare','haunted','ghost',
        'demon','cursed','asylum','cemetery','ritual','occult','madness','whisper',
        'scream','decay','rot','dread','horror','flesh','bone','undead',
        'terror','ghoul','zombie','infected','morgue','slaughter','monster','eerie',
        'sinister','phantom','macabre','corpse','butcher'
    ],
    'mystery': [
        'clue','detective','murder','suspect','evidence','secret','crime','witness',
        'alibi','motive','case','conspiracy','solve','puzzle','code','hidden',
        'truth','forensic','investigate','noir','heist','police','cop','inspector',
        'victim','corpse','body','alley','rain','rainy','theft','stolen',
        'owner','blackmail','private eye','revolver','fingerprint','interrogation'
    ],
    'adventure': [
        'journey','explore','treasure','map','wilderness','mountain','ocean',
        'island','pirate','expedition','survival','ruins','discover','cave',
        'river','desert','jungle','compass','camp','climb','voyage','ancient',
        'relic','artifact','tomb','safari','uncharted','canyon','frontier','sailor'
    ],
}

# ── Anti-repetition ring buffer ───────────────────────────────────────────────

class _RecentTracker:
    """Tracks recently used fragment indices to prevent repetition."""
    __slots__ = ('_used',)
    def __init__(self):
        self._used = {}  # pool_name -> deque of recent indices

    def pick(self, pool_name, pool):
        """Pick a random item from pool, avoiding recent picks."""
        if not pool:
            return ''
        from collections import deque
        recent = self._used.setdefault(pool_name, deque(maxlen=max(3, len(pool)//2)))
        available = [i for i in range(len(pool)) if i not in recent]
        if not available:
            recent.clear()
            available = list(range(len(pool)))
        idx = random.choice(available)
        recent.append(idx)
        return pool[idx]

# Global tracker instance — persists across calls within same server process
_tracker = _RecentTracker()

def _pick(pool, name=None):
    """Pick from pool with anti-repetition if name given."""
    if name:
        return _tracker.pick(name, pool)
    return random.choice(pool) if pool else ''

def _extract_keywords(text):
    """Pull meaningful nouns/adjectives from player input for story integration."""
    if not text:
        return []
    stop = {'i','the','a','an','to','and','or','but','in','on','at','for','of','is',
            'it','my','me','do','go','up','so','if','by','no','am','be','we','us',
            'this','that','with','from','into','what','them','their','there','here',
            'just','more','some','very','want','try','see','take','make','get','let',
            'hey','hello','hi','yes','ok','okay','well','now','then','how','why','when',
            'where','who','which','are','was','were','will','would','can','could','should',
            'have','has','had','not','all','any','one','out','about','like','know','think',
            'look','good','bad','start','begin','end','stop','please','help','fuck','shit'}
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return [w for w in words if w not in stop and len(w) > 3][:6]

def _parse_player_identity(opening):
    """Infer role, drive, wound, and voice from the player's premise."""
    text = opening or ''
    lower = text.lower()

    role = None
    for candidate in PLAYER_ROLES:
        if re.search(rf'\b{re.escape(candidate)}\b', lower):
            role = candidate
            break
    if not role:
        for candidate, keywords in ROLE_KEYWORDS.items():
            if any(keyword in lower for keyword in keywords):
                role = candidate
                break
    role = role or 'wanderer'

    drive = 'survival'
    for candidate, keywords in DRIVE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            drive = candidate
            break

    wound = _extract_player_wound(text, role, drive)

    voice = 'careful'
    for candidate, keywords in VOICE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            voice = candidate
            break

    return {'role': role, 'drive': drive, 'wound': wound, 'voice': voice}

def _extract_player_wound(opening, role, drive):
    """Turn player premise into a visceral recurring wound."""
    lower = (opening or '').lower()
    if ('army' in lower and 'death' in lower) or ('maps' in lower and 'death' in lower):
        return 'the memory of the lives swallowed by your wrong map'
    if any(word in lower for word in ('ship', 'sea', 'crew', 'drowned')):
        return 'the cold salt-spray that took your final command'
    if any(word in lower for word in ('betrayed', 'oath', 'cast out', 'banished')):
        return 'the cold sting of the broken oath'
    if any(word in lower for word in ('debt', 'owed', 'price')):
        return 'the unpaid debt that keeps finding new collectors'
    if any(word in lower for word in ('lost', 'home', 'homeland')):
        return 'the home you cannot return to'

    match = re.search(r'(?:whose|where|when|after|because)\s+([^.]+)', opening or '', re.I)
    if match:
        phrase = match.group(1).strip()
        phrase = re.sub(r'\s+', ' ', phrase)
        if phrase:
            return phrase[:140]

    role_wounds = {
        'cartographer': 'the line you drew that someone else bled across',
        'healer': 'the pulse you could not bring back',
        'deserter': 'the order you left behind still marching in your sleep',
        'spy': 'the secret that outlived everyone meant to hear it',
        'thief': 'the hand you failed to pull from danger',
        'priest': 'the prayer that did not answer when named',
        'knight': 'the vow that broke before the blade did',
        'mercenary': 'the contract whose price keeps increasing',
        'survivor': 'the empty place where the others should be',
    }
    return role_wounds.get(role, f'the old {drive} that has not forgiven you')

def _recast_to_second_person(opening):
    """Recast a player premise into embodied second-person prose."""
    text = (opening or '').strip()
    if not text:
        return "You arrive with no name the road is willing to trust"
    replacements = [
        (r"\bI\s+am\s+a\b", "You are a"),
        (r"\bI\s+am\s+an\b", "You are an"),
        (r"\bI'm\s+a\b", "You are a"),
        (r"\bI'm\s+an\b", "You are an"),
        (r"\bI\s+am\b", "You are"),
        (r"\bI'm\b", "You are"),
        (r"\bI\s+was\b", "You were"),
        (r"\bI\s+have\b", "You have"),
        (r"\bI\s+had\b", "You had"),
        (r"\bI\s+carry\b", "You carry"),
        (r"\bI\s+lost\b", "You lost"),
        (r"\bI\b", "you"),
        (r"\bmyself\b", "yourself"),
        (r"\bmy\b", "your"),
        (r"\bmine\b", "yours"),
        (r"\bme\b", "you"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)

    if not text.lower().startswith("you "):
        m = re.match(r"^(a|an)\s+(.*)", text, flags=re.I)
        if m:
            art, rest = m.group(1), m.group(2)
            rest = re.sub(r"\bsearches\b", "searching", rest, flags=re.I)
            rest = re.sub(r"\bwalks\b", "walking", rest, flags=re.I)
            rest = re.sub(r"\bfollows\b", "following", rest, flags=re.I)
            rest = re.sub(r"\bcrosses\b", "crossing", rest, flags=re.I)
            rest = re.sub(r"\blooks\b", "looking", rest, flags=re.I)
            rest = re.sub(r"\bhunts\b", "hunting", rest, flags=re.I)
            rest = re.sub(r"\btries\b", "trying", rest, flags=re.I)
            rest = re.sub(r"\bopens\b", "opening", rest, flags=re.I)
            rest = re.sub(r"\bcarries\b", "carrying", rest, flags=re.I)
            rest = re.sub(r"\bgathers\b", "gathering", rest, flags=re.I)
            rest = re.sub(r"\bseeks\b", "seeking", rest, flags=re.I)
            rest = re.sub(r"\btravels\b", "travelling", rest, flags=re.I)
            rest = re.sub(r"\bescapes\b", "escaping", rest, flags=re.I)
            rest = re.sub(r"\bhis\b", "your", rest, flags=re.I)
            rest = re.sub(r"\bher\b", "your", rest, flags=re.I)
            rest = re.sub(r"\bits\b", "your", rest, flags=re.I)
            text = f"You are {art.lower()} {rest}"

    text = re.sub(r'\s+', ' ', text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.rstrip('.')

def _identity_opening_sentence(state, opening):
    """Build the authored-feeling first sentence from player identity."""
    recast = _recast_to_second_person(opening)
    role = state.get('player_role', 'wanderer')
    context = ROLE_CONTEXT.get(role, ROLE_CONTEXT.get('wanderer', ''))
    wound = state.get('player_wound', 'what the road has not asked about yet')
    if wound and wound not in ('the old hurt', 'the old road', 'survival'):
        return f"{recast}. {context} Beneath it all waits {wound}."
    return f"{recast}. {context}"

def _identity_callback_sentence(state):
    """Surface role, drive, or wound on structural turns."""
    turn = state.get('turn', 0)
    role = state.get('player_role', 'wanderer')
    drive = state.get('player_drive', 'survival')
    wound = state.get('player_wound', 'the old hurt')
    tension = state.get('tension', 0.5)
    phase = state.get('arc_phase', 'setup')
    parts = []
    if turn and turn % 4 == 0 and 'ROLE_CALLBACKS' in globals():
        parts.append(_pick(ROLE_CALLBACKS, 'role_cb').format(role=role))
    if (tension > 0.72 or phase == 'climax') and 'DRIVE_CALLBACKS' in globals():
        parts.append(_pick(DRIVE_CALLBACKS, 'drive_cb').format(drive=drive))
    if turn and turn % 8 == 0 and 'WOUND_CALLBACKS' in globals():
        parts.append(_pick(WOUND_CALLBACKS, 'wound_cb').format(wound=wound))
    return ' '.join(parts)

def _npc_memory_sentence(npc_record):
    """Describe relationship memory without exposing numeric disposition."""
    relationship = npc_record.get('relationship', 'neutral')
    reactions = globals().get('NPC_MEMORY_REACTIONS', {})
    if relationship in reactions:
        return _pick(reactions[relationship], f'npc_mem_{relationship}')
    if relationship == 'hostile':
        return "They remember enough to save their warmth for someone else."
    if relationship == 'ally':
        return "They remember your better choices and make no performance of it."
    return "They measure you against the version of you that reached them first."

def _format_npc_tic(tic):
    """Normalize stored NPC tics from older saves into complete sentences."""
    if not tic:
        return ''
    text = tic.strip().rstrip('.')
    lower = text.lower()
    if lower.startswith(('they ', 'their ')):
        return text[0].upper() + text[1:] + '.'
    verb_map = {
        'touches': 'touch', 'counts': 'count', 'rubs': 'rub', 'pauses': 'pause',
        'keeps': 'keep', 'folds': 'fold', 'checks': 'check', 'presses': 'press',
        'speaks': 'speak', 'holds': 'hold', 'smiles': 'smile', 'watches': 'watch',
        'moves': 'move', 'taps': 'tap', 'breathes': 'breathe',
    }
    first, _, rest = text.partition(' ')
    first = verb_map.get(first.lower(), first)
    return f"They {first} {rest}".strip() + '.'

def _npc_dialogue_line(npc_record):
    """Build persistent NPC dialogue from motive, secret, and relationship."""
    relationship = npc_record.get('relationship', 'neutral')
    if relationship == 'hostile':
        return f"\"I know what follows you,\" {npc_record['name'].split(',')[0]} says. \"Do not bring it nearer.\""
    if relationship == 'ally':
        return f"\"I kept one answer back for you,\" {npc_record['name'].split(',')[0]} says. \"It may cost us both.\""
    line = _pick(globals().get('NPC_DIALOGUE', []), 'npc_dialogue') or '"Tell me what you noticed, not what you hoped to see."'
    return line

def _scene_context(state, beat=None, intent=None, action=None):
    """Build the concrete facts every prose line and choice must obey."""
    location = state.get('location', 'the road')
    description = state.get('location_desc', 'a dangerous stretch of road')
    world = state.get('world', {})
    region = world.get('current_region', 'the road')
    region_data = _current_region_data(state)
    faction = region_data.get('faction', 'locals')
    weather = world.get('weather', 'still air')
    time_slot = world.get('time', {}).get('slot', 'day')
    action_terms = _extract_keywords(action)
    category = _location_category(location)
    features = _scene_features(location, description, action_terms, category)
    loc_state = state.setdefault('location_states', {}).setdefault(
        location, _default_location_state(state, location)
    )
    npc_name = state.get('last_npc') if beat == 'encounter' or state.get('last_npc') in state.get('continuity', {}).get('npcs', {}) else None
    npc_record = _get_or_create_npc_record(state, npc_name) if npc_name else None
    inventory_items = [item.get('name') for item in state.get('inventory', {}).get('items', []) if item.get('name')]
    current_object = _current_scene_object(state, action_terms, features, inventory_items)
    return {
        'beat': beat or state.get('last_beat') or 'discovery',
        'intent': intent or 'explore',
        'action': action or '',
        'action_terms': action_terms,
        'location': location,
        'description': description,
        'region': region,
        'faction': faction,
        'weather': weather,
        'time_slot': time_slot,
        'category': category,
        'features': features,
        'object': current_object,
        'npc': npc_record,
        'loc_state': loc_state,
        'role': state.get('player_role', 'wanderer'),
        'drive': state.get('player_drive', 'survival'),
        'wound': state.get('player_wound', 'the old wound'),
        'reputation': world.get('reputation', {}).get(region, 'unknown'),
        'inventory_items': inventory_items,
    }

def _scene_features(location, description, action_terms, category):
    """Pick concrete scene nouns from the actual location, description, and action."""
    features = []
    source = f"{location} {description}"
    for word in _extract_keywords(source):
        if word not in features:
            features.append(word)
    for term in action_terms:
        if term not in features:
            features.append(term)
    category_features = {
        'road': ['milestone', 'ruts', 'ditch'],
        'settlement': ['threshold', 'window', 'market'],
        'ruin': ['lintel', 'floor', 'old marks'],
        'wilderness': ['track', 'tree line', 'mud'],
        'interior': ['door', 'hearth', 'floorboards'],
    }
    for feature in category_features.get(category, ['track', 'threshold']):
        if feature not in features:
            features.append(feature)
    return features[:8]

def _current_scene_object(state, action_terms, features, inventory_items):
    """Choose an object that is actually present, carried, or named by the action."""
    if action_terms:
        for term in action_terms:
            if term in ('map', 'maps', 'milestone', 'ledger', 'door', 'gate', 'road', 'witness', 'airlock', 'terminal', 'console', 'deck', 'altar', 'relic'):
                return term
    if state.get('player_role') == 'cartographer':
        return 'map'
    if inventory_items:
        return inventory_items[-1]

    adjective_blocklist = {
        'orbital', 'rainy', 'neon', 'drowned', 'frost-bitten', 'war-torn',
        'stolen', 'stranded', 'disgraced', 'vanished', 'plague', 'inland',
        'evil', 'lost', 'dark', 'ancient', 'red', 'cold', 'mysterious',
        'heavy', 'silent', 'black', 'narrow', 'deep', 'ruined', 'cracked',
        'wet', 'broken', 'old', 'quiet', 'still', 'sour', 'thin', 'hard'
    }
    candidate_features = [f for f in features if f.lower() not in adjective_blocklist and len(f) > 2]
    if candidate_features:
        loc = state.get('location', '').lower()
        distinct = [f for f in candidate_features if f.lower() != loc]
        return distinct[0] if distinct else candidate_features[0]
    return state.get('location', 'road').split()[-1]

def _scene_anchor_sentence(ctx):
    """Introduce or re-anchor the concrete scene."""
    loc = ctx['location']
    desc = ctx['description']
    region = ctx['region']
    faction = ctx['faction']
    weather = ctx['weather']
    time_slot = ctx['time_slot']
    return (
        f"You are at the {loc}, {desc}. "
        f"In {region}, {time_slot} brings {weather}, and {faction} are the nearest power with a memory."
    )

def _action_ack_sentence(ctx):
    """Acknowledge the player's action using only scene-supported nouns."""
    action = ctx.get('action', '').strip()
    obj = ctx['object']
    loc = ctx['location']
    role = ctx['role']
    if not action:
        return f"You take stock of the {loc}, letting the {obj} become the center of the moment."
    if ctx['intent'] == 'aggressive':
        return f"You turn the action toward force at the {loc}, choosing the {obj} before the road can offer a gentler answer."
    if ctx['intent'] == 'social' and ctx.get('npc'):
        return f"You address {ctx['npc']['name']} with the {obj} still between you and the truth."
    if ctx['intent'] == 'cautious':
        return f"You slow yourself at the {loc}, checking the {obj} and the nearest exits before committing."
    if ctx['intent'] == 'move':
        return f"You move through the {loc} by the line the {role} in you trusts least."
    if ctx['intent'] == 'use_item':
        return f"You bring the {obj} into the open and test what it can honestly change here."
    return f"You study the {obj} at the {loc}, looking for the part of the scene that refuses to fit."

def _beat_sentence(ctx):
    """Render the beat as a concrete development in the current scene."""
    beat = ctx['beat']
    loc = ctx['location']
    obj = ctx['object']
    faction = ctx['faction']
    feature = ctx['features'][0] if ctx['features'] else obj
    if beat == 'encounter' and ctx.get('npc'):
        npc = ctx['npc']
        return (
            f"{npc['name']} waits near the {feature}. {_format_npc_tic(npc.get('tic'))} "
            f"{_npc_memory_sentence(npc)} They want {npc['want']}, and they know enough about you to be careful. "
            f"{_npc_dialogue_line(npc)}"
        ).replace('  ', ' ').strip()
    if beat == 'obstacle':
        return f"The way through the {loc} is blocked at the {feature}; getting past it will leave evidence."
    if beat == 'revelation':
        return f"The {obj} gives up a practical truth: someone used this place recently, and {faction} will care who noticed."
    if beat == 'transition':
        return f"A route out of the {loc} becomes visible, but it runs through ground your old map marked uncertain."
    if beat == 'conflict':
        return f"The danger at the {loc} stops being atmospheric and chooses a position near the {feature}."
    if beat == 'rest':
        return f"For a short while, the {loc} gives you cover enough to count wounds, supplies, and lies."
    return f"The {feature} at the {loc} answers your attention with one concrete detail you can use."

def _location_return_sentence(ctx):
    """Acknowledge revisits and location changes."""
    loc_state = ctx.get('loc_state') or {}
    visits = loc_state.get('last_visited', 0)
    history = [h for h in loc_state.get('events', []) if h and h != 'first marked on your map']
    changes = loc_state.get('changes', [])
    if history and visits < ctx.get('turn', 999999):
        return f"You have been here before: {history[-1]}. The {ctx['location']} has kept the evidence."
    if changes:
        return f"The {ctx['location']} is not as it was; {changes[-1]}."
    return ''

def _grounded_world_sentence(state, ctx):
    """Describe world state without importing unrelated locations."""
    faction_score = state.get('faction_dispositions', {}).get(ctx['faction'], 0)
    feeling = 'watching for a reason to trust you' if faction_score > 0 else 'less patient with your name' if faction_score < 0 else 'still undecided about you'
    return f"Here, your reputation is {ctx['reputation']}, and {ctx['faction']} are {feeling}."

def _contextual_hook(state, phase=None):
    """End a scene with a hook that follows from current state."""
    ctx = state.get('current_scene') or _scene_context(state, beat=state.get('last_beat'), intent='explore')
    due = state.get('consequence_queue', [])
    if due:
        entry = due[0]
        return f"Before you can leave the {ctx['location']}, you realize {entry.get('heard_by', 'rumour')} may bring this back sooner than mercy would."
    if ctx.get('npc'):
        return f"{ctx['npc']['name'].split(',')[0]} notices what you noticed, and waits to see whether you lie."
    if ctx['role'] == 'cartographer':
        return f"The line on your map and the line before your boots disagree."
    if state.get('surfaced_consequences'):
        return f"The {ctx['location']} has made the consequence visible; now you have to answer it."
    return f"The next useful truth is still somewhere inside the {ctx['location']}."

def _clean_sentence(sentence):
    """Normalize one generated sentence without changing its meaning."""
    text = re.sub(r'\s+', ' ', str(sentence or '')).strip()
    if not text:
        return ''
    while text.endswith('..') and not text.endswith('...'):
        text = text[:-1]
    if text[-1] not in '.!?"\'':
        text += '.'
    return text[0].upper() + text[1:]

def _validate_choices(state, choices, ctx):
    """Keep only choices supported by current scene facts, then refill if needed."""
    support = {
        ctx['location'].lower(),
        ctx['region'].lower(),
        ctx['faction'].lower(),
        ctx['role'].lower(),
        ctx['object'].lower(),
    }
    support.update(term.lower() for term in ctx.get('features', []))
    support.update(term.lower() for term in ctx.get('action_terms', []))
    unsupported = {
        'hidden mechanism', 'concealed space', 'deeper pattern', 'what lies beyond',
        'immediate threat', 'exposed flank', 'escape route', 'the object',
        'gain an advantage', 'unfamiliar territory',
    }
    grounded = []
    for choice in choices:
        lower = choice.lower()
        if any(phrase in lower for phrase in unsupported):
            continue
        if any(term and term in lower for term in support):
            if choice not in grounded:
                grounded.append(choice)
    for fallback in _fallback_choices(ctx):
        if fallback not in grounded:
            grounded.append(fallback)
        if len(grounded) >= 4:
            break
    return grounded[:5]

def _fallback_choices(ctx):
    """Scene-supported choices used when a generated option fails validation."""
    loc = ctx['location']
    obj = ctx['object']
    role = ctx['role']
    faction = ctx['faction']
    region = ctx['region']
    return [
        f"Use your {role}'s eye to read the {obj} at the {loc}",
        f"Mark the safest line through the {loc} before {faction} notices",
        f"Compare the {loc} against what your map claims about {region}",
        f"Leave a sign at the {loc} so this mistake is not repeated",
    ]

# ── Main paragraph composer ──────────────────────────────────────────────────

def compose_paragraph(state, beat, intent, action):
    """Compose a grounded scene using Dynamic Sequence Templates and state facts."""
    ctx = _scene_context(state, beat=beat, intent=intent, action=action)
    ctx['turn'] = state.get('turn', 0)
    state['current_scene'] = ctx

    # The older four-part templates were mechanically consistent but made every
    # turn sound alike. Lead with the player's concrete action and vary the
    # dramatic lens instead; the existing state systems still supply continuity.
    return _compose_richer_scene(state, ctx, beat, intent, action)


def _compose_richer_scene(state, ctx, beat, intent, action):
    ctx = LoreManager.enrich_scene_context(state, ctx)
    loc = ctx['location']
    desc = ctx.get('lore_environment') or ctx['description']
    feature = ctx['features'][0] if ctx['features'] else ctx['object']
    obj = ctx['object']
    weather = ctx['weather']
    faction = ctx['faction']
    region = ctx['region']
    role = ctx.get('role', 'wanderer')
    action_text = (action or 'look around').strip().rstrip('.')
    turn = state.get('turn', 1)
    phase = state.get('arc_phase', 'setup')

    phase_formats = {
        'setup': ['reflective', 'sensory_first', 'observational'],
        'rising': ['observational', 'action_first', 'tense'],
        'climax': ['tense', 'action_first'],
        'falling': ['action_first', 'reflective'],
    }
    preferred = phase_formats.get(phase, ['reflective', 'sensory_first', 'observational'])
    ctx['template_format'] = preferred[turn % len(preferred)]

    openings = {
        'explore': [
            f"You scan the immediate ground at the {loc}, parsing {desc} for details that don't match the background.",
            f"You test your footing at the {loc}, letting your senses adjust to the shifting {weather}.",
            f"Under the {weather}, the {loc} presents a sharp contrast: {desc}, dominated by {feature}.",
            f"You move cautiously through the {loc}, refusing to accept the quiet at face value.",
        ],
        'cautious': [
            f"Keeping to the shadows of the {loc}, you track the sightlines around {feature}.",
            f"You advance with measured steps across {desc}, checking for observers or concealed ambushes.",
            f"You hold still at the {loc}, letting the ambient sounds of {weather} filter past your focus.",
        ],
        'social': [
            f"Your voice cuts through the {weather} around the {loc}, seeking an answer from whoever watches.",
            f"You step into the open near {feature}, projecting deliberate calm across the {loc}.",
            f"You make your presence known at the {loc}, reading the space for how {faction} responds.",
        ],
        'aggressive': [
            f"You seize the initiative at the {loc}, putting direct pressure on {feature}.",
            f"Restraint gives way to decisive action as you take commanding position at the {loc}.",
            f"You close the distance across {desc}, daring anything in the {loc} to bar your path.",
        ],
        'move': [
            f"Leaving the immediate threshold of the {loc} behind, you push into the open line across {desc}.",
            f"You stay in motion through {desc}, keeping {feature} between yourself and potential pursuit.",
            f"The route through the {loc} narrows, carrying you forward under the {weather}.",
        ],
        'use_item': [
            f"You bring your {obj} to bear at the {loc}, using its specific properties against {feature}.",
            f"The weight of the {obj} in your grip changes how you approach the problem at the {loc}.",
            f"Putting your gear to practical use, you employ the {obj} to clear a path through {desc}.",
        ],
    }

    concise_action = (action or 'look around').strip().rstrip('.')
    concise_action = re.sub(r'^(to\s+|you\s+)', '', concise_action.lower())
    if len(concise_action) > 35:
        words = concise_action.split()
        concise_action = ' '.join(words[:4])
    concise_action = re.sub(r'\s+(at|in|on|with|to|from|by|for|of|the|a|an)\s*$', '', concise_action)

    action_variants = [
        f"Your decision to {concise_action} shifts the immediate momentum at the {loc}.",
        f"Carrying out your intent to {concise_action}, you force the scene to yield a concrete response.",
        f"As you {concise_action}, an overlooked detail near {feature} comes into sharp focus.",
        f"You commit to {concise_action}; the tension around {feature} adjusts in your favor.",
        f"Taking the initiative to {concise_action}, you establish control over the immediate ground.",
    ]

    beat_lines = {
        'encounter': f"Movement catches your eye near the {feature}: someone steps into your awareness.",
        'obstacle': f"A deliberate blockage at the {feature} arrests your progress; someone clearly wanted this route barred.",
        'revelation': f"A telling sign near {feature} clarifies the situation: fresh marks point to recent activity by {faction}.",
        'transition': f"Beyond the {loc}, a viable thoroughfare toward {region} opens through the {weather}.",
        'conflict': f"Hostile intent flares around the {feature}; you have mere seconds to defend your position against {faction}.",
        'rest': f"A moment of respite settles over the {loc}, giving you quiet shelter beneath {feature}.",
        'discovery': f"At the base of the {feature}, you uncover a tangible clue left by a previous crossing.",
    }

    chosen = random.choice(openings.get(intent, openings['explore']))
    action_line = action_variants[turn % len(action_variants)]
    line = beat_lines.get(beat, beat_lines['discovery'])
    if beat == 'encounter' and ctx.get('npc'):
        npc = ctx['npc']
        genre = state.get('genre', 'fantasy')
        comm_mode = ctx.get('comm_mode') or ('radio_comms' if genre == 'scifi' else 'feline_sensory' if genre == 'feline' else 'cyber_link' if genre == 'cyberpunk' else 'spoken')
        dialogue = _npc_dialogue_line_adaptive(state, npc, ctx)
        if comm_mode == 'radio_comms' or genre == 'scifi':
            line = f"A signal transmission from {npc['name']} breaks through on your helmet receiver. {dialogue}"
        elif comm_mode == 'feline_sensory' or genre == 'feline':
            line = f"A sudden movement draws your ears back: {npc['name']} watches from nearby. {dialogue}"
        elif comm_mode == 'cyber_link' or genre == 'cyberpunk':
            line = f"An encrypted neural packet pings from {npc['name']}. {dialogue}"
        else:
            line = f"{npc['name']} steps into view near the {feature}. {dialogue}"

    # Weave premise naturally and atmospherically
    harvest = state.get('opening_keywords_harvest', {})
    nouns = harvest.get('nouns', [])
    target_nouns = [n for n in nouns if n != role]
    target = target_nouns[-1] if target_nouns else (nouns[0] if nouns else '')
    premise_anchor = ''
    if target:
        is_proper = target.lower() in ('jupiter', 'mars', 'europa', 'earth', 'tokyo', 'london', 'venus', 'saturn', 'neptune')
        if target.lower() == 'orbit':
            premise_anchor = f"The unforgiving physics of orbital trajectory sharpen your resolve in the quiet of the {loc}."
        elif is_proper:
            premise_anchor = f"The thought of {target.title()} sharpens your resolve in the quiet of the {loc}."
        elif target in PERSON_NOUNS:
            premise_anchor = f"The search for {PREMISE_NOUN_PHRASING.get(target, (f'your {target}',))[0]} remains your guiding compass."
        elif target in PLACE_NOUNS:
            premise_anchor = f"Every step through the {loc} brings you closer to {PREMISE_NOUN_PHRASING.get(target, (f'the {target}',))[0]}."
        elif target in ('cure', 'oxygen', 'food', 'water', 'supplies'):
            premise_anchor = f"The urgent necessity of {PREMISE_NOUN_PHRASING.get(target, (f'the {target}',))[0]} drives your every choice."
        else:
            phrased = PREMISE_NOUN_PHRASING.get(target, (f"the {target}",))[0]
            premise_anchor = f"The thought of {phrased} sharpens your resolve in the quiet of the {loc}."

    motif = _get_motif_text(state)
    hooks = [
        f"The {faction} would care about what happened here; your next move must be deliberate.",
        f"The {weather} continues to shift over {desc}, and whatever waits in {region} will not wait forever.",
        f"The path ahead offers both risk and opportunity; you must choose how to press the advantage.",
        f"The silence around the {loc} is temporary, and the consequences of your choice are already setting in.",
    ]
    hook = hooks[(turn + len(state.get('events', []))) % len(hooks)]

    parts = [chosen, action_line, line]
    if premise_anchor:
        parts.append(premise_anchor)
    parts.append(motif)

    pending_item = state.pop('_pending_item_use', None)
    if pending_item:
        parts.insert(2, pending_item)

    stat_note = _stat_pressure_sentence(state, intent, beat)
    if stat_note:
        parts.append(stat_note)

    for pending_line in state.pop('_pending_consequence_lines', []) or []:
        parts.append(pending_line)

    pivot_line = state.pop('_pending_pivot_line', None)
    if pivot_line:
        parts.append(pivot_line)

    ambient_line = state.pop('_pending_ambient_line', None)
    if ambient_line:
        parts.append(f"At the {loc}, {ambient_line[0].lower() + ambient_line[1:]}")

    identity_note = _identity_callback_sentence(state)
    if identity_note:
        parts.append(identity_note)

    parts.append(hook)

    story = ' '.join(_clean_sentence(p) for p in parts if p)
    return _shape_scene_prose(state, story, phase)


# ── Choice generator ─────────────────────────────────────────────────────────

def generate_choices(state, beat):
    """Build choices from the concrete scene context, then validate support."""
    ctx = state.get('current_scene') or _scene_context(state, beat=beat, intent='explore', action=state.get('last_action', ''))
    loc = ctx['location']
    obj = ctx['object']
    obj_gives = 'they give up' if obj.endswith('s') and not obj.endswith('ss') else 'it gives up'
    role = ctx['role']
    faction = ctx['faction']
    region = ctx['region']
    npc = ctx.get('npc')
    tool = ROLE_ITEM_OR_TOOL.get(role, 'map' if role == 'cartographer' else 'instincts')

    choices = []
    if beat == 'encounter' and npc:
        choices.extend([
            f"Ask {npc['name']} what {faction} wants at the {loc}",
            f"Watch {npc['name'].split(',')[0]} while you compare their story to your {tool}",
            f"Offer {npc['name'].split(',')[0]} a cautious truth about the {loc}",
        ])
    elif beat == 'obstacle':
        third_choice = (f"Leave a map mark at the {loc} before forcing passage"
                        if role == 'cartographer'
                        else f"Use your {tool} to find a safer way through the {loc}")
        choices.extend([
            f"Measure the blocked line through the {loc} like a {role}",
            f"Search the {obj} for a safer way past the {loc}",
            third_choice,
        ])
    elif beat == 'revelation':
        choices.extend([
            f"Record what the {obj} proves about {region}",
            f"Decide whether to hide this truth from {faction}",
            f"Compare the {loc} against the mistake that still wounds you",
        ])
    elif beat == 'transition':
        second_choice = (f"Check whether your map lies about the next stretch of {region}"
                         if role == 'cartographer'
                         else f"Check what your {tool} reveals about the next stretch of {region}")
        choices.extend([
            f"Mark the road out of the {loc} before you follow it",
            second_choice,
            f"Leave a warning at the {loc} for anyone following your line",
        ])
    elif beat == 'conflict':
        third_choice = (f"Break away through the part of the {loc} your map still explains"
                        if role == 'cartographer'
                        else f"Break away through the part of the {loc} your {tool} guides you through")
        choices.extend([
            f"Use the {obj} at the {loc} before {faction} can close in",
            f"Hold the line at the {loc} and make your next move visible",
            third_choice,
        ])
    elif beat == 'rest':
        first_choice = (f"Update your map of the {loc} while you still have quiet"
                        if role == 'cartographer'
                        else f"Rely on your {tool} to secure the {loc} while you still have quiet")
        choices.extend([
            first_choice,
            f"Count supplies at the {loc} and decide what can be spared",
            f"Listen for what {faction} are saying about you in {region}",
        ])
    else:
        second_choice = (f"Compare the {loc} against the map you no longer trust"
                         if role == 'cartographer'
                         else f"Scout the {loc} through the lens of a {role}")
        choices.extend([
            f"Study the {obj} at the {loc} until {obj_gives} a usable fact",
            second_choice,
            f"Ask what {faction} would gain by hiding this part of {region}",
        ])

    stats = state.get('character', {}).get('stats', {})
    if stats.get('Lore', 0) >= 4 and beat in ('discovery', 'revelation', 'obstacle'):
        choices.append(_lore_stat_choice(role, loc))
    elif stats.get('Presence', 0) >= 4 and beat == 'encounter':
        choices.append(f"Use your reputation in {region} before {faction} define it for you")
    elif stats.get('Cunning', 0) >= 4 and beat in ('obstacle', 'conflict'):
        choices.append(f"Turn the layout of the {loc} against whoever set this up")
    elif stats.get('Strength', 0) >= 4 and beat in ('conflict', 'obstacle'):
        choices.append(f"Force the hard route through the {loc} and accept the witnesses")

    role_choice = _role_specific_choice(state, beat)
    if role_choice:
        choices.append(role_choice)
    if state.get('consequence_queue') and beat in ('encounter', 'revelation', 'rest'):
        next_due = state['consequence_queue'][0]
        choices.append(f"Prepare at the {loc} for what {next_due.get('heard_by', 'rumour')} is carrying back toward you")

    choices = _generate_choices_premise_aware(state, beat, choices, ctx)
    return _validate_choices(state, choices, ctx)

def _lore_stat_choice(role, location):
    """Render high-Lore options without replacing the player's identity."""
    if role == 'scholar':
        return f"Read the old signs at the {location} with a scholar's patience"
    if role == 'cartographer':
        return f"Read the old signs at the {location} with a mapmaker's patience"
    if role == 'priest':
        return f"Read the old signs at the {location} as a disputed rite"
    return f"Read the old signs at the {location} with hard-won patience"

def _role_specific_choice(state, beat):
    """Offer a fourth or fifth choice grounded in player identity."""
    role = state.get('player_role', 'wanderer')
    location = state.get('location', 'road')
    region = state.get('world', {}).get('current_region', 'region')
    npc = state.get('last_npc', 'the stranger')
    table = {
        'cartographer': {
            'discovery': f"Compare the {location} against the map you no longer trust",
            'transition': f"Mark the false road out of the {location} before it harms someone else",
            'obstacle': f"Measure the obstruction at the {location} for the line it interrupts",
        },
        'healer': {
            'encounter': f"Read {npc}'s breathing before you answer",
            'conflict': f"Look for the wound at the {location} that can end this without another death",
            'rest': f"Spend your dwindling herbs at the {location} on what still has a chance",
        },
        'deserter': {
            'encounter': f"Study {npc}'s formation for the officer behind it",
            'transition': f"Leave no track out of the {location} a regiment could love",
            'conflict': f"Break the encirclement at the {location} before it remembers your old drills",
        },
        'spy': {
            'encounter': f"Feed {npc} a useful lie and watch what they protect",
            'discovery': f"Separate the true signal at the {location} from the public noise",
            'revelation': f"Burn the false pattern in {region} before it burns you",
        },
        'priest': {
            'encounter': f"Invoke the old obligation at the {location} and listen for who flinches",
            'revelation': f"Name the sin beneath the local custom in {region}",
            'rest': f"Make a quiet rite from what the {location} has left you",
        },
        'thief': {
            'obstacle': f"Let the lock at the {location} teach you who built the fear around it",
            'encounter': f"Watch {npc}'s pockets while they watch your face",
            'discovery': f"Find what everyone at the {location} assumes is already gone",
        },
        'astronaut': {
            'discovery': f"Scan the {location} for life support readings or structural integrity",
            'obstacle': f"Bypass the hazard at the {location} before suit reserves drop",
            'revelation': f"Transmit anomalous findings from the {location} across open frequencies",
        },
        'hacker': {
            'discovery': f"Tap into the local subnet near the {location} for encrypted nodes",
            'obstacle': f"Override the security lock at the {location} with your deck",
            'revelation': f"Trace the origin of the rogue protocol discovered at the {location}",
        },
        'detective': {
            'discovery': f"Dust the {location} for latent prints or overlooked evidence",
            'encounter': f"Press {npc} on their alibi regarding the {location}",
            'revelation': f"Piece together the timeline that connects {region} to the crime",
        },
        'cat': {
            'discovery': f"Sniff around the {location} for familiar scents or warmth",
            'obstacle': f"Leap quietly over the obstacle at the {location}",
            'rest': f"Curl into a hidden nook at the {location} and listen attentively",
        },
        'pilot': {
            'discovery': f"Survey the terrain at the {location} for emergency landing clearance",
            'obstacle': f"Navigate the hazardous passage at the {location} with steady hands",
            'revelation': f"Recalibrate navigation vectors against landmarks in {region}",
        },
        'witch': {
            'discovery': f"Read the subtle omens lingering around the {location}",
            'encounter': f"Whisper a binding verse to see if {npc} recoils",
            'rest': f"Brew a calming infusion at the {location} using gathered herbs",
        },
        'scientist': {
            'discovery': f"Collect environmental samples from the {location} for analysis",
            'obstacle': f"Formulate a rational method to circumvent the hazard at the {location}",
            'revelation': f"Synthesize your notes on the anomaly discovered in {region}",
        },
        'ranger': {
            'discovery': f"Track the freshest footprints crossing the {location}",
            'obstacle': f"Find a concealed stalker's trail around the {location}",
            'transition': f"Mark the terrain ahead from the highest vantage near the {location}",
        },
        'assassin': {
            'discovery': f"Identify all blind spots and lethal angles overlooking the {location}",
            'encounter': f"Position yourself behind {npc}'s guard before speaking",
            'conflict': f"Strike swiftly from the shadows of the {location}",
        },
        'engineer': {
            'discovery': f"Inspect the mechanical conduits and joints near the {location}",
            'obstacle': f"Rig a makeshift bypass for the broken machinery at the {location}",
            'rest': f"Service and tune your gear beside the shelter of the {location}",
        },
    }
    return table.get(role, {}).get(beat)


def _ensure_state_defaults(state, new_game=False):
    """Hydrate missing RPG systems while preserving older save fields."""
    state = state or {}
    genre = state.get('genre') or 'fantasy'
    if genre not in GENRE_LOCATIONS:
        genre = 'fantasy'
        state['genre'] = genre

    state.setdefault('prev_locations', [])
    state.setdefault('npc_tags', {})
    state.setdefault('items_found', [])
    state.setdefault('events', [])
    state.setdefault('behavior_counts', {'aggressive':0,'cautious':0,'social':0,'explore':0,'move':0,'use_item':0})
    state['behavior_counts'].setdefault('use_item', 0)
    state.setdefault('dominant_behavior', None)
    state.setdefault('emotion', 'wonder')
    state.setdefault('image_nonce', 0)
    state.setdefault('lore_bias', {})
    state.setdefault('turns_since_location_change', 0)
    identity = _parse_player_identity(state.get('opening', ''))
    state.setdefault('player_role', identity['role'])
    state.setdefault('player_drive', identity['drive'])
    state.setdefault('player_wound', identity['wound'])
    state.setdefault('player_voice', identity['voice'])
    opening = state.get('opening', '')
    state.setdefault('opening_keywords_harvest', _harvest_premise(opening))
    state.setdefault('opening_keywords', _extract_keywords(opening))
    state.setdefault('beat_history', [])
    state.setdefault('branch_history', [])
    state.setdefault('consequence_queue', [])
    state.setdefault('surfaced_consequences', [])
    state.setdefault('pivots_applied', [])
    state.setdefault('unused_pivots', list(PIVOT_TYPES))
    if not state['unused_pivots']:
        state['unused_pivots'] = list(PIVOT_TYPES)
    state.setdefault('location_states', {})
    state.setdefault('faction_dispositions', {})
    state.setdefault('player_knowledge', [])
    state.setdefault('rumour_state', {})
    state.setdefault('prose_memory', {'recent_hooks': [], 'recent_phrases': []})
    state['prose_memory'].setdefault('recent_hooks', [])
    state['prose_memory'].setdefault('recent_phrases', [])
    
    # ── Advanced narrative system structures ──
    state.setdefault('entity_graph', {'nodes': {}, 'edges': []})
    state.setdefault('active_threads', [])
    state.setdefault('scene_card', {
        'objective': 'Explore and understand the surroundings',
        'obstacle': 'None',
        'cast': [],
        'setting': ''
    })
    state.setdefault('memory_graph', {'events': [], 'visits': {}})
    state.setdefault('consequence_graph', {'triggers': []})

    state.setdefault('inventory', _default_inventory())
    inv = state['inventory']
    inv.setdefault('items', [])
    inv.setdefault('gold', 0)
    inv.setdefault('equipped', {})
    for slot in ('weapon', 'armour', 'accessory'):
        inv['equipped'].setdefault(slot, None)

    if 'character' not in state:
        state['character'] = _default_character(identity=identity)
    else:
        character = state['character']
        character.setdefault('name', 'The Unnamed Traveller')
        character.setdefault('stats', _stats_for_identity(identity))
        for stat in STAT_NAMES:
            character['stats'].setdefault(stat, _stats_for_identity(identity)[stat])
        character['creation'] = {'in_progress': False, 'step': 4, 'answers': character.get('creation', {}).get('answers', [])}
    state['character'].setdefault('identity', {
        'role': state.get('player_role'),
        'drive': state.get('player_drive'),
        'wound': state.get('player_wound'),
        'voice': state.get('player_voice'),
    })

    state.setdefault('world', _generate_world(genre, state.get('opening', '')))
    world = state['world']
    world.setdefault('regions', _generate_world(genre, state.get('opening', '')).get('regions', []))
    if not world['regions']:
        world['regions'] = _generate_world(genre, state.get('opening', '')).get('regions', [])
    first_region = world['regions'][0]['name'] if world['regions'] else 'Veldmoor'
    world.setdefault('current_region', first_region)
    world.setdefault('time', {'day': 1, 'slot': 'dawn', 'turns_in_slot': 0})
    world.setdefault('weather', random.choice(WEATHER_STATES))
    world.setdefault('reputation', {r['name']: 'unknown' for r in world['regions']})
    for region in world['regions']:
        world['reputation'].setdefault(region['name'], 'unknown')
    world.setdefault('rumours', _initial_rumours(world['regions']))
    _hydrate_faction_dispositions(state)
    _hydrate_location_states(state)
    _hydrate_rumour_state(state)

    continuity = state.setdefault('continuity', {})
    continuity.setdefault('npcs', {})
    continuity.setdefault('world_flags', {
        'doors_opened': [],
        'enemies_defeated': [],
        'factions_influenced': {},
        'secrets_discovered': [],
    })
    flags = continuity['world_flags']
    flags.setdefault('doors_opened', [])
    flags.setdefault('enemies_defeated', [])
    flags.setdefault('factions_influenced', {})
    flags.setdefault('secrets_discovered', [])
    flags.setdefault('locations_changed', [])
    flags.setdefault('rumours_distorted', [])
    continuity.setdefault('narrative_threads', [])
    continuity.setdefault('location_memory', {})
    continuity.setdefault('cause_effects', [])

    location = state.get('location')
    if location:
        continuity['location_memory'].setdefault(location, {'visits': 0, 'history': ['first marked on your map'], 'last_seen_turn': 0})

    return state

def _hydrate_faction_dispositions(state):
    """Ensure every known faction has a persistent numeric disposition."""
    dispositions = state.setdefault('faction_dispositions', {})
    for faction in REGION_FACTIONS:
        dispositions.setdefault(faction, 0)
    for region in state.get('world', {}).get('regions', []):
        if region.get('faction'):
            dispositions.setdefault(region['faction'], 0)

def _hydrate_location_states(state):
    """Create persistent per-location memory records."""
    location_states = state.setdefault('location_states', {})
    loc = state.get('location')
    if loc:
        location_states.setdefault(loc, _default_location_state(state, loc))
    for old_loc in state.get('prev_locations', [])[-8:]:
        location_states.setdefault(old_loc, _default_location_state(state, old_loc))

def _default_location_state(state, location):
    """Return a location state record for revisits and world changes."""
    region = state.get('world', {}).get('current_region', 'the road')
    faction = _current_region_data(state).get('faction', 'locals') if state.get('world') else 'locals'
    return {
        'events': ['first marked on your map'],
        'faction_presence': faction,
        'accessibility': 'open',
        'last_visited': state.get('turn', 0),
        'atmosphere': state.get('mood', 'mysterious'),
        'region': region,
        'changes': [],
    }

def _hydrate_rumour_state(state):
    """Normalize rumours into persistent distortion records."""
    rumour_state = state.setdefault('rumour_state', {})
    for idx, rumour in enumerate(state.get('world', {}).get('rumours', [])):
        key = rumour.get('id') or f"rumour_{idx}_{rumour.get('region', 'road')}"
        rumour['id'] = key
        rumour_state.setdefault(key, {
            'text': rumour.get('text', ''),
            'region': rumour.get('region'),
            'distortion': 0,
            'heard': bool(rumour.get('heard')),
            'last_spread_turn': 0,
            'carriers': [],
        })


def _default_inventory():
    """Return the empty inventory object used by new and old saves."""
    return {'items': [], 'gold': 0, 'equipped': {'weapon': None, 'armour': None, 'accessory': None}}


def _balanced_stats():
    """Return baseline Roadwarden-style stats."""
    return {'Vitality': 4, 'Resolve': 4, 'Cunning': 3, 'Strength': 3, 'Presence': 3, 'Lore': 2}


def _stats_for_identity(identity):
    """Derive practical stats from the player's stated identity."""
    identity = identity or {}
    role = identity.get('role', 'wanderer')
    drive = identity.get('drive', 'survival')
    stats = dict(STAT_PRESETS.get(role, STAT_PRESETS.get('wanderer', _balanced_stats())))
    role_bonuses = {
        'cartographer': {'Lore': 2, 'Cunning': 1},
        'healer': {'Lore': 1, 'Presence': 1, 'Resolve': 1},
        'deserter': {'Cunning': 1, 'Vitality': 1, 'Resolve': 1},
        'spy': {'Cunning': 2, 'Presence': 1},
        'thief': {'Cunning': 2, 'Vitality': 1},
        'priest': {'Presence': 1, 'Lore': 1, 'Resolve': 1},
        'knight': {'Strength': 1, 'Presence': 1, 'Resolve': 1},
        'mercenary': {'Strength': 1, 'Vitality': 1, 'Cunning': 1},
        'sailor': {'Vitality': 1, 'Resolve': 1, 'Cunning': 1},
        'survivor': {'Vitality': 1, 'Resolve': 2},
        'outcast': {'Cunning': 1, 'Resolve': 1, 'Presence': 1},
        'astronaut': {'Lore': 2, 'Resolve': 1},
        'hacker': {'Cunning': 2, 'Lore': 1},
        'detective': {'Cunning': 1, 'Lore': 1, 'Presence': 1},
        'witch': {'Lore': 2, 'Resolve': 1},
        'cat': {'Cunning': 2, 'Vitality': 1},
        'pilot': {'Resolve': 1, 'Cunning': 1, 'Vitality': 1},
        'scientist': {'Lore': 2, 'Resolve': 1},
        'captain': {'Presence': 2, 'Resolve': 1},
        'ranger': {'Vitality': 1, 'Cunning': 1, 'Resolve': 1},
        'assassin': {'Cunning': 2, 'Strength': 1},
        'engineer': {'Lore': 1, 'Cunning': 1, 'Resolve': 1},
    }
    drive_bonuses = {
        'atonement': {'Resolve': 1, 'Lore': 1},
        'redemption': {'Resolve': 1, 'Presence': 1},
        'grief': {'Resolve': 1},
        'revenge': {'Strength': 1},
        'discovery': {'Lore': 1},
        'escape': {'Cunning': 1},
        'duty': {'Presence': 1},
        'survival': {'Vitality': 1},
    }
    for bonuses in (role_bonuses.get(role, {}), drive_bonuses.get(drive, {})):
        for stat, amount in bonuses.items():
            stats[stat] = min(6, stats.get(stat, 3) + amount)
    for stat in STAT_NAMES:
        stats.setdefault(stat, _balanced_stats()[stat])
    return stats


def _character_name_for_identity(identity):
    """Name the character sheet from the premise without asking a second origin."""
    role = (identity or {}).get('role', 'wanderer')
    names = {
        'cartographer': 'The Disgraced Cartographer',
        'healer': 'The Roadside Healer',
        'deserter': 'The Runaway Soldier',
        'spy': 'The Quiet Informant',
        'thief': 'The Lockwise Traveller',
        'priest': 'The Unanswered Priest',
        'knight': 'The Uncrested Knight',
        'mercenary': 'The Debt-Worn Blade',
        'scholar': 'The Ink-Stained Roadwarden',
        'fighter': 'The Scarred Roadwarden',
        'survivor': 'The Last Witness',
        'outcast': 'The Marked Outcast',
        'sailor': 'The Inland Sailor',
        'exile': 'The Banished Roadwarden',
        'astronaut': 'The Void Walker',
        'hacker': 'The Ghost in the Grid',
        'detective': 'The Rain-Soaked Investigator',
        'witch': 'The Hearth-Bound Witch',
        'cat': 'The Stray Wanderer',
        'pilot': 'The Grounded Pilot',
        'scientist': 'The Field Researcher',
        'captain': 'The Stranded Captain',
        'ranger': 'The Border Ranger',
        'assassin': 'The Shadow Hand',
        'engineer': 'The Machine Smith',
    }
    return names.get(role, 'The Weathered Roadwarden')


def _default_character(new_game=False, identity=None):
    """Return a character object derived from the player's premise."""
    identity = identity or {'role': 'wanderer', 'drive': 'survival', 'wound': 'the old road', 'voice': 'careful'}
    return {
        'name': _character_name_for_identity(identity),
        'stats': _stats_for_identity(identity),
        'creation': {'in_progress': False, 'step': 4, 'answers': []},
        'origin': identity.get('role'),
        'burden': identity.get('wound'),
        'method': identity.get('drive'),
    }


def _generate_world(genre, opening):
    """Generate a persistent small world of named regions."""
    prefixes = GENRE_REGION_PREFIXES.get(genre, REGION_PREFIXES)
    suffixes = GENRE_REGION_SUFFIXES.get(genre, REGION_SUFFIXES)
    geographies = GENRE_REGION_GEOGRAPHY.get(genre, REGION_GEOGRAPHY)
    factions = GENRE_FACTIONS.get(genre, REGION_FACTIONS)

    count = random.randint(3, 5)
    names = []
    for _ in range(count * 2):
        name = random.choice(prefixes) + random.choice(suffixes)
        name = name[0].upper() + name[1:]
        if name not in names:
            names.append(name)
        if len(names) >= count:
            break
    regions = []
    for name in names:
        regions.append({
            'name': name,
            'geography': random.choice(geographies),
            'faction': random.choice(factions),
            'truth': random.choice(['watched', 'starving', 'rebelling', 'haunted', 'sealed', 'for sale']),
        })
    return {
        'name': _world_name(opening, names),
        'regions': regions,
        'current_region': regions[0]['name'] if regions else 'Veldmoor',
        'time': {'day': 1, 'slot': 'dawn', 'turns_in_slot': 0},
        'weather': random.choice(WEATHER_STATES),
        'reputation': {r['name']: 'unknown' for r in regions},
        'rumours': _initial_rumours(regions),
    }


def _world_name(opening, names):
    """Name the generated world from opening keywords and region names."""
    keywords = _extract_keywords(opening)
    if keywords:
        root = keywords[0].capitalize()
        if any(w in (opening or '').lower() for w in ('space', 'mars', 'cyber', 'neon', 'orbit', 'colony', 'station')):
            return f"The {root} Sector"
        return f"The {root} Marches"
    if names:
        return f"The {names[0]} Reach"
    return "The Unmapped Road"


def _initial_rumours(regions):
    """Create persistent regional rumours with uncertain truth."""
    rumours = []
    for idx, region in enumerate(regions or []):
        text = f"They say the road through {region['name']} is {region['truth']} by {region['faction']}."
        rumours.append({
            'text': text,
            'region': region['name'],
            'truth': random.choice([True, False]),
            'heard': idx == 0,
        })
    return rumours


def _advance_world(state, intent, beat):
    """Advance time, weather, region reputation, and rumour availability."""
    world = state['world']
    time = world.setdefault('time', {'day': 1, 'slot': 'dawn', 'turns_in_slot': 0})
    time['turns_in_slot'] = time.get('turns_in_slot', 0) + 1
    if time['turns_in_slot'] >= 2:
        time['turns_in_slot'] = 0
        idx = TIME_SLOTS.index(time.get('slot', 'dawn')) if time.get('slot') in TIME_SLOTS else 0
        idx = (idx + 1) % len(TIME_SLOTS)
        time['slot'] = TIME_SLOTS[idx]
        if time['slot'] == 'dawn':
            time['day'] = time.get('day', 1) + 1
        if random.random() < 0.45:
            world['weather'] = random.choice(WEATHER_STATES)

    region = world.get('current_region')
    rep = world.setdefault('reputation', {})
    rep.setdefault(region, 'unknown')
    if intent == 'aggressive':
        rep[region] = 'feared' if rep[region] != 'hunted' else 'hunted'
    elif intent == 'social' and rep[region] in ('unknown', 'feared'):
        rep[region] = 'trusted'
    elif intent == 'cautious' and rep[region] == 'hunted':
        rep[region] = 'feared'

    if beat == 'encounter':
        unheard = [r for r in world.get('rumours', []) if not r.get('heard')]
        if unheard and random.random() < 0.5:
            random.choice(unheard)['heard'] = True

def _record_branch_event(state, intent, action):
    """Record what the player did, where, who saw it, and who heard."""
    turn = state.get('turn', 0)
    loc = state.get('location', 'the road')
    region = state.get('world', {}).get('current_region', 'the road')
    witness, heard_by = _witness_context(state, intent)
    record = {
        'turn': turn,
        'branch': intent,
        'action': action or '',
        'location': loc,
        'region': region,
        'witnessed_by': witness,
        'heard_by': heard_by,
        'emotional_drive': state.get('player_drive'),
        'role': state.get('player_role'),
    }
    state.setdefault('branch_history', []).append(record)
    del state['branch_history'][:-30]
    return record

def _witness_context(state, intent):
    """Choose witnesses from NPC continuity, factions, and regional traffic."""
    region_data = _current_region_data(state)
    faction = region_data.get('faction', 'locals')
    if state.get('last_npc') and random.random() < 0.55:
        witness = state['last_npc']
    elif intent == 'cautious':
        witness = random.choice(['no one certain', 'a half-seen roof watcher', faction])
    else:
        witness = random.choice([faction, 'a toll child', 'a road seller', 'a hidden scout'])
    heard_by = random.choice([faction, 'market gossip', 'the next inn', 'a courier line', 'pilgrim rumour'])
    return witness, heard_by

def _enqueue_consequence(state, branch_event, intent, beat):
    """Queue delayed consequences from player action and current beat."""
    if intent not in ('aggressive', 'social', 'cautious', 'use_item') and beat not in ('revelation', 'conflict'):
        return None
    turn = state.get('turn', 0)
    loc = branch_event.get('location', state.get('location', 'the road'))
    region = branch_event.get('region', state.get('world', {}).get('current_region', 'the road'))
    faction = _current_region_data(state).get('faction', 'locals')
    delay = random.randint(2, 5)
    consequence_type = {
        'aggressive': 'enemy_created',
        'social': 'ally_remembers',
        'cautious': 'knowledge_uncovered',
        'use_item': 'item_legacy',
    }.get(intent, 'world_reacts')
    descriptions = {
        'enemy_created': f"{faction} begin asking who gave you leave to spill trouble at the {loc}",
        'ally_remembers': f"someone you treated as a person at the {loc} repeats that mercy where it matters",
        'knowledge_uncovered': f"the hidden route you noticed near the {loc} changes who can follow you",
        'item_legacy': f"the use of {state.get('last_item', 'your gear')} at the {loc} wakes an older claim",
        'world_reacts': f"the choice at the {loc} alters the local account of you",
    }
    entry = {
        'type': consequence_type,
        'description': descriptions[consequence_type],
        'due_turn': turn + delay,
        'location': loc,
        'region': region,
        'source_turn': turn,
        'source_action': branch_event.get('action', ''),
        'witnessed_by': branch_event.get('witnessed_by'),
        'heard_by': branch_event.get('heard_by'),
        'intensity': 2 if intent == 'aggressive' else 1,
        'surfaced': False,
    }
    
    ns = NarrativeState(state)
    ns.consequences.queue.append(entry)
    ns.consequences.queue.sort(key=lambda item: item.get('due_turn', 9999))
    
    if intent == 'cautious':
        state.setdefault('player_knowledge', []).append(f"hidden path near {loc}")
        del state['player_knowledge'][:-18]
        ns.consequences.spread_rumor(f"Someone knows the hidden paths near {loc}", 1)
    if intent == 'aggressive':
        state.setdefault('faction_dispositions', {})[faction] = state.setdefault('faction_dispositions', {}).get(faction, 0) - 1
        ns.consequences.add_grudge(faction, 2, f"violence at {loc}")
    elif intent == 'social':
        if 'last_npc' in state:
            ns.consequences.add_debt(state['last_npc'], 1, f"a favor at {loc}")
        state.setdefault('faction_dispositions', {})[faction] = state.setdefault('faction_dispositions', {}).get(faction, 0) + 1
    return entry

def _surface_due_consequences(state):
    """Move due consequences into the current scene."""
    turn = state.get('turn', 0)
    queue = state.setdefault('consequence_queue', [])
    due = [entry for entry in queue if entry.get('due_turn', 9999) <= turn]
    if not due:
        state.pop('_pending_consequence_lines', None)
        return []
    due.sort(key=lambda entry: (entry.get('due_turn', 0), entry.get('source_turn', 0)))
    surfaced_now = due[:2]
    state['consequence_queue'] = [entry for entry in queue if entry not in surfaced_now]
    lines = [_format_consequence(state, entry) for entry in surfaced_now]
    state['_pending_consequence_lines'] = lines
    state.setdefault('surfaced_consequences', []).extend(surfaced_now)
    del state['surfaced_consequences'][:-20]
    return lines

def _format_consequence(state, entry):
    """Render a due consequence as authored prose."""
    pool = globals().get('CONSEQUENCE_FRAGMENTS', [])
    if pool:
        template = _pick(pool, 'consequence_frag')
    else:
        template = "What you did at {location} has reached {region}: {description}"
    return template.format(
        location=entry.get('location', state.get('location', 'the road')),
        region=entry.get('region', state.get('world', {}).get('current_region', 'the road')),
        heard_by=entry.get('heard_by', 'rumour'),
        witnessed_by=entry.get('witnessed_by', 'someone'),
        source_turn=entry.get('source_turn', 0),
        description=entry.get('description', 'the world answers late'),
    )

def _simulate_ambient_world(state, intent, beat):
    """Advance factions, rumours, and offscreen pressure even away from the player."""
    region_data = _current_region_data(state)
    faction = region_data.get('faction', 'locals')
    dispositions = state.setdefault('faction_dispositions', {})
    dispositions.setdefault(faction, 0)
    if beat in ('conflict', 'obstacle') or intent == 'aggressive':
        dispositions[faction] -= 1
    elif intent == 'social':
        dispositions[faction] += 1
    elif intent == 'cautious' and random.random() < 0.35:
        dispositions[faction] += 0

    rumour_state = state.setdefault('rumour_state', {})
    if rumour_state:
        key = random.choice(list(rumour_state.keys()))
        rumour = rumour_state[key]
        if state.get('turn', 0) - rumour.get('last_spread_turn', 0) >= 2:
            rumour['distortion'] = min(3, rumour.get('distortion', 0) + 1)
            rumour['last_spread_turn'] = state.get('turn', 0)
            rumour.setdefault('carriers', []).append(faction)
            del rumour['carriers'][:-5]
            state['continuity']['world_flags'].setdefault('rumours_distorted', [])
            _append_unique(state['continuity']['world_flags']['rumours_distorted'], key)

    if random.random() < 0.35:
        category = _location_category(state.get('location', 'road'))
        events = globals().get('AMBIENT_EVENTS', {}).get(category, [])
        if events:
            state['_pending_ambient_line'] = _pick(events, f'ambient_{category}')

def _apply_pivot_if_due(state, beat, intent):
    """Apply a structural world pivot every sixth turn."""
    turn = state.get('turn', 0)
    if not turn or turn % 6 != 0:
        state.pop('_pending_pivot_line', None)
        return None
    unused = state.setdefault('unused_pivots', list(PIVOT_TYPES))
    if not unused:
        unused.extend(PIVOT_TYPES)
    pivot_type = unused.pop(random.randrange(len(unused)))
    loc = state.get('location', 'the road')
    region = state.get('world', {}).get('current_region', 'the road')
    faction = _current_region_data(state).get('faction', 'locals')
    npc = state.get('last_npc') or _make_named_npc(state)
    item = state.get('last_item', 'old token')
    source_turn = state.get('branch_history', [{}])[-1].get('turn', turn)
    template = _pick(globals().get('PIVOT_BEATS', []), 'pivot_beat') or "{faction} changes the road near {location}."
    description = template.format(
        npc=npc, location=loc, item=item, wound=state.get('player_wound', 'the old wound'),
        faction=faction, region=region, source_turn=source_turn,
    )
    record = {
        'turn': turn,
        'type': pivot_type,
        'beat': beat,
        'intent': intent,
        'location': loc,
        'region': region,
        'faction': faction,
        'description': description,
    }
    state.setdefault('pivots_applied', []).append(record)
    del state['pivots_applied'][:-24]
    flags = state['continuity'].setdefault('world_flags', {})
    flags.setdefault('factions_influenced', {})[region] = faction
    if pivot_type == 'location_lost':
        loc_state = state.setdefault('location_states', {}).setdefault(loc, _default_location_state(state, loc))
        loc_state['accessibility'] = 'changed'
        loc_state.setdefault('changes', []).append('a route changed after your choices')
        _append_unique(flags.setdefault('locations_changed', []), loc)
    elif pivot_type in ('secret_surfaces', 'player_past'):
        state.setdefault('player_knowledge', []).append(f"a pivot at {loc} exposed {pivot_type.replace('_', ' ')}")
        _append_unique(flags.setdefault('secrets_discovered', []), loc)
    elif pivot_type in ('faction_move', 'reputation_shift', 'world_event'):
        state.setdefault('faction_dispositions', {})[faction] = state.setdefault('faction_dispositions', {}).get(faction, 0) - 1
    elif pivot_type in ('npc_turns', 'ally_cost'):
        record_npc = _get_or_create_npc_record(state, npc)
        record_npc['score'] -= 1 if pivot_type == 'ally_cost' else 0
        record_npc['relationship'] = _relationship_from_score(record_npc['score'])
    state['_pending_pivot_line'] = description
    return record

def _location_category(location):
    """Map a generated location name to ambient event categories."""
    lower = (location or '').lower()
    if any(word in lower for word in ('market', 'inn', 'bar', 'ford')):
        return 'settlement'
    if any(word in lower for word in ('temple', 'cathedral', 'ruin', 'spire', 'shrine', 'archive', 'vault')):
        return 'ruin'
    if any(word in lower for word in ('room', 'atrium', 'hall', 'tower', 'corridor')):
        return 'interior'
    if any(word in lower for word in ('forest', 'moor', 'fen', 'grove', 'wastes', 'canyon', 'coast', 'plain')):
        return 'wilderness'
    return 'road'

def _describe_intent(intent):
    return {
        'aggressive': 'chose force',
        'cautious': 'moved carefully',
        'social': 'opened a conversation',
        'explore': 'searched for truth',
        'move': 'pressed onward',
        'use_item': 'relied on what you carried',
    }.get(intent, 'acted')


def _region_for_location_shift(state):
    """Occasionally move the player into another generated region."""
    world = state.get('world', {})
    regions = world.get('regions', [])
    if not regions:
        return
    current = world.get('current_region')
    candidates = [r for r in regions if r['name'] != current]
    if candidates:
        world['current_region'] = random.choice(candidates)['name']


def _relationship_from_score(score):
    """Convert a numeric relationship score into ally/neutral/hostile."""
    if score >= 2:
        return 'ally'
    if score <= -2:
        return 'hostile'
    return 'neutral'

def _get_or_create_npc_record(state, name=None):
    """Return a persistent NPC record with motives, secrets, tic, and memory."""
    continuity = state.setdefault('continuity', {})
    registry = continuity.setdefault('npcs', {})
    if name and name in registry:
        return registry[name]
    if not name:
        used = set(registry)
        genre = state.get('genre', 'fantasy')
        lore = LoreManager.detect_lore_pack(state.get('opening', '') + ' ' + genre)
        if lore and lore.get('npcs'):
            chosen = random.choice(lore['npcs'])
            name = f"{chosen['name']}, {chosen.get('role', 'contact')}"
        elif genre == 'scifi':
            sci_names = ['Commander Hayes', 'Dr. Vane', 'Officer Chen', 'Relay Beacon Echo', 'Pilot Thorne', 'Unit 07 Android']
            sci_titles = ['the flight lead', 'the survivor', 'the engineer', 'the automated relay', 'the shuttle pilot']
            available = [n for n in sci_names if not any(existing.startswith(n) for existing in used)]
            proper = random.choice(available or sci_names)
            title = random.choice(sci_titles)
            name = f"{proper}, {title}"
        elif genre == 'feline':
            cat_names = ['Barnaby', 'Pip', 'Buster', 'Madame Rosa', 'Sooty', 'Old Tom']
            cat_titles = ['the ginger tomcat', 'the alley kitten', 'the yard dog', 'the fishmonger', 'the roof prowler']
            available = [n for n in cat_names if not any(existing.startswith(n) for existing in used)]
            proper = random.choice(available or cat_names)
            title = random.choice(cat_titles)
            name = f"{proper}, {title}"
        elif genre == 'cyberpunk':
            cyber_names = ['Cipher', 'Doc Kessler', 'Vector', 'Chrome-Eye', 'Siren']
            cyber_titles = ['the netrunner', 'the ripperdoc', 'the data courier', 'the street enforcer']
            available = [n for n in cyber_names if not any(existing.startswith(n) for existing in used)]
            proper = random.choice(available or cyber_names)
            title = random.choice(cyber_titles)
            name = f"{proper}, {title}"
        else:
            available = [n for n in NPC_PROPER_NAMES if not any(existing.startswith(n) for existing in used)]
            proper = _pick(available or NPC_PROPER_NAMES, 'npc_proper')
            title = _pick(NPC_NAMES, 'npc_name')
            name = f"{proper}, {title}"
    archetypes = globals().get('NPC_ARCHETYPES', ['road witness', 'border scout', 'local guide'])
    secrets = globals().get('NPC_SECRETS', ['they know more than they can safely say'])
    wants = globals().get('NPC_WANTS', ['to leave with their name intact'])
    loyalties = globals().get('NPC_LOYALTIES', REGION_FACTIONS)
    tics = globals().get('NPC_TICS', ['watches your hands before answering'])
    record = {
        'name': name,
        'archetype': _pick(archetypes, 'npc_archetype'),
        'secret': _pick(secrets, 'npc_secret'),
        'want': _pick(wants, 'npc_want'),
        'loyalty': _pick(loyalties, 'npc_loyalty'),
        'tic': _pick(tics, 'npc_tic'),
        'relationship': 'neutral',
        'score': 0,
        'disposition': 0,
        'last_seen_location': state.get('location', 'somewhere unknown'),
        'last_interaction': 'first noticed on the road',
        'said_or_did': 'watched you carefully',
        'knowledge_of_player': [],
        'witnessed_actions': [],
        'heard_rumours': [],
        'turn_introduced': state.get('turn', 0),
    }
    registry[name] = record
    return record


def _record_npc(state, npc, intent, beat):
    """Persist named NPC relationship and last-seen memory."""
    entry = _get_or_create_npc_record(state, npc)
    if intent == 'social':
        entry['score'] += 1
        entry['said_or_did'] = 'offered a guarded answer'
    elif intent == 'aggressive':
        entry['score'] -= 1
        entry['said_or_did'] = 'remembered your violence'
    elif intent == 'cautious':
        entry['said_or_did'] = 'noticed your silence'
    else:
        entry['said_or_did'] = 'watched you carefully'
    entry['disposition'] = entry.get('score', 0)
    entry['relationship'] = _relationship_from_score(entry['score'])
    entry['last_seen_location'] = state.get('location', entry['last_seen_location'])
    entry['last_interaction'] = f"{beat} during turn {state.get('turn', 0)}"
    memory = (
        f"At the {entry['last_seen_location']}, you {_describe_intent(intent)} "
        f"while the scene bent toward {beat}."
    )
    if memory not in entry.setdefault('knowledge_of_player', []):
        entry['knowledge_of_player'].append(memory)
    del entry['knowledge_of_player'][:-8]
    branch = state.get('branch_history', [{}])[-1] if state.get('branch_history') else {}
    if branch:
        witness_note = {
            'turn': branch.get('turn'),
            'action': branch.get('action'),
            'location': branch.get('location'),
            'heard_by': branch.get('heard_by'),
        }
        entry.setdefault('witnessed_actions', []).append(witness_note)
        del entry['witnessed_actions'][:-6]


def _record_world_flags(state, intent, action, beat):
    """Track doors, defeated enemies, influenced factions, and discovered secrets."""
    flags = state['continuity']['world_flags']
    al = (action or '').lower()
    loc = state.get('location', 'the road')
    if any(word in al for word in ('open', 'unlock', 'force open')):
        _append_unique(flags['doors_opened'], loc)
    if intent == 'aggressive' and beat in ('conflict', 'encounter'):
        _append_unique(flags['enemies_defeated'], loc)
        region = state.get('world', {}).get('current_region', loc)
        faction = _current_region_data(state).get('faction', 'locals')
        flags['factions_influenced'][region] = faction
    if intent == 'social':
        region = state.get('world', {}).get('current_region', loc)
        faction = _current_region_data(state).get('faction', 'locals')
        flags['factions_influenced'][region] = faction
    if beat == 'revelation' or any(word in al for word in ('secret', 'read', 'inscription', 'study')):
        _append_unique(flags['secrets_discovered'], loc)


def _append_unique(items, value, limit=12):
    """Append a unique value to a bounded list."""
    if value not in items:
        items.append(value)
    del items[:-limit]


def _record_thread(state, text, kind, importance=5):
    """Record a bounded narrative thread event by importance."""
    threads = state['continuity'].setdefault('narrative_threads', [])
    threads.append({
        'turn': state.get('turn', 0),
        'kind': kind,
        'importance': importance,
        'text': text,
    })
    threads.sort(key=lambda e: (e.get('importance', 0), e.get('turn', 0)), reverse=True)
    del threads[10:]
    threads.sort(key=lambda e: e.get('turn', 0))


def _touch_location_memory(state, location, event):
    """Update descriptive history for a visited place."""
    memory = state['continuity'].setdefault('location_memory', {})
    entry = memory.setdefault(location, {'visits': 0, 'history': [], 'last_seen_turn': 0})
    entry['visits'] += 1
    entry['last_seen_turn'] = state.get('turn', 0)
    if event and event not in entry['history']:
        entry['history'].append(event)
    del entry['history'][:-4]


def _update_continuity_after_turn(state, beat, intent, action, gained_item=None):
    """Persist continuity consequences after a generated turn."""
    loc = state.get('location', 'the road')
    if beat == 'conflict':
        event = f"you nearly died at the {loc}"
        importance = 8
    elif beat == 'encounter':
        event = f"you met {state.get('last_npc', 'someone')} at the {loc}"
        importance = 7
    elif gained_item:
        event = f"you found {gained_item['name']} in the {loc}"
        importance = 6
    elif beat == 'revelation':
        event = f"a secret surfaced in the {loc}"
        importance = 8
    else:
        event = f"you passed through the {loc}"
        importance = 4
    _touch_location_memory(state, loc, event)
    _record_thread(state, event, beat, importance)
    _record_world_flags(state, intent, action, beat)
    if beat == 'encounter':
        _record_npc(state, state.get('last_npc', 'the stranger'), intent, beat)
    elif state.get('last_npc') and random.random() < 0.25:
        _record_npc(state, state.get('last_npc'), intent, beat)
    if intent == 'aggressive' and state.get('turn', 0) <= 5:
        effects = state['continuity'].setdefault('cause_effects', [])
        if 'act1_aggression' not in effects:
            effects.append('act1_aggression')
    loc_state = state.setdefault('location_states', {}).setdefault(loc, _default_location_state(state, loc))
    loc_state['last_visited'] = state.get('turn', 0)
    loc_state['atmosphere'] = state.get('mood', loc_state.get('atmosphere', 'mysterious'))
    loc_state.setdefault('events', []).append(event)
    del loc_state['events'][:-6]


def _current_region_data(state):
    """Return metadata for the current region."""
    world = state.get('world', {})
    current = world.get('current_region')
    for region in world.get('regions', []):
        if region.get('name') == current:
            return region
    return world.get('regions', [{}])[0] if world.get('regions') else {}


def _make_named_npc(state):
    """Create a proper NPC name with a familiar title."""
    return _get_or_create_npc_record(state)['name']


def _create_item(state, item_type=None, name=None):
    """Create a procedural inventory item dictionary."""
    item_type = item_type if item_type in ITEM_TYPES else random.choice(ITEM_TYPES)
    material = _pick(ENV_VARS['surface'])
    noun_map = {
        'weapon': ['blade', 'hatchet', 'spear', 'knife'],
        'armour': ['coat', 'mail', 'mantle', 'vambrace'],
        'consumable': ['draught', 'salve', 'ration', 'bitterroot'],
        'key': ['key', 'seal', 'token', 'charm'],
        'artefact': ['idol', 'lens', 'reliquary', 'astrolabe'],
        'lore': ['chronicle', 'scrap', 'tablet', 'ledger'],
        'accessory': ['ring', 'brooch', 'cord', 'mask'],
    }
    noun = random.choice(noun_map[item_type])
    if not name:
        if item_type == 'weapon' and random.random() < 0.4:
            name = random.choice(["Mireth's Blade", "Ashwake", "The Frost-Hilt", "Veldmoor Fang"])
        else:
            name = f"{material.capitalize()} {noun}"
    effect_map = {
        'weapon': 'steadies violent action',
        'armour': 'softens the next wound',
        'consumable': 'restores a little Vitality or Resolve',
        'key': 'opens a remembered threshold',
        'artefact': 'answers old magic with older silence',
        'lore': 'raises questions the road was hiding',
        'accessory': 'makes strangers look twice',
    }
    description = (
        f"A {random.choice(['weathered','cold','scarred','carefully wrapped','strangely warm'])} "
        f"{noun} of {material}, carrying the smell of {random.choice(['rain','iron','smoke','moss','salt'])}."
    )
    return {
        'name': name,
        'type': item_type,
        'description': description,
        'weight': random.choice(ITEM_WEIGHTS),
        'effect': effect_map[item_type],
    }


def _maybe_gain_item(state, beat, intent, action):
    """Add items from explicit choices, discoveries, victories, gifts, and chests."""
    al = (action or '').lower()
    item_type = None
    should_gain = False
    if any(word in al for word in ('take', 'pick up', 'loot', 'chest', 'claim')):
        should_gain = True
        item_type = 'key' if 'key' in al else None
    elif beat == 'discovery' and random.random() < 0.5:
        should_gain = True
    elif beat == 'conflict' and intent == 'aggressive' and random.random() < 0.35:
        should_gain = True
        item_type = 'weapon'
    elif beat == 'encounter' and intent == 'social' and random.random() < 0.35:
        should_gain = True
        item_type = random.choice(['lore', 'accessory', 'consumable'])

    if not should_gain:
        return None

    item = _create_item(state, item_type=item_type)
    names = {i.get('name') for i in state['inventory']['items']}
    if item['name'] not in names:
        state['inventory']['items'].append(item)
        state['items_found'].append(item['name'])
        state['last_item'] = item['name']
        if item['type'] in ('weapon', 'armour', 'accessory') and not state['inventory']['equipped'].get(item['type']):
            slot = 'armour' if item['type'] == 'armour' else item['type']
            state['inventory']['equipped'][slot] = item['name']
        if len(state['items_found']) > 12:
            state['items_found'] = state['items_found'][-12:]
        return item
    return None


def _find_inventory_item(state, action):
    """Find an inventory item mentioned in the player's action."""
    al = (action or '').lower()
    for item in state.get('inventory', {}).get('items', []):
        if item.get('name', '').lower() in al:
            return item
    action_terms = set(_extract_keywords(action))
    for item in state.get('inventory', {}).get('items', []):
        name_terms = set(_extract_keywords(item.get('name', '')))
        if action_terms & name_terms:
            return item
    return None


def _prepare_inventory_use(state, action):
    """Store pending item-use prose for the paragraph composer."""
    state.pop('_pending_item_use', None)
    item = _find_inventory_item(state, action)
    if not item:
        if (action or '').lower().strip().startswith('use '):
            state['_pending_item_use'] = "Your hand searches your pack and finds only absence."
        return None
    if item['type'] in ('weapon', 'armour', 'accessory'):
        slot = 'armour' if item['type'] == 'armour' else item['type']
        state['inventory']['equipped'][slot] = item['name']
    if item['type'] == 'consumable':
        stats = state['character']['stats']
        stats['Vitality'] = min(6, stats.get('Vitality', 4) + 1)
        stats['Resolve'] = min(6, stats.get('Resolve', 4) + 1)
    state['_pending_item_use'] = f"You grip {item['name']}; {item.get('effect', 'its purpose wakes quietly')}."
    return item


def _stat_pressure_sentence(state, intent, beat):
    """Apply and describe stat pressure without turning combat into rounds."""
    stats = state.get('character', {}).get('stats', {})
    if beat == 'conflict':
        if stats.get('Strength', 0) >= 4:
            return "Strength answers before fear can finish speaking."
        stats['Vitality'] = max(0, stats.get('Vitality', 4) - 1)
        return "The clash costs you; pain blooms under the ribs and stays there."
    if intent == 'social' and beat == 'encounter':
        if stats.get('Presence', 0) >= 4:
            return "Your voice finds the one shape this stranger is willing to trust."
        return "The stranger hears the uncertainty beneath your words and grows colder."
    if intent == 'explore' and stats.get('Lore', 0) >= 4 and beat in ('discovery', 'revelation'):
        return "Lore turns the old marks legible just before ignorance would have hurt you."
    if intent == 'cautious' and stats.get('Resolve', 0) <= 2:
        stats['Resolve'] = max(0, stats.get('Resolve', 2) - 1)
        return "Your hands shake despite your care; resolve has edges, and yours are wearing thin."
    return ''


def _lore_bias_sentence(state):
    """Let uploaded lore affect cadence without adding unsupported scene facts."""
    bias = state.get('lore_bias') or {}
    if not bias:
        return ''

    ctx = state.get('current_scene') or _scene_context(state, beat=state.get('last_beat'), intent='explore')
    register = _plain_register(bias.get('dominant_register') or (bias.get('moods') or ['old'])[0])
    feature = ctx['features'][0] if ctx.get('features') else ctx['object']
    obj = ctx.get('object') or feature

    scene_terms = {ctx['location'].lower(), ctx['region'].lower(), ctx['role'].lower(), obj.lower()}
    scene_terms.update(t.lower() for t in ctx.get('features', []))
    scene_terms.update(t.lower() for t in ctx.get('action_terms', []))
    matching_terms = [
        term for term in bias.get('terms', [])
        if term and term.lower() in scene_terms
    ]

    if matching_terms:
        term = matching_terms[0]
        return f"At the {ctx['location']}, the {term} matters because it changes what the {obj} can prove."
    article = 'an' if register[:1] in 'aeiou' else 'a'
    return f"At the {ctx['location']}, {article} {register} weight gathers around the {obj}; the useful fact remains the {feature}."


def _plain_register(register):
    """Turn lore-register labels into readable adjectives."""
    table = {
        'archaic': 'old',
        'geological': 'hard',
        'pastoral': 'weathered',
        'political': 'political',
        'grim': 'grave',
        'tolkienesque': 'old-road',
        'epic_weight': 'heavy',
        'naturalistic': 'plain',
        'mercantile': 'priced',
        'military': 'martial',
        'ecclesiastical': 'ritual',
        'criminal': 'watchful',
        'scholarly': 'careful',
        'maritime': 'tide-worn',
    }
    cleaned = re.sub(r'[^a-z_ -]+', '', str(register or '').lower()).strip()
    return table.get(cleaned, 'older')


def _vitality_text(value):
    """Render Vitality as atmospheric prose."""
    if value >= 5:
        return "Your body feels strong, almost impatient."
    if value >= 3:
        return "Your body holds, though it complains."
    if value >= 1:
        return "Every movement spends pain."
    return "You are near collapse."


def _resolve_text(value):
    """Render Resolve as atmospheric prose."""
    if value >= 5:
        return "Your mind is steady as a shuttered lantern."
    if value >= 3:
        return "Your thoughts remain yours, mostly."
    if value >= 1:
        return "Your hands are shaking."
    return "The dark has begun speaking in your voice."


def _panel_payload(state):
    """Build textual inventory, journal, and character panels for the UI."""
    state = _ensure_state_defaults(state)
    inv = state['inventory']
    items = inv.get('items', [])
    if items:
        lines = []
        for item in items:
            worn = ''
            if item['name'] in inv.get('equipped', {}).values():
                worn = ' Worn or ready.'
            lines.append(f"{item['name']} - {item['description']} It is {item['weight']}.{worn}")
        inventory = "\n".join(lines)
    else:
        inventory = "Your pack is almost empty. It remembers the shape of things you have not found yet."

    world = state['world']
    region = world.get('current_region', 'the road')
    time = world.get('time', {})
    rep = world.get('reputation', {}).get(region, 'unknown')
    
    # Expose custom active rumors from rumour_state
    active_rumours = []
    for r in state.get('rumour_state', {}).values():
        if isinstance(r, dict) and 'text' in r:
            active_rumours.append(r['text'])
        elif isinstance(r, str):
            active_rumours.append(r)
            
    rumours = [r['text'] for r in world.get('rumours', []) if r.get('heard')] + active_rumours
    threads = [e.get('text', '') for e in state['continuity'].get('narrative_threads', [])[-10:]]
    journal_parts = [
        f"The current region is {region}; day {time.get('day', 1)} has reached {time.get('slot', 'day')} under {world.get('weather', 'still air')}.",
        f"Here, your reputation is {rep}.",
    ]
    if rumours:
        journal_parts.append("Rumours travel ahead of you: " + " ".join(rumours[-3:]))
    if threads:
        journal_parts.append("The road keeps these events warm: " + " ".join(threads))
        
    # Expose Faction Goal progression
    faction_threads = state.get('faction_threads', [])
    if faction_threads:
        f_parts = []
        for ft in faction_threads:
            f_parts.append(f"{ft['faction']} are focused on {ft['goal']} ({ft['progress']}% complete)")
        journal_parts.append("Faction off-screen goal progress: " + " | ".join(f_parts))

    if state.get('pivots_applied'):
        journal_parts.append("Recent world shifts: " + " ".join(p['description'] for p in state['pivots_applied'][-2:]))
    if state.get('consequence_queue'):
        due = state['consequence_queue'][0]
        journal_parts.append(
            f"Unsettled consequence: what happened at {due.get('location')} is due to return around turn {due.get('due_turn')}."
        )
    journal = "\n\n".join(journal_parts)

    character = state['character']
    stats = character['stats']
    character_text = (
        f"You are {character.get('name', 'unnamed')}. "
        f"Beneath the roadwarden's work, you remain a {state.get('player_role', 'wanderer')} driven by {state.get('player_drive', 'survival')}; "
        f"the private wound is {state.get('player_wound', 'still unnamed')}. "
        f"{_vitality_text(stats.get('Vitality', 4))} {_resolve_text(stats.get('Resolve', 4))} "
        f"Cunning shows in how you count exits; Strength in what you dare move; "
        f"Presence in who keeps listening; Lore in which old lies fail to fool you."
    )
    return {'inventory': inventory, 'journal': journal, 'character': character_text}


def _build_image_prompt(state, action=None):
    """Build a vivid, focused image prompt for the current scene."""
    state = _ensure_state_defaults(state)
    ctx = state.get('current_scene') or _scene_context(state, beat=state.get('last_beat'), intent='explore', action=action)

    role = state.get('player_role', 'wanderer')
    loc = ctx.get('location', '')
    desc = ctx.get('description', '')
    genre = state.get('genre', 'fantasy')
    weather = state.get('world', {}).get('weather', 'mist')
    time_slot = state.get('world', {}).get('time', {}).get('slot', 'dusk')

    role_visuals = {
        'cat': 'a sleek solitary stray cat with watchful eyes',
        'astronaut': 'a lone astronaut in an EVA spacesuit with reflective helmet visor',
        'hacker': 'a cyberpunk netrunner with cybernetic implants and portable data deck',
        'detective': 'a brooding noir detective in a rain-drenched trench coat',
        'cartographer': 'a weathered cartographer holding an ancient unrolled parchment map',
        'witch': 'a solitary mysterious witch with dark robes and an herb satchel',
        'pilot': 'a grounded pilot in flight gear with leather jacket',
        'scientist': 'a field researcher with portable sensor scanner and analytical gear',
        'fighter': 'a battle-scarred warrior in worn leather and steel armor',
        'scholar': 'a solitary scholar in ink-stained travel robes',
        'thief': 'a nimble hooded rogue in shadowed leather gear',
        'priest': 'a solitary pilgrim wearing a worn sacred pendant',
        'sailor': 'a weathered sailor carrying sea-worn travel gear',
        'ranger': 'a hooded frontier scout with bow and tracking gear',
        'engineer': 'a resourceful technician with tool belt and goggles',
    }
    subject = role_visuals.get(role, f"a lone {role}")

    setting_parts = []
    if loc:
        setting_parts.append(loc)
    if desc and desc != loc:
        setting_parts.append(desc)
    setting_str = ', '.join(setting_parts)

    genre_styles = {
        'scifi': 'cinematic sci-fi concept art, atmospheric neon and volumetric lighting, photorealistic digital painting, 8k',
        'mystery': 'atmospheric film noir digital art, moody cinematic lighting, dramatic shadows, rain-slick surfaces, 8k',
        'fantasy': 'dark fantasy concept art, atmospheric oil painting style, moody cinematic lighting, intricate details, trending on artstation',
        'horror': 'atmospheric dark gothic horror concept art, eerie mist, deep shadows, cinematic ominous lighting, 8k',
        'adventure': 'vibrant cinematic adventure concept art, dramatic composition, rich environmental detail, 8k',
        'feline': 'cinematic atmospheric digital painting of a feline exploring, moody volumetric lighting, rich detail, 8k',
    }
    style = genre_styles.get(genre, genre_styles['fantasy'])

    prompt = f"{subject} at {setting_str}, {weather}, {time_slot}, {style}"
    return re.sub(r'\s+', ' ', prompt).strip()

def _shape_scene_prose(state, story, phase=None):
    """Apply phase-aware paragraph rhythm and anti-repetition memory."""
    phase = phase or state.get('arc_phase', 'setup')
    sentences = _split_sentences(story)
    if not sentences:
        return story

    if phase == 'climax':
        paragraph_count = 2
    elif phase == 'setup':
        paragraph_count = 3 if len(sentences) >= 4 else 2
    elif phase == 'rising':
        paragraph_count = 3 if len(sentences) >= 5 and random.random() < 0.45 else 2
    else:
        paragraph_count = 3 if len(sentences) >= 5 else 2

    paragraph_count = max(1, min(paragraph_count, len(sentences)))
    chunks = [[] for _ in range(paragraph_count)]
    for idx, sentence in enumerate(sentences):
        chunks[min(idx * paragraph_count // len(sentences), paragraph_count - 1)].append(sentence)
    paragraphs = [' '.join(chunk).strip() for chunk in chunks if chunk]
    shaped = '\n\n'.join(paragraphs)

    return _remember_and_filter_prose(state, shaped)

def _split_sentences(text):
    """Split prose without losing punctuation."""
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text or '') if s.strip()]

def _remember_and_filter_prose(state, story):
    """Track recent prose signatures and replace overused atmospheric phrasing."""
    memory = state.setdefault('prose_memory', {'recent_hooks': [], 'recent_phrases': []})
    recent = memory.setdefault('recent_phrases', [])
    signature = _prose_signature(story)
    if signature in recent:
        story += "\n\nThe scene refuses the shape it wore before; a different pressure gathers."
        signature = _prose_signature(story)
    recent.append(signature)
    del recent[:-12]
    replacements = {
        'something watches': 'attention gathers',
        'the silence here has weight': 'the quiet presses close',
        'everything changes': 'the terms of the moment alter',
    }
    lowered = story.lower()
    for phrase, replacement in replacements.items():
        if lowered.count(phrase) > 1:
            story = re.sub(re.escape(phrase), replacement, story, flags=re.I, count=1)
    return story

def _prose_signature(story):
    """Create a coarse signature from meaningful words."""
    words = [w for w in re.findall(r'[a-zA-Z]{4,}', (story or '').lower()) if w not in {
        'your', 'with', 'that', 'this', 'from', 'into', 'there', 'what', 'when',
    }]
    return ' '.join(words[:14])

# ── Main engine class ─────────────────────────────────────────────────────────

class StoryEngine:
    @staticmethod
    def detect_genre(text):
        text_lower = text.lower()
        scores = {}
        for genre, kws in GENRE_KEYWORDS.items():
            scores[genre] = sum(1 for kw in kws if kw in text_lower)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'fantasy'

    @staticmethod
    def ensure_state_defaults(state):
        """Hydrate missing systems on old saves without changing existing fields."""
        return _ensure_state_defaults(state, new_game=False)

    @staticmethod
    def create_item(state, item_type=None, name=None):
        """Create a procedural inventory item."""
        state = _ensure_state_defaults(state)
        return _create_item(state, item_type=item_type, name=name)

    @staticmethod
    def panel_payload(state):
        """Return textual panel payloads for inventory, journal, and character."""
        return _panel_payload(state)

    @staticmethod
    def build_image_prompt(state, action=None):
        """Return a scene image query built from full narrative context."""
        return _build_image_prompt(state, action=action)

    @staticmethod
    def create_state(opening):
        genre = StoryEngine.detect_genre(opening)
        harvest = _harvest_premise(opening)
        loc = _select_starting_location(genre, harvest)
        keywords = _extract_keywords(opening)
        identity = _parse_player_identity(opening)
        state = {
            'genre': genre,
            'location': loc[0],
            'location_desc': loc[1],
            'prev_locations': [],
            'mood': 'mysterious',
            'tension': 0.3,
            'arc_phase': 'setup',
            'npcs_met': [],
            'npc_tags': {},         # npc_name -> [tags like 'warning','promise']
            'items_found': [],
            'events': [],
            'turn': 0,
            'opening': opening,
            'opening_keywords': keywords,
            'opening_keywords_harvest': harvest,
            'player_role': identity['role'],
            'player_drive': identity['drive'],
            'player_wound': identity['wound'],
            'player_voice': identity['voice'],
            'last_npc': _pick(NPC_NAMES, 'npc_name'),
            'last_item': _pick(ENV_VARS['surface']) + ' fragment',
            'last_beat': None,
            # ── New narrative systems ──
            'emotion': 'wonder',
            'behavior_counts': {'aggressive':0,'cautious':0,'social':0,'explore':0,'move':0,'use_item':0},
            'dominant_behavior': None,     # computed from behavior_counts
            'beat_history': [],
            'branch_history': [],
            'consequence_queue': [],
            'surfaced_consequences': [],
            'pivots_applied': [],
            'unused_pivots': list(PIVOT_TYPES),
            'location_states': {},
            'faction_dispositions': {},
            'player_knowledge': [],
            'rumour_state': {},
            'prose_memory': {'recent_hooks': [], 'recent_phrases': []},
        }
        return _ensure_state_defaults(state, new_game=True)

    @staticmethod
    def generate_opening(opening, state):
        state = _ensure_state_defaults(state, new_game=True)
        state['turn'] = 1
        loc = state['location']
        ctx = _scene_context(state, beat='discovery', intent='explore', action=opening)
        state['current_scene'] = ctx

        harvest = state.get('opening_keywords_harvest', {})
        nouns = harvest.get('nouns', [])
        role = state.get('player_role', 'wanderer')
        loc_words = set(loc.lower().split())
        desc_nouns = [n for n in nouns if n != role and n != loc.lower() and n not in loc_words]
        preferred = [n for n in desc_nouns if n in PREMISE_NOUN_PHRASING or n in PERSON_NOUNS]
        if preferred:
            target_noun = preferred[-1]
        elif desc_nouns:
            target_noun = desc_nouns[-1]
        else:
            target_noun = nouns[-1] if nouns else None

        if target_noun and target_noun in PREMISE_NOUN_PHRASING:
            phrased_premise = PREMISE_NOUN_PHRASING[target_noun][0]
        elif target_noun and target_noun in PERSON_NOUNS:
            phrased_premise = f"your search for {target_noun}"
        elif target_noun and target_noun in PLACE_NOUNS:
            phrased_premise = f"your pursuit of {target_noun}"
        elif target_noun:
            phrased_premise = f"your quest for {target_noun}"
        else:
            phrased_premise = None

        if role == 'cat':
            role_sensory = f"Your whiskers twitch as cool air sweeps across the {loc}, your pads soundless on the damp surface."
            role_thought = f"Every feline instinct tells you {phrased_premise} is waiting somewhere beyond this turn." if phrased_premise else "Your ears swivel, tracking every faint rustle in the shadows."
        elif role == 'astronaut':
            role_sensory = f"Your suit displays calibrate against the stark expanse of the {loc}, life support readouts ticking in your peripheral vision."
            role_thought = f"Survival demands precision: {phrased_premise} remains your driving objective." if phrased_premise else "The desolate silence of the frontier offers neither rescue nor shelter."
        elif role == 'hacker':
            role_sensory = f"Neon glare and fractured static spill across the {loc}, your cyberdeck humming as it sniffs for wireless handshakes."
            role_thought = f"Somewhere in the city's encrypted traffic lies what you came for: {phrased_premise}." if phrased_premise else "The local subnet is alive with corporate counter-measures."
        elif role == 'detective':
            role_sensory = f"Rain-slick pavement and hollow echoes define the {loc}, every shadow holding the silhouette of an unanswered question."
            role_thought = f"You turn up your collar against the chill, your focus locked onto {phrased_premise}." if phrased_premise else "Every detail here is evidence waiting to be read."
        elif role == 'cartographer':
            role_sensory = f"Your eyes trace the contours of the {loc}, seeking lines of certainty where none exist."
            role_thought = "Your hand touches the map before it touches certainty—the parchment heavy with routes that ended in ruin."
        elif role == 'pilot':
            role_sensory = f"The horizon beyond the {loc} stretches wide and unforgiving, familiar cockpit gauges silent at your side."
            role_thought = f"With no flight plan and no ground crew, {phrased_premise} is the only heading that matters." if phrased_premise else "Every instinct honed in flight now answers to footfalls on solid ground."
        elif role == 'witch':
            role_sensory = f"The subtle hum of old currents tingles at your fingertips as you take in the {loc}."
            role_thought = f"The charms in your satchel rattle softly; {phrased_premise} drew you across the boundary." if phrased_premise else "The local spirits have already taken note of your presence."
        elif role == 'scholar':
            role_sensory = f"You study the weathered angles of the {loc}, piecing together the architecture of what came before."
            role_thought = f"Ink-stained fingers reach for notes: {phrased_premise} is more than theory now." if phrased_premise else "The texts spoke of this place, though they omitted the creeping chill."
        else:
            tool = ROLE_ITEM_OR_TOOL.get(role, 'instincts')
            role_sensory = f"You steady your breath against the quiet of the {loc}, letting your senses adjust to the terrain."
            role_thought = f"With your {tool} ready, you keep your mind fixed on {phrased_premise}." if phrased_premise else "Whatever brought you to this threshold, turning back is no longer an option."

        opening_lines = [
            f"The first thing you notice is {state['location_desc']}. Your senses adjust before your mind can reconcile how far you have come.",
            role_sensory,
            role_thought,
            f"Somewhere beyond the {loc}, a sound answers the fact of your arrival. It is too deliberate to be weather.",
            f"You have one immediate advantage: you are alert, and the place has not yet decided what your arrival means.",
        ]
        base_story = ' '.join(opening_lines)
        p0 = _identity_opening_sentence(state, opening)
        story = (p0 + " " + base_story) if p0 else base_story
        story = _shape_scene_prose(state, story, state.get('arc_phase', 'setup'))
        scene = state['location_desc']
        choices = generate_choices(state, 'discovery')
        _record_thread(state, f"your story began at the {loc}", 'opening', 7)
        _touch_location_memory(state, loc, 'your story began here')
        ns = NarrativeState(state)
        ns.memory.record_visit(loc)
        state['beat_history'].append('discovery')
        state['last_action'] = opening
        return story, scene, choices, None

    @staticmethod
    def generate(state, action=None):
        state = _ensure_state_defaults(state)
        state['turns_since_location_change'] = state.get('turns_since_location_change', 0) + 1
        state['last_action'] = action or ''
        genre = state['genre']
        locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
        turn = state.get('turn', 0) + 1
        state['turn'] = turn

        # Consequence Graph triggers & Faction simulation
        ns = NarrativeState(state)
        ns.memory.record_visit(state['location'])
        _simulate_faction_threads(state)
        consequences_fired = ns.consequences.check_and_fire()
        consequence_texts = []
        for trigger in consequences_fired:
            mut = trigger.get('mutation')
            if mut == 'force_conflict':
                state['force_next_beat'] = 'conflict'
            elif mut == 'add_debt':
                meta = trigger.get('metadata', {})
                ns.consequences.add_debt(meta.get('npc'), meta.get('severity', 1), meta.get('context', 'past actions'))
            elif mut == 'add_grudge':
                meta = trigger.get('metadata', {})
                ns.consequences.add_grudge(meta.get('faction'), meta.get('severity', 1), meta.get('context', 'past actions'))
            elif mut == 'reveal_secret':
                state.setdefault('player_knowledge', []).append(trigger.get('metadata', {}).get('secret', 'a hidden truth'))
            consequence_texts.append(f"Word catches up: {trigger.get('metadata', {}).get('description') or trigger.get('description', 'a consequence has triggered')}.")

        state['_consequence_texts'] = consequence_texts

        _advance_arc(state, turn)

        intent = _parse_intent(action) if action else 'explore'
        used_item = _prepare_inventory_use(state, action) if intent == 'use_item' else None
        branch_event = _record_branch_event(state, intent, action)

        # Track player behavior for consequence echoes
        counts = state.setdefault('behavior_counts', {'aggressive':0,'cautious':0,'social':0,'explore':0,'move':0,'use_item':0})
        counts.setdefault('use_item', 0)
        if intent in counts:
            counts[intent] = counts.get(intent, 0) + 1
        # Update dominant behavior
        if sum(counts.values()) >= 3:
            state['dominant_behavior'] = max(counts, key=counts.get)

        # Pick beat through salience after action intent is known.
        prev_beat = state.get('last_beat')
        beat = _pick_beat(state, intent=intent)
        state['last_beat'] = beat
        _enqueue_consequence(state, branch_event, intent, beat)
        _surface_due_consequences(state)

        # Update emotional temperature
        _update_emotion(state, beat, intent)
        _advance_world(state, intent, beat)
        _simulate_ambient_world(state, intent, beat)
        _apply_pivot_if_due(state, beat, intent)

        # Location transitions
        if beat == 'transition':
            old = state['location']
            state['prev_locations'].append(old)
            candidates = [l for l in locs if l[0] != old]
            new_loc = random.choice(candidates) if candidates else random.choice(locs)
            state['location'] = new_loc[0]
            state['location_desc'] = new_loc[1]
            ns.memory.record_visit(new_loc[0])
            _region_for_location_shift(state)
            state['turns_since_location_change'] = 0

        # Track NPCs and items for continuity
        gained_item = used_item
        if not gained_item:
            gained_item = _maybe_gain_item(state, beat, intent, action)

        if beat == 'encounter':
            if _is_npc_in_scene(state, beat, prev_beat):
                npc = state['last_npc']
            else:
                if state.get('continuity', {}).get('npcs') and random.random() < 0.35:
                    npc = random.choice(list(state['continuity']['npcs'].keys()))
                else:
                    npc = _make_named_npc(state)
                npc_record = _get_or_create_npc_record(state, npc)
                npc_record['last_seen_location'] = state['location']
                state['npcs_met'].append(npc)
                state['last_npc'] = npc
                if len(state['npcs_met']) > 6:
                    state['npcs_met'] = state['npcs_met'][-6:]

        # Compose
        story = compose_paragraph(state, beat, intent, action)
        consequence_texts = state.pop('_consequence_texts', [])
        if consequence_texts:
            story = " ".join(consequence_texts) + " " + story
        scene = state['location_desc']
        choices = generate_choices(state, beat)
        checkpoint = _maybe_checkpoint(state, beat, turn)

        # Record event for memory
        state['events'].append(f"{beat}:{state['location']}")
        if len(state['events']) > 20:
            state['events'] = state['events'][-20:]
        state.setdefault('beat_history', []).append(beat)
        del state['beat_history'][:-40]
        _update_continuity_after_turn(state, beat, intent, action, gained_item=gained_item)

        # Mood shift + NPC tag assignment
        mood_map = {
            'conflict': 'tense', 'obstacle': 'tense', 'rest': 'calm',
            'revelation': random.choice(['mysterious','tense']),
            'encounter': random.choice(['mysterious','tense','calm']),
            'discovery': random.choice(['mysterious','calm']),
            'transition': 'mysterious',
        }
        state['mood'] = mood_map.get(beat, state['mood'])

        # Assign NPC tag when encountering
        if beat == 'encounter':
            tags = ['warning','promise','threat','gift','riddle','silence','prophecy']
            npc = state.get('last_npc', 'the stranger')
            npc_tags = state.setdefault('npc_tags', {})
            npc_tags[npc] = random.choice(tags)
            if len(npc_tags) > 8:
                oldest = list(npc_tags.keys())[0]
                del npc_tags[oldest]

        return story, scene, choices, checkpoint, state


# ── Internal helpers ────────────────────────────────────────────────────────────

def _update_emotion(state, beat, intent):
    """Shift emotional temperature based on what's happening."""
    emotion_shifts = {
        ('conflict', 'aggressive'): 'resolve',
        ('conflict', 'cautious'): 'dread',
        ('conflict', 'social'): 'confusion',
        ('revelation', None): 'wonder',
        ('obstacle', None): 'dread',
        ('rest', None): 'melancholy',
        ('discovery', None): 'wonder',
        ('encounter', 'social'): 'resolve',
        ('encounter', 'cautious'): 'dread',
        ('transition', None): 'wonder',
    }
    # Try specific (beat, intent) first, then (beat, None)
    new_emotion = emotion_shifts.get((beat, intent)) or emotion_shifts.get((beat, None))
    if new_emotion:
        state['emotion'] = new_emotion

def _advance_arc(state, turn):
    # Slower paced arc progression
    if turn <= 4:
        state['arc_phase'] = 'setup'
        state['tension'] = 0.2 + random.random() * 0.1
    elif turn <= 10:
        state['arc_phase'] = 'rising'
        state['tension'] = min(0.8, state['tension'] + 0.05 + random.random() * 0.04)
    elif turn <= 14:
        state['arc_phase'] = 'climax'
        state['tension'] = 0.7 + random.random() * 0.3
    elif turn <= 18:
        state['arc_phase'] = 'falling'
        state['tension'] = max(0.3, state['tension'] - 0.08 - random.random() * 0.05)
    else:
        c = (turn - 18) % 12
        if c < 5:
            state['arc_phase'] = 'rising'
            state['tension'] = min(0.9, state['tension'] + 0.05)
        elif c < 8:
            state['arc_phase'] = 'climax'
            state['tension'] = 0.7 + random.random() * 0.3
        elif c < 10:
            state['arc_phase'] = 'falling'
            state['tension'] = max(0.25, state['tension'] - 0.1)
        else:
            state['arc_phase'] = 'setup'
            state['tension'] = 0.3 + random.random() * 0.1

def _pick_beat(state, intent=None):
    """Select the next beat deterministically using ActiveThreads and ChapterState."""
    forced = state.pop('force_next_beat', None)
    if forced:
        return forced
    ns = NarrativeState(state)
    phase = ns.chapter_state
    
    # 1. Thread-driven deterministic beats
    top_thread = ns.threads.get_top_thread()
    history = state.setdefault('beat_history', [])[-5:]
    
    # Avoid repeating the last beat even if thread demands it
    last_beat = history[-1] if history else None

    if top_thread:
        priority = top_thread.get('priority', 1)
        progress = top_thread.get('progress', 0)
        if priority >= 4 or progress >= 60:
            if phase in ('climax', 'rising'):
                if last_beat != 'conflict': return 'conflict'
            else:
                if last_beat != 'revelation': return 'revelation'
        elif 30 <= progress < 60:
            if last_beat != 'encounter': return 'encounter'
            
    # 2. Tension management
    if ns.tension > 0.85 and last_beat != 'rest':
        return 'rest'  # Force a breath beat
    elif ns.tension < 0.3 and phase == 'rising' and last_beat != 'encounter':
        return 'encounter' # Inject friction
        
    # 3. Fallback to modified weight selection
    weights = _beat_weights_for_phase(phase, state.get('turn', 0))
    candidates = []
    for beat, base in weights.items():
        if base <= 0:
            continue
        if beat == last_beat:
            continue
        if beat in ('discovery', 'conflict') and history.count(beat) >= 2:
            continue
        score = base + _beat_salience(state, beat, intent)
        if score > 0:
            candidates.append((beat, score))

    if not candidates:
        fallback = [beat for beat in weights if beat != last_beat]
        fallback = [beat for beat in fallback if beat not in ('discovery', 'conflict') or history.count(beat) < 2]
        if not fallback:
            fallback = ['transition', 'encounter', 'rest', 'obstacle']
        candidates = [(beat, max(weights.get(beat, 1), 1)) for beat in fallback]

    # Deterministic selection: sort descending by score and pick the highest
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]

def _beat_weights_for_phase(phase, turn):
    """Return phase-specific base salience for story beats."""
    if phase == 'setup':
        return {'discovery':5,'encounter':2,'transition':2,'rest':2,'obstacle':1,'revelation':0,'conflict':0}
    if phase == 'rising':
        return {'encounter':4,'obstacle':3,'discovery':4,'transition':2,'revelation':2,'conflict':2,'rest':1}
    if phase == 'climax':
        return {'conflict':5,'revelation':4,'obstacle':3,'encounter':2,'discovery':1,'transition':1,'rest':0}
    if phase == 'falling':
        return {'discovery':3,'rest':4,'transition':3,'revelation':2,'encounter':2,'obstacle':1,'conflict':0}
    cycle = (turn - 19) % 12 if turn >= 19 else 0
    if cycle < 4:
        return {'discovery':4,'encounter':3,'transition':2,'obstacle':2,'revelation':1,'conflict':1,'rest':1}
    if cycle < 8:
        return {'conflict':4,'obstacle':3,'revelation':3,'encounter':2,'discovery':1,'transition':1,'rest':0}
    return {'rest':4,'discovery':3,'transition':3,'encounter':2,'revelation':2,'obstacle':1,'conflict':0}

def _beat_salience(state, beat, intent):
    """Score a beat against current state qualities."""
    score = 0
    tension = state.get('tension', 0.5)
    role = state.get('player_role')
    drive = state.get('player_drive')
    
    # 1. Intent Coupling (Tuned for tighter pacing)
    if intent == 'aggressive' and beat in ('conflict', 'obstacle', 'encounter'):
        score += 5
    if intent == 'social' and beat == 'encounter':
        score += 6
    if intent == 'cautious':
        if beat in ('discovery', 'rest'):
            score += 5
        elif beat == 'obstacle':
            score += 4
    if intent == 'use_item' and beat in ('revelation', 'obstacle', 'discovery'):
        score += 4
    if intent == 'move' and beat == 'transition':
        score += 5
        
    # 2. State & Tension Coupling
    if state.get('consequence_queue') and beat in ('encounter', 'revelation', 'conflict'):
        score += 2
    if state.get('turn', 0) and state.get('turn', 0) % 6 == 0 and beat != 'rest':
        score += 1
    if tension > 0.72 and beat in ('conflict', 'revelation', 'obstacle'):
        score += 3
    if tension < 0.35 and beat in ('discovery', 'transition', 'encounter'):
        score += 2
        
    # 3. Role & Drive Specific Modifiers
    if role == 'cartographer' and beat in ('discovery', 'transition'):
        score += 2
    if role == 'scholar' and beat in ('revelation', 'discovery'):
        score += 2
    if role == 'spy' and beat in ('revelation', 'encounter'):
        score += 2
    if drive in ('revenge', 'survival') and beat in ('conflict', 'obstacle'):
        score += 2
    if drive in ('atonement', 'redemption') and beat in ('encounter', 'revelation'):
        score += 2
        
    # 4. Active Threads Modifier
    active_threads = state.get('active_threads', [])
    if active_threads and beat in ('conflict', 'revelation'):
        score += 2

    # 5. Active Wound Matcher (Ties character lore to story beat salience)
    wound = (state.get('player_wound') or '').lower()
    if wound:
        if any(w in wound for w in ['bleed', 'death', 'lives', 'blade', 'hurt', 'wound', 'kill', 'mercenary', 'order']):
            if beat in ('conflict', 'obstacle', 'encounter'):
                score += 3
        if any(w in wound for w in ['secret', 'oath', 'vow', 'prayer', 'lies', 'spy']):
            if beat in ('revelation', 'discovery'):
                score += 3
        if any(w in wound for w in ['drowned', 'salt', 'sea', 'ship', 'home', 'road', 'map', 'cartographer', 'deserter']):
            if beat in ('transition', 'discovery'):
                score += 3
        if any(w in wound for w in ['debt', 'contract', 'price', 'thief']):
            if beat in ('encounter', 'obstacle'):
                score += 3
        if any(w in wound for w in ['healer', 'pulse', 'rest', 'empty', 'survivor']):
            if beat == 'rest':
                score += 3

    if beat == 'transition':
        turns_stayed = state.get('turns_since_location_change', 0)
        if turns_stayed > 2:
            score += (turns_stayed - 2) * 2
            
    return score

def _parse_intent(action):
    if not action:
        return 'explore'
    al = action.lower()
    for intent, kws in {
        'use_item':   ['use ', 'equip', 'drink', 'apply', 'wield', 'read the', 'unlock with'],
        'aggressive': ['attack','fight','strike','charge','confront','slash','hit','kill','destroy','punch','shoot','stab','smash'],
        'cautious':   ['hide','sneak','observe','wait','listen','watch','careful','quiet','stealth','crouch','retreat','avoid'],
        'social':     ['talk','ask','negotiate','befriend','persuade','greet','speak','call','shout','convince','trade','barter'],
        'explore':    ['search','investigate','examine','look','open','check','inspect','read','touch','study','explore','scan'],
        'move':       ['go','walk','run','follow','climb','enter','leave','flee','escape','cross','swim','jump','descend','ascend'],
    }.items():
        if any(kw in al for kw in kws):
            return intent
    return 'explore'

def _maybe_checkpoint(state, beat, turn):
    t = state.get('tension', 0.5)
    loc = state.get('location', 'unknown')
    if beat == 'conflict' and t > 0.7:
        return {'type': 'death', 'description': f"Deadly confrontation at the {loc}"}
    if beat == 'revelation' and turn > 3:
        return {'type': 'discovery', 'description': f"Truth unveiled in the {loc}"}
    if beat == 'encounter' and random.random() < 0.1:
        return {'type': 'choice', 'description': f"Fateful encounter at the {loc}"}
    if turn > 0 and turn % 8 == 0:
        return {'type': 'achievement', 'description': f"Survived {turn} turns of the unknown"}
    return None

def _simulate_faction_threads(state):
    """Simulate faction goal progress off-screen, triggering events and location-based consequence triggers."""
    ns = NarrativeState(state)
    factions = REGION_FACTIONS
    faction_threads = state.setdefault('faction_threads', [])
    
    # Initialize faction threads if empty
    if not faction_threads:
        # Choose 2 random factions to track
        for f in random.sample(factions, 2):
            goals = ["securing borders", "hunting defectors", "extracting tithes", "gathering relics"]
            faction_threads.append({
                'faction': f,
                'goal': random.choice(goals),
                'progress': random.randint(10, 30)
            })
            
    # Advance progress
    for thread in faction_threads:
        thread['progress'] += random.randint(10, 20)
        if thread['progress'] >= 100:
            thread['progress'] = 0
            genre = state.get('genre', 'fantasy')
            locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
            target_loc = random.choice(locs)[0]
            event_desc = f"The {thread['faction']} completed their goal of {thread['goal']} at the {target_loc}."
            
            # Record in MemoryGraph
            ns.memory.add_event(
                event_type='faction_event',
                location=target_loc,
                description=event_desc,
                impact=2
            )
            
            # Queue location-match consequence trigger
            ns.consequences.add_trigger(
                trigger_type='faction_ambush',
                condition='location_match',
                mutation='force_conflict',
                due_turn=state.get('turn', 0) + 1,
                metadata={'location': target_loc, 'faction': thread['faction']}
            )
            
            # Spread rumor
            ns.consequences.spread_rumor(
                f"Rumors say the {thread['faction']} have finished {thread['goal']} near the {target_loc}.",
                spread_speed=2
            )
