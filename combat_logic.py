from data_loader import data

# Load reference data
BASE_CATEGORIES = data['base_categories']
CR_TABLE = data['cr_table']
COMBAT_KITS = data['combat_kits']
WEAPONS = data['weapons']
RACES = data['races']
MAGIC_KITS = data['magic_kits']


def calculate_ac(cr: str, base: str, primary: str | None, combat_kits: list[str] | None) -> int:
    """Calculates the final AC based on CR, base category, primary stat, and combat kits.
    Uses the CR table for a baseline AC, then applies an offset from the base category
    depending on whether enhanced conditions are met (DEX primary or kit flag)."""

    # Get base AC from CR table
    ac = CR_TABLE[cr]['armour_class']

    # Enhanced AC if the NPC is DEX-focused or any kit grants it, otherwise default
    if primary == 'DEX' or (combat_kits and any(COMBAT_KITS[k]['enhanced_ac'] for k in combat_kits)):
        ac += BASE_CATEGORIES[base]['armour']['ac_mod_enhanced']
    else:
        ac += BASE_CATEGORIES[base]['armour']['ac_mod_default']

    return ac


def calculate_hp(cr: str, base: str, con_mod: int) -> dict[int, str]:
    """Calculates the final HP and dice expression string for an NPC.
    Uses hit dice count from the CR table, hit die size from the base category,
    and the NPC's actual CON modifier. Returns a dictionary with keys 'hp' and 'dice_string'."""

    num_dice = CR_TABLE[cr]['hit_dice_count']
    die_size = BASE_CATEGORIES[base]['hit_die']

    # CR 0 with negative CON is an edge case - floor HP at 1
    if cr == "0" and con_mod < 0:
        dice_string = f"1d{die_size} - {abs(con_mod)}"
        return {"hp": 1, "dice_string": dice_string}

    # Calculate total HP: num_dice × avg_die + num_dice × con_mod
    avg_die = (die_size + 1) / 2
    hp = int(num_dice * avg_die + num_dice * con_mod)

    # Build the dice expression string based on the sign of the CON contribution
    con_contribution = num_dice * con_mod

    if con_contribution < 0:
        dice_string = f"{num_dice}d{die_size} - {abs(con_contribution)}"
    elif con_contribution == 0:
        dice_string = f"{num_dice}d{die_size}"
    else:
        dice_string = f"{num_dice}d{die_size} + {con_contribution}"

    return {"hp": hp, "dice_string": dice_string}


def generate_action_data(
    cr: str,
    modifiers: dict[str, int],
    actions: dict | None,
    use_primary_for_casting: bool = False,
    primary: str | None = None
) -> dict | None:
    """Generates a dict of action data based on CR, stat modifiers, and
    available actions. Calculates weapon stats, multiattack structure,
    spellcasting block, and passes through traits, bonus actions, and
    reactions with their CR-based budget.

    Returns None if no actions are provided."""

    if actions is None:
        return None

    action_data: dict = {}
    weapons_data: dict = {}
    weapon_list: list[str] = actions.get("weapons", [])
    has_shield: bool = "Shield Bash" in weapon_list
    prof_bonus: int = CR_TABLE[cr]["proficiency_bonus"]

    # Weapons - calculate to-hit, damage bonus, average damage, and
    # weapon type classification for each weapon in the action set
    for weapon in weapon_list:
        weapon_info: dict = WEAPONS[weapon]

        # Classify weapon type based on reach and range values
        if weapon_info["range"]["short"] > 0 and weapon_info["reach"] >= 5:
            weapon_type = "thrown"
        elif weapon_info["reach"] >= 5:
            weapon_type = "melee"
        else:
            weapon_type = "ranged"

        # Versatile weapons use two-handed damage only when no shield is present
        versatile: bool = weapon_info["versatile"] and not has_shield

        # Finesse weapons use the higher of STR or DEX for attack and damage
        if weapon_info["finesse"]:
            attack_mod: int = max(modifiers["STR"], modifiers["DEX"])
        else:
            attack_mod = modifiers[weapon_info["to_hit_stat"]]

        to_hit: int = attack_mod + prof_bonus
        damage_bonus: int = attack_mod

        # Use versatile damage dice when applicable, otherwise standard
        num_of_die: int = weapon_info["versatile_damage"]["amount"] if versatile else weapon_info["damage"]["amount"]
        die_size: int = weapon_info["versatile_damage"]["dice"] if versatile else weapon_info["damage"]["dice"]
        damage_avg: int = int(num_of_die * (die_size + 1) / 2 + damage_bonus)

        weapons_data[weapon] = {
            "weapon_type": weapon_type,
            "num_of_die": num_of_die,
            "die_size": die_size,
            "damage_type": weapon_info["damage_type"],
            "to_hit": to_hit,
            "damage_bonus": damage_bonus,
            "damage_avg": damage_avg,
            "reach": weapon_info["reach"],
            "range_min": weapon_info["range"]["short"] if weapon_type != "melee" else None,
            "range_max": weapon_info["range"]["long"] if weapon_type != "melee" else None,
            "targets": weapon_info["targets"],
        }

    if weapons_data:
        action_data["weapons"] = weapons_data

    # Multiattack - only generated when CR grants more than one attack
    # and the NPC has at least one weapon available.
    # Future: switch type to "prescriptive" for monstrous base types
    if CR_TABLE[cr]["multiattack_count"] > 1 and weapon_list:
        action_data["multiattack"] = {
            "type": "any_combination",
            "count": CR_TABLE[cr]["multiattack_count"],
            "weapons": weapon_list,
            "has_shield": has_shield,
        }

    # Spells - determine the spellcasting ability, save DC, and attack
    # bonus. When use_primary_for_casting is True, the primary stat is
    # used regardless of its value. Otherwise, the highest mental stat
    # (INT, WIS, CHA) is selected automatically.
    if "spells" in actions:
        if use_primary_for_casting and primary:
            spellcasting_stat: str = primary
        else:
            spellcasting_stat = max(["INT", "WIS", "CHA"], key=modifiers.get)

        casting_mod: int = modifiers[spellcasting_stat]
        # LEGACY: budget is now a legacy value. See traits.
        action_data["spells"] = {
            "spells_list": actions["spells"],
            "spell_save_dc": 8 + casting_mod + prof_bonus,
            "spell_attack_bonus": casting_mod + prof_bonus,
            "spell_budget": CR_TABLE[cr]["spell_budget"],
            "spellcasting_stat": spellcasting_stat,
        }

    # Traits, Bonus Actions, and Reactions are passed through as-is.
    # LEGACY: traits budget is now legacy code but kept in for 
    # potential future use. Was intended to cull traits to avoid bloat.
    # User now controls the number of traits displayed.
    if "traits" in actions or "bonus_actions" in actions or "reactions" in actions:
        action_data["trait_budget"] = CR_TABLE[cr]["trait_budget"]
    if "traits" in actions:
        action_data["traits"] = actions["traits"]
    if "bonus_actions" in actions:
        action_data["bonus_actions"] = actions["bonus_actions"]
    if "reactions" in actions:
        action_data["reactions"] = actions["reactions"]

    return action_data

    
        


