"""Grounded narrative engine for The Butterfly Effect RPG.

The engine keeps every beat tied to the player premise, current location,
present NPCs, inventory, faction pressure, and remembered consequences. Random
selection is used for pacing and variety, not for introducing unsupported nouns
or ornamental prose.
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

NPC_PROPER_NAMES = [
    'Mireth Vale', 'Oren Blackreed', 'Sera Voss', 'Calder Wren',
    'Ilyan Thorne', 'Veyra Mourn', 'Tovin Ash', 'Elira Fen',
    'Damaris Pike', 'Rook Marrow', 'Ansel Grey', 'Nadia Kest',
    'Bren Tor', 'Silas Veld', 'Maera Quill', 'Corin Redhand',
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
    'survivor', 'fighter',
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
    'deserter': "You keep counting the seconds it would take pursuit to reach the treeline.",
    'spy': "The unused report lives behind your teeth, addressed to no one living.",
    'healer': "Your satchel smells of bitter herbs and old blood that no clean water finished removing.",
    'thief': "Every latch speaks a small language, and your fingers answer before pride can stop them.",
    'scholar': "The margins of your old notes are full of corrections that cannot correct what happened.",
    'exile': "Behind you is a boundary stone; ahead is a place where your name has not yet been priced.",
    'outcast': "The mark may have faded from your skin, but people still seem to read it there.",
    'survivor': "You know the difference between silence and aftermath; this place is deciding which one it is.",
    'fighter': "Your body keeps its old ledgers in scar tissue and balance.",
    'wanderer': "The road does not care where you came from, and that is the first mercy it offers.",
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
    text = re.sub(r'\s+', ' ', text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.rstrip('.')

def _identity_opening_sentence(state, opening):
    """Build the authored-feeling first sentence from player identity."""
    recast = _recast_to_second_person(opening)
    role = state.get('player_role', 'wanderer')
    context = ROLE_CONTEXT.get(role, ROLE_CONTEXT['wanderer'])
    wound = state.get('player_wound', 'what the road has not asked about yet')
    return f"{recast}. {context} Beneath it all waits {wound}."

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
            if term in ('map', 'maps', 'milestone', 'ledger', 'door', 'gate', 'road', 'witness'):
                return term
    if state.get('player_role') == 'cartographer':
        return 'map'
    if inventory_items:
        return inventory_items[-1]
    return features[0] if features else state.get('location', 'road')

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
    """Compose a grounded scene from current state facts only."""
    ctx = _scene_context(state, beat=beat, intent=intent, action=action)
    ctx['turn'] = state.get('turn', 0)
    state['current_scene'] = ctx

    sentences = [
        _scene_anchor_sentence(ctx),
        _action_ack_sentence(ctx),
        _beat_sentence(ctx),
    ]

    return_line = _location_return_sentence(ctx)
    if return_line:
        sentences.append(return_line)

    pending_item = state.pop('_pending_item_use', None)
    if pending_item:
        sentences.append(pending_item)

    stat_note = _stat_pressure_sentence(state, intent, beat)
    if stat_note:
        sentences.append(stat_note)

    for pending_key in ('_pending_consequence_lines',):
        for pending_line in state.pop(pending_key, []) or []:
            sentences.append(pending_line)

    pivot_line = state.pop('_pending_pivot_line', None)
    if pivot_line:
        sentences.append(pivot_line)

    ambient_line = state.pop('_pending_ambient_line', None)
    if ambient_line:
        sentences.append(f"At the {ctx['location']}, {ambient_line[0].lower() + ambient_line[1:]}")

    identity_note = _identity_callback_sentence(state)
    if identity_note:
        sentences.append(identity_note)

    lore_note = _lore_bias_sentence(state)
    if lore_note:
        sentences.append(lore_note)

    sentences.append(_grounded_world_sentence(state, ctx))
    sentences.append(_contextual_hook(state, state.get('arc_phase', 'setup')))

    cleaned = [_clean_sentence(sentence) for sentence in sentences if sentence]
    return _shape_scene_prose(state, ' '.join(cleaned), state.get('arc_phase', 'setup'))


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

    choices = []
    if beat == 'encounter' and npc:
        choices.extend([
            f"Ask {npc['name']} what {faction} wants at the {loc}",
            f"Watch {npc['name'].split(',')[0]} while you compare their story to your map",
            f"Offer {npc['name'].split(',')[0]} a cautious truth about the {loc}",
        ])
    elif beat == 'obstacle':
        choices.extend([
            f"Measure the blocked line through the {loc} like a {role}",
            f"Search the {obj} for a safer way past the {loc}",
            f"Leave a map mark at the {loc} before forcing passage",
        ])
    elif beat == 'revelation':
        choices.extend([
            f"Record what the {obj} proves about {region}",
            f"Decide whether to hide this truth from {faction}",
            f"Compare the {loc} against the mistake that still wounds you",
        ])
    elif beat == 'transition':
        choices.extend([
            f"Mark the road out of the {loc} before you follow it",
            f"Check whether your map lies about the next stretch of {region}",
            f"Leave a warning at the {loc} for anyone following your line",
        ])
    elif beat == 'conflict':
        choices.extend([
            f"Use the {obj} at the {loc} before {faction} can close in",
            f"Hold the line at the {loc} and make your next move visible",
            f"Break away through the part of the {loc} your map still explains",
        ])
    elif beat == 'rest':
        choices.extend([
            f"Update your map of the {loc} while you still have quiet",
            f"Count supplies at the {loc} and decide what can be spared",
            f"Listen for what {faction} are saying about you in {region}",
        ])
    else:
        choices.extend([
            f"Study the {obj} at the {loc} until {obj_gives} a usable fact",
            f"Compare the {loc} against the map you no longer trust",
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
    identity = _parse_player_identity(state.get('opening', ''))
    state.setdefault('player_role', identity['role'])
    state.setdefault('player_drive', identity['drive'])
    state.setdefault('player_wound', identity['wound'])
    state.setdefault('player_voice', identity['voice'])
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
    for profile in globals().get('FACTION_PROFILES', []):
        if isinstance(profile, (list, tuple)) and profile:
            dispositions.setdefault(profile[0], 0)
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
    count = random.randint(3, 5)
    names = []
    for _ in range(count * 2):
        name = random.choice(REGION_PREFIXES) + random.choice(REGION_SUFFIXES)
        name = name[0].upper() + name[1:]
        if name not in names:
            names.append(name)
        if len(names) >= count:
            break
    regions = []
    for name in names:
        regions.append({
            'name': name,
            'geography': random.choice(REGION_GEOGRAPHY),
            'faction': random.choice(REGION_FACTIONS),
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
        return f"The {root} Marches"
    if names:
        return f"The {names[0]} Road"
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
    state.setdefault('consequence_queue', []).append(entry)
    state['consequence_queue'].sort(key=lambda item: item.get('due_turn', 9999))
    if intent == 'cautious':
        state.setdefault('player_knowledge', []).append(f"hidden path near {loc}")
        del state['player_knowledge'][:-18]
    if intent == 'aggressive':
        state.setdefault('faction_dispositions', {})[faction] = state.setdefault('faction_dispositions', {}).get(faction, 0) - 1
    elif intent == 'social':
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
        'lore': ['codex', 'scrap', 'tablet', 'ledger'],
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
    rumours = [r['text'] for r in world.get('rumours', []) if r.get('heard')]
    threads = [e.get('text', '') for e in state['continuity'].get('narrative_threads', [])[-10:]]
    journal_parts = [
        f"The current region is {region}; day {time.get('day', 1)} has reached {time.get('slot', 'day')} under {world.get('weather', 'still air')}.",
        f"Here, your reputation is {rep}.",
    ]
    if rumours:
        journal_parts.append("Rumours travel ahead of you: " + " ".join(rumours[-3:]))
    if threads:
        journal_parts.append("The road keeps these events warm: " + " ".join(threads))
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
    """Build a contextual image search prompt for the current scene."""
    state = _ensure_state_defaults(state)
    ctx = state.get('current_scene') or _scene_context(state, beat=state.get('last_beat'), intent='explore', action=action)
    pieces = [
        ctx.get('location', ''),
        ctx.get('description', ''),
        state.get('last_npc', ''),
        action or state.get('last_action', ''),
        ctx.get('object', ''),
        ctx.get('faction', ''),
        state.get('genre', 'fantasy'),
        state.get('emotion', 'wonder'),
        state.get('world', {}).get('weather', ''),
        state.get('world', {}).get('time', {}).get('slot', ''),
        'fantasy digital art atmospheric',
    ]
    return ' '.join(str(p).strip() for p in pieces if p).strip()

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
        locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
        loc = random.choice(locs)
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

        # Build opening that integrates the player's own premise
        p0 = _identity_opening_sentence(state, opening)
        p1 = _scene_anchor_sentence(ctx)
        map_phrase = 'maps' if 'map' in ctx['object'] else ctx['object']
        map_verb = 'make' if map_phrase.endswith('s') else 'makes'
        p2 = (
            f"The {map_phrase} in your pack {map_verb} the {ctx['location']} feel less like discovery "
            f"and more like evidence waiting to be mishandled."
        )
        p3 = (
            f"If your old error began with a line on paper, this scene begins with a line under your boots: "
            f"{ctx['features'][0]} leading toward {ctx['faction']}."
        )
        p4 = _contextual_hook(state, 'setup')

        raw_sentences = [p0, p1, p2, p3, p4]
        cleaned = []
        for s in raw_sentences:
            s = s.strip()
            if not s: continue
            if s[-1] not in '.!?"\'':
                s += '.'
            s = s[0].upper() + s[1:]
            cleaned.append(s)
            
        story = ' '.join(cleaned)
        story = _shape_scene_prose(state, story, state.get('arc_phase', 'setup'))

        scene = state['location_desc']
        choices = generate_choices(state, 'discovery')
        _record_thread(state, f"your story began at the {loc}", 'opening', 7)
        _touch_location_memory(state, loc, 'your story began here')
        state['beat_history'].append('discovery')
        state['last_action'] = opening
        return story, scene, choices, None

    @staticmethod
    def generate(state, action=None):
        state = _ensure_state_defaults(state)
        state['last_action'] = action or ''
        genre = state['genre']
        locs = GENRE_LOCATIONS.get(genre, GENRE_LOCATIONS['fantasy'])
        turn = state.get('turn', 0) + 1
        state['turn'] = turn

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
        if beat == 'transition' or (random.random() < 0.2 and turn > 2):
            old = state['location']
            state['prev_locations'].append(old)
            candidates = [l for l in locs if l[0] != old]
            new_loc = random.choice(candidates) if candidates else random.choice(locs)
            state['location'] = new_loc[0]
            state['location_desc'] = new_loc[1]
            _region_for_location_shift(state)

        # Track NPCs and items for continuity
        gained_item = used_item
        if not gained_item:
            gained_item = _maybe_gain_item(state, beat, intent, action)

        if beat == 'encounter':
            if state.get('continuity', {}).get('npcs') and random.random() < 0.35:
                npc = random.choice(list(state['continuity']['npcs'].keys()))
            else:
                npc = _make_named_npc(state)
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
    """Select the next beat using phase, salience, recency, and caps."""
    phase = state.get('arc_phase', 'setup')
    weights = _beat_weights_for_phase(phase, state.get('turn', 0))
    history = state.setdefault('beat_history', [])[-5:]
    candidates = []
    for beat, base in weights.items():
        if base <= 0:
            continue
        if history and beat == history[-1]:
            continue
        if beat in ('discovery', 'conflict') and history.count(beat) >= 2:
            continue
        score = base + _beat_salience(state, beat, intent)
        if score > 0:
            candidates.append((beat, score))

    if not candidates:
        fallback = [beat for beat in weights if not history or beat != history[-1]]
        fallback = [beat for beat in fallback if beat not in ('discovery', 'conflict') or history.count(beat) < 2]
        if not fallback:
            fallback = ['transition', 'encounter', 'rest', 'obstacle']
        candidates = [(beat, max(weights.get(beat, 1), 1)) for beat in fallback]

    total = sum(score for _, score in candidates)
    roll = random.uniform(0, total)
    cursor = 0
    for beat, score in candidates:
        cursor += score
        if roll <= cursor:
            return beat
    return candidates[-1][0]

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
    if intent == 'aggressive' and beat in ('conflict', 'obstacle', 'encounter'):
        score += 3
    if intent == 'social' and beat == 'encounter':
        score += 3
    if intent == 'cautious' and beat in ('discovery', 'obstacle', 'rest'):
        score += 2
    if intent == 'use_item' and beat in ('revelation', 'obstacle', 'discovery'):
        score += 2
    if intent == 'move' and beat == 'transition':
        score += 3
    if state.get('consequence_queue') and beat in ('encounter', 'revelation', 'conflict'):
        score += 1
    if state.get('turn', 0) and state.get('turn', 0) % 6 == 0 and beat != 'rest':
        score += 1
    if tension > 0.72 and beat in ('conflict', 'revelation', 'obstacle'):
        score += 2
    if tension < 0.35 and beat in ('discovery', 'transition', 'encounter'):
        score += 1
    if state.get('player_role') == 'cartographer' and beat in ('discovery', 'transition'):
        score += 1
    if state.get('player_drive') in ('atonement', 'redemption') and beat in ('encounter', 'revelation'):
        score += 1
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
