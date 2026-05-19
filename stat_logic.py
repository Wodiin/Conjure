from cr_logic import get_stat_array
from data_loader import data

# Load reference data
BASE_CATEGORIES = data['base_categories']
RACES = data['races']


def generate_stats(cr: str, base: str, primary: str | None, secondary: str | None, race: str) -> dict[str, int]:
    """Takes user selections and returns a complete stat dict with racial bonuses applied.
    Orchestrates the full stat generation pipeline: CR array -> priority reorder -> zip -> racial ASIs."""

    # Get the six-stat value array based on CR
    stat_array = get_stat_array(cr)

    # Reorder stat names based on base category and user's primary/secondary choices
    stat_tags = reorder_stats(base, primary, secondary)

    # Pair each stat name with its corresponding value
    stats = dict(zip(stat_tags, stat_array))

    # Apply racial ability score increases
    race_mods = RACES[race]['stat_bonus'].copy()
    for bonus in race_mods:
        stats[bonus] += race_mods[bonus]

    return stats


def reorder_stats(base: str, primary: str | None, secondary: str | None) -> list[str]:
    """Takes primary and secondary stat tags and a base category, returns a list of
    all six stat tags in priority order. If provided, primary is placed first and
    secondary second. Remaining stats maintain their original base category order."""

    # Copy to avoid mutating the source data
    base_array = BASE_CATEGORIES[base]['stat_priority'].copy()

    # No overrides - return the default category priority
    if primary is None and secondary is None:
        return base_array

    # Secondary only - keep default first stat, slot secondary into second
    elif primary is None:
        base_array.remove(secondary)
        return [base_array[0]] + [secondary] + base_array[1:]

    # Primary only - slot primary into first, rest shift down
    elif secondary is None:
        base_array.remove(primary)
        return [primary] + base_array

    # Both provided - primary first, secondary second, rest shift down
    base_array.remove(primary)
    base_array.remove(secondary)
    return [primary, secondary] + base_array