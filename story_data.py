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
