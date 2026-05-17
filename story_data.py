"""Rich vocabulary pools for compositional story generation."""

# ── Sensory fragments (sight, sound, smell, touch, taste) ─────────────────────

SIGHT = [
    "shadows twist into shapes that shouldn't exist",
    "pale light bleeds through cracks above",
    "dust motes spiral in a shaft of cold light",
    "the walls glisten with moisture that catches the light",
    "everything is painted in shades of bruise and ash",
    "faint phosphorescence outlines the edges of stone",
    "the horizon warps like heat over iron",
    "colors here feel wrong—too saturated, too alive",
    "a thin veil of mist clings to the ground",
    "light fractures through something crystalline overhead",
    "everything beyond arm's reach dissolves into murk",
    "the darkness isn't empty—it moves, it breathes",
    "strange symbols pulse faintly on every surface",
    "the sky overhead churns like a wound",
    "firelight throws jagged silhouettes across the walls",
    "something glints in your peripheral vision, then vanishes",
    "the architecture defies geometry—angles that hurt to follow",
    "veins of luminous mineral thread through the rock",
    "your shadow falls in the wrong direction",
    "the landscape ripples as if seen through deep water",
]

SOUND = [
    "a low hum vibrates through the floor beneath you",
    "something drips in a rhythm too deliberate to be natural",
    "the silence here has weight—it presses against your ears",
    "distant echoes fold over themselves, impossible to source",
    "a sound like breathing comes from everywhere at once",
    "metal scrapes against metal somewhere out of sight",
    "the wind carries a fragment of melody, then swallows it",
    "your footsteps return to you wrong—delayed, distorted",
    "a crack splits the air like snapping bone",
    "whispers thread through the stillness, just below comprehension",
    "stone groans deep within the walls, settling or waking",
    "the acoustics twist your voice into something unfamiliar",
    "a rhythmic tapping starts, stops, starts again closer",
    "thunder rolls through the ground rather than the sky",
    "something large shifts its weight in the dark ahead",
    "the crackle of energy builds to a subsonic throb",
    "water rushes somewhere below—fast, urgent, hidden",
    "a single clear note rings out, then fades to nothing",
    "insects fall silent in a wave spreading outward from you",
    "the sound of your own heartbeat becomes deafening",
]

SMELL = [
    "the air tastes of copper and old stone",
    "something sweet and rotting threads through each breath",
    "ozone hangs sharp and electric after the discharge",
    "the scent of wet earth and crushed herbs rises underfoot",
    "smoke—old smoke, baked into every surface",
    "a mineral sharpness burns the back of your throat",
    "the air carries something floral and deeply wrong",
    "petrichor mixes with something chemical and acrid",
    "incense and rust—an impossible combination",
    "the smell of the sea, miles from any ocean",
    "cold air carries no scent at all, which feels worse",
    "iron and salt—the unmistakable tang of blood",
    "pine resin and char, the aftermath of something burned",
    "the damp has a taste—fungal, ancient, patient",
    "every breath feels thick, coated, medicinal",
]

TOUCH = [
    "the surface is warm where it should be cold",
    "your fingers come away coated in fine, glittering dust",
    "the ground vibrates with a deep, irregular pulse",
    "the air itself feels heavier here—thicker, resistant",
    "your skin prickles with static that won't discharge",
    "the stone is glass-smooth, worn by something patient",
    "temperature shifts in bands—warm, cold, warm—as you move",
    "something brushes your shoulder that isn't there when you turn",
    "the wall yields slightly under pressure, almost organic",
    "frost crystals form on your fingertips, then melt instantly",
    "a draft pushes against you like a slow exhalation",
    "the texture changes beneath your feet—grit to silk to grit",
    "heat radiates from somewhere below, rising through your boots",
    "moisture collects on your skin despite no visible source",
    "the metal hums against your palm, resonant and alive",
]

# ── Verbs by intensity ────────────────────────────────────────────────────────

