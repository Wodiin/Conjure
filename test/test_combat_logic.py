import unittest
from combat_logic import calculate_ac, calculate_hp, get_action_data, generate_action_data


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


class TestGetActionDataEarlyExit(unittest.TestCase):
    """Tests for get_action_data — early exit when no sources are provided."""

    def test_all_none_returns_none(self):
        """All None inputs should return None."""
        result = get_action_data(None, None, None)
        self.assertIsNone(result)

    def test_human_no_kits_returns_empty(self):
        """Human has no traits, spells, bonus actions, or reactions — should return empty dict."""
        result = get_action_data(None, None, "Human")
        self.assertEqual(result, {})


class TestGetActionDataRaceOnly(unittest.TestCase):
    """Tests for get_action_data — gathering data from a single race source."""

    # --- Bonus action from race ---

    def test_firbolg_bonus_action(self):
        """Firbolg's Hidden Step should appear in Bonus Actions."""
        result = get_action_data(None, None, "Firbolg")
        self.assertIn("Bonus Actions", result)
        self.assertIn("Hidden Step", result["Bonus Actions"])

    def test_firbolg_no_traits(self):
        """Hidden Step was moved to bonus_actions — traits should be absent."""
        result = get_action_data(None, None, "Firbolg")
        self.assertNotIn("Traits", result)

    # --- Reaction from race ---

    def test_goliath_reaction(self):
        """Goliath's Stone's Endurance should appear in Reactions."""
        result = get_action_data(None, None, "Goliath")
        self.assertIn("Reactions", result)
        self.assertIn("Stone's Endurance", result["Reactions"])

    # --- Spells from race ---

    def test_firbolg_spells(self):
        """Firbolg should have Detect Magic and Disguise Self in Spells."""
        result = get_action_data(None, None, "Firbolg")
        self.assertIn("Spells", result)
        self.assertIn("Detect Magic", result["Spells"])
        self.assertIn("Disguise Self", result["Spells"])

    # --- No weapons from race ---

    def test_firbolg_no_weapons(self):
        """Races don't provide weapons — Weapons should be absent."""
        result = get_action_data(None, None, "Firbolg")
        self.assertNotIn("Weapons", result)


class TestGetActionDataCombatKitOnly(unittest.TestCase):
    """Tests for get_action_data — gathering data from combat kits only."""

    # --- Reactions from combat kit ---

    def test_duelist_reactions(self):
        """Duelist's Parry and Riposte should appear in Reactions."""
        result = get_action_data(["Duelist"], None, None)
        self.assertIn("Reactions", result)
        self.assertIn("Parry", result["Reactions"])
        self.assertIn("Riposte", result["Reactions"])

    def test_duelist_no_traits(self):
        """Parry and Riposte were moved to reactions — traits should be absent."""
        result = get_action_data(["Duelist"], None, None)
        self.assertNotIn("Traits", result)

    # --- Weapons from combat kit ---

    def test_duelist_weapons(self):
        """Duelist should provide Rapier as a weapon."""
        result = get_action_data(["Duelist"], None, None)
        self.assertIn("Weapons", result)
        self.assertEqual(result["Weapons"], ["Rapier"])

    # --- Traits from combat kit ---

    def test_berserker_traits(self):
        """Berserker's Reckless Attack and Relentless should appear in Traits."""
        result = get_action_data(["Berserker"], None, None)
        self.assertIn("Traits", result)
        self.assertIn("Reckless Attack", result["Traits"])
        self.assertIn("Relentless", result["Traits"])

    # --- Bonus actions from combat kit ---

    def test_hexblade_bonus_actions(self):
        """Hexblade's Curse and Shadow Step should appear in Bonus Actions."""
        result = get_action_data(["Hexblade"], None, None)
        self.assertIn("Bonus Actions", result)
        self.assertIn("Hexblade's Curse", result["Bonus Actions"])
        self.assertIn("Shadow Step", result["Bonus Actions"])


