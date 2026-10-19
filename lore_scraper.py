"""Automated lore scraper and repository builder for The Butterfly Effect.

Fetches authoritative world-building, science, environmental, and genre lore from
encyclopedic and web sources, structuring them into premise-aligned lore packs
stored in lore_corpus/documents/.
"""

import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LORE_DIR = BASE_DIR / "lore_corpus" / "documents"
try:
    LORE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    LORE_DIR = Path("/tmp/lore_corpus/documents")
    try:
        LORE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

_SSL_CTX = ssl._create_unverified_context()
_USER_AGENT = "ButterflyLoreScraper/2.0 (narrative_research; +https://github.com/kaunshivansh/The_Butterfly_Effect)"


def scrape_wikipedia_topic(title: str) -> dict:
    """Fetch structured extract and sections from Wikipedia REST API."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=8) as res:
            data = json.loads(res.read().decode("utf-8"))
            return {
                "title": data.get("title", title),
                "description": data.get("description", ""),
                "extract": data.get("extract", ""),
            }
    except Exception as e:
        return {"title": title, "error": str(e), "extract": ""}


def search_wikipedia_topics(query: str, limit: int = 3) -> list[str]:
    """Search Wikipedia for topics related to query."""
    clean_q = re.sub(r'[\'\"\,]', '', query).strip()
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
            hits = data.get("query", {}).get("search", [])
            return [h["title"] for h in hits[:limit] if h.get("title")]
    except Exception:
        return []


def scrape_and_create_lore_pack(premise: str, role: str = "", setting: str = "") -> dict:
    """Dynamically scrape authoritative web/encyclopedic sources for a novel premise,
    assemble a rich, structured Lore Pack, and save it into lore_corpus/documents/{genre_id}.json.
    """
    # 1. Derive slug and keywords
    role_clean = (role or "").strip().lower()
    if role_clean and len(role_clean) >= 3:
        genre_id = re.sub(r"[^a-z0-9]+", "_", role_clean).strip("_")
    else:
        words = re.findall(r"[a-zA-Z]{4,}", premise.lower())
        stop = {"whose", "which", "where", "their", "there", "about", "would", "could", "should", "every", "before"}
        meaningful = [w for w in words if w not in stop]
        genre_id = meaningful[0] if meaningful else "adventure"

    # Keywords from premise
    premise_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", premise)]
    keywords = list(dict.fromkeys([genre_id, role_clean] + [w for w in premise_words if len(w) > 3]))[:15]

    # 2. Determine communication mode
    kw_str = " ".join(keywords)
    if any(k in kw_str for k in ("astronaut", "space", "shuttle", "submersible", "submarine", "pilot", "ship", "radio", "comms")):
        comm_mode = "radio_comms"
    elif any(k in kw_str for k in ("hacker", "cyberpunk", "netrunner", "android", "ai", "cyborg", "terminal", "matrix")):
        comm_mode = "cyber_link"
    elif any(k in kw_str for k in ("cat", "kitten", "feline", "wolf", "hound", "dog", "beast", "paws")):
        comm_mode = "feline_sensory"
    elif any(k in kw_str for k in ("ghost", "gothic", "haunted", "crypt", "cult", "vampire", "horror", "curse")):
        comm_mode = "whisper"
    else:
        comm_mode = "spoken"

    # 3. Search and scrape Wikipedia topics
    search_queries = [
        f"{role_clean} {setting}".strip(),
        genre_id.replace("_", " "),
        premise[:50],
    ]
    topics = []
    for q in search_queries:
        if q and len(q) > 2:
            hits = search_wikipedia_topics(q, limit=2)
            for h in hits:
                if h not in topics:
                    topics.append(h)
        if len(topics) >= 3:
            break

    scraped_data = []
    scraped_extracts = []
    for top in topics[:3]:
        info = scrape_wikipedia_topic(top)
        if info.get("extract"):
            scraped_data.append(info)
            scraped_extracts.append(info["extract"])

    combined_text = " ".join(scraped_extracts)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", combined_text) if len(s.strip()) > 25]

    # 4. Extract realistic facts and atmospheric elements
    env_sentences = [s for s in sentences if any(w in s.lower() for w in ("in", "city", "region", "area", "built", "located", "place", "structure", "room", "center"))][:4]
    if not env_sentences:
        env_sentences = [
            f"a quiet, high-walled chamber steeped in the history of {genre_id.replace('_', ' ')}",
            f"the threshold of {setting or 'the district'}, where old traditions meet sudden change",
        ]

    terminology = list(dict.fromkeys([w.lower() for w in re.findall(r"\b[A-Z][a-z]{3,}\b", combined_text)]))[:10]
    if not terminology:
        terminology = [genre_id.replace("_", " "), "chronicle", "threshold", "archives", "quarters"]

    npcs = [
        {"name": f"The Elder {genre_id.replace('_', ' ').title()}", "role": "senior advisor", "format": comm_mode},
        {"name": f"Courier of {setting.title() or 'the Quarter'}", "role": "messenger", "format": comm_mode},
    ]

    dialogue_templates = [
        f"\"Stay vigilant,\" {{name}} cautions in low tones. \"What happened at the {{location}} was only the beginning.\"",
        f"{{name}} steps forward with a measured nod: \"If you seek answers, you will not find them by standing still.\"",
    ]

    sensory_details = [
        f"the faint, unmistakable scent of aged parchment, dry timber, and cold stone",
        f"the muted echoes of footsteps vibrating across the stone floor",
    ]

    choice_templates = [
        "Investigate the archives at the {location} for hidden historical records",
        "Consult your notes and plan your next move with deliberate caution",
        "Confront the watchful observer near the entrance to demand an explanation",
        "Survey the surrounding ground for signs of recent passage",
    ]

    lore_pack = {
        "genre_id": genre_id,
        "name": f"{genre_id.replace('_', ' ').title()} Chronicles",
        "keywords": keywords,
        "communication_mode": comm_mode,
        "scraped_sources": scraped_data,
        "environment": env_sentences,
        "hazards": [f"an unexpected challenge arising from the tensions in {setting or genre_id}"],
        "terminology": terminology,
        "npcs": npcs,
        "dialogue_templates": dialogue_templates,
        "sensory_details": sensory_details,
        "choice_templates": choice_templates,
    }

    # Save to story repository
    dest_file = LORE_DIR / f"{genre_id}.json"
    try:
        dest_file.write_text(json.dumps(lore_pack, indent=2), encoding="utf-8")
    except OSError:
        pass
    return lore_pack


def build_lore_pack(
    genre_id: str,
    name: str,
    keywords: list[str],
    topics_to_scrape: list[str],
    communication_mode: str,
    custom_facts: dict,
) -> dict:
    """Scrape web knowledge and assemble a complete, coherent Lore Pack."""
    print(f"Scraping lore for genre [{genre_id}]...")
    scraped_data = []
    for topic in topics_to_scrape:
        info = scrape_wikipedia_topic(topic)
        if info.get("extract"):
            scraped_data.append(info)

    lore_pack = {
        "genre_id": genre_id,
        "name": name,
        "keywords": keywords,
        "communication_mode": communication_mode,  # 'radio_comms', 'feline_sensory', 'cyber_link', 'noir_whisper', 'spoken'
        "scraped_sources": scraped_data,
        "environment": custom_facts.get("environment", []),
        "hazards": custom_facts.get("hazards", []),
        "terminology": custom_facts.get("terminology", []),
        "npcs": custom_facts.get("npcs", []),
        "dialogue_templates": custom_facts.get("dialogue_templates", []),
        "sensory_details": custom_facts.get("sensory_details", []),
        "choice_templates": custom_facts.get("choice_templates", []),
    }

    dest_file = LORE_DIR / f"{genre_id}.json"
    try:
        dest_file.write_text(json.dumps(lore_pack, indent=2), encoding="utf-8")
        print(f"Saved lore pack to {dest_file} ({dest_file.stat().st_size} bytes)")
    except OSError:
        pass
    return lore_pack


def seed_core_lore_repository():
    """Scrape and populate the core story repository with rich, genre-coherent lore."""
    # 1. Sci-Fi Space & Planetary Survival
    build_lore_pack(
        genre_id="scifi_space",
        name="Deep Space & Planetary Survival",
        keywords=[
            "astronaut", "space", "moon", "jupiter", "europa", "orbit", "oxygen",
            "spacesuit", "shuttle", "station", "satellite", "debris", "airlock",
            "telemetry", "radiation", "propulsion", "lander", "eva", "vacuum",
            "cosmic", "alien planet", "starship", "cryo", "colony"
        ],
        topics_to_scrape=["Europa_(moon)", "Extravehicular_activity", "Space_suit", "Space_debris"],
        communication_mode="radio_comms",
        custom_facts={
            "environment": [
                "a desolate plain of fractured cryo-ice glowing beneath the gas giant's banded clouds",
                "a field of jagged orbital wreckage drifting in silent gravitational lock",
                "the airless rim of an ancient impact crater where telemetry signals bounce erratically",
                "a pressurized habitation module humming with the strained vibration of auxiliary scrubbers",
                "a sub-surface ice cavern lit only by the narrow beam of your helmet floodlight",
            ],
            "hazards": [
                "life-support telemetry warning that oxygen reserves have fallen below critical thresholds",
                "a sharp spike in ionizing cosmic radiation penetrating your suit's outer shielding",
                "a micro-meteorite puncture venting pressure from an auxiliary thruster seal",
                "a sudden fracture in the subterranean cryo-ice threatening structural breach",
                "electromagnetic interference from Jupiter's magnetosphere scrambling your nav-beacon",
            ],
            "terminology": [
                "oxygen scrubbers", "telemetry HUD", "EVA thruster pack", "radiation dosimeter",
                "airlock decompression valve", "distress transponder", "cryo-volcanic fissure",
                "inertial guidance tracker", "pressurized suit seals", "emergency oxygen canister"
            ],
            "npcs": [
                {"name": "Colony Dispatch Delta", "role": "automated comm beacon", "format": "radio"},
                {"name": "Synthetics Unit Echo", "role": "damaged station android", "format": "radio"},
                {"name": "Commander Vane", "role": "surviving shuttle pilot", "format": "suit_radio"},
                {"name": "Deep-Scan Rover 04", "role": "autonomous exploratory probe", "format": "hud_feed"},
            ],
            "dialogue_templates": [
                "Static tears across your helmet comms: \"{name} to survivor... signal strength at twenty percent. Confirm life signs before the next radiation cycle.\"",
                "An automated alert pings inside your visor HUD: \"{name} reports atmospheric depletion. Recommend immediate breach containment.\"",
                "A tense, strained voice breaks through the radio frequency: \"Survivor, this is {name}. Keep your seals tight. There is an active leak near the airlock.\"",
                "The distress repeater loops across your headset: \"All personnel: {name} beacon is active. Orbital rendezvous window closes in three hours.\"",
            ],
            "sensory_details": [
                "the mechanical hiss of recycled breath scraping against your inner helmet visor",
                "the colossal marbled silhouette of Jupiter filling half the silent, star-punctured sky",
                "the cold numbness creeping into your gloved fingertips as ambient temperature drops",
                "the rhythmic red blink of the oxygen warning in the lower quadrant of your HUD",
                "the muffled vibration of your boots transmitting impact through solid extraterrestrial ice",
            ],
            "choice_templates": [
                "Check your suit telemetry and re-route auxiliary power to life support",
                "Scan the wreckage at the {location} for a salvageable emergency oxygen canister",
                "Broadcast a directional distress frequency toward {region} orbit",
                "Secure a magnetic tether and navigate the cryo-ice ridge",
                "Examine the damaged airlock controls to force a pressure cycle",
            ]
        }
    )

    # 2. Cyberpunk & High-Tech Noir
    build_lore_pack(
        genre_id="cyberpunk",
        name="Cyberpunk & Neon Sprawl",
        keywords=[
            "hacker", "cyberpunk", "netrunner", "cyborg", "cybernetic", "neon",
            "megacorp", "tokyo", "data", "deck", "ice", "ai", "terminal", "implant",
            "black market", "synthetic", "android", "drone", "glitch", "subroutine"
        ],
        topics_to_scrape=["Cyberpunk", "Neuromancer", "Cyberware"],
        communication_mode="cyber_link",
        custom_facts={
            "environment": [
                "a rain-slicked alleyway bathed in the stuttering cyan glow of holographic adverts",
                "a smoke-choked underground cyber-clinic humming with jury-rigged diagnostic rigs",
                "the steel catwalk overlooking the neon-drenched canyon of the lower district",
                "an abandoned server node lined with cooled optical fiber racks and humming fans",
            ],
            "hazards": [
                "a Black ICE counter-intrusion probe scorching your neural jack",
                "a corporate surveillance drone hovering overhead with scanning optics",
                "a corrupt precinct officer demanding an unregistered cred-chip transfer",
                "a sudden power surge frying the bypass capacitors in your deck",
            ],
            "terminology": [
                "neural jack", "cyberdeck", "ICE breaker", "encrypted datashard",
                "sub-dermal plating", "holographic visor", "optical camouflage", "cred-chip"
            ],
            "npcs": [
                {"name": "Null-Vector", "role": "renegade netrunner", "format": "cyber_link"},
                {"name": "Doc Kessler", "role": "back-alley ripperdoc", "format": "spoken"},
                {"name": "Voss", "role": "corporate syndicate fixer", "format": "cyber_link"},
            ],
            "dialogue_templates": [
                "A direct neuro-link packet flickers in your peripheral vision: \"{name} here. The corp ICE is already sniffing this subnet. Pull the shard and disconnect.\"",
                "\"{name} told you this gig was dirty,\" the voice murmurs through the encrypted channel. \"Don't leave digital fingerprints on the grid.\"",
                "\"You're burning daylight and bandwidth,\" {name} whispers. \"The security drones sweep this block every ninety seconds.\"",
            ],
            "sensory_details": [
                "the hot metallic tang of overclocked cyberware humming beneath your temple",
                "acid rain hissing against asphalt, reflecting fractured magenta and violet neon",
                "the synthetic hum of repulsor vehicles cruising along high-rise transit rails",
            ],
            "choice_templates": [
                "Jack into the terminal at the {location} and run a stealth ICE bypass",
                "Slip beneath the neon shadows to evade the security drone patrol",
                "Analyze the encrypted datashard for corporate clearance codes",
                "Overclock your cybernetic optics to trace the server's optical cables",
            ]
        }
    )

    # 3. Urban Feline / Stray Cat
    build_lore_pack(
        genre_id="feline",
        name="Urban Feline Perspective",
        keywords=[
            "cat", "feline", "kitten", "stray", "paws", "whiskers", "claws",
            "tail", "fur", "prowling", "alleycat", "purr", "meow", "gutter"
        ],
        topics_to_scrape=["Feral_cat", "Cat_senses", "Cat_behavior"],
        communication_mode="feline_sensory",
        custom_facts={
            "environment": [
                "a narrow cobblestone alley flanked by damp brick walls and overflowing wooden crates",
                "a dizzying zinc rooftop slick with twilight drizzle and chimney smoke",
                "the sheltered hollow beneath a market stall smelling of salt herring and sawdust",
                "a sun-warmed windowsill overlooking the restless bustle of the street below",
            ],
            "hazards": [
                "a snarling neighborhood dog straining against a rusted wire chain",
                "a sudden downpour cascading off gutters and flooding the cobblestones",
                "a territory-marking rival tomcat bristling on the garden fence",
                "an impatient street vendor wielding a wooden broom",
            ],
            "terminology": [
                "velvet paws", "whiskers", "scent markings", "retractable claws",
                "tail twitch", "night vision", "low crouch", "cobblestone cracks"
            ],
            "npcs": [
                {"name": "The Old Ginger Tom", "role": "scarred territory rival", "format": "hiss"},
                {"name": "The Baker's Apprentice", "role": "friendly bread-thrower", "format": "spoken"},
                {"name": "The Butcher's Mastiff", "role": "chained alley dog", "format": "growl"},
            ],
            "dialogue_templates": [
                "Across the yard, {name} lowers its ears flat and emits a warning rasp: the alley has already been claimed.",
                "From the open doorway, {name} tosses a scrap of warm fat into the sawdust with a quiet whistle.",
                "The low, vibrating rumble of {name} rattles against the wooden fence: one step closer means teeth.",
            ],
            "sensory_details": [
                "the damp scent of moss, chimney soot, and frying lard riding the evening breeze",
                "the sharp prickle of cold rain striking your ears as whiskers twitch with vigilance",
                "the silent, cushioned impact of your paws springing between wet stone steps",
                "every distant footstep vibrating through the floorboards into your ribcage",
            ],
            "choice_templates": [
                "Leap silently onto the wooden awning above the {location}",
                "Crouch low in the shadows and test the air for the scent of food",
                "Arch your spine and give a low, firm warning hiss at the intruder",
                "Squeeze through the iron railing into the dry courtyard",
            ]
        }
    )

    # 4. Noir Detective & Mystery
    build_lore_pack(
        genre_id="noir",
        name="Hardboiled Noir & Detective Mystery",
        keywords=[
            "detective", "noir", "private eye", "murder", "investigator", "trenchcoat",
            "cigarette", "revolver", "alibi", "crime", "clue", "gumshoe", "suspect"
        ],
        topics_to_scrape=["Film_noir", "Hardboiled", "Private_investigator"],
        communication_mode="noir_whisper",
        custom_facts={
            "environment": [
                "a rain-drenched street corner where yellow taxicabs throw glare across wet asphalt",
                "a second-story office smelling of stale tobacco, dried ink, and cheap bourbon",
                "a shadowy warehouse dock where river water slaps rhythmically against oily pilings",
            ],
            "hazards": [
                "a hired muscle waiting in the stairwell with a lead pipe",
                "a forged alibi leading straight into a police commissioner's crosshairs",
                "a blackmail photograph that someone is willing to kill to recover",
            ],
            "terminology": [
                ".38 snub-nose", "matchbook clue", "brass knuckles", "venetian blinds",
                "corrupt precinct", "faded ledger", "trenchcoat pocket", "ballistics report"
            ],
            "npcs": [
                {"name": "Lieutenant O'Malley", "role": "cynical precinct cop", "format": "spoken"},
                {"name": "Vivian Ross", "role": "nervous heiress", "format": "spoken"},
                {"name": "Mickey the Pen", "role": "dockside informant", "format": "whisper"},
            ],
            "dialogue_templates": [
                "\"{name} warned you to drop this case three days ago,\" the voice says through the smoke. \"Curiosity has a habit of ending at the coroner's slab.\"",
                "\"{name} didn't tell you the whole story,\" Mickey whispers, pressing a crumpled matchbook into your palm. \"Check the address inside.\"",
            ],
            "sensory_details": [
                "the cold trickle of rain sneaking past your upturned trenchcoat collar",
                "the click of a silver lighter illuminating tired, suspicious eyes in the dark",
                "the sour tang of burnt coffee and cheap tobacco hanging in the hallway",
            ],
            "choice_templates": [
                "Search the desk drawers at the {location} for the missing correspondence",
                "Question the contact about who paid for the silence at the {location}",
                "Slip out through the fire escape before precinct detectives arrive",
                "Examine the bloodstains and tire marks on the wet pavement",
            ]
        }
    )

    # 5. Gothic Horror & Occult
    build_lore_pack(
        genre_id="horror",
        name="Gothic Horror & Psychological Dread",
        keywords=[
            "horror", "gothic", "haunted", "ghost", "witch", "curse", "vampire",
            "mansion", "crypt", "graveyard", "nightmare", "occult", "demon"
        ],
        topics_to_scrape=["Gothic_fiction", "Haunted_house", "Occult"],
        communication_mode="whisper",
        custom_facts={
            "environment": [
                "an ancient ancestral manor where portraits seem to shift their gaze in the flickering candlelight",
                "a mist-strangled graveyard where sunken headstones lean like broken teeth",
                "a damp stone cellar echoing with the slow, deliberate drip of unseen water",
            ],
            "hazards": [
                "a sudden draft that extinguishes your last tallow candle",
                "a scratching sound behind the wainscoting that follows your exact pace",
                "a rusted iron gate that swings shut with a deafening latch",
            ],
            "terminology": [
                "tallow candle", "iron talisman", "parchment ritual", "tomb seal",
                "ancestral crypt", "salt circle", "decaying timber", "unconsecrated ground"
            ],
            "npcs": [
                {"name": "Sister Agnes", "role": "traumatized nun", "format": "whisper"},
                {"name": "Gideon the Sexton", "role": "gravekeeper", "format": "spoken"},
            ],
            "dialogue_templates": [
                "\"{name} told us the seals were unbroken,\" a rasping whisper breathes from the gloom. \"They lied.\"",
                "\"Do not look into the mirror at the end of the hall,\" {name} trembles. \"It no longer shows the living.\"",
            ],
            "sensory_details": [
                "the stench of old damp earth and sweet, sickly rot hanging in the cold air",
                "the rhythmic thud of your own pulse ringing deafeningly in your ears",
                "the freezing cold that sweeps through the room right before the floorboards creak",
            ],
            "choice_templates": [
                "Hold up the tallow candle and inspect the scratch marks on the door",
                "Recite the protective ward and bar the iron latch behind you",
                "Search the decaying bookshelves at the {location} for the family chronicle",
                "Tread softly across the creaking floorboards toward the window",
            ]
        }
    )

    # 6. Oceanic Abyss & Submersible
    build_lore_pack(
        genre_id="oceanic",
        name="Abyssal Trench & Deep Sea",
        keywords=[
            "submarine", "ocean", "deep sea", "abyss", "diver", "trench",
            "hull", "sonar", "torpedo", "water", "drowning", "pressure", "submersible"
        ],
        topics_to_scrape=["Challenger_Deep", "Submersible", "Deep_sea"],
        communication_mode="radio_comms",
        custom_facts={
            "environment": [
                "the cramped, condensation-drenched cockpit of a deep-sea submersible suspended in pitch-black water",
                "a towering hydrothermal chimney spewing shimmering mineral plumes into the abyss",
                "the crushed skeletal iron of a sunken freighter resting upon the silty trench floor",
            ],
            "hazards": [
                "a deafening groan of titanium framing as ambient pressure exceeds six hundred atmospheres",
                "a flashing red indicator warning that the starboard ballast valve has frozen open",
                "a sudden battery drain plunging the cabin into absolute, suffocating darkness",
            ],
            "terminology": [
                "titanium hull", "hydrothermal vent", "sonar ping", "ballast tank",
                "oxygen scrubbers", "bioluminescent tendril", "pressure gauge", "depth sonar"
            ],
            "npcs": [
                {"name": "Chief Engineer Barnes", "role": "sonar operator", "format": "intercom"},
                {"name": "Nautilus Automated Core", "role": "submersible AI", "format": "speaker"},
            ],
            "dialogue_templates": [
                "Barnes's voice cracks over the intercom: \"Sonar picked up a solid contact at two hundred meters below us... and it's climbing fast.\"",
                "A warning klaxon sounds: \"{name} alerts hull stress at eighty-eight percent. Discontinue dive immediately.\"",
            ],
            "sensory_details": [
                "the cold drops of condensed moisture falling steadily onto the back of your neck",
                "the deep, metallic ping of the active sonar echoing through the pressurized steel",
                "ghostly ribbons of pale blue bioluminescence drifting past the thick acrylic viewport",
            ],
            "choice_templates": [
                "Purge the forward ballast tank to arrest the descent",
                "Direct the external searchlights toward the hydrothermal chimney",
                "Seal the watertight hatch leading to the lower engine compartment",
                "Re-calibrate the sonar hydrophone to isolate the anomalous acoustic ping",
            ]
        }
    )

    print("Lore repository successfully populated!")


if __name__ == "__main__":
    seed_core_lore_repository()
