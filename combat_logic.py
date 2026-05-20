from data_loader import data

# Load reference data
BASE_CATEGORIES = data['base_categories']
CR_TABLE = data['cr_table']
COMBAT_KITS = data['combat_kits']


def calculate_ac(cr: str, base: str, primary: str | None, combat_kits: list[str] | None) -> int:
    """Calculates the final AC based on CR, base category, primary stat, and combat kit.
    Uses the CR table for a baseline AC, then applies an offset from the base category
    depending on whether enhanced conditions are met (DEX primary or kit flag)."""

    # Get base AC from CR table
    ac = CR_TABLE[cr]['armour_class']

    # Enhanced AC if the NPC is DEX-focused or the kit grants it, otherwise default
    if primary == 'DEX' or (combat_kits and any(COMBAT_KITS[k]['enhanced_ac'] for k in combat_kits)):
        ac += BASE_CATEGORIES[base]['armour']['ac_mod_enhanced']
    else:
        ac += BASE_CATEGORIES[base]['armour']['ac_mod_default']

    return ac