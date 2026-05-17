"""
Compositional Story Engine v3 — vivid, non-repetitive, continuity-aware.
Builds unique prose from granular fragments with anti-repetition tracking,
player-input integration, consequence memory, motif recurrence, emotional
temperature, foreshadowing, NPC memory tags, and varied sentence rhythm.
"""
import random, re
from story_data import *

# Proper NPC title/names for continuity references
NPC_NAMES = [
    'the stranger','the watcher','the keeper','the wanderer','the exile',
    'the sentinel','the courier','the guide','the survivor','the scholar',
    'the hunter','the alchemist','the cartographer','the deserter','the oracle',
    'the engineer','the hermit','the prophet','the smuggler','the warden',
]

# ── Motif system ──────────────────────────────────────────────────────────────
# Recurring symbolic images that create unconscious narrative patterns

MOTIFS = {
    'mirror':  ['a cracked mirror catches your reflection — but the timing is wrong',
                'another mirror. The crack pattern matches the last one exactly',
                'the mirror shows something behind you. When you turn, nothing is there'],
    'bell':    ['a distant bell tolls once, from a direction that doesn\'t exist',
                'the bell again. Closer now. You feel it in your teeth',
                'the bell is deafening. It\'s been inside you all along'],
    'door':    ['a locked door. No handle, no keyhole. Just a door that refuses',
                'the same door. You recognize the grain of the wood, the exact scratches',
                'the door is open. It was always open. You just couldn\'t see it'],
    'water':   ['water drips upward here, defying everything you know',
                'the water remembers you. It parts before your hand touches it',
                'you see yourself reflected in water that isn\'t there'],
    'shadow':  ['your shadow moves independently — just for a moment',
                'the shadow is back. It\'s getting bolder, staying separate longer',
                'the shadow speaks. One word. Your name'],
    'clock':   ['a clock with no hands. Time here is theoretical',
                'another clock. Same make. All frozen at the same moment',
                'the clock starts. The hands move backward. Then the room changes'],
}

# ── Emotional temperature vocabulary ──────────────────────────────────────────

EMOTION_VOCAB = {
    'wonder':     {'adj': ['luminous','vast','crystalline','impossible','radiant'],
                   'verb': ['unfold','shimmer','reveal','bloom','transform']},
    'dread':      {'adj': ['suffocating','gnawing','creeping','hollow','visceral'],
                   'verb': ['constrict','seep','coil','press','devour']},
    'melancholy': {'adj': ['fading','distant','fragile','worn','bittersweet'],
                   'verb': ['dissolve','linger','ache','echo','dim']},
    'resolve':    {'adj': ['clear','steady','deliberate','focused','iron'],
                   'verb': ['sharpen','harden','crystallize','anchor','ignite']},
    'confusion':  {'adj': ['fractured','layered','contradictory','shifting','recursive'],
                   'verb': ['fragment','blur','twist','loop','unravel']},
}

# ── Foreshadowing templates ───────────────────────────────────────────────────

FORESHADOW_PLANTS = [
    "Something in the air changes. A pressure, building toward a point you can't see yet.",
    "The pattern isn't complete. One piece is missing, and it's heading this way.",
    "You get the sense that everything so far has been preparation. For what comes next.",
    "A thread of wrongness runs through this place. It leads somewhere specific.",
    "The calm feels manufactured. Engineered. A held breath before the exhale.",
]

FORESHADOW_PAYOFFS = [
    "This is what the silence was building toward.",
    "The missing piece clicks into place. The pattern completes.",
    "Now you understand what the pressure was warning you about.",
    "The thread of wrongness ends here. At this exact moment.",
    "The breath exhales. And everything changes.",
]

# ── Player behavior consequence templates ─────────────────────────────────────