def _casting_rank(amount: str) -> int:
    """Converts casting frequency to a comparable integer. Higher is better."""
    if amount == "at will":
        return 99
    return int(amount.split("/")[0])
 
 
def get_action_data(combat_kits: list[str] | None, magic_kits: list[str] | None, race: str | None) -> dict | None:
    """Gathers traits, weapons, spells, bonus actions, and reactions from
    the selected race, combat kits, and magic kits. Returns a structured
    dict organised for downstream action generation, or None if no
    sources are provided."""
    if race is None and magic_kits is None and combat_kits is None:
        return None
 
    action_data = {}
 
    def _collect_descriptions(race_key: str, combat_key: str, magic_key: str) -> dict[str, str]:
        """Builds a name → description dict from every selected source,
        sorted alphabetically by name."""
        result = {}
        if race is not None:
            for item in RACES[race].get(race_key, []):
                result[item["name"]] = item["description"]
        if combat_kits is not None:
            for kit in combat_kits:
                for item in COMBAT_KITS[kit].get(combat_key, []):
                    result[item["name"]] = item["description"]
        if magic_kits is not None:
            for kit in magic_kits:
                for item in MAGIC_KITS[kit].get(magic_key, []):
                    result[item["name"]] = item["description"]
        return dict(sorted(result.items()))
 
    # Traits
    traits = _collect_descriptions("traits", "traits", "traits")
    if traits:
        action_data["traits"] = traits
 
    # weapons - melee first, shield bash second, ranged last
    weapons: list[str] = []
    if combat_kits is not None:
        for kit in combat_kits:
            weapons.extend(COMBAT_KITS[kit]["weapons"])
    if magic_kits is not None:
        for kit in magic_kits:
            weapons.extend(MAGIC_KITS[kit]["weapons"])
    weapons = list(set(weapons))
    melee = sorted([w for w in weapons if WEAPONS[w]["reach"] >= 5 and w != "Shield Bash"])
    shield = [w for w in weapons if w == "Shield Bash"]
    ranged = sorted([w for w in weapons if WEAPONS[w]["reach"] < 5 and WEAPONS[w]["range"]["short"] > 0])
    weapons = melee + shield + ranged
    if weapons:
        action_data["weapons"] = weapons
 
    # Spells - deduplicated, keeping the higher casting frequency
    spells: dict[str, dict] = {}
    if race is not None:
        for spell in RACES[race].get("spells", []):
            spells[spell["name"]] = {"level": spell["level"], "casting_amount": spell["casting_amount"]}
    if magic_kits is not None:
        for kit in magic_kits:
            for spell in MAGIC_KITS[kit].get("spells", []):
                name = spell["name"]
                entry = {"level": spell["level"], "casting_amount": spell["casting_amount"]}
                if name not in spells or _casting_rank(spell["casting_amount"]) > _casting_rank(spells[name]["casting_amount"]):
                    spells[name] = entry
    spells = dict(sorted(spells.items(), key=lambda x: (x[1]["level"], x[0])))
    if spells:
        action_data["spells"] = spells
 
    # Bonus Actions
    bonus_actions = _collect_descriptions("bonus_actions", "bonus_actions", "bonus_actions")
    if bonus_actions:
        action_data["bonus_actions"] = bonus_actions
 
    # Reactions
    reactions = _collect_descriptions("reactions", "reactions", "reactions")
    if reactions:
        action_data["reactions"] = reactions
 
    return action_data