class TestGetActionDataMagicKitOnly(unittest.TestCase):
    """Tests for get_action_data — gathering data from magic kits only."""

    # --- Trait separation ---

    def test_abjuration_trait_stays(self):
        """Arcane Ward should remain in Traits after Projected Ward moved to Reactions."""
        result = get_action_data(None, ["Abjuration"], None)
        self.assertIn("Traits", result)
        self.assertIn("Arcane Ward", result["Traits"])
        self.assertNotIn("Projected Ward", result["Traits"])

    def test_abjuration_reaction(self):
        """Projected Ward should appear in Reactions."""
        result = get_action_data(None, ["Abjuration"], None)
        self.assertIn("Reactions", result)
        self.assertIn("Projected Ward", result["Reactions"])

    # --- Spells from magic kit ---

    def test_abjuration_spells(self):
        """Abjuration should provide Blade Ward as an at-will cantrip."""
        result = get_action_data(None, ["Abjuration"], None)
        self.assertIn("Spells", result)
        self.assertIn("Blade Ward", result["Spells"])
        self.assertEqual(result["Spells"]["Blade Ward"]["casting_amount"], "at will")

    # --- Bonus actions from magic kit ---

    def test_conjuration_bonus_action(self):
        """Conjuration's Benign Transposition should appear in Bonus Actions."""
        result = get_action_data(None, ["Conjuration"], None)
        self.assertIn("Bonus Actions", result)
        self.assertIn("Benign Transposition", result["Bonus Actions"])

    def test_nature_bonus_action(self):
        """Nature's Wild Shape should appear in Bonus Actions."""
        result = get_action_data(None, ["Nature"], None)
        self.assertIn("Bonus Actions", result)
        self.assertIn("Wild Shape", result["Bonus Actions"])


class TestGetActionDataFullCombo(unittest.TestCase):
    """Tests for get_action_data — full pipeline with Firbolg + Duelist + Abjuration."""

    def setUp(self):
        self.result = get_action_data(["Duelist"], ["Abjuration"], "Firbolg")

    def test_traits_from_magic_kit(self):
        """Only Arcane Ward should appear — other traits moved to reactions/bonus actions."""
        self.assertIn("Traits", self.result)
        self.assertIn("Arcane Ward", self.result["Traits"])
        self.assertEqual(len(self.result["Traits"]), 1)

    def test_weapons_from_both_kits(self):
        """Rapier from Duelist and Quarterstaff from Abjuration should both appear."""
        self.assertIn("Weapons", self.result)
        self.assertIn("Rapier", self.result["Weapons"])
        self.assertIn("Quarterstaff", self.result["Weapons"])
        self.assertEqual(len(self.result["Weapons"]), 2)

    def test_spells_from_race_and_magic_kit(self):
        """All spells from Firbolg and Abjuration should appear."""
        self.assertIn("Spells", self.result)
        expected = [
            "Blade Ward", "Detect Magic", "Disguise Self",
            "Mage Armor", "Shield", "Counterspell",
            "Dispel Magic", "Globe of Invulnerability",
        ]
        for spell in expected:
            self.assertIn(spell, self.result["Spells"])

    def test_bonus_actions_from_race(self):
        """Only Hidden Step from Firbolg should appear."""
        self.assertIn("Bonus Actions", self.result)
        self.assertIn("Hidden Step", self.result["Bonus Actions"])
        self.assertEqual(len(self.result["Bonus Actions"]), 1)

    def test_reactions_from_both_kits(self):
        """Parry and Riposte from Duelist, Projected Ward from Abjuration."""
        self.assertIn("Reactions", self.result)
        self.assertIn("Parry", self.result["Reactions"])
        self.assertIn("Projected Ward", self.result["Reactions"])
        self.assertIn("Riposte", self.result["Reactions"])
        self.assertEqual(len(self.result["Reactions"]), 3)


class TestGetActionDataMultipleKits(unittest.TestCase):
    """Tests for get_action_data — combining multiple combat or magic kits."""

    def test_two_combat_kits_combine_traits(self):
        """Traits from both Berserker and Ambusher should appear."""
        result = get_action_data(["Berserker", "Ambusher"], None, None)
        self.assertIn("Reckless Attack", result["Traits"])
        self.assertIn("Darkness is my ally", result["Traits"])

    def test_two_magic_kits_combine_spells(self):
        """Spells from both Abjuration and Evocation should appear."""
        result = get_action_data(None, ["Abjuration", "Evocation"], None)
        self.assertIn("Blade Ward", result["Spells"])
        self.assertIn("Fire Bolt", result["Spells"])


