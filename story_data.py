"""Grounded fragment pools for The Butterfly Effect narrative engine.

These pools are intentionally narrow. Each entry supports a concrete scene fact:
NPC memory, faction pressure, location changes, identity callbacks, or delayed
consequence. Broad sensory/metaphor fragments were removed because they allowed
the engine to decorate scenes with unsupported nouns.
"""

ENV_VARS = {
    "surface": [
        "stone",
        "wood",
        "iron",
        "mud",
        "road dust",
        "oilcloth",
        "granite",
        "salt",
        "ash",
        "old paper",
    ],
}

NPC_TICS = [
    "they touch the signet at their throat before answering",
    "they count your exits with one slow movement of the eyes",
    "they rub old ink from the side of their thumb",
    "they pause whenever your pack shifts, listening for metal",
    "they keep their wounded side angled away from you",
    "they fold every sentence as carefully as a letter",
    "they check the road behind you before meeting your gaze",
    "they press two fingers against a hidden charm under the coat",
    "they speak only after the rain has filled the silence",
    "they hold still in the practiced way of someone avoiding notice",
    "they smile too late, as if remembering the shape of courtesy",
    "they watch your hands instead of your face",
    "they move their jaw around a name they will not say",
    "they tap a route-map rhythm against their sleeve",
    "they breathe through pain and pretend it is patience",
]

NPC_ARCHETYPES = [
    "border scout",
    "debt clerk",
    "pilgrim courier",
    "failed officer",
    "salt broker",
    "road surgeon",
    "abbey informant",
    "map thief",
    "gravewarden witness",
    "runaway heir",
    "muted negotiator",
    "cart road saboteur",
    "black ford guide",
    "ledger priest",
]

NPC_SECRETS = [
    "they sold a route that should have stayed unwritten",
    "they know which faction burned the toll records",
    "they are carrying a message addressed to your old name",
    "they watched a patrol vanish and reported the wrong direction",
    "they have been paid twice to betray the same traveler",
    "they hid a survivor where the official count says none remained",
    "they can identify the mark that keeps appearing near your path",
    "they owe protection to someone who wants you delayed",
    "they remember your role from a version of the story you deny",
    "they buried a key under a milestone and no longer know why",
]

NPC_WANTS = [
    "to leave the region before the weather closes the road",
    "to trade information without becoming its owner",
    "to make you choose a side where neutrality used to be possible",
    "to recover a ledger before the names inside it start dying",
    "to buy one clean hour for someone they failed",
    "to learn whether your reputation is useful or fatal",
    "to pass a warning to the Glass Abbey without being seen",
    "to have their betrayal understood as necessity",
    "to test whether you are the kind of person rumours claim",
    "to move a hidden witness from one danger into another",
]

NPC_LOYALTIES = [
    "soldiers in red",
    "the Toll Guild",
    "the Glass Abbey",
    "moth-cloaked pilgrims",
    "gravewardens",
    "salt smugglers",
    "exiled banner-men",
    "keepers of the old road",
    "the Hollow Court",
    "the Cartographers Accord",
    "black border scouts",
    "border healers",
]

NPC_MEMORY_REACTIONS = {
    "ally": [
        "Their guarded face softens by one careful degree; they remember what you risked.",
        "They leave space beside the fire without offering it aloud.",
        "They answer the question you are too proud to ask first.",
    ],
    "neutral": [
        "They measure you against what the road has been saying.",
        "They keep courtesy between you like a knife laid flat.",
        "They remember enough to be cautious, not enough to be kind.",
    ],
    "hostile": [
        "The look they give you has already made its decision.",
        "They use your name like evidence.",
        "Nothing in their posture offers a road back to trust.",
    ],
}

NPC_DIALOGUE = [
    '"You have been described badly; I am deciding whether badly means accurately."',
    '"Names move faster than feet here. Yours arrived wet, cold, and armed."',
    '"If you want truth, pay in something heavier than coin."',
    '"No one crosses this stretch without owing a future favor."',
    '"The road has started making room for you. That should frighten you."',
    '"I can tell you who saw it. I cannot promise they are still alive."',
    '"Speak carefully. Half the roofs here repeat what they hear."',
    '"I know what you did two villages back. I know who survived it."',
    '"There is a version of this story where you turn around. I recommend it."',
    '"You carry old weather with you. People notice."',
    '"Ask the right question and I will risk a useful answer."',
    '"Do not mistake silence for ignorance. We keep accounts."',
]

