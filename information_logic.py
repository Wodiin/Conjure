from data_loader import data
import random

RACES = data['races']
COMBAT_KITS = data['combat_kits']
MAGIC_KITS = data['magic_kits']
ROLE_KITS = data['role_kits']
ENVIRONMENTS = data['environments']
PERSONALITIES = data['personalities']
NAMES = data['names']
PROFICIENCIES = data['proficiencies_map']
CR_TABLE = data['cr_table']

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


def _map_proficiencies(entries: list[str], modifiers: dict[str, int], prof_bonus: int) -> dict[str, int]:
    """Maps proficiency entries to a {proficiency: modifier} dict, adding the
    proficiency bonus to the relevant ability modifier found in the
    proficiencies map. Raises if an entry is missing from the map so a
    contributor sees the gap loudly rather than shipping a wrong number."""
    result = {}
    for entry in entries:
        ability = PROFICIENCIES.get(entry)
        if ability is None:
            raise KeyError(f"'{entry}' is not mapped in proficiencies_map.json")
        result[entry] = modifiers[ability] + prof_bonus
    return result


# Passive Perception is a mandatory line on every stat block, so its call site
# is unguarded unlike the optional sections. The proficiency bonus is only
# added when the NPC is proficient in Perception.
def _calculate_passive_perception(wis_mod: int, prof_bonus: int, is_proficient: bool) -> int:
    """Calculate the passive perception score based on the wisdom modifier,
    proficiency bonus, and whether the NPC is proficient in perception."""
    passive_perception = 10 + wis_mod
    if is_proficient:
        passive_perception += prof_bonus
    return passive_perception


def generate_information(
    race: str,
    combat_kits: list[str] | None,
    magic_kits: list[str] | None,
    role_kits: list[str] | None,
    environment: str | None,
    modifiers: dict[str, int],
    cr: str,
) -> dict:
    """Build the non-combat portion of an NPC stat block from the user's
    selections. Gathers senses, damage modifiers, speed,
    proficiencies, and out-of-combat traits. Only sections that actually have
    content are included in the returned dict."""

    info: dict = {}

    # Proficiency bonus is read once here and threaded into the skill and
    # passive Perception calculations below, rather than looked up per use.
    prof_bonus = CR_TABLE[cr]["proficiency_bonus"]

    # Kit sources grouped for reuse. Senses and damage come from combat and
    # magic kits only. Proficiencies additionally come from role kits.
    combat_magic = ((combat_kits, COMBAT_KITS), (magic_kits, MAGIC_KITS))
    all_kits = combat_magic + ((role_kits, ROLE_KITS),)

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
    proficiency_mods = _map_proficiencies(proficiencies, modifiers, prof_bonus)
    if proficiency_mods:
        info["proficiencies"] = proficiency_mods

    info["passive_perception"] = _calculate_passive_perception(
        modifiers["WIS"], prof_bonus, "Perception" in proficiencies
    )

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


def _order_by_weight(a: tuple[str, int], b: tuple[str, int]) -> str:
    """Join two (display_name, display_name_weight) kits into a title, higher
    weight first. Ties keep the first argument ahead, which preserves
    selection order since callers pass the earlier kit first."""
    if a[1] >= b[1]:
        return f"{a[0]} {b[0]}"
    return f"{b[0]} {a[0]}"


def _pair(kits: list[str], table: dict, i: int) -> tuple[str, int]:
    """The (display_name, display_name_weight) of the kit at index i."""
    entry = table[kits[i]]
    return entry["display_name"], entry["display_name_weight"]


def resolve_title(
    role_kits: list[str] | None,
    combat_kits: list[str] | None,
    magic_kits: list[str] | None,
) -> str:
    """Derive an NPC's default title from its selected kits.

    Walks a fixed precedence ladder, first match wins: no kits, Mythical
    Conjuration, a single maxed specialty, then a weight-ordered title built
    from combat and magic kits, then from role kits, with a Commoner floor.
    Role counts as a full specialty alongside combat and magic.

    Concatenation never exceeds two names. When combat and magic are both
    present, each bucket's first selected kit is the finalist and the two are
    ordered by weight. When only one specialty is present, that bucket's first
    two selected kits fight it out, or its single kit is shown alone. A bucket
    is represented by selection order, so the user reorders names by
    deselecting and reselecting a kit."""

    num_combat = len(combat_kits) if combat_kits else 0
    num_magic = len(magic_kits) if magic_kits else 0
    num_role = len(role_kits) if role_kits else 0

    # Tier 1: nothing selected.
    if not (num_combat or num_magic or num_role):
        return "Commoner"

    # Tier 2: two specialties maxed (3+ each), or all three at 2+.
    maxed = sum(n >= 3 for n in (num_combat, num_magic, num_role))
    if maxed >= 2 or (num_combat >= 2 and num_magic >= 2 and num_role >= 2):
        return "Mythical Conjuration"

    # Tier 3: exactly one specialty maxed (mutually exclusive after tier 2).
    if num_combat >= 3:
        return "Master of Arms"
    if num_magic >= 3:
        return "Magus"
    if num_role >= 3:
        return "Jack of All Trades"

    # Tier 4: combat and/or magic present, role ignored. Two buckets fight it
    # out across each other; one bucket fights within itself; a lone kit shows
    # alone.
    if num_combat or num_magic:
        if num_combat and num_magic:
            return _order_by_weight(_pair(combat_kits, COMBAT_KITS, 0),
                                    _pair(magic_kits, MAGIC_KITS, 0))
        if num_combat:
            if num_combat == 1:
                return COMBAT_KITS[combat_kits[0]]["display_name"]
            return _order_by_weight(_pair(combat_kits, COMBAT_KITS, 0),
                                    _pair(combat_kits, COMBAT_KITS, 1))
        if num_magic == 1:
            return MAGIC_KITS[magic_kits[0]]["display_name"]
        return _order_by_weight(_pair(magic_kits, MAGIC_KITS, 0),
                                _pair(magic_kits, MAGIC_KITS, 1))

    # Tier 5: only role kits remain.
    if num_role == 1:
        return ROLE_KITS[role_kits[0]]["display_name"]
    return _order_by_weight(_pair(role_kits, ROLE_KITS, 0),
                            _pair(role_kits, ROLE_KITS, 1))

    # Failsafe: Should never be reached since tier 1 covers the no-kit case, but just in case:
    return "Report this name bug to Developer"


# The following functions generate random names and personalities when the user requests them.
# They also provide enumerations of valid options for the name and personality fields,
# which the UI can use to validate user input and populate dropdowns.
def generate_name(race: str, gender: str | None) -> str:
    """Generate a random name appropriate to the NPC's race and gender."""
    if gender is None:
        gender = "Neutral"
    return random.choice(NAMES[gender][race]["First"]) + " " + random.choice(NAMES[gender][race]["Last"])


def generate_personality(personality: str | None) -> str | None:
    """Generate a random personality trait if the user requested one."""
    if personality is None:
        return None
    return random.choice(PERSONALITIES[personality]["entries"])["description"]


def enum_name_races() -> list[str]:
    """Return a list of all valid race names."""
    return sorted(list(NAMES["Neutral"].keys()))


def enum_personality_options() -> list[str]:
    """Return a list of all valid personality options."""
    return sorted(list(PERSONALITIES.keys()))