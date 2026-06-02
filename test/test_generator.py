import unittest

from generator import generate_npc, Selections


# ---------------------------------------------------------------------------
# Top-level contract.
#
# generate_npc is pure orchestration: it must always return a dict with the
# same seven keys regardless of which selections are set, because the renderer
# depends on that shape being stable.
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "stats",
    "modifiers",
    "ac",
    "hp",
    "action_data",
    "title",
    "information",
}


class TestStructure(unittest.TestCase):

    def test_returns_dict(self):
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.assertIsInstance(npc, dict)

    def test_has_exactly_expected_keys(self):
        """The contract is fixed - no missing keys, no surprise extras."""
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.assertEqual(set(npc.keys()), EXPECTED_KEYS)

    def test_keys_present_even_with_full_selection(self):
        """A fully populated selection still yields exactly the same keys."""
        npc = generate_npc(Selections(
            cr="10",
            base="Half Caster",
            race="Elf",
            primary="DEX",
            secondary="CON",
            combat_kits=["Skirmisher"],
            magic_kits=["Abjuration"],
            role_kits=["Sailor"],
            environment="Mountain",
            use_primary_for_casting=True,
        ))
        self.assertEqual(set(npc.keys()), EXPECTED_KEYS)

    def test_field_types(self):
        """Each top-level value carries the type the renderer expects."""
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.assertIsInstance(npc["stats"], dict)
        self.assertIsInstance(npc["modifiers"], dict)
        self.assertIsInstance(npc["ac"], int)
        self.assertIsInstance(npc["hp"], dict)
        self.assertIsInstance(npc["title"], str)
        self.assertIsInstance(npc["information"], dict)
        # action_data is a dict (possibly empty) for any NPC, since race is
        # always set and get_action_data therefore never returns None.
        self.assertIsInstance(npc["action_data"], dict)


# ---------------------------------------------------------------------------
# Minimal NPC - the bare cr/base/race call with every optional field defaulted.
#
# Values here are anchored to numbers already proven in the per-module suites:
# the Human CR5 Melee stat array, the 19-die HP math, and the race-only speed.
# ---------------------------------------------------------------------------

class TestMinimalNPC(unittest.TestCase):

    def setUp(self):
        self.npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))

    def test_stats_flow_through(self):
        """Human +1-to-all on the CR5 Melee default array."""
        self.assertEqual(
            self.npc["stats"],
            {"STR": 17, "CON": 14, "DEX": 13, "WIS": 12, "CHA": 11, "INT": 11},
        )

    def test_modifiers_derived_from_stats(self):
        """Modifiers are (score - 10) // 2 applied to the stat dict above."""
        self.assertEqual(
            self.npc["modifiers"],
            {"STR": 3, "CON": 2, "DEX": 1, "WIS": 1, "CHA": 0, "INT": 0},
        )

    def test_hp_uses_con_modifier(self):
        """CON mod +2 feeds calculate_hp: 19 dice d10, 104.5 + 38 -> 142."""
        self.assertEqual(self.npc["hp"]["hp"], 142)
        self.assertEqual(self.npc["hp"]["dice_string"], "19d10 + 38")

    def test_no_kits_gives_commoner(self):
        self.assertEqual(self.npc["title"], "Commoner")

    def test_action_data_is_empty_dict_not_none(self):
        """A kitless Human has no actions, but the value is {} not None."""
        self.assertEqual(self.npc["action_data"], {})

    def test_information_is_race_speed_only(self):
        self.assertEqual(self.npc["information"], {"speed": {"Walking": 30}})


# ---------------------------------------------------------------------------
# HP shape - guards the tuple -> dict refactor at the orchestration boundary.
# ---------------------------------------------------------------------------

class TestHpShape(unittest.TestCase):

    def test_hp_has_both_keys(self):
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.assertEqual(set(npc["hp"].keys()), {"hp", "dice_string"})

    def test_hp_value_is_int(self):
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.assertIsInstance(npc["hp"]["hp"], int)

    def test_dice_string_is_str(self):
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.assertIsInstance(npc["hp"]["dice_string"], str)


# ---------------------------------------------------------------------------
# Action data path - the get_action_data -> generate_action_data handoff.
# ---------------------------------------------------------------------------

class TestActionData(unittest.TestCase):

    def test_combat_kit_adds_weapons(self):
        """Skirmisher carries weapons, so the action block surfaces them."""
        npc = generate_npc(Selections(
            cr="5", base="Melee", race="Human", combat_kits=["Skirmisher"],
        ))
        self.assertIn("weapons", npc["action_data"])
        self.assertTrue(npc["action_data"]["weapons"])

    def test_magic_kit_adds_spellcasting_block(self):
        """A magic kit produces a spells block with a save DC and casting stat."""
        npc = generate_npc(Selections(
            cr="5", base="Full Caster", race="Human", magic_kits=["Abjuration"],
        ))
        self.assertIn("spells", npc["action_data"])
        self.assertIn("spell_save_dc", npc["action_data"]["spells"])
        self.assertIn("spellcasting_stat", npc["action_data"]["spells"])

    def test_no_spells_block_without_magic_kit(self):
        npc = generate_npc(Selections(
            cr="5", base="Melee", race="Human", combat_kits=["Skirmisher"],
        ))
        self.assertNotIn("spells", npc["action_data"])