class TestGetActionDataWeaponOrdering(unittest.TestCase):
    """Tests for get_action_data — verifying weapon sort order:
    melee (alphabetical) → shield bash → ranged (alphabetical)."""

    def test_melee_before_shield_bash_before_ranged(self):
        """Longsword should precede Shield Bash, which should precede Longbow."""
        result = get_action_data(["Bodyguard", "Sharpshooter"], None, None)
        weapons = result["Weapons"]
        self.assertLess(weapons.index("Longsword"), weapons.index("Shield Bash"))
        self.assertLess(weapons.index("Shield Bash"), weapons.index("Longbow"))

    def test_melee_sorted_alphabetically(self):
        """Melee weapons should appear in alphabetical order."""
        result = get_action_data(["Duelist"], ["Abjuration"], None)
        weapons = result["Weapons"]
        melee = [w for w in weapons if w != "Shield Bash"]
        self.assertEqual(melee, sorted(melee))

    def test_weapon_dedup(self):
        """Ambusher and Skirmisher share Shortsword and Shortbow — no duplicates."""
        result = get_action_data(["Ambusher", "Skirmisher"], None, None)
        weapons = result["Weapons"]
        self.assertEqual(weapons.count("Shortsword"), 1)
        self.assertEqual(weapons.count("Shortbow"), 1)


class TestGetActionDataSpellDedup(unittest.TestCase):
    """Tests for get_action_data — verifying spell deduplication keeps
    the higher casting frequency when duplicates appear across sources."""

    def test_misty_step_keeps_higher_frequency(self):
        """Githyanki has Misty Step 1/day, Conjuration has 3/day — should keep 3/day."""
        result = get_action_data(None, ["Conjuration"], "Githyanki")
        self.assertEqual(result["Spells"]["Misty Step"]["casting_amount"], "3/day")

    def test_darkness_keeps_higher_frequency(self):
        """Tiefling has Darkness 1/day, Shadow Pact has 2/day — should keep 2/day."""
        result = get_action_data(None, ["Shadow Pact"], "Tiefling")
        self.assertEqual(result["Spells"]["Darkness"]["casting_amount"], "2/day")

    def test_enlarge_reduce_keeps_higher_frequency(self):
        """Fairy has Enlarge/Reduce 1/day, Transmutation has 3/day — should keep 3/day."""
        result = get_action_data(None, ["Transmutation"], "Fairy")
        self.assertEqual(result["Spells"]["Enlarge/Reduce"]["casting_amount"], "3/day")

    def test_mage_hand_same_frequency_no_duplicate(self):
        """Githyanki and Conjuration both have Mage Hand at will — should appear once."""
        result = get_action_data(None, ["Conjuration"], "Githyanki")
        self.assertIn("Mage Hand", result["Spells"])


class TestGetActionDataSorting(unittest.TestCase):
    """Tests for get_action_data — verifying alphabetical sorting for traits,
    bonus actions, and reactions, and level-then-name sorting for spells."""

    def test_traits_alphabetical(self):
        """Traits should be sorted alphabetically by name."""
        result = get_action_data(["Berserker"], ["Evocation"], "Elf")
        trait_names = list(result["Traits"].keys())
        self.assertEqual(trait_names, sorted(trait_names))

    def test_reactions_alphabetical(self):
        """Reactions should be sorted alphabetically by name."""
        result = get_action_data(["Duelist"], ["Abjuration"], "Firbolg")
        reaction_names = list(result["Reactions"].keys())
        self.assertEqual(reaction_names, sorted(reaction_names))

    def test_spells_sorted_by_level(self):
        """Spells should be ordered by level ascending."""
        result = get_action_data(None, ["Abjuration"], "Firbolg")
        spell_levels = [v["level"] for v in result["Spells"].values()]
        self.assertEqual(spell_levels, sorted(spell_levels))

    def test_spells_same_level_sorted_by_name(self):
        """Spells at the same level should be sorted alphabetically."""
        result = get_action_data(None, ["Abjuration"], "Firbolg")
        level_1_spells = [
            name for name, data in result["Spells"].items()
            if data["level"] == 1
        ]
        self.assertEqual(level_1_spells, sorted(level_1_spells))


