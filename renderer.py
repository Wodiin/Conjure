import textwrap
from dataclasses import dataclass
from generator import generate_npc


@dataclass
class RenderedNPC:
    npc: dict
    name: str
    cr: str
    race: str
    personality: str
    alignment: str
    languages: list[str]


# Single knob for block width. The divider and prose wrapping must agree
# or the block renders ragged. 42 was too narrow: the info cluster lines
# (senses, saves) already run past it unwrapped.
WIDTH = 60
DIVIDER = "-" * WIDTH
SPEED_LABELS = { "Swimming": "Swim", "Flying": "Fly", "Climbing": "Climb", "Burrowing": "Burrow" }
ABILITY_ORDER = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
STAT_LABELS = { "STR": "Strength", "DEX": "Dexterity", "CON": "Constitution", "INT": "Intelligence", "WIS": "Wisdom", "CHA": "Charisma" }
MA_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                  6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def _wrap(text: str) -> list[str]:
    return textwrap.wrap(text, WIDTH)


def _wrap_entries(entries: list[str]) -> list[str]:
    # Blank line between entries, otherwise wrapped prose blocks
    # blur into one mass of text.
    lines = []
    for entry in entries:
        if lines:
            lines.append("")
        lines += textwrap.wrap(entry, WIDTH)
    return lines


def _join_blocks(*blocks: list[str]) -> list[str]:
    # Blank line between adjacent non-empty blocks. Empty blocks
    # contribute nothing, so no stray blanks on sparse NPCs.
    lines = []
    for block in blocks:
        if not block:
            continue
        if lines:
            lines.append("")
        lines += block
    return lines


def _header(rendered: RenderedNPC) -> list[str]:
    return [rendered.name, f"{rendered.npc['information']['size']} Humanoid ({rendered.race}), {rendered.alignment}"]


def _defence(rendered: RenderedNPC) -> list[str]:
    return [
        f"Armour Class {rendered.npc['ac']}",
        f"Hit Points {rendered.npc['hp']['hp']} ({rendered.npc['hp']['dice_string']})",
        f"Speed {_format_speed(rendered.npc['information']['speed'])}"
    ]


def _format_speed(speed_dict: dict[str, int]) -> str:
    joined_speeds = []
    for speed_type, distance in speed_dict.items():
        if speed_type == "Walking":
            joined_speeds.append(f"{distance}ft")
        else:
            joined_speeds.append(f"{SPEED_LABELS[speed_type]} {distance}ft")
    return " ".join(joined_speeds)


def _stats(rendered: RenderedNPC) -> list[str]:
    header = []
    footer = []
    for stat in ABILITY_ORDER:
        value = rendered.npc["stats"][stat]
        header.append(f"{stat:^7}")
        cell = f"{value}({_format_mod(rendered.npc['modifiers'][stat])})"
        footer.append(f"{cell:^7}")

    return [ "".join(header), "".join(footer) ]


def _saving_throws(rendered: RenderedNPC) -> list[str]:
    saving_throws = rendered.npc["information"]["saving_throws"]
    return ["Saving Throws " + ", ".join(f"{stat} {_format_mod(mod)}" for stat, mod in saving_throws.items())]


def _skills(rendered: RenderedNPC) -> list[str]:
    if "proficiencies" not in rendered.npc["information"]:
        return []
    skills = rendered.npc["information"]["proficiencies"]
    return ["Skills " + ", ".join(f"{skill} {_format_mod(mod)}" for skill, mod in skills.items())]


def _senses(rendered: RenderedNPC) -> list[str]:
    result = []
    if "senses" not in rendered.npc["information"]:
        return [f"Senses Passive Perception {rendered.npc['information']['passive_perception']}"]
    senses = rendered.npc["information"]["senses"]
    for sense, value in senses.items():
        result.append(f"{sense} {value}ft")
    return ["Senses " + ", ".join(result) + f", Passive Perception {rendered.npc['information']['passive_perception']}"]


