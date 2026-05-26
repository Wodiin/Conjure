import unittest
from combat_logic import calculate_ac, calculate_hp


class TestCalculateAC(unittest.TestCase):
    """Tests for calculate_ac — verifying AC calculation from CR baseline
    with category offsets and enhanced conditions."""

    # --- Baseline + default offset tests ---

    def test_default_ac_no_kits_no_dex(self):
        """No kits, no DEX primary — should apply ac_mod_default."""
        # CR 5 base AC = 15, Melee ac_mod_default = 2
        result = calculate_ac("5", "Melee", "STR", None)
        self.assertEqual(result, 17)

    def test_default_ac_empty_kit_list(self):
        """Empty kit list should behave the same as None."""
        result = calculate_ac("5", "Melee", "STR", [])
        self.assertEqual(result, 17)

    def test_full_caster_default_penalty(self):
        """Full Caster should have a negative default offset."""
        # CR 5 base AC = 15, Full Caster ac_mod_default = -2
        result = calculate_ac("5", "Full Caster", "INT", None)
        self.assertEqual(result, 13)

    def test_non_combatant_default_penalty(self):
        """Non Combatant should have the largest negative offset."""
        # CR 5 base AC = 15, Non Combatant ac_mod_default = -4
        result = calculate_ac("5", "Non Combatant", "WIS", None)
        self.assertEqual(result, 11)

    # --- Enhanced condition tests ---

    def test_enhanced_from_dex_primary(self):
        """DEX as primary stat should trigger enhanced AC."""
        # CR 5 base AC = 15, Melee ac_mod_enhanced = 4
        result = calculate_ac("5", "Melee", "DEX", None)
        self.assertEqual(result, 19)

    def test_enhanced_from_single_kit(self):
        """A single kit with enhanced_ac: true should trigger enhanced AC."""
        # Berserker has enhanced_ac: true
        # CR 5 base AC = 15, Melee ac_mod_enhanced = 4
        result = calculate_ac("5", "Melee", "STR", ["Berserker"])
        self.assertEqual(result, 19)

    def test_default_from_non_enhanced_kit(self):
        """A kit with enhanced_ac: false should not trigger enhanced AC."""
        # Ambusher has enhanced_ac: false
        # CR 5 base AC = 15, Melee ac_mod_default = 2
        result = calculate_ac("5", "Melee", "STR", ["Ambusher"])
        self.assertEqual(result, 17)

    # --- Multiple kit tests ---

    def test_multiple_kits_one_enhanced(self):
        """If any kit in the list has enhanced_ac: true, enhanced should apply."""
        # Ambusher = false, Berserker = true
        # CR 5 base AC = 15, Melee ac_mod_enhanced = 4
        result = calculate_ac("5", "Melee", "STR", ["Ambusher", "Berserker"])
        self.assertEqual(result, 19)

    def test_multiple_kits_none_enhanced(self):
        """If no kit in the list has enhanced_ac: true, default should apply."""
        # Ambusher = false, Sharpshooter = false
        # CR 5 base AC = 15, Ranged ac_mod_default = 1
        result = calculate_ac("5", "Ranged", "STR", ["Ambusher", "Sharpshooter"])
        self.assertEqual(result, 16)

    def test_multiple_kits_all_enhanced(self):
        """Multiple enhanced kits should still only apply the offset once."""
        # Berserker = true, Knight = true
        # CR 5 base AC = 15, Melee ac_mod_enhanced = 4
        result = calculate_ac("5", "Melee", "STR", ["Berserker", "Knight"])
        self.assertEqual(result, 19)

    # --- DEX + kit combination tests ---

    def test_dex_primary_with_non_enhanced_kit(self):
        """DEX primary should trigger enhanced even if kit is not enhanced."""
        # CR 5 base AC = 15, Ranged ac_mod_enhanced = 2
        result = calculate_ac("5", "Ranged", "DEX", ["Sharpshooter"])
        self.assertEqual(result, 17)

    def test_dex_primary_with_enhanced_kit(self):
        """Both conditions true — should still only apply enhanced once."""
        # CR 5 base AC = 15, Melee ac_mod_enhanced = 4
        result = calculate_ac("5", "Melee", "DEX", ["Berserker"])
        self.assertEqual(result, 19)

    # --- CR edge cases ---

    def test_cr_zero(self):
        """CR 0 baseline AC with default offset."""
        # CR 0 base AC = 13, Melee ac_mod_default = 2
        result = calculate_ac("0", "Melee", "STR", None)
        self.assertEqual(result, 15)

    def test_cr_30(self):
        """CR 30 ceiling with enhanced offset."""
        # CR 30 base AC = 19, Melee ac_mod_enhanced = 4
        result = calculate_ac("30", "Melee", "DEX", None)
        self.assertEqual(result, 23)

    # --- None primary tests ---

    def test_none_primary_no_kits(self):
        """None primary with no kits should apply default."""
        # CR 5 base AC = 15, Melee ac_mod_default = 2
        result = calculate_ac("5", "Melee", None, None)
        self.assertEqual(result, 17)

    def test_none_primary_with_enhanced_kit(self):
        """None primary but an enhanced kit should still trigger enhanced."""
        # CR 5 base AC = 15, Melee ac_mod_enhanced = 4
        result = calculate_ac("5", "Melee", None, ["Knight"])
        self.assertEqual(result, 19)