class TestGenerateActionDataEarlyExit(unittest.TestCase):
    """Tests for generate_action_data when no actions are provided."""

    def test_none_actions_returns_none(self):
        """None actions input should return None."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        result = generate_action_data("5", modifiers, None)
        self.assertIsNone(result)


class TestGenerateActionDataWeapons(unittest.TestCase):
    """Tests for generate_action_data weapon calculations including
    to-hit, damage bonus, average damage, and type classification."""

    # --- Weapon type classification ---

    def test_melee_weapon_type(self):
        """Longsword (reach 5, range 0) should be classified as melee."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Longsword"]["weapon_type"], "melee")

    def test_ranged_weapon_type(self):
        """Longbow (reach 0, range 150/600) should be classified as ranged."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longbow"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Longbow"]["weapon_type"], "ranged")

    def test_thrown_weapon_type(self):
        """Dagger (reach 5, range 20/60) should be classified as thrown."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Dagger"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Dagger"]["weapon_type"], "thrown")

    # --- Range values ---

    def test_melee_range_is_none(self):
        """Melee weapons should have None for range_min and range_max."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertIsNone(result["Weapons"]["Longsword"]["range_min"])
        self.assertIsNone(result["Weapons"]["Longsword"]["range_max"])

    def test_ranged_range_values(self):
        """Longbow should have range_min=150 and range_max=600."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longbow"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Longbow"]["range_min"], 150)
        self.assertEqual(result["Weapons"]["Longbow"]["range_max"], 600)

    def test_thrown_range_values(self):
        """Dagger should have range_min=20 and range_max=60."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Dagger"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Dagger"]["range_min"], 20)
        self.assertEqual(result["Weapons"]["Dagger"]["range_max"], 60)

    # --- Standard (non-finesse) weapon calculations ---

    def test_str_weapon_to_hit(self):
        """Greataxe (STR weapon) at CR 5 with STR mod +3. to_hit = 3 + 3 = 6."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Greataxe"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Greataxe"]["to_hit"], 6)

    def test_str_weapon_damage_bonus(self):
        """Greataxe damage bonus should equal the STR modifier."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Greataxe"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Greataxe"]["damage_bonus"], 3)

    def test_str_weapon_damage_avg(self):
        """Greataxe (1d12) with STR +3. avg = int(1 * 6.5 + 3) = 9."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Greataxe"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Greataxe"]["damage_avg"], 9)

    def test_dex_weapon_to_hit(self):
        """Longbow (DEX weapon) at CR 5 with DEX mod +1. to_hit = 1 + 3 = 4."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longbow"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Longbow"]["to_hit"], 4)

    # --- Finesse weapon calculations ---

    def test_finesse_uses_str_when_higher(self):
        """Rapier (finesse) with STR +3, DEX +1 should use STR for to_hit."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Rapier"]}
        result = generate_action_data("5", modifiers, actions)
        # to_hit = max(3, 1) + prof(3) = 6
        self.assertEqual(result["Weapons"]["Rapier"]["to_hit"], 6)
        self.assertEqual(result["Weapons"]["Rapier"]["damage_bonus"], 3)

    def test_finesse_uses_dex_when_higher(self):
        """Rapier (finesse) with STR +1, DEX +3 should use DEX for to_hit."""
        modifiers = {"STR": 1, "DEX": 3, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Rapier"]}
        result = generate_action_data("5", modifiers, actions)
        # to_hit = max(1, 3) + prof(3) = 6
        self.assertEqual(result["Weapons"]["Rapier"]["to_hit"], 6)
        self.assertEqual(result["Weapons"]["Rapier"]["damage_bonus"], 3)

    # --- Versatile weapon calculations ---

    def test_versatile_uses_two_handed_without_shield(self):
        """Longsword (versatile d10) without shield should use d10."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Longsword"]["die_size"], 10)
        # damage_avg = int(1 * 5.5 + 3) = 8
        self.assertEqual(result["Weapons"]["Longsword"]["damage_avg"], 8)

    def test_versatile_uses_one_handed_with_shield(self):
        """Longsword with Shield Bash present should use d8 (one-handed)."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword", "Shield Bash"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Weapons"]["Longsword"]["die_size"], 8)
        # damage_avg = int(1 * 4.5 + 3) = 7
        self.assertEqual(result["Weapons"]["Longsword"]["damage_avg"], 7)

    # --- Proficiency bonus scaling ---

    def test_to_hit_scales_with_cr(self):
        """Same weapon and modifiers at different CRs should have different to_hit."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result_cr0 = generate_action_data("0", modifiers, actions)
        result_cr17 = generate_action_data("17", modifiers, actions)
        # CR 0 prof = 2, CR 17 prof = 6
        self.assertEqual(result_cr0["Weapons"]["Longsword"]["to_hit"], 5)
        self.assertEqual(result_cr17["Weapons"]["Longsword"]["to_hit"], 9)

    # --- No weapons ---

    def test_no_weapons_key_when_absent(self):
        """Actions with no Weapons key should not produce Weapons in output."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Traits": {"Brave": "advantage on saves vs frightened"}}
        result = generate_action_data("5", modifiers, actions)
        self.assertNotIn("Weapons", result)


