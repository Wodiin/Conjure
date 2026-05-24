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


def calculate_hp(cr: str, base: str, con_mod: int) -> tuple[int, str]:
    """Calculates the final HP and dice expression string for an NPC.
    Uses hit dice count from the CR table, hit die size from the base category,
    and the NPC's actual CON modifier. Returns a tuple of (total_hp, dice_string)."""

    num_dice = CR_TABLE[cr]['hit_dice_count']
    die_size = BASE_CATEGORIES[base]['hit_die']

    # CR 0 with negative CON is an edge case — floor HP at 1
    if cr == "0" and con_mod < 0:
        dice_string = f"1d{die_size} - {abs(con_mod)}"
        return 1, dice_string

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

    return hp, dice_string


def generate_action_data(cr: str, modifiers: dict[str, int], combat_kits: list[str] | None) -> dict:
    """Generates a dict of action data based on CR, stat modifiers, and combat kits.
    Determines available actions from combat kits, then calculates relevant values for each action using the appropriate stat modifiers and data."""
   





"""
    {
        "Multiattack": {
            "weapons": {
                "longsword": 2,
                "has_shield": True
            }
        },
        "Weapons": {
            "longsword": {
                "weapon_type": "melee",
                "num_of_die": 1,
                "die_size": 8,
                "damage_type": "slashing",
                "to_hit": 5,
                "damage_bonus": 3,
                "damage_avg": 7,
                "reach": 5,
                "range_min": None,
                "range_max": None,
                "targets": 1
            },
            "shield_bash": {
                "weapon_type": "melee",
                "num_of_die": 1,
                "die_size": 4,
                "damage_type": "bludgeoning",
                "to_hit": 3,
                "damage_bonus": 1,
                "damage_avg": 3,
                "reach": 5,
                "range_min": None,
                "range_max": None,
                "targets": 1
            }
        },
        "Bonus Actions": {
            "Second Wind": {
                "description": "The NPC can use a bonus action to regain hit points equal to 1d10 + their fighter level. Once they use this feature, they must finish a short or long rest before they can use it again."
            }
        },
        "Reactions": {
            "Parry": {
                "description": "The NPC adds 2 to their AC against one melee attack that would hit them. To do so, the NPC must see the attacker and be wielding a melee weapon."
            }
        }
    }
"""