def _resistances(rendered: RenderedNPC, key: str, label: str) -> list[str]:
    if key not in rendered.npc["information"]:
        return []
    return [f"{label} " + ", ".join(rendered.npc["information"][key])]


def _languages(rendered: RenderedNPC) -> list[str]:
    return ["Languages " + ", ".join(rendered.languages)]


def _challenge(rendered: RenderedNPC) -> list[str]:
    return [f"Challenge {rendered.cr} ({rendered.npc['information']['xp']:,}xp)"]


def _format_mod(mod: int) -> str:
    return f"{mod:+d}"


def _traits(rendered: RenderedNPC) -> list[str]:
    renderedNPC = rendered.npc
    info = renderedNPC["information"]
    action_data = renderedNPC["action_data"] or {}
    traits = action_data.get("traits", {})
    enviro = info.get("environmental_traits", {})
    role = info.get("role_traits", {})
    combined = {**traits, **enviro, **role}
    if not combined:
        return []
    entries = [f"{trait_name}. {trait_desc}" for trait_name, trait_desc in combined.items()]
    return _wrap_entries(entries)


def _section_header(rendered: RenderedNPC, keys: list[str], label: str) -> list[str]:
    action_data = rendered.npc["action_data"] or {}
    for k in keys:
        if k in action_data:
            return ["", label, DIVIDER]
    return []


def _multiattack(rendered: RenderedNPC) -> list[str]:
    action_data = rendered.npc["action_data"] or {}
    if "multiattack" not in action_data:
        return []
    count = action_data["multiattack"]["count"]
    count_str = MA_COUNT_WORDS.get(count, str(count))
    weapons = action_data["multiattack"]["weapons"]
    combat_weapons = [w for w in weapons if w != "Shield Bash"]
    has_shield = action_data["multiattack"]["has_shield"]
    if not combat_weapons:
        line = f"Multiattack. The character makes {count_str} attacks with their Shield Bash."
    elif len(combat_weapons) == 1:
        line = f"Multiattack. The character makes {count_str} attacks with their {combat_weapons[0]}."
    else:
        line = f"Multiattack. The character makes {count_str} attacks, which can be any combination of the following weapons: {', '.join(combat_weapons)}."
    if has_shield and combat_weapons:
        line += " It can replace one attack with a use of Shield Bash."
    return _wrap(line)


def _actions(rendered: RenderedNPC) -> list[str]:
    action_data = rendered.npc["action_data"] or {}
    if "weapons" not in action_data:
        return []
    entries = []
    for weapon_name, weapon_info in action_data["weapons"].items():
        wtype = weapon_info["weapon_type"]
        bonus = weapon_info["damage_bonus"]
        dice = f"{weapon_info['num_of_die']}d{weapon_info['die_size']} {'+' if bonus >= 0 else '-'} {abs(bonus)}"
        if wtype == "melee":
            attack = "Melee Attack Roll"
            distance = f"reach {weapon_info['reach']} ft."
        elif wtype == "ranged":
            attack = "Ranged Attack Roll"
            distance = f"range {weapon_info['range_min']}/{weapon_info['range_max']} ft."
        elif wtype == "thrown":
            attack = "Melee or Ranged Attack Roll"
            distance = f"reach {weapon_info['reach']} ft. or range {weapon_info['range_min']}/{weapon_info['range_max']} ft."
        else:
            raise ValueError(f"Unknown weapon type: {wtype}")
        entries.append(f"{weapon_name}. {attack}: {_format_mod(weapon_info['to_hit'])}, {distance} Hit: {weapon_info['damage_avg']} ({dice}) {weapon_info['damage_type'].capitalize()} damage.")
    return _wrap_entries(entries)


