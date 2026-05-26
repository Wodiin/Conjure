import unittest
from stat_logic import reorder_stats, generate_stats, generate_stat_modifiers


class TestReorderStats(unittest.TestCase):
    """Tests for reorder_stats — verifying stat priority reordering
    based on primary and secondary stat selections."""

    def test_both_none_returns_default(self):
        """No overrides — should return the base category's default priority."""
        result = reorder_stats("Melee", None, None)
        self.assertEqual(result, ["STR", "CON", "DEX", "WIS", "CHA", "INT"])

    def test_primary_only(self):
        """Primary override only — primary goes first, rest shift down."""
        result = reorder_stats("Melee", "DEX", None)
        self.assertEqual(result[0], "DEX")
        self.assertEqual(len(result), 6)
        self.assertNotIn("DEX", result[1:])

    def test_secondary_only(self):
        """Secondary override only — default first stat stays, secondary slots into second."""
        result = reorder_stats("Melee", None, "INT")
        self.assertEqual(result[0], "STR")  # Melee default first stat
        self.assertEqual(result[1], "INT")
        self.assertEqual(len(result), 6)

    def test_both_provided(self):
        """Both overrides — primary first, secondary second, rest maintain relative order."""
        result = reorder_stats("Melee", "DEX", "WIS")
        self.assertEqual(result[0], "DEX")
        self.assertEqual(result[1], "WIS")
        # Remaining should be the leftovers in original order
        self.assertEqual(result[2:], ["STR", "CON", "CHA", "INT"])

    def test_primary_matches_default_first(self):
        """Primary is already the default first stat — should be a no-op for first position."""
        result = reorder_stats("Melee", "STR", "CHA")
        self.assertEqual(result[0], "STR")
        self.assertEqual(result[1], "CHA")

    def test_all_six_stats_present(self):
        """Every reorder must still contain all six stats exactly once."""
        combos = [
            ("Full Caster", "STR", "DEX"),
            ("Ranged", None, "INT"),
            ("Non Combatant", "CON", None),
            ("Half Caster", None, None),
        ]
        all_stats = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
        for base, pri, sec in combos:
            result = reorder_stats(base, pri, sec)
            with self.subTest(base=base, primary=pri, secondary=sec):
                self.assertEqual(set(result), all_stats)
                self.assertEqual(len(result), 6)

    def test_does_not_mutate_source_data(self):
        """Calling reorder_stats should not change the original base_categories data."""
        from data_loader import data
        original = data['base_categories']['Melee']['stat_priority'].copy()
        reorder_stats("Melee", "INT", "CHA")
        self.assertEqual(data['base_categories']['Melee']['stat_priority'], original)