VERBS_MOTION_LOW = ['drift','ease','slip','edge','glide','pad','creep','thread','weave','meander']
VERBS_MOTION_MED = ['stride','push','navigate','carve','trace','press','cut','cross','climb','wade']
VERBS_MOTION_HIGH = ['hurtle','plunge','sprint','crash','barrel','lunge','vault','scramble','dive','bolt']

VERBS_LOOK = ['study','examine','trace','scan','peer at','squint at','survey','scrutinize','observe','drink in']
VERBS_DISCOVER = ['uncover','reveal','expose','stumble upon','find','unearth','notice','recognize','spot','identify']
VERBS_REACT = ['freeze','flinch','steady yourself','catch your breath','clench your jaw','narrow your eyes',
               'feel your pulse spike','swallow hard','set your stance','grip tighter']

# ── Adjectives by mood ────────────────────────────────────────────────────────

ADJ_TENSE = ['jagged','fractured','raw','unstable','volatile','razor-thin','trembling',
             'brittle','charged','suffocating','razor-edged','taut','splintered']
ADJ_MYSTERIOUS = ['impossible','shifting','mercurial','liminal','half-formed','othered',
                  'refracted','dreamlike','uncanny','spectral','gossamer','elusive']
ADJ_CALM = ['weathered','settled','patient','worn-smooth','ancient','quiet','still',
            'moss-draped','sun-warmed','slow','unhurried','gentle','amber-lit']
ADJ_DARK = ['lightless','hollow','rotting','gnawed','sepulchral','blackened','corroded',
            'festering','rank','sunken','pitted','scabrous','withered']

# ── Environmental fragments ───────────────────────────────────────────────────

ENV_DETAILS = [
    "cracks web across the {surface} like veins in old skin",
    "water has carved channels into the {surface} over centuries",
    "{growth} pushes through every gap, stubborn and blind",
    "the {surface} bears marks—deliberate, scored deep by something sharp",
    "layers of {deposit} have built up in rippled formations",
    "the {structure} tilts at an angle that suggests violence, not time",
    "everything here is coated in a fine layer of {substance}",
    "{light_source} casts the space in shades of {color} and deep shadow",
    "the {structure} is older than it should be—impossibly, unsettlingly old",
    "nature is reclaiming this place with {growth} and {substance}",
    "the geometry feels intentional—someone built this, someone with purpose",
    "erosion has softened every edge into something almost organic",
]

ENV_VARS = {
    'surface': ['stone','metal','wood','crystal','bone','glass','earth','ceramic','iron','granite'],
    'growth': ['lichen','roots','fungi','moss','vines','coral','barnacles','crystals','mold','creepers'],
    'deposit': ['calcium','mineral','salt','ice','sediment','ash','dust','sand','rust','resin'],
    'structure': ['archway','column','wall','ceiling','floor','doorframe','staircase','bridge','altar','throne'],
    'substance': ['dust','ash','salt','frost','grime','pollen','soot','spores','condensation','residue'],
    'light_source': ['bioluminescence','filtered sunlight','a single torch','reflected water-light',
                     'phosphorescent fungi','distant fire','cracks in the ceiling','an unknown source',
                     'crystalline refraction','dying embers'],
    'color': ['amber','cobalt','violet','copper','jade','silver','crimson','ochre','teal','bone-white'],
}

# ── Character/NPC fragments ──────────────────────────────────────────────────

NPC_INTROS = [
    "A figure materializes from the {adj} gloom—{desc}. {detail}.",
    "Someone is already here. {desc}, {posture}. {detail}.",
    "You almost miss them—{desc}, nearly invisible against the {background}. {detail}.",
    "A voice reaches you before the face does. {desc} steps into view, {posture}. {detail}.",
    "Movement. Your hand moves to defend before your mind catches up. It's {desc}, {posture}.",
]

NPC_DESCS = [
    "tall, gaunt, wrapped in layers of {fabric}",
    "small and sharp-eyed, hands never still",
    "broad-shouldered, face mapped with old scars",
    "young—too young for the exhaustion in their eyes",
    "ancient, steady, radiating a quiet authority",
    "hooded, their face a geometry of shadow and cheekbone",
    "lean and coiled, every movement precise and economical",
    "weathered, sun-dark, with hands like old leather",
    "pale and luminous, as if lit from within",
    "hunched, muttering, fingers tracing patterns in the air",
]