PIVOT_BEATS = [
    "By sunset, {faction} has barred the road behind {location}; return will now cost more than courage.",
    "{npc} changes allegiance in the space between one breath and the next, and {region} quietly changes with them.",
    "A witness repeats what you did earlier, but the rumour has grown teeth by the time it reaches {region}.",
    "The old path near {location} is gone, swallowed by weather, sabotage, or a decision made without you.",
    "Someone spends your name as currency, and {faction} accepts it at a ruinous rate.",
    "A local account in {region} adds one unpaid line pointing back to {wound}.",
    "The faction banners at {location} are rehung before dawn, and nobody admits who ordered it.",
    "An ally near {location} pays for helping you, which means the help has become part of the world's debt.",
    "{faction} hears of the {item} at {location} and starts treating it as proof.",
    "The weather turns around {location} as if the road itself has chosen a side.",
]

AMBIENT_EVENTS = {
    "road": [
        "A cart passes with its wheels wrapped in cloth, hiding either cargo or grief.",
        "Someone has corrected the mile marker by knife, then corrected the correction.",
        "The ditch holds fresh bootprints facing both directions and belonging to no visible traveler.",
        "A toll notice has been nailed over a prayer, and both are still wet.",
    ],
    "settlement": [
        "Market voices lower as you pass, then rise behind you in a different arrangement.",
        "A child is pulled indoors before they can finish pointing at your gear.",
        "Someone has left bread on a windowsill with a black thread tied through it.",
        "The inn sign has been turned inward, as if hospitality has become a private matter.",
    ],
    "ruin": [
        "Old ash shifts in a wind that does not reach your face.",
        "A carved name has been recently scratched out with professional patience.",
        "Water collects in the stone sockets of statues whose eyes were removed long ago.",
        "Someone has swept one path clean through the dust, then vanished from it.",
    ],
    "wilderness": [
        "Birdsong stops in sections, as though the trees pass warning by border.",
        "The mud preserves a running track that begins without approach.",
        "A snare hangs open, bait untouched, trigger already sprung.",
        "Rainwater gathers in hoofprints too large for any local horse.",
    ],
    "interior": [
        "A latch clicks somewhere in the walls and then regrets the sound.",
        "The hearth is cold, but ash has been stirred within the hour.",
        "A ledger page curls near the flame without burning.",
        "Dust has been cleared from one chair and no others.",
    ],
}

ROLE_CALLBACKS = [
    "The {role} in you reads the room before the rest of you admits there is danger.",
    "Old habits from your life as a {role} rise through your hands, practical and unwelcome.",
    "You notice what another traveler would miss because the road is speaking to the {role} you used to be.",
    "For a moment, the {role} returns: not as title, but as reflex.",
    "The scene asks for nerve, but your answer comes first from the {role}'s training.",
]

WOUND_CALLBACKS = [
    "The old wound returns as a bodily fact: {wound}, carried under the ribs rather than in memory.",
    "For one breath you are back inside {wound}, and the present has to wait its turn.",
    "The scene touches {wound} with a cold finger, and your next choice narrows.",
    "You thought {wound} had gone quiet. It had only learned patience.",
    "Something in the air names {wound} without words.",
]

DRIVE_CALLBACKS = [
    "Your {drive} does not speak grandly. It tightens your grip and keeps you moving.",
    "The road offers reasons to stop; your {drive} answers each one badly but firmly.",
    "You feel {drive} become less like motive and more like weather.",
    "At this pressure, {drive} is the only honest map you have left.",
    "Whatever else has changed, {drive} still knows the shape of forward.",
]

CONSEQUENCE_FRAGMENTS = [
    "What you did at {location} has reached {region} ahead of you, carried by {heard_by}.",
    "{witnessed_by} saw enough at {location} to make a shorter, harsher story of it.",
    "A debt opens from an earlier choice: {description}",
    "The local faction has adjusted its manners around what happened at {location}; this is not forgiveness.",
    "Someone repeats your action without your context, and the world judges the shorter version.",
    "The delayed cost arrives without ceremony: {description}",
    "A colder greeting waits near {location}; consequence has learned logistics.",
    "{location} remembers not the decision, but the damage pattern it left behind.",
]

# ── Overhaul v4 Systems additions ─────────────────────────────────────────────