# ---------------------------------------------------------------------------
# Casting stat override - the use_primary_for_casting / primary interaction
# flowing through generate_npc end to end.
# ---------------------------------------------------------------------------

class TestCastingOverride(unittest.TestCase):

    def test_primary_override_sets_casting_stat(self):
        """Toggle on with a primary stat uses that stat for casting."""
        npc = generate_npc(Selections(
            cr="5",
            base="Full Caster",
            race="Human",
            primary="STR",
            magic_kits=["Abjuration"],
            use_primary_for_casting=True,
        ))
        self.assertEqual(npc["action_data"]["spells"]["spellcasting_stat"], "STR")

    def test_toggle_on_but_primary_none_falls_back(self):
        """Toggle on with no primary must not crash; it falls back to a
        mental stat rather than passing None down."""
        npc = generate_npc(Selections(
            cr="5",
            base="Full Caster",
            race="Human",
            primary=None,
            magic_kits=["Abjuration"],
            use_primary_for_casting=True,
        ))
        self.assertIn(
            npc["action_data"]["spells"]["spellcasting_stat"],
            {"INT", "WIS", "CHA"},
        )


# ---------------------------------------------------------------------------
# Title flow - resolve_title reached through the orchestrator.
# ---------------------------------------------------------------------------

class TestTitleFlow(unittest.TestCase):

    def test_combat_kit_title_is_not_commoner(self):
        npc = generate_npc(Selections(
            cr="5", base="Melee", race="Human", combat_kits=["Skirmisher"],
        ))
        self.assertNotEqual(npc["title"], "Commoner")
        self.assertTrue(npc["title"])

    def test_role_only_title_is_not_commoner(self):
        npc = generate_npc(Selections(
            cr="5", base="Non Combatant", race="Human", role_kits=["Sailor"],
        ))
        self.assertNotEqual(npc["title"], "Commoner")


# ---------------------------------------------------------------------------
# Information flow - generate_information stays nested under one key.
# ---------------------------------------------------------------------------

class TestInformationFlow(unittest.TestCase):

    def test_environment_surfaces_in_information(self):
        """An environment selection should expand the information block beyond
        the bare race speed."""
        bare = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        with_env = generate_npc(Selections(
            cr="5", base="Melee", race="Human", environment="Mountain",
        ))
        self.assertNotEqual(with_env["information"], bare["information"])

    def test_information_kept_nested(self):
        """The information dict is one value, not spread across the top level."""
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        # speed lives inside information, never promoted to a top-level key.
        self.assertIn("speed", npc["information"])
        self.assertNotIn("speed", npc)


# ---------------------------------------------------------------------------
# Edge cases and determinism.
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_cr_zero_produces_valid_npc(self):
        """CR 0 is the bottom of the table - it must still build cleanly."""
        npc = generate_npc(Selections(cr="0", base="Melee", race="Human"))
        self.assertEqual(set(npc.keys()), EXPECTED_KEYS)
        self.assertGreaterEqual(npc["hp"]["hp"], 1)

    def test_cr_thirty_produces_valid_npc(self):
        """CR 30 is the ceiling - same contract holds."""
        npc = generate_npc(Selections(cr="30", base="Melee", race="Human"))
        self.assertEqual(set(npc.keys()), EXPECTED_KEYS)

    def test_fractional_cr(self):
        npc = generate_npc(Selections(cr="1/4", base="Ranged", race="Elf"))
        self.assertEqual(set(npc.keys()), EXPECTED_KEYS)

    def test_deterministic_for_identical_selections(self):
        """No name/personality in the dict means generation is pure: identical
        selections must yield identical output."""
        sel = Selections(
            cr="7", base="Half Caster", race="Dwarf",
            combat_kits=["Skirmisher"], magic_kits=["Abjuration"],
        )
        self.assertEqual(generate_npc(sel), generate_npc(sel))

    def test_all_three_kit_types_together(self):
        """Stacking every kit type must not collide or crash."""
        npc = generate_npc(Selections(
            cr="9",
            base="Half Caster",
            race="Human",
            combat_kits=["Skirmisher"],
            magic_kits=["Abjuration"],
            role_kits=["Sailor"],
        ))
        self.assertEqual(set(npc.keys()), EXPECTED_KEYS)
        self.assertIsInstance(npc["action_data"], dict)


if __name__ == "__main__":
    unittest.main()