BEHAVIOR_ECHOES = {
    'aggressive': [
        "This place remembers violence. The walls seem to flinch as you pass.",
        "Your reputation precedes you here. Something shifts warily in the dark.",
        "The marks you've left on this world are visible. Scars in stone, cracks in silence.",
    ],
    'cautious': [
        "Patience has become your language. The world speaks it back to you now.",
        "Your careful path has preserved things others would have broken.",
        "The shadows recognize a fellow creature of silence.",
    ],
    'social': [
        "Word travels in places like this. You've been spoken of. Described.",
        "The connections you've made form a web. You can feel it vibrating.",
        "Trust, once given, changes the shape of what comes next.",
    ],
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
    ],
}

GENRE_KEYWORDS = {
    'fantasy': ['dragon','sword','magic','kingdom','elf','wizard','quest','castle','knight',
                'sorcerer','enchanted','dungeon','goblin','dwarf','throne','spell','potion',
                'ancient','rune','prophecy','forest','warrior','mage','mythical','arcane'],
    'scifi':   ['space','ship','planet','robot','AI','laser','galaxy','station','alien',
                'cyberpunk','android','neon','future','tech','colony','warp','quantum',
                'hologram','cyborg','neural','plasma','orbit','starship','mech','synthetic'],
    'horror':  ['dark','shadow','fear','blood','creature','nightmare','haunted','ghost',
                'demon','cursed','asylum','cemetery','ritual','occult','madness','whisper',
                'scream','decay','rot','dread','horror','flesh','bone','undead'],
    'mystery': ['clue','detective','murder','suspect','evidence','secret','crime','witness',
                'alibi','motive','case','conspiracy','solve','puzzle','code','hidden',
                'truth','forensic','investigate','noir','heist'],
    'adventure':['journey','explore','treasure','map','wilderness','mountain','ocean',
                'island','pirate','expedition','survival','ruins','discover','cave',
                'river','desert','jungle','compass','camp','climb','voyage'],
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

# ── Sentence builders ─────────────────────────────────────────────────────────

def _fill_env(template):
    result = template
    for key, pool in ENV_VARS.items():
        if '{'+key+'}' in result:
            result = result.replace('{'+key+'}', _pick(pool, 'env_'+key), 1)
    return result

def _sensory_sentence(tension=0.5):
    if tension > 0.7:
        channel = _pick([SIGHT, SOUND, TOUCH], 'sense_ch')
    else:
        channel = _pick([SIGHT, SOUND, SMELL, TOUCH], 'sense_ch')
    return _pick(channel, 'sensory').capitalize()

def _sensory_detail(tension=0.5):
    """Same as sensory_sentence but lowercase, no trailing period — for embedding."""
    if tension > 0.7:
        channel = _pick([SIGHT, SOUND, TOUCH], 'sense_ch')
    else:
        channel = _pick([SIGHT, SOUND, SMELL, TOUCH], 'sense_ch')
    return _pick(channel, 'sensory')

def _env_sentence():
    return _fill_env(_pick(ENV_DETAILS, 'env_det')).capitalize()

def _adj_for_mood(mood, tension):
    if tension > 0.7:   pool = ADJ_TENSE + ADJ_DARK
    elif mood in ('mysterious','eerie'): pool = ADJ_MYSTERIOUS + ADJ_DARK
    elif mood in ('calm','triumphant'):  pool = ADJ_CALM + ADJ_MYSTERIOUS
    else: pool = ADJ_TENSE + ADJ_MYSTERIOUS
    return _pick(pool, 'adj')

def _motion_verb(tension):
    if tension > 0.7:  return _pick(VERBS_MOTION_HIGH, 'motion')
    if tension > 0.4:  return _pick(VERBS_MOTION_MED, 'motion')
    return _pick(VERBS_MOTION_LOW, 'motion')

def _extract_keywords(text):
    """Pull meaningful nouns/adjectives from player input for story integration."""
    if not text:
        return []
    stop = {'i','the','a','an','to','and','or','but','in','on','at','for','of','is',
            'it','my','me','do','go','up','so','if','by','no','am','be','we','us',
            'this','that','with','from','into','what','them','their','there','here',
            'just','more','some','very','want','try','see','take','make','get','let'}
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return [w for w in words if w not in stop and len(w) > 2][:6]

# ── Paragraph builders ────────────────────────────────────────────────────────

def _npc_paragraph(state):
    adj = _adj_for_mood(state.get('mood','mysterious'), state.get('tension',0.5))
    fabric = _pick(['tattered cloth','stained leather','military surplus','patchwork hide',
                     'faded silk','salvaged material','weather-beaten wool','reinforced canvas'], 'fabric')
    desc = _pick(NPC_DESCS, 'npc_desc').format(fabric=fabric)
    posture = _pick(NPC_POSTURES, 'npc_post')
    detail = _pick(NPC_DETAILS, 'npc_det')
    background = _pick(['stonework','vegetation','machinery','darkness','debris','architecture'], 'bg')
    intro = _pick(NPC_INTROS, 'npc_intro').format(
        adj=adj, desc=desc, posture=posture, detail=detail, background=background)
    tone = _pick(TONES, 'tone')
    reaction = _pick(REACTIONS, 'react')
    dialogue = _pick(DIALOGUE_OPENERS, 'dialogue').format(tone=tone, reaction=reaction)
    return intro + ' ' + dialogue

def _fight_paragraph(action_words=None):
    outcome = _pick(FIGHT_OUTCOMES, 'fight_out')
    impact = _pick(IMPACTS, 'impact')
    body = _pick(FIGHT_FRAGMENTS, 'fight_frag').format(outcome=outcome, impact=impact)
    return body + ' ' + _sensory_sentence(0.9)

def _stealth_paragraph():
    cover = _pick(COVERS, 'cover')
    detail = _sensory_detail(0.4)
    return _pick(STEALTH_FRAGMENTS, 'stealth').format(cover=cover, detail=detail)

def _explore_paragraph(state):
    surface = _pick(ENV_VARS['surface'], 'env_surface')
    feature = _pick(ENV_VARS['structure'], 'env_structure')
    look_verb = _pick(VERBS_LOOK, 'look')
    finding = _pick(FINDINGS, 'finding').format(surface=surface)
    return _pick(EXPLORE_FRAGMENTS, 'explore').format(
        look_verb=look_verb, surface=surface, feature=feature, finding=finding)

def _transition_paragraph(state):
    passage = _pick(['threshold','corridor','opening','gap','breach',
                      'passage','gateway','tunnel','crack','divide'], 'passage')
    adj = _adj_for_mood(state.get('mood','mysterious'), state.get('tension',0.5))
    quality = _pick(QUALITIES, 'quality')
    element = _pick(ELEMENTS, 'element')
    simile = _pick(SIMILES, 'simile')
    verb = _pick(['smolders','settles','echoes','bleeds','pulses','hums','seeps','lingers'], 'verb')
    fi = _pick(FIRST_IMPRESSIONS, 'first_imp').format(
        quality=quality, element=element, adj=adj, simile=simile, verb=verb)
    return _pick(TRANSITIONS, 'transition').format(passage=passage, first_impression=fi)

def _callback_sentence(state):
    """Reference past events for continuity — never if no history."""
    items = state.get('items_found', [])
    npcs = state.get('npcs_met', [])
    locs = state.get('prev_locations', [])
    npc_tags = state.get('npc_tags', {})

    # NPC tag callback (uses memory of encounter quality)
    if npc_tags and random.random() < 0.2:
        npc, tag = random.choice(list(npc_tags.items()))
        tag_callbacks = {
            'warning': f"You remember {npc}'s warning. It takes on new weight here.",
            'promise': f"What {npc} promised feels closer now. Almost tangible.",
            'threat': f"The threat {npc} made hangs in the air. They meant every word.",
            'gift': f"What {npc} gave you — you understand its purpose now.",
            'riddle': f"{npc.capitalize()}'s riddle surfaces in your mind. The answer might be here.",
            'silence': f"{npc.capitalize()}'s silence said more than words. You understand that now.",
            'prophecy': f"What {npc} foretold — this is the shape of it.",
        }
        return tag_callbacks.get(tag, '')

    if items and npcs and locs and random.random() < 0.35:
        return _pick(CALLBACKS, 'callback').format(
            item=_pick(items), npc=_pick(npcs), location=_pick(locs)) + '.'
    if items and locs and random.random() < 0.2:
        return f"The {_pick(items)} shifts in your grip, responding to the {_pick(locs)}'s residual energy."
    return ''

def _player_echo(action, keywords):
    """Weave the player's own words back into the narrative for responsiveness."""
    if not keywords:
        return ''
    kw = random.choice(keywords)
    echoes = [
        f"The word '{kw}' echoes in your mind as the scene unfolds.",
        f"Your instinct about the {kw} proves sharper than expected.",
        f"The {kw} becomes the axis around which everything turns.",
    ]
    return random.choice(echoes) if random.random() < 0.25 else ''

# ── Main paragraph composer ──────────────────────────────────────────────────

def compose_paragraph(state, beat, intent, action):
    """Compose a paragraph with varied rhythm. Never repeats across recent turns."""
    tension = state.get('tension', 0.5)
    keywords = _extract_keywords(action)
    sentences = []

    # Layer 1: Action acknowledgment
    if action and intent != 'explore':
        if intent == 'aggressive':
            sentences.append(_fight_paragraph(keywords))
        elif intent == 'cautious':
            sentences.append(_stealth_paragraph())
        elif intent == 'social' and beat == 'encounter':
            sentences.append(_npc_paragraph(state))
        elif intent == 'move':
            v = _motion_verb(tension)
            sentences.append(f"You {v} forward, every sense sharpened. {_sensory_sentence(tension)}")
        else:
            sentences.append(_explore_paragraph(state))
    elif action:
        sentences.append(_explore_paragraph(state))

    # Layer 2: Beat-specific content
    if beat == 'encounter' and intent != 'social':
        sentences.append(_npc_paragraph(state))
    elif beat == 'discovery':
        if intent != 'explore' or not action:
            sentences.append(_explore_paragraph(state))
    elif beat == 'obstacle':
        adj = _adj_for_mood(state.get('mood','tense'), tension)
        sub = _pick(ENV_VARS['substance'], 'env_substance')
        obstacle = _pick([
            f"The way forward narrows to nothing — a {adj} collapse blocks the passage",
            f"A chasm splits the floor, edges {adj} and crumbling, barely jumpable",
            f"Something has sealed this entrance. The barrier is {adj}, deliberate, recent",
            f"The ceiling sags dangerously, {adj} supports groaning under impossible weight",
            f"A wall of {sub} blocks the path, pulsing faintly, {adj} and alive",
        ], 'obstacle')
        sentences.append(obstacle + '. ' + _sensory_sentence(tension))
    elif beat == 'revelation':
        sentences.append(_pick([
            "The pattern snaps into focus with sickening clarity. " + _sensory_sentence(tension),
            "Understanding hits like a physical force. Everything recontextualizes. " + _env_sentence(),
            "A single detail reshuffles everything. What seemed random was deliberate all along. " + _sensory_sentence(tension),
            "The evidence was always there. You just weren't asking the right questions. " + _env_sentence(),
            "Connections fire in rapid succession — the markings, the behavior, the timing. It all points to one conclusion. " + _sensory_sentence(tension),
        ], 'revelation'))
    elif beat == 'transition':
        sentences.append(_transition_paragraph(state))
    elif beat == 'conflict':
        if not sentences:
            sentences.append(_fight_paragraph(keywords))
    elif beat == 'rest':
        sentences.append(_pick([
            f"A pocket of stillness. You allow yourself to breathe. {_sensory_sentence(0.2)}",
            f"The pressure eases, if only for a moment. Your body reminds you of its limits. {_env_sentence()}",
            f"Quiet. Real quiet, not the held-breath kind. {_sensory_sentence(0.2)}",
            f"You find a place where the danger can't reach — at least not yet. {_env_sentence()}",
        ], 'rest'))

    # Layer 3: Environmental texture (adaptive length by arc phase)
    phase = state.get('arc_phase', 'setup')
    target_map = {'setup': 5, 'rising': 4, 'climax': 3, 'falling': 5, 'resolution': 4}
    target_len = target_map.get(phase, 4)
    if len(sentences) < target_len:
        sentences.append(_env_sentence())
    if len(sentences) < target_len and random.random() < 0.65:
        sentences.append(_sensory_sentence(tension))

    # Layer 4: Continuity callback
    cb = _callback_sentence(state)
    if cb:
        sentences.append(cb)

    # Layer 5: Player-echo (weave their words back in)
    echo = _player_echo(action, keywords)
    if echo:
        sentences.append(echo)

    # Layer 6: Hook closer (not every turn — ~50%)
    if random.random() < 0.5:
        sentences.append(_pick(HOOKS, 'hook'))
    # Normalize: ensure each sentence ends with proper punctuation
    cleaned = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        while s.endswith('..') and not s.endswith('...'):
            s = s[:-1]
        if s and s[-1] not in '.!?"\'':
            s += '.'
        cleaned.append(s)

    # ── Motif insertion (recurring symbols) ──
    motifs = state.get('motifs', [])
    intensity = state.get('motif_intensity', {})
    if motifs and random.random() < 0.2 and len(cleaned) >= 2:
        m = random.choice(motifs)
        level = min(intensity.get(m, 0), len(MOTIFS.get(m, [''])) - 1)
        motif_text = MOTIFS.get(m, [''])[level]
        if motif_text:
            cleaned.insert(-1, motif_text.capitalize() + '.')
            intensity[m] = intensity.get(m, 0) + 1
            state['motif_intensity'] = intensity

    # ── Foreshadowing ──
    phase = state.get('arc_phase', 'setup')
    if phase == 'rising' and not state.get('foreshadow_planted') and random.random() < 0.3:
        cleaned.append(random.choice(FORESHADOW_PLANTS))
        state['foreshadow_planted'] = True
    elif phase == 'climax' and state.get('foreshadow_planted') and random.random() < 0.5:
        cleaned.insert(0, random.choice(FORESHADOW_PAYOFFS))
        state['foreshadow_planted'] = False

    # ── Behavior echo (consequence of player patterns) ──
    dom = state.get('dominant_behavior')
    if dom and dom in BEHAVIOR_ECHOES and state.get('turn', 0) > 4 and random.random() < 0.12:
        cleaned.append(random.choice(BEHAVIOR_ECHOES[dom]))

    # ── Emotional color sentence ──
    emotion = state.get('emotion', 'wonder')
    if emotion in EMOTION_VOCAB and random.random() < 0.2:
        ev = EMOTION_VOCAB[emotion]
        adj = random.choice(ev['adj'])
        verb = random.choice(ev['verb'])
        cleaned.append(f"Something {adj} begins to {verb} at the edges of perception.")

    return ' '.join(cleaned)


# ── Choice generator ─────────────────────────────────────────────────────────

def generate_choices(state, beat):
    """Build 3 contextual, non-generic choices rooted in current story state."""
    location = state.get('location', 'this place')
    last_npc = state.get('last_npc', 'the stranger')
    last_item = state.get('last_item', 'the object')

    bold = _pick(CHOICE_VERBS_BOLD, 'cv_bold')
    cautious = _pick(CHOICE_VERBS_CAUTIOUS, 'cv_cautious')
    clever = _pick(CHOICE_VERBS_CLEVER, 'cv_clever')

    # Context-specific targets (never generic)
    beat_targets = {
        'encounter': [last_npc, "their motives", "what they're concealing"],
        'discovery':  [f"the {last_item}", "the hidden mechanism", "the concealed space"],
        'obstacle':   ["the barrier ahead", "the structural weakness", "an alternate route"],
        'revelation': ["this new truth", "the deeper pattern", "who stands to gain"],
        'transition': [f"the {location}", "the unfamiliar territory", "what lies beyond"],
        'conflict':   ["the immediate threat", "their exposed flank", "the escape route"],
        'rest':       ["the perimeter", "your remaining resources", "the path forward"],
    }

    targets = beat_targets.get(beat, beat_targets['discovery'])
    choices = [
        f"{bold.capitalize()} {targets[0]}",
        f"{cautious.capitalize()} {targets[1]}",
        f"{clever.capitalize()} {targets[2]}",
    ]

    # Occasionally substitute with item-based choice
    items = state.get('items_found', [])
    if items and random.random() < 0.3:
        choices[2] = f"Use the {_pick(items)} to gain an advantage"

    # Occasionally add location-specific flavor
    if random.random() < 0.2:
        choices[0] = f"Press deeper into the {location}"

    return choices


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
    def create_state(opening):
        genre = StoryEngine.detect_genre(opening)
        locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
        loc = random.choice(locs)
        keywords = _extract_keywords(opening)
        return {
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
            'last_npc': _pick(NPC_NAMES, 'npc_name'),
            'last_item': _pick(ENV_VARS['surface']) + ' fragment',
            'last_beat': None,
            # ── New narrative systems ──
            'emotion': 'wonder',           # emotional temperature
            'motifs': [],                  # active recurring motifs
            'motif_intensity': {},         # motif_name -> times_seen (0-2)
            'behavior_counts': {'aggressive':0,'cautious':0,'social':0,'explore':0,'move':0},
            'foreshadow_planted': False,   # whether a foreshadow seed is active
            'dominant_behavior': None,     # computed from behavior_counts
        }

    @staticmethod
    def generate_opening(opening, state):
        state['turn'] = 1
        loc = state['location']
        keywords = state.get('opening_keywords', [])

        # Build opening that integrates the player's own premise
        p1 = _transition_paragraph(state)
        p2 = _sensory_sentence(0.3)
        p3 = _env_sentence()

        # Weave player's keywords into the opening
        if keywords:
            kw = keywords[0]
            bridges = [
                f"The {kw} you came looking for — this is where it begins.",
                f"Something about this place connects to the {kw}. You feel it before you understand it.",
                f"The {kw} is close. Every instinct confirms it.",
            ]
            p4 = random.choice(bridges)
        else:
            p4 = _pick(HOOKS, 'hook')

        story = f"{p1} {p2} {p3} {p4}"
        scene = state['location_desc']
        choices = generate_choices(state, 'discovery')
        return story, scene, choices, None

    @staticmethod
    def generate(state, action=None):
        genre = state['genre']
        locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
        turn = state.get('turn', 0) + 1
        state['turn'] = turn

        _advance_arc(state, turn)
        phase = state['arc_phase']  # used later for foreshadow reset

        # Pick beat, avoiding repeating the same beat twice in a row
        beat = _pick_beat(state)
        if beat == state.get('last_beat') and random.random() < 0.7:
            beat = _pick_beat(state)  # re-roll once
        state['last_beat'] = beat

        intent = _parse_intent(action) if action else 'explore'

        # Track player behavior for consequence echoes
        counts = state.setdefault('behavior_counts', {'aggressive':0,'cautious':0,'social':0,'explore':0,'move':0})
        if intent in counts:
            counts[intent] = counts.get(intent, 0) + 1
        # Update dominant behavior
        if sum(counts.values()) >= 3:
            state['dominant_behavior'] = max(counts, key=counts.get)

        # Seed motifs at turn 2 if none exist
        if turn == 2 and not state.get('motifs'):
            available = list(MOTIFS.keys())
            state['motifs'] = random.sample(available, min(2, len(available)))
            state['motif_intensity'] = {m: 0 for m in state['motifs']}

        # Update emotional temperature
        _update_emotion(state, beat, intent)

        # Location transitions
        if beat == 'transition' or (random.random() < 0.2 and turn > 2):
            old = state['location']
            state['prev_locations'].append(old)
            candidates = [l for l in locs if l[0] != old]
            new_loc = random.choice(candidates) if candidates else random.choice(locs)
            state['location'] = new_loc[0]
            state['location_desc'] = new_loc[1]

        # Track NPCs and items for continuity
        if beat == 'discovery' and random.random() < 0.5:
            material = _pick(ENV_VARS['surface'])
            item_type = _pick(['shard','fragment','key','device','artifact','token','seal','lens'])
            item = f"{material} {item_type}"
            state['items_found'].append(item)
            state['last_item'] = item
            if len(state['items_found']) > 8:
                state['items_found'] = state['items_found'][-8:]

        if beat == 'encounter':
            npc = _pick(NPC_NAMES, 'npc_name')
            state['npcs_met'].append(npc)
            state['last_npc'] = npc
            if len(state['npcs_met']) > 6:
                state['npcs_met'] = state['npcs_met'][-6:]

        # Compose
        story = compose_paragraph(state, beat, intent, action)
        scene = state['location_desc']
        choices = generate_choices(state, beat)
        checkpoint = _maybe_checkpoint(state, beat, turn)

        # Record event for memory
        state['events'].append(f"{beat}:{state['location']}")
        if len(state['events']) > 20:
            state['events'] = state['events'][-20:]

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

        # Reset foreshadow at new arc cycle
        if phase == 'setup':
            state['foreshadow_planted'] = False

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
    if turn <= 2:
        state['arc_phase'] = 'setup'
        state['tension'] = 0.2 + random.random() * 0.15
    elif turn <= 5:
        state['arc_phase'] = 'rising'
        state['tension'] = min(0.8, state['tension'] + 0.08 + random.random() * 0.06)
    elif turn <= 8:
        state['arc_phase'] = 'climax'
        state['tension'] = 0.7 + random.random() * 0.3
    elif turn <= 10:
        state['arc_phase'] = 'falling'
        state['tension'] = max(0.3, state['tension'] - 0.12 - random.random() * 0.05)
    else:
        c = (turn - 10) % 7
        if c < 3:
            state['arc_phase'] = 'rising'
            state['tension'] = min(0.9, state['tension'] + 0.07)
        elif c < 5:
            state['arc_phase'] = 'climax'
            state['tension'] = 0.7 + random.random() * 0.3
        elif c < 6:
            state['arc_phase'] = 'falling'
            state['tension'] = max(0.25, state['tension'] - 0.12)
        else:
            state['arc_phase'] = 'setup'
            state['tension'] = 0.3 + random.random() * 0.1

def _pick_beat(state):
    phase = state['arc_phase']
    w = {
        'setup':     {'discovery':3,'encounter':2,'transition':2,'rest':1,'obstacle':1,'revelation':1,'conflict':0},
        'rising':    {'encounter':3,'obstacle':3,'discovery':2,'transition':1,'revelation':2,'conflict':2,'rest':0},
        'climax':    {'conflict':4,'revelation':3,'obstacle':2,'encounter':2,'discovery':1,'transition':0,'rest':0},
        'falling':   {'discovery':2,'rest':3,'transition':2,'revelation':2,'encounter':1,'obstacle':1,'conflict':0},
        'resolution':{'rest':3,'discovery':2,'revelation':2,'transition':1,'encounter':1,'obstacle':0,'conflict':0},
    }.get(phase, {'discovery':2,'encounter':2,'obstacle':2,'revelation':1,'transition':1,'conflict':1,'rest':1})
    beats = list(w.keys())
    wts = [w[b] for b in beats]
    return random.choices(beats, weights=wts, k=1)[0]

def _parse_intent(action):
    if not action:
        return 'explore'
    al = action.lower()
    for intent, kws in {
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
