import unittest
from cr_logic import get_stat_array, cr_to_num


class TestCrToNum(unittest.TestCase):

    def test_whole_number(self):
        self.assertEqual(cr_to_num("5"), 5)

    def test_zero(self):
        self.assertEqual(cr_to_num("0"), 0)

    def test_fraction_eighth(self):
        self.assertEqual(cr_to_num("1/8"), 0.125)

    def test_fraction_quarter(self):
        self.assertEqual(cr_to_num("1/4"), 0.25)

    def test_fraction_half(self):
        self.assertEqual(cr_to_num("1/2"), 0.5)

    def test_large_number(self):
        self.assertEqual(cr_to_num("30"), 30)


class TestGetStatArray(unittest.TestCase):

    # Edge cases - no interpolation
    def test_cr_0_returns_flat_array(self):
        result = get_stat_array("0")
        self.assertEqual(result, [10, 10, 10, 10, 10, 10])

    def test_cr_30_returns_ceiling(self):
        result = get_stat_array("30")
        self.assertEqual(result, [22, 21, 20, 19, 18, 16])

    # Exact band boundaries - increase_by is 0
    def test_cr_1_exact_band(self):
        result = get_stat_array("1")
        self.assertEqual(result, [14, 12, 11, 10, 9, 8])

    def test_cr_5_exact_band(self):
        result = get_stat_array("5")
        self.assertEqual(result, [16, 13, 12, 11, 10, 10])

    def test_cr_17_exact_band(self):
        result = get_stat_array("17")
        self.assertEqual(result, [19, 18, 17, 16, 15, 13])

    # Mid-band interpolation
    def test_cr_7_interpolation(self):
        # Band "5" to "9", band_size=4, increase_by=2
        # (18-16)/4=0.5 *2=1 +16=17, (14-13)/4=0.25 *2=0.5 +13=13.5->13, etc.
        result = get_stat_array("7")
        self.assertEqual(result, [17, 13, 12, 11, 10, 10])

    def test_cr_15_interpolation(self):
        # Band "13" to "17", band_size=4, increase_by=2
        result = get_stat_array("15")
        self.assertEqual(result, [19, 17, 16, 14, 13, 11])

    # Fractional CRs - tests downward interpolation
    def test_cr_quarter_downward_dip(self):
        # Band "0" to "1", band_size=1, increase_by=0.25
        # Positions 4 and 5 should dip below 10
        result = get_stat_array("1/4")
        self.assertEqual(result, [11, 10, 10, 10, 9, 9])

    def test_cr_half_downward_dip(self):
        # Band "0" to "1", band_size=1, increase_by=0.5
        result = get_stat_array("1/2")
        self.assertEqual(result, [12, 11, 10, 10, 9, 9])

    # Return type
    def test_returns_list_of_ints(self):
        result = get_stat_array("10")
        self.assertIsInstance(result, list)
        for val in result:
            self.assertIsInstance(val, int)

    def test_always_returns_six_stats(self):
        for cr in ["0", "1/8", "1/4", "1/2", "1", "5", "10", "20", "25", "30"]:
            result = get_stat_array(cr)
            self.assertEqual(len(result), 6, f"CR {cr} returned {len(result)} stats")

    # Mutation safety
    def test_does_not_mutate_source_data(self):
        result = get_stat_array("0")
        result[0] = 999
        second_result = get_stat_array("0")
        self.assertEqual(second_result, [10, 10, 10, 10, 10, 10])


if __name__ == "__main__":
    unittest.main()