THEME_KEYWORDS = {
    'forest': ['forest', 'wood', 'grove', 'trees', 'thicket', 'canopy', 'branch', 'foliage', 'green', 'leaf', 'twigs', 'pine', 'sap', 'bark'],
    'water': ['water', 'sea', 'ocean', 'drowned', 'sailor', 'ship', 'boat', 'lake', 'river', 'coast', 'causeways', 'surf', 'salt', 'reef', 'drown', 'wreck', 'cenote', 'tide'],
    'ruins': ['ruin', 'spire', 'temple', 'cathedral', 'tower', 'stone', 'basalt', 'milestone', 'statue', 'lintel', 'cairn', 'archway', 'obelisk', 'city', 'vanished', 'pueblo', 'excavation'],
    'stealth': ['spy', 'documents', 'stolen', 'thief', 'border', 'soldier', 'patrol', 'secret', 'hidden', 'cautious', 'sneak', 'war-torn', 'crosses', 'informant'],
    'cold': ['frost', 'ice', 'snow', 'winter', 'chill', 'glacier', 'frozen', 'gloom', 'cold', 'sour']
}

MOTIFS = {
    'broken_mirrors': {
        'low': "A tiny shard of silvered glass catches the light in the dirt, reflecting a fractured sky.",
        'medium': "Cracked glass fragments catch the light at your feet, showing your face split into unrecognizable halves.",
        'high': "A shattered mirror hangs askew nearby, its sharp shards shivering in the wind like a silent scream."
    },
    'distant_bells': {
        'low': "A faint, brass chime sounds from somewhere beyond the ridge, fading quickly.",
        'medium': "The iron bell of a distant chapel tolls three slow, heavy strokes through the fog.",
        'high': "A deafening, rhythmic tolling echoes off the surrounding stone, filling the air with the taste of old bronze."
    },
    'black_dust': {
        'low': "A fine layer of soot-like ash covers the nearby surfaces.",
        'medium': "Black, upward-dripping residue pools in the deep hollows of the path.",
        'high': "A dark, choking smoke rises from the dry soil, smelling of ancient lightning."
    },
    'water_marks': {
        'low': "A damp outline showing high-water levels stains the nearest vertical stone.",
        'medium': "Upward-dripping moisture pools on the underside of the rock overhead.",
        'high': "Water seeps directly from the dry grain of the wood, carrying the cold smell of old salt."
    }
}

