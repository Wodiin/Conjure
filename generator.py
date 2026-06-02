from dataclasses import dataclass
from stat_logic import generate_stats, generate_stat_modifiers
from combat_logic import calculate_ac, calculate_hp, get_action_data, generate_action_data
from information_logic import resolve_title, generate_information


@dataclass
class Selections:
    """A dataclass to represent the user's selections for generating an NPC."""

    cr: str
    base: str
    race: str
    primary: str | None = None
    secondary: str | None = None
    combat_kits: list[str] | None = None
    magic_kits: list[str] | None = None
    role_kits: list[str] | None = None
    environment: str | None = None
    use_primary_for_casting: bool = False
    personality: str | None = None
    gender: str | None = None
    generate_name_toggle: bool = False



#call sequence mockup:
# generate stats  = generate_stats(selections.cr, selections.base, selections.primary, selections.secondary, selections.race)
# generate modifiers = generate_stat_modifiers(stats)
# calculate AC = calculate_ac(selections.cr, selections.base, selections.primary, selections.combat_kits)
# calculate HP = calculate_hp(selections.cr, selections.base, modifiers["CON"])
# get the action data = get_action_data(selections.combat_kits, selections.magic_kits, selections.race)
# generate action data = generate_action_data(selections.cr, modifiers, action_data, selections.use_primary_for_casting, selections.primary)
# resolve name title = resolve_title(selections.role_kits, selections.combat_kits, selections.magic_kits)
# generate information = generate_information(selections.race, selections.combat_kits, selections.magic_kits, selections.role_kits, selections.environment)


def generate_npc(selections: Selections) -> dict:
    """Takes a Selections object and orchestrates the full NPC generation process,
    returning a complete NPC data dict ready for rendering."""

    # Generate stats and modifiers
    stats = generate_stats(selections.cr, selections.base, selections.primary, selections.secondary, selections.race)
    modifiers = generate_stat_modifiers(stats)

    # Calculate AC and HP
    ac = calculate_ac(selections.cr, selections.base, selections.primary, selections.combat_kits)
    hp = calculate_hp(selections.cr, selections.base, modifiers["CON"])

    # Get and generate action data
    raw_action_data = get_action_data(selections.combat_kits, selections.magic_kits, selections.race)
    action_data = generate_action_data(selections.cr, modifiers, raw_action_data, selections.use_primary_for_casting, selections.primary)

    # Resolve name title
    title = resolve_title(selections.role_kits, selections.combat_kits, selections.magic_kits)

    # Generate information
    information = generate_information(selections.race, selections.combat_kits, selections.magic_kits, selections.role_kits, selections.environment)

    # Return the complete NPC data
    return {
        "stats": stats,
        "modifiers": modifiers,
        "ac": ac,
        "hp": hp,
        "action_data": action_data,
        "title": title,
        "information": information
    }