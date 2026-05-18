import math
from data_loader import data

# Load CR reference data and stat band arrays
CR_DATA = data['cr_table']
CR_STATS = data['cr_stat_array']
CR_LIST = list(CR_DATA.keys())


def get_stat_array(cr: str) -> list[int]:
    """Takes a CR string, returns a six-stat array in priority order
    by interpolating between stat band base arrays."""

    cr_index = cr_to_num(cr)

    # Walk through band keys, collecting until we find one above the chosen CR
    next_cr_list: list[str] = []
    for stat_key in CR_STATS:
        int_stat = cr_to_num(stat_key)
        next_cr_list.append(stat_key)
        if int_stat > cr_index:
            break

    # Edge case: CR 30 — no band above, return ceiling array as a copy
    if len(next_cr_list) == len(CR_STATS):
        final_array = list(CR_STATS[next_cr_list[-1]])
        return final_array

    # Edge case: CR 0 — only one band collected, return it as a copy
    elif len(next_cr_list) == 1:
        final_array = list(CR_STATS[next_cr_list[0]])
        return final_array

    # Normal case: interpolate between current band and next band
    else:
        next_band_cr: int | float = cr_to_num(next_cr_list[-1])
        current_band_cr: int | float = cr_to_num(next_cr_list[-2])
        next_band_array: list[int] = CR_STATS[next_cr_list[-1]]
        base_array: list[int] = CR_STATS[next_cr_list[-2]]

    # Calculate how far into the band the chosen CR sits
    band_size: int | float = next_band_cr - current_band_cr
    increase_by: int | float = cr_index - current_band_cr

    # Interpolate each stat position and floor to int
    final_array: list[int] = []
    for base, next_array in zip(base_array, next_band_array):
        increment: float = (next_array - base) / band_size
        final_array.append(math.floor(base + (increment * increase_by)))

    return final_array


def cr_to_num(cr_str: str) -> int | float:
    """Converts a CR string to a numeric value.
    Handles fractions like '1/8' and whole numbers like '5'."""

    if "/" in cr_str:
        num, denom = cr_str.split("/")
        return int(num) / int(denom)
    else:
        return int(cr_str)