class TestCalculateHP(unittest.TestCase):
    """Tests for calculate_hp — verifying HP calculation and dice expression
    string generation from CR hit dice count, base category hit die, and CON modifier."""

    # --- Standard HP calculation tests ---

    def test_melee_positive_con(self):
        """Melee (d10) at CR 5 with +3 CON mod."""
        # 19 dice, avg 5.5, con +3: 19 * 5.5 + 19 * 3 = 104.5 + 57 = 161
        hp, dice = calculate_hp("5", "Melee", 3)
        self.assertEqual(hp, 161)
        self.assertEqual(dice, "19d10 + 57")

    def test_full_caster_positive_con(self):
        """Full Caster (d6) at CR 5 with +1 CON mod."""
        # 19 dice, avg 3.5, con +1: 19 * 3.5 + 19 * 1 = 66.5 + 19 = 85
        hp, dice = calculate_hp("5", "Full Caster", 1)
        self.assertEqual(hp, 85)
        self.assertEqual(dice, "19d6 + 19")

    def test_ranged_positive_con(self):
        """Ranged (d8) at CR 5 with +2 CON mod."""
        # 19 dice, avg 4.5, con +2: 19 * 4.5 + 19 * 2 = 85.5 + 38 = 123
        hp, dice = calculate_hp("5", "Ranged", 2)
        self.assertEqual(hp, 123)
        self.assertEqual(dice, "19d8 + 38")

    # --- Dice string format tests ---

    def test_negative_con_dice_string(self):
        """Negative CON mod should produce a minus in the dice string."""
        hp, dice = calculate_hp("5", "Full Caster", -1)
        # 19 dice, avg 3.5, con -1: 19 * 3.5 - 19 = 66.5 - 19 = 47
        self.assertEqual(hp, 47)
        self.assertEqual(dice, "19d6 - 19")

    def test_zero_con_dice_string(self):
        """Zero CON mod should omit the modifier from the dice string."""
        hp, dice = calculate_hp("5", "Melee", 0)
        # 19 dice, avg 5.5: 19 * 5.5 = 104
        self.assertEqual(hp, 104)
        self.assertEqual(dice, "19d10")

    # --- Return type tests ---

    def test_returns_tuple(self):
        """Should return a tuple of (int, str)."""
        result = calculate_hp("5", "Melee", 3)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], str)

    # --- CR edge cases ---

    def test_cr_zero_positive_con(self):
        """CR 0 with positive CON mod — 1 die."""
        # 1 die, d10, avg 5.5, con +2: 1 * 5.5 + 1 * 2 = 7
        hp, dice = calculate_hp("0", "Melee", 2)
        self.assertEqual(hp, 7)
        self.assertEqual(dice, "1d10 + 2")

    def test_cr_zero_negative_con_floors_at_1(self):
        """CR 0 with negative CON mod — HP should floor at 1."""
        hp, dice = calculate_hp("0", "Full Caster", -2)
        self.assertEqual(hp, 1)
        self.assertEqual(dice, "1d6 - 2")

    def test_cr_zero_zero_con(self):
        """CR 0 with zero CON mod — just the average die."""
        # 1 die, d10, avg 5.5 = 5
        hp, dice = calculate_hp("0", "Melee", 0)
        self.assertEqual(hp, 5)
        self.assertEqual(dice, "1d10")

    def test_cr_30_high_con(self):
        """CR 30 ceiling — large dice count with high CON."""
        # 58 dice, d10, avg 5.5, con +7: 58 * 5.5 + 58 * 7 = 319 + 406 = 725
        hp, dice = calculate_hp("30", "Melee", 7)
        self.assertEqual(hp, 725)
        self.assertEqual(dice, "58d10 + 406")

    # --- Category differentiation tests ---

    def test_melee_more_hp_than_caster_same_cr(self):
        """At the same CR and CON mod, Melee (d10) should have more HP than Full Caster (d6)."""
        melee_hp, _ = calculate_hp("10", "Melee", 2)
        caster_hp, _ = calculate_hp("10", "Full Caster", 2)
        self.assertGreater(melee_hp, caster_hp)

    def test_higher_con_more_hp(self):
        """Higher CON mod should produce more HP for the same CR and category."""
        low_hp, _ = calculate_hp("5", "Melee", 1)
        high_hp, _ = calculate_hp("5", "Melee", 4)
        self.assertGreater(high_hp, low_hp)


if __name__ == '__main__':
    unittest.main()