# Rich variant templates for the story beats. Keys are beats, values are lists of templates.
PROSE_TEMPLATES = {
    'discovery': [
        {
            'format': "sensory_first",
            'intro': "Under the {weather} of the {location}, a quiet detail presents itself. {motif_text}",
            'body': "Your decision to {action_verb} leads you directly to {object_name}. The {location_noun} feels less like a new path and more like a line drawn by someone who knew you were coming.",
            'beat': "Here, the {features[0]} has been left exposed, bearing the markings of the {faction}.",
            'hook': "The next useful truth remains buried somewhere in this {location_noun}."
        },
        {
            'format': "action_first",
            'intro': "You choose to {action_verb} near the {features[0]}, forcing the {location_noun} to yield a response.",
            'body': "The {object_name} catches the light. {motif_text} In the surrounding {region}, where the {faction} holds sway, details do not hide without a purpose.",
            'beat': "A careful inspection reveals a physical trace: {description_detail}.",
            'hook': "What you did here will not stay quiet for long."
        }
    ],
    'encounter': [
        {
            'format': "observational",
            'intro': "The {features[0]} at the {location_noun} is not empty. {motif_text}",
            'body': "A figure steps from the shadow of the {features[0]}. It is {npc_name}, a {npc_archetype} whose eyes are already counting your gear.",
            'beat': "{npc_tic_text} {npc_memory_text} \"I know what path you have walked,\" they whisper. \"{npc_dialogue}\"",
            'hook': "{npc_short_name} watches you closely, waiting to see if your silence matches your reputation."
        },
        {
            'format': "tense",
            'intro': "The tension at the {location_noun} thickens as {weather} settles over the {features[0]}.",
            'body': "You confront {npc_name} by the {features[0]}, the {object_name} still between you. They stand as a {npc_archetype} who knows what faction holds the road here.",
            'beat': "{npc_tic_text} {npc_memory_text} \"If you came for answers,\" they say, \"speak with the {faction} first.\" {npc_dialogue}",
            'hook': "The space between you remains narrow and cold."
        }
    ],
    'obstacle': [
        {
            'format': "tense",
            'intro': "The path forward through the {location_noun} is blocked. {motif_text}",
            'body': "The {features[0]} forms a barrier that your map maker's eye did not account for. Attempting to {action_verb} here will leave an obvious trail for the {faction} to follow.",
            'beat': "A heavy barrier of wood and iron blocks the line; forcing it will require Strength or Cunning.",
            'hook': "The road demands a price, and the nearest witnesses are already watching."
        },
        {
            'format': "reflective",
            'intro': "Your history as a {role} taught you to look for the structural weakness in any block. {motif_text}",
            'body': "You check the obstruction at the {location_noun}. The {object_name} offers a leverage point, but the memory of {wound} makes you pause.",
            'beat': "The block at the {features[0]} is deliberate; the {faction} clearly intended to seal this route.",
            'hook': "You must decide what you are willing to break to pass."
        }
    ],
    'revelation': [
        {
            'format': "reflective",
            'intro': "A moment of stillness catches you at the {location_noun}. {motif_text}",
            'body': "By the light of the {weather}, the true nature of the {object_name} becomes legible. Your wound, {wound}, echoes in the silence.",
            'beat': "The {features[0]} reveals a hidden truth: {description_detail}. The {faction} has been active here, and their records are incomplete.",
            'hook': "The truth is yours now, but its weight is already shifting."
        },
        {
            'format': "observational",
            'intro': "You study the {object_name} under the shade of the {features[0]}.",
            'body': "The details align. What you wanted to find at the {location_noun} is gone, but this place leaves a different answer: {description_detail}.",
            'beat': "A local sign matches the rumors about {faction} in {region}.",
            'hook': "You have the line; now you must choose where it leads."
        }
    ],
    'transition': [
        {
            'format': "action_first",
            'intro': "You press onward, leaving the {location_noun} behind as the {weather} worsens.",
            'body': "Your choice to {action_verb} opens a line out of the area. {motif_text} Your reputation as {reputation} travels faster than your boots.",
            'beat': "A narrow causeway leading toward {region} becomes visible near the {features[0]}.",
            'hook': "The next stretch of road waits, unmapped and silent."
        },
        {
            'format': "sensory_first",
            'intro': "The light shifts over the {features[0]}, indicating that your time at the {location_noun} is done. {motif_text}",
            'body': "You map a route past the {object_name}. The {faction} patrols the border, but the {role} in you knows how to read the landscape for exits.",
            'beat': "The path shifts toward a new region, leaving the old marks behind.",
            'hook': "Ahead lies the boundary of {region}."
        }
    ],
    'conflict': [
        {
            'format': "tense",
            'intro': "Danger stops being atmospheric at the {location_noun}. {motif_text}",
            'body': "The sound of steel or shouting echoes near the {features[0]}. You face the threat with the {object_name} in hand, your drive for {drive} tightening your grip.",
            'beat': "The clash costs you; pain blooms under the ribs as the patrol closes the exits.",
            'hook': "The conflict is active, and only force or quick movement will resolve it."
        },
        {
            'format': "action_first",
            'intro': "You strike first by the {features[0]}, choosing the aggressive line before the {location_noun} can turn against you.",
            'body': "Your actions at the {location_noun} are witnessed by the {faction}. {motif_text} The cost of this confrontation is written on the road.",
            'beat': "The clash is brief but violent, leaving marks on the stone and your body.",
            'hook': "The echoes of this violence will reach the next town before you do."
        }
    ],
    'rest': [
        {
            'format': "reflective",
            'intro': "For a short while, the {location_noun} gives you cover under the {weather}. {motif_text}",
            'body': "You rest by the hearth or the treeline, counting your wounds. You look at your {object_name}, letting {wound} fade into the quiet background.",
            'beat': "Your stats show the cost of the road, but the silence here is a temporary shield.",
            'hook': "The road is waiting, but for now, you breathe."
        },
        {
            'format': "observational",
            'intro': "The quiet at the {location_noun} holds. {motif_text}",
            'body': "You take shelter near the {features[0]}, checking your supplies. In {region}, the local rumors about {faction} feel distant for a moment.",
            'beat': "You update your notes or your map, tracing the lines of where you have bled.",
            'hook': "The silence will break when the dawn comes."
        }
    ]
}

PREMISE_NOUN_PHRASING = {
    'sister': ('your sister', 'person'),
    'brother': ('your brother', 'person'),
    'father': ('your father', 'person'),
    'mother': ('your mother', 'person'),
    'friend': ('your friend', 'person'),
    'god': ('the drowned god', 'person'),
    'fighter': ('your identity as a fighter', 'person'),
    'cartographer': ('your identity as a cartographer', 'person'),
    'sailor': ('your identity as a sailor', 'person'),
    'spy': ('your identity as a spy', 'person'),
    'healer': ('your identity as a healer', 'person'),
    'city': ('the vanished city', 'place'),
    'border': ('the war-torn border', 'place'),
    'forest': ('the frost-bitten forest', 'place'),
    'ruins': ('the plague ruins', 'place'),
    'cure': ('the cure', 'object'),
    'documents': ('the stolen documents', 'object'),
    'rumors': ('the rumors', 'object'),
}

