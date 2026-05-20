from data_loader import data

# Load reference data
BASE_CATEGORIES = data['base_categories']
CR_TABLE = data['cr_table']
COMBAT_KITS = data['combat_kits']


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