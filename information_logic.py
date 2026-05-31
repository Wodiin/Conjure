from data_loader import data
import random

RACES = data['races']
COMBAT_KITS = data['combat_kits']
MAGIC_KITS = data['magic_kits']
ROLE_KITS = data['role_kits']
ENVIRONMENTS = data['environments']
PERSONALITIES = data['personalities']
NAMES = data['names']

# Damage reduction strength ranking. Used to resolve conflicts when the same
# damage type is contributed by more than one source. Immunity beats
# resistance, and resistance beats vulnerability.
DAMAGE_RANK = {"Vuln": 1, "Half": 2, "Full": 3}


def _gather(
    key: str,
    race: str | None = None,
    kit_sources: tuple = (),
    environment: str | None = None,
) -> list:
    """Collect every list entry stored under `key` across the requested
    sources, with no deduplication.

    `kit_sources` is an iterable of (selected_names, kit_table) pairs, where
    selected_names may be None when that kit type is unused. A source is only
    read when its argument is provided, so callers control which of race,
    kits, and environment contribute to a given field."""
    entries: list = []
    if race is not None:
        entries.extend(RACES[race].get(key, []))
    for selected, table in kit_sources:
        if selected is None:
            continue
        for kit in selected:
            entries.extend(table[kit].get(key, []))
    if environment is not None:
        entries.extend(ENVIRONMENTS[environment].get(key, []))
    return entries


def _reduce_max(entries: list[dict], value_key: str) -> dict[str, int]:
    """Reduce name/value entries to a {name: value} dict, keeping the highest
    value when a name appears more than once."""
    result: dict[str, int] = {}
    for entry in entries:
        name = entry["name"]
        value = entry[value_key]
        if name not in result or value > result[name]:
            result[name] = value
    return result


def _reduce_unique(items: list[str]) -> list[str]:
    """Deduplicate a list of strings while preserving first-seen order."""
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _reduce_descriptions(entries: list[dict]) -> dict[str, str]:
    """Reduce name/description entries to a {name: description} dict, matching
    the trait shape produced by the action data logic."""
    return {entry["name"]: entry["description"] for entry in entries}


def generate_information(
    race: str,
    name: bool,
    gender: str | None,
    personality: str | None,
    combat_kits: list[str] | None,
    magic_kits: list[str] | None,
    role_kits: list[str] | None,
    environment: str | None,
) -> dict:
    """Build the non-combat portion of an NPC stat block from the user's
    selections. Gathers name, personality, senses, damage modifiers, speed,
    proficiencies, and out-of-combat traits. Only sections that actually have
    content are included in the returned dict."""

    info: dict = {}

    # Kit sources grouped for reuse. Senses and damage come from combat and
    # magic kits only. Proficiencies additionally come from role kits.
    combat_magic = ((combat_kits, COMBAT_KITS), (magic_kits, MAGIC_KITS))
    all_kits = combat_magic + ((role_kits, ROLE_KITS),)

    # Name. gender defaults to Neutral when not supplied.
    if name:
        name_gender = gender or "Neutral"
        first = random.choice(NAMES[name_gender][race]["First"])
        last = random.choice(NAMES[name_gender][race]["Last"])
        info["name"] = f"{first} {last}"

    # Personality.
    if personality:
        info["personality"] = random.choice(PERSONALITIES[personality]["entries"])["description"]

    # Senses: race, combat/magic kits, and environment, keeping the longest
    # range per sense type.
    senses = _reduce_max(
        _gather("senses", race=race, kit_sources=combat_magic, environment=environment),
        "range",
    )
    if senses:
        info["senses"] = senses

    # Damage modifiers: gather every resistance entry from race, combat/magic
    # kits, and environment, keeping the strongest reduction per damage type,
    # then split into the three stat block lines. Resolving by rank here means
    # a type can only ever land in one bucket, so no later reconciliation is
    # needed.
    damage: dict[str, str] = {}
    for entry in _gather("resistances", race=race, kit_sources=combat_magic, environment=environment):
        damage_type = entry["name"]
        reduction = entry["damage_reduction"]
        if damage_type not in damage or DAMAGE_RANK[reduction] > DAMAGE_RANK[damage[damage_type]]:
            damage[damage_type] = reduction

    resistances = [dtype for dtype, red in damage.items() if red == "Half"]
    immunities = [dtype for dtype, red in damage.items() if red == "Full"]
    vulnerabilities = [dtype for dtype, red in damage.items() if red == "Vuln"]
    if resistances:
        info["resistances"] = resistances
    if immunities:
        info["immunities"] = immunities
    if vulnerabilities:
        info["vulnerabilities"] = vulnerabilities

    # Speed: race and environment only, keeping the fastest per movement type.
    speed = _reduce_max(
        _gather("speed", race=race, environment=environment),
        "distance",
    )
    if speed:
        info["speed"] = speed

    # Proficiencies and tool proficiencies: all kit types, deduplicated.
    proficiencies = _reduce_unique(_gather("proficiencies", kit_sources=all_kits))
    if proficiencies:
        info["proficiencies"] = proficiencies

    tool_proficiencies = _reduce_unique(_gather("proficiencies_t", kit_sources=all_kits))
    if tool_proficiencies:
        info["tool_proficiencies"] = tool_proficiencies

    # Out-of-combat traits: environment and role kits, kept uncapped since they
    # carry no combat weight. Stored as {name: description} to match the trait
    # shape used by the action data logic.
    environmental_traits = _reduce_descriptions(_gather("traits", environment=environment))
    if environmental_traits:
        info["environmental_traits"] = environmental_traits

    role_traits = _reduce_descriptions(_gather("traits", kit_sources=((role_kits, ROLE_KITS),)))
    if role_traits:
        info["role_traits"] = role_traits

    return info