class TestGenerateActionDataMultiattack(unittest.TestCase):
    """Tests for generate_action_data multiattack structure based on CR
    attack count, weapon availability, and shield presence."""

    def test_multiattack_at_cr5(self):
        """CR 5 grants 2 attacks, which qualifies for multiattack."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertIn("Multiattack", result)
        self.assertEqual(result["Multiattack"]["count"], 2)

    def test_no_multiattack_at_cr0(self):
        """CR 0 grants 1 attack, so no multiattack should appear."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("0", modifiers, actions)
        self.assertNotIn("Multiattack", result)

    def test_no_multiattack_without_weapons(self):
        """Pure caster with no weapons should not get multiattack even at high CR."""
        modifiers = {"STR": -1, "DEX": 1, "CON": 0, "INT": 3, "WIS": 2, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("17", modifiers, actions)
        self.assertNotIn("Multiattack", result)

    def test_multiattack_has_shield_true(self):
        """Shield Bash in weapons should set has_shield to True."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword", "Shield Bash"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertTrue(result["Multiattack"]["has_shield"])

    def test_multiattack_has_shield_false(self):
        """No Shield Bash should set has_shield to False."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertFalse(result["Multiattack"]["has_shield"])

    def test_multiattack_type_is_any_combination(self):
        """Current implementation should always produce any_combination type."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Multiattack"]["type"], "any_combination")

    def test_multiattack_weapons_list(self):
        """Multiattack weapons list should match the input weapons."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword", "Dagger"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Multiattack"]["weapons"], ["Longsword", "Dagger"])

    def test_multiattack_count_scales_with_cr(self):
        """CR 7 should grant 3 attacks, CR 17 should grant 4."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result_cr7 = generate_action_data("7", modifiers, actions)
        result_cr17 = generate_action_data("17", modifiers, actions)
        self.assertEqual(result_cr7["Multiattack"]["count"], 3)
        self.assertEqual(result_cr17["Multiattack"]["count"], 4)


class TestGenerateActionDataSpells(unittest.TestCase):
    """Tests for generate_action_data spellcasting calculations including
    stat selection, save DC, attack bonus, and budget."""

    # --- Spellcasting stat selection ---

    def test_highest_mental_stat_selected(self):
        """Default should pick highest of INT, WIS, CHA."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 4, "WIS": 2, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Spells"]["Spellcasting Stat"], "INT")

    def test_wis_selected_when_highest(self):
        """WIS should be selected when it is the highest mental stat."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": 4, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Spells"]["Spellcasting Stat"], "WIS")

    def test_ignores_physical_stats(self):
        """STR should not be selected even if it is the highest overall stat."""
        modifiers = {"STR": 5, "DEX": 4, "CON": 3, "INT": 2, "WIS": 1, "CHA": 0}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Spells"]["Spellcasting Stat"], "INT")

    # --- Primary stat override ---

    def test_use_primary_for_casting(self):
        """Toggle on should use primary stat regardless of mental stats."""
        modifiers = {"STR": 5, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions, use_primary_for_casting=True, primary="STR")
        self.assertEqual(result["Spells"]["Spellcasting Stat"], "STR")

    def test_use_primary_falls_back_when_none(self):
        """Toggle on but primary is None should fall back to highest mental stat."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 4, "WIS": 2, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions, use_primary_for_casting=True, primary=None)
        self.assertEqual(result["Spells"]["Spellcasting Stat"], "INT")

    # --- Save DC and attack bonus calculations ---

    def test_spell_save_dc(self):
        """Save DC = 8 + casting mod + proficiency bonus. INT +4 at CR 5 (prof 3) = 15."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 4, "WIS": 2, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Spells"]["Spell Save DC"], 15)

    def test_spell_attack_bonus(self):
        """Spell attack bonus = casting mod + proficiency bonus. INT +4 at CR 5 (prof 3) = 7."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 4, "WIS": 2, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Spells"]["Spell Attack Bonus"], 7)

    def test_spell_save_dc_with_primary_override(self):
        """STR primary override at CR 5 with STR +5. DC = 8 + 5 + 3 = 16."""
        modifiers = {"STR": 5, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result = generate_action_data("5", modifiers, actions, use_primary_for_casting=True, primary="STR")
        self.assertEqual(result["Spells"]["Spell Save DC"], 16)

    # --- Spell budget ---

    def test_spell_budget_from_cr(self):
        """Spell budget should match the CR table value."""
        modifiers = {"STR": -1, "DEX": 1, "CON": 0, "INT": 3, "WIS": 2, "CHA": -1}
        actions = {"Spells": {"Fire Bolt": {"level": 0, "casting_amount": "at will"}}}
        result_cr5 = generate_action_data("5", modifiers, actions)
        result_cr13 = generate_action_data("13", modifiers, actions)
        self.assertEqual(result_cr5["Spells"]["Spell Budget"], 6)
        self.assertEqual(result_cr13["Spells"]["Spell Budget"], 10)

    # --- Spell data pass-through ---

    def test_spells_passed_through(self):
        """The spell list should be passed through unchanged."""
        modifiers = {"STR": -1, "DEX": 1, "CON": 0, "INT": 3, "WIS": 2, "CHA": -1}
        spells = {
            "Fire Bolt": {"level": 0, "casting_amount": "at will"},
            "Fireball": {"level": 3, "casting_amount": "3/day"},
        }
        actions = {"Spells": spells}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Spells"]["Spells"], spells)

    # --- No spells ---

    def test_no_spells_key_when_absent(self):
        """Actions without Spells should not produce Spells in output."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertNotIn("Spells", result)


class TestGenerateActionDataPassthrough(unittest.TestCase):
    """Tests for generate_action_data pass-through of traits, bonus actions,
    reactions, and their shared trait budget."""

    # --- Trait budget ---

    def test_trait_budget_present_when_traits_exist(self):
        """Trait Budget should appear when any of traits/BA/reactions exist."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Traits": {"Brave": "advantage on saves vs frightened"}}
        result = generate_action_data("5", modifiers, actions)
        self.assertIn("Trait Budget", result)
        self.assertEqual(result["Trait Budget"], 5)

    def test_trait_budget_present_for_reactions_only(self):
        """Trait Budget should still appear when only reactions exist."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Reactions": {"Parry": "add 2 to AC against one attack"}}
        result = generate_action_data("5", modifiers, actions)
        self.assertIn("Trait Budget", result)

    def test_no_trait_budget_without_any_sections(self):
        """Trait Budget should not appear when no traits/BA/reactions exist."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertNotIn("Trait Budget", result)

    # --- Pass-through data ---

    def test_traits_passed_through(self):
        """Traits should appear in output unchanged."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        traits = {"Brave": "advantage on saves vs frightened", "Fey Ancestry": "advantage vs charm"}
        actions = {"Traits": traits}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Traits"], traits)

    def test_bonus_actions_passed_through(self):
        """Bonus Actions should appear in output unchanged."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        bonus_actions = {"Hidden Step": "turn invisible as a bonus action"}
        actions = {"Bonus Actions": bonus_actions}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Bonus Actions"], bonus_actions)

    def test_reactions_passed_through(self):
        """Reactions should appear in output unchanged."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        reactions = {"Parry": "add 2 to AC against one attack"}
        actions = {"Reactions": reactions}
        result = generate_action_data("5", modifiers, actions)
        self.assertEqual(result["Reactions"], reactions)

    # --- Absent sections ---

    def test_no_traits_key_when_absent(self):
        """Traits should not appear in output when not in actions."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertNotIn("Traits", result)

    def test_no_bonus_actions_key_when_absent(self):
        """Bonus Actions should not appear in output when not in actions."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertNotIn("Bonus Actions", result)

    def test_no_reactions_key_when_absent(self):
        """Reactions should not appear in output when not in actions."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Weapons": ["Longsword"]}
        result = generate_action_data("5", modifiers, actions)
        self.assertNotIn("Reactions", result)

    # --- Trait budget scaling ---

    def test_trait_budget_scales_with_cr(self):
        """CR 0 should have budget 1, CR 9 should have budget 8, CR 13 should be 999."""
        modifiers = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": -1, "CHA": -1}
        actions = {"Traits": {"Brave": "advantage on saves vs frightened"}}
        result_cr0 = generate_action_data("0", modifiers, actions)
        result_cr9 = generate_action_data("9", modifiers, actions)
        result_cr13 = generate_action_data("13", modifiers, actions)
        self.assertEqual(result_cr0["Trait Budget"], 1)
        self.assertEqual(result_cr9["Trait Budget"], 8)
        self.assertEqual(result_cr13["Trait Budget"], 999)


if __name__ == '__main__':
    unittest.main()