NPC_POSTURES = [
    "watching you with an expression you can't read",
    "one hand resting on something at their hip",
    "leaning against the wall like they've been waiting",
    "crouched over something they shield with their body",
    "standing perfectly still, unnervingly still",
    "pacing a tight circle, wearing a groove in the ground",
    "arms crossed, chin raised, measuring you",
    "turned half away, as if deciding whether to bolt",
]

NPC_DETAILS = [
    "Their eyes hold knowledge they aren't sharing",
    "A fresh wound on their forearm seeps through cloth",
    "They carry something wrapped in stained fabric",
    "The air around them smells of herbs and desperation",
    "Their breathing is controlled—trained, deliberate",
    "Something about their posture says military, or worse",
    "They flinch at a sound only they can hear",
    "Their gear is expensive but damaged—someone who fell far",
]

DIALOGUE_OPENERS = [
    '"You shouldn\'t be here." Their voice is {tone}.',
    '"Finally." The word drops like a stone. {reaction}.',
    '"Don\'t move." {reaction}. "Not yet."',
    '"I\'ve been waiting for someone. Not you, specifically. But someone." {reaction}.',
    '"Turn back." Their eyes flick past you. "While turning back is still an option."',
    '"You see it too, don\'t you?" {reaction}. "Tell me you see it."',
    '"Three others came this way. None came back." {reaction}.',
    '"I can help you. For a price." {reaction}.',
    'They say nothing. Just extend a hand—palm up, offering something small and glinting.',
    '"How much do you know?" {reaction}. "About any of this?"',
]

TONES = ['flat, drained of everything','a rasp, barely above a whisper',
         'steady, rehearsed, like they\'ve said it before',
         'sharp enough to cut','warm, unexpectedly warm',
         'trembling despite their best effort','hollow, echoing oddly',
         'musical, lilting, wrong for the setting']

REACTIONS = [
    'You feel your jaw tighten','Something cold settles in your chest',
    'The hairs on your arms lift','Your hand moves instinctively',
    'A beat of silence stretches too long','You hold their gaze, reading nothing',
    'Trust wars with instinct inside you','The weight of the moment lands hard',
]

# ── Action response fragments ────────────────────────────────────────────────

FIGHT_FRAGMENTS = [
    "You commit to the strike—weight forward, no hesitation. {outcome}.",
    "Instinct overrides thought. Your body moves before the decision is fully made. {outcome}.",
    "The first blow connects with a sound like {impact}. {outcome}.",
    "You close the distance in two steps, reading their center of gravity. {outcome}.",
    "Everything narrows to a single point of focus. {outcome}.",
]

FIGHT_OUTCOMES = [
    "The impact reverberates up your arm. Something gives, but you can't tell whose",
    "They stagger. Not enough. They're already adjusting, already countering",
    "Contact. Solid. The shock of it jolts through you like voltage",
    "They're faster than expected. Your strike grazes but doesn't land clean",
    "For one frozen second, you see surprise in their eyes. Then the moment shatters",
]

STEALTH_FRAGMENTS = [
    "You press into the {cover}, controlling each breath until it matches the silence. {detail}",
    "Movement becomes meditation—each step placed with surgical patience. {detail}",
    "You find the rhythm of this place and slip between its beats. {detail}",
    "Shadow becomes ally, texture becomes map. You navigate by absence. {detail}",
]

EXPLORE_FRAGMENTS = [
    "You {look_verb} the space with fresh attention, letting details surface. {finding}.",
    "Running your hands along the {surface}, you feel for what eyes might miss. {finding}.",
    "You work the area methodically—left to right, top to bottom, missing nothing. {finding}.",
    "Something about the {feature} doesn't sit right. You look closer. {finding}.",
    "Pattern recognition kicks in. What seemed random resolves into {finding}.",
]