def _spells(rendered: RenderedNPC) -> list[str]:
    action_data = rendered.npc["action_data"] or {}
    if "spells" not in action_data:
        return []
    spells = action_data["spells"]
    intro = f"Spellcasting. The character casts one of the following spells, using {STAT_LABELS[spells['spellcasting_stat']]} as their spellcasting ability"
    intro += f" (spell save DC {spells['spell_save_dc']}, {_format_mod(spells['spell_attack_bonus'])} to hit with spell attacks):"
    buckets: dict[str, list[str]] = {}
    lines = _wrap(intro)
    lines.append("")
    for spell_name, spell_info in spells["spells_list"].items():
        buckets.setdefault(spell_info["casting_amount"], []).append(spell_name)
    for amount in sorted(buckets, key=_casting_rank, reverse=True):
        if amount == "at will":
            label = "At Will"
        else:
            parts = amount.split("/")
            label = f"{parts[0]}/{parts[1].capitalize()} Each"
        spell_list = ", ".join(buckets[amount])
        lines += _wrap(f"{label}: {spell_list}")
    return lines


def _casting_rank(amount: str) -> int:
    """Mirrors same function in combat_logic.py"""
    if amount == "at will":
        return 99
    return int(amount.split("/")[0])


def _bonus_actions(rendered: RenderedNPC) -> list[str]:
    action_data = rendered.npc["action_data"] or {}
    if "bonus_actions" not in action_data:
        return []
    entries = [f"{name}. {desc}" for name, desc in action_data["bonus_actions"].items()]
    return _wrap_entries(entries)


def _reactions(rendered: RenderedNPC) -> list[str]:
    action_data = rendered.npc["action_data"] or {}
    if "reactions" not in action_data:
        return []
    entries = [f"{name}. {desc}" for name, desc in action_data["reactions"].items()]
    return _wrap_entries(entries)


def render_as_text(rendered: RenderedNPC) -> str:
    render = []
    render.append(DIVIDER)
    render += _header(rendered)
    render.append(DIVIDER)
    render += _defence(rendered)
    render.append(DIVIDER)
    render += _stats(rendered)
    render.append(DIVIDER)
    render += _saving_throws(rendered)
    render += _skills(rendered)
    render += _resistances(rendered, "resistances", "Resistances")
    render += _resistances(rendered, "immunities", "Immunities")
    render += _resistances(rendered, "vulnerabilities", "Vulnerabilities")
    render += _senses(rendered)
    render += _languages(rendered)
    render += _challenge(rendered)

    # Traits and action sections are all optional. Building them first
    # and gating the divider on content avoids the stacked double
    # divider a bare NPC produced.
    body = []
    body += _traits(rendered)
    body += _section_header(rendered, ["weapons", "spells"], "Actions")
    body += _join_blocks(_multiattack(rendered), _actions(rendered), _spells(rendered))
    body += _section_header(rendered, ["bonus_actions"], "Bonus Actions")
    body += _bonus_actions(rendered)
    body += _section_header(rendered, ["reactions"], "Reactions")
    body += _reactions(rendered)
    while body and body[0] == "":
        body.pop(0)
    if body:
        render.append(DIVIDER)
        render += body

    render.append(DIVIDER)
    render += _wrap(rendered.personality)
    return "\n".join(render)





    '''
    ------------------------------------------
    Name:
    Medium Humanoid (race), Chaotic Neutral
    ------------------------------------------
    Armour Class 99
    Hit Points 999 (99d12 + 99)
    Speed 30ft Swim 30ft Fly 60ft
    ------------------------------------------
    STR    DEX    CON    INT    WIS    CHA
    10(+0) 10(+0) 10(+0) 10(+0) 10(+0) 10(+0) 
    ------------------------------------------
    Saving Throws Con +0, Wis +0
    Skills Athletics +5, Deception +5
    Senses passive Perception 10
    Languages Common
    Challenge 1 (200xp)
    ------------------------------------------
    Test Trait.. This test trait grants the 
    character the ability to test traits. How
    fun.

    Actions
    ------------------------------------------
    Multiattack. The character makes three 
    attacks with their Shortsword.

    Shortsword. Melee Weapon Attack: +2 to hit,
    reach 5ft, one target. 
    Hit: 6(1d6 + 3) piercing damage

    Reactions
    ------------------------------------------
    Parry. The character adds 2 to its AC
    against one melee attack that would hit it.
    To do so, the character must see the
    attacker and be wielding a melee weapon.
    '''