class TestGenerateStats(unittest.TestCase):
    """Tests for generate_stats — verifying the full pipeline from CR array
    through priority zip to racial ASI application."""

    def test_returns_dict_with_six_stats(self):
        """Output should be a dict with all six stat keys."""
        result = generate_stats("5", "Melee", "STR", "CON", "Dwarf")
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"STR", "DEX", "CON", "INT", "WIS", "CHA"})

    def test_primary_gets_highest_value(self):
        """The primary stat should receive the highest value from the CR array."""
        result = generate_stats("5", "Melee", "DEX", "WIS", "Dwarf")
        # DEX is primary so before racial mods it should have the highest base value
        # Dwarf only boosts CON so DEX is unmodified — should still be highest or tied
        for stat, val in result.items():
            if stat != "DEX" and stat != "CON":  # CON gets +2 from Dwarf
                self.assertGreaterEqual(result["DEX"], val)

    def test_racial_bonus_single_stat(self):
        """Dwarf gets +2 CON — verify it's applied on top of the base value."""
        # Use None/None so default Melee order applies: STR, CON, DEX, WIS, CHA, INT
        no_race_result = generate_stats("5", "Melee", None, None, "Halfling")
        dwarf_result = generate_stats("5", "Melee", None, None, "Dwarf")
        # Halfling gives +2 DEX, Dwarf gives +2 CON
        # CON is position 2 in Melee default so base value is 13 at CR 5
        self.assertEqual(dwarf_result["CON"], 13 + 2)

    def test_racial_bonus_all_stats(self):
        """Human gets +1 to all stats — every stat should be 1 higher than unmodified."""
        human_result = generate_stats("5", "Melee", None, None, "Human")
        # CR 5 Melee default order: STR=16, CON=13, DEX=12, WIS=11, CHA=10, INT=10
        expected = {"STR": 17, "CON": 14, "DEX": 13, "WIS": 12, "CHA": 11, "INT": 11}
        self.assertEqual(human_result, expected)

    def test_cr_zero_flat_array(self):
        """CR 0 gives all 10s — with Human that should be all 11s."""
        result = generate_stats("0", "Melee", None, None, "Human")
        for stat, val in result.items():
            self.assertEqual(val, 11, f"{stat} should be 11 at CR 0 with Human")

    def test_cr_30_ceiling(self):
        """CR 30 should use the ceiling array values."""
        result = generate_stats("30", "Melee", "STR", "CON", "Gnome")
        # CR 30 array: [22, 21, 20, 19, 18, 16], Gnome gives +2 INT
        self.assertEqual(result["STR"], 22)
        self.assertEqual(result["CON"], 21)

    def test_none_primary_secondary(self):
        """Both None — should use default category order without errors."""
        result = generate_stats("5", "Full Caster", None, None, "Gnome")
        # Full Caster default: INT, CHA, CON, DEX, WIS, STR
        # CR 5: [16, 13, 12, 11, 10, 10], Gnome: +2 INT
        self.assertEqual(result["INT"], 16 + 2)
        self.assertEqual(result["CHA"], 13)


class TestGenerateStatModifiers(unittest.TestCase):
    """Tests for generate_stat_modifiers — verifying the standard 5e
    modifier formula (score - 10) // 2 across various inputs."""

    def test_standard_scores(self):
        """Known stat values should produce correct modifiers."""
        stats = {"STR": 16, "CON": 14, "DEX": 12, "WIS": 10, "CHA": 8, "INT": 7}
        expected = {"STR": 3, "CON": 2, "DEX": 1, "WIS": 0, "CHA": -1, "INT": -2}
        self.assertEqual(generate_stat_modifiers(stats), expected)

    def test_all_tens(self):
        """All 10s should produce all 0 modifiers."""
        stats = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
        result = generate_stat_modifiers(stats)
        for stat, mod in result.items():
            self.assertEqual(mod, 0, f"{stat} modifier should be 0 for score 10")

    def test_odd_scores_floor(self):
        """Odd scores should floor down — 11 gives +0, 9 gives -1, 15 gives +2."""
        stats = {"STR": 11, "DEX": 9, "CON": 15, "INT": 13, "WIS": 7, "CHA": 5}
        expected = {"STR": 0, "DEX": -1, "CON": 2, "INT": 1, "WIS": -2, "CHA": -3}
        self.assertEqual(generate_stat_modifiers(stats), expected)

    def test_high_scores(self):
        """Scores above 20 — CR 30 can push stats to 22+."""
        stats = {"STR": 22, "DEX": 20, "CON": 18, "INT": 24, "WIS": 16, "CHA": 14}
        expected = {"STR": 6, "DEX": 5, "CON": 4, "INT": 7, "WIS": 3, "CHA": 2}
        self.assertEqual(generate_stat_modifiers(stats), expected)

    def test_returns_all_six_keys(self):
        """Output dict should have the same keys as the input."""
        stats = {"STR": 16, "CON": 15, "DEX": 12, "WIS": 11, "CHA": 10, "INT": 10}
        result = generate_stat_modifiers(stats)
        self.assertEqual(set(result.keys()), set(stats.keys()))

    def test_pipeline_with_generate_stats(self):
        """Full pipeline — generate_stats output fed directly into generate_stat_modifiers."""
        stats = generate_stats("0", "Melee", None, None, "Human")
        # CR 0 Human = all 11s, modifier for 11 = 0
        mods = generate_stat_modifiers(stats)
        for stat, mod in mods.items():
            self.assertEqual(mod, 0, f"{stat} modifier should be 0 for score 11")


if __name__ == '__main__':
    unittest.main()