FINDINGS = [
    "there—a seam in the {surface} that shouldn't exist, behind it, hollow space",
    "markings, recent ones, overlaid on much older ones, telling a different story",
    "a mechanism, disguised as ornament, yields under pressure with a soft click",
    "the proportions are wrong — this space is smaller inside than outside",
    "residue — chemical, biological, impossible to identify but definitely recent",
    "a draft, barely perceptible, from a direction that makes no architectural sense",
    "scratches in the {surface} — not random, a message left by someone in a hurry",
]

COVERS = ['deepest shadow','narrow alcove','gap between structures','rubble',
          'overgrown recess','fallen debris','natural formation','dark pocket']

IMPACTS = ['cracking timber','a bell struck wrong','splitting stone','wet cloth tearing',
           'an axe hitting frozen wood','a door slamming shut','bone on bone','breaking ceramic']

# ── Transition & consequence fragments ────────────────────────────────────────

TRANSITIONS = [
    "The {passage} opens into something entirely different. {first_impression}.",
    "You emerge from the {passage} and stop dead. {first_impression}.",
    "The landscape transforms within a dozen steps. {first_impression}.",
    "A threshold—physical, maybe more. Beyond it, {first_impression}.",
    "The world rearranges itself around a corner. {first_impression}.",
]

FIRST_IMPRESSIONS = [
    "Scale hits first—this space is vast, cathedral-vast, and humming with {quality}",
    "The air changes instantly: {quality}, sharp, alive with {element}",
    "Everything here is {adj}—the walls, the floor, even the light itself",
    "Your body registers danger before your mind names it. Something is deeply {adj} here",
    "Beauty, unexpected and fierce. {element} catches the light like {simile}",
    "Ruin. Complete, thorough, and very recent. {element} still {verb} in the aftermath",
]

QUALITIES = ['stillness','energy','decay','growth','absence','presence','wrongness',
             'anticipation','age','power','grief','hunger','memory','potential']
ELEMENTS = ['crystal formations','running water','suspended particles','living light',
            'root systems','mineral deposits','thermal vents','ancient machinery',
            'organic structures','electrical discharge','frozen time','moving shadow']
SIMILES = ['shattered cathedral glass','liquid mercury','a held breath','spilled ink',
           'burning magnesium','frozen lightning','shed skin','scattered teeth']

# ── Consequence/continuity phrases ────────────────────────────────────────────

CALLBACKS = [
    "The {item} you found earlier pulses once, responding to something here",
    "This connects to what the {npc} said—the pattern is becoming clearer",
    "You've seen these markings before. The same hand, the same urgency",
    "Whatever happened at the {location}, it started here. Or ended here",
    "The {item} feels different now—heavier, warmer, more insistent",
    "You remember the {npc}'s warning. They were right about more than you credited",
]

# ── Hook/cliffhanger closers ─────────────────────────────────────────────────

HOOKS = [
    "Then you see it. And everything you thought you understood rearranges itself.",
    "A sound reaches you—distant, deliberate, and heading this way.",
    "The ground shifts. Not an earthquake. Something underneath. Something aware.",
    "You realize, with cold clarity, that you are not the first to stand here today.",
    "The way back has changed. You're certain of it. The geometry is different now.",
    "Something watches. You can't see it. You can't prove it. But you know.",
    "A choice presents itself—one that can't be unmade once taken.",
    "The silence that follows is louder than anything that came before.",
    "Your instincts scream two contradictory warnings at once.",
    "And then the light goes out.",
    "In the distance, something answers.",
    "It moves. Whatever it is—it moves.",
    "You hear your own name. Spoken clearly. From the wrong direction.",
    "The mark on the wall matches the mark on your skin. Exactly.",
    "You have seconds to decide. The window is already closing.",
]

# ── Choice verb pools ─────────────────────────────────────────────────────────

CHOICE_VERBS_BOLD = ['confront','breach','challenge','seize','charge','push into',
                     'demand answers from','face down','break through','force open']
CHOICE_VERBS_CAUTIOUS = ['observe','circle around','test carefully','wait for',
                         'listen at','study from cover','probe','feel out','shadow','map']
CHOICE_VERBS_CLEVER = ['exploit','redirect','repurpose','decode','outsmart',
                       'find leverage in','reverse-engineer','piece together','dismantle','unravel']
