import math
from data_loader import data

cr_data = data['cr_table']
cr_stats = data['cr_stat_array']
cr_list = list(cr_data.keys())

def get_stat_array(cr)->list[int]:
    cr_index = cr_to_num(cr)
    next_cr_list = []
    for stat_key in cr_stats:
        int_stat = cr_to_num(stat_key)
        next_cr_list.append(stat_key)
        if int_stat > cr_index:
            break

    if len(next_cr_list) == len(cr_stats):
        final_array = list(cr_stats[next_cr_list[-1]])
        return final_array
    elif len(next_cr_list) == 1:
        final_array = list(cr_stats[next_cr_list[0]])
        return final_array
    else:
        next_band_cr = cr_to_num(next_cr_list[-1])
        current_band_cr = cr_to_num(next_cr_list[-2])
        next_band_array = cr_stats[next_cr_list[-1]]
        base_array = cr_stats[next_cr_list[-2]]

    band_size = next_band_cr - current_band_cr
    final_array = []
    increase_by = cr_index - current_band_cr
    for base, next_array in zip(base_array, next_band_array):
        increment = (next_array - base)/band_size
        final_array.append(math.floor(base + (increment * increase_by)))
    return final_array



def cr_to_num(cr_str)->int | float:
    if "/" in cr_str:
        num, denom = cr_str.split("/")
        return int(num) / int(denom)
    else:
        return int(cr_str)  