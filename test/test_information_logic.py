import unittest
import random
from unittest import mock

import information_logic
from information_logic import (
    generate_information,
    _gather,
    _reduce_max,
    _reduce_unique,
    _reduce_descriptions,
    DAMAGE_RANK,
)
from data_loader import data


# ---------------------------------------------------------------------------
# Pure helper tests - fully synthetic input, no dependence on real data.
# ---------------------------------------------------------------------------

class TestGather(unittest.TestCase):

    def test_no_sources_returns_empty(self):
        """With no race, kits, or environment, gather returns an empty list."""
        self.assertEqual(_gather("senses"), [])

    def test_kit_sources_combine_in_order(self):
        """Entries are collected across kit sources in the order given."""
        table = {"A": {"k": [1, 2]}, "B": {"k": [3]}}
        sources = ((["A", "B"], table),)
        self.assertEqual(_gather("k", kit_sources=sources), [1, 2, 3])

    def test_none_selected_is_skipped(self):
        """A kit source whose selected list is None contributes nothing."""
        table = {"A": {"k": [1]}}
        sources = ((None, table),)
        self.assertEqual(_gather("k", kit_sources=sources), [])

    def test_missing_key_defaults_to_empty(self):
        """A kit entry lacking the key contributes nothing rather than crashing."""
        table = {"A": {"other": [1]}}
        sources = ((["A"], table),)
        self.assertEqual(_gather("k", kit_sources=sources), [])

    def test_multiple_kit_groups_combine(self):
        """Two separate kit groups are both read."""
        t1 = {"A": {"k": [1]}}
        t2 = {"B": {"k": [2]}}
        sources = ((["A"], t1), (["B"], t2))
        self.assertEqual(_gather("k", kit_sources=sources), [1, 2])

    def test_race_path_reads_real_race(self):
        """The race path returns exactly the race's stored entries."""
        self.assertEqual(
            _gather("senses", race="Elf"),
            information_logic.RACES["Elf"]["senses"],
        )

    def test_environment_path_reads_real_environment(self):
        """The environment path returns exactly the environment's entries."""
        self.assertEqual(
            _gather("traits", environment="Mountain"),
            information_logic.ENVIRONMENTS["Mountain"]["traits"],
        )

    def test_source_order_race_then_kits_then_environment(self):
        """Combined sources are concatenated race, kits, environment."""
        race = {"k": ["r"]}
        env = {"k": ["e"]}
        table = {"K": {"k": ["k"]}}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            result = _gather(
                "k",
                race="_R",
                kit_sources=((["K"], table),),
                environment="_E",
            )
        self.assertEqual(result, ["r", "k", "e"])


class TestReduceMax(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_reduce_max([], "range"), {})

    def test_single_entry(self):
        entries = [{"name": "Darkvision", "range": 60}]
        self.assertEqual(_reduce_max(entries, "range"), {"Darkvision": 60})

    def test_keeps_higher_when_higher_seen_second(self):
        entries = [{"name": "X", "range": 30}, {"name": "X", "range": 60}]
        self.assertEqual(_reduce_max(entries, "range"), {"X": 60})

    def test_keeps_higher_when_higher_seen_first(self):
        entries = [{"name": "X", "range": 60}, {"name": "X", "range": 30}]
        self.assertEqual(_reduce_max(entries, "range"), {"X": 60})

    def test_distinct_names_all_kept(self):
        entries = [{"name": "A", "range": 30}, {"name": "B", "range": 60}]
        self.assertEqual(_reduce_max(entries, "range"), {"A": 30, "B": 60})

    def test_works_with_distance_key(self):
        entries = [{"name": "Walking", "distance": 25}, {"name": "Walking", "distance": 30}]
        self.assertEqual(_reduce_max(entries, "distance"), {"Walking": 30})


class TestReduceUnique(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_reduce_unique([]), [])

    def test_preserves_first_seen_order(self):
        self.assertEqual(_reduce_unique(["b", "a", "c"]), ["b", "a", "c"])

    def test_deduplicates(self):
        self.assertEqual(_reduce_unique(["a", "b", "a"]), ["a", "b"])

    def test_dedup_keeps_first_position(self):
        self.assertEqual(_reduce_unique(["a", "b", "a", "c", "b"]), ["a", "b", "c"])


class TestReduceDescriptions(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_reduce_descriptions([]), {})

    def test_builds_name_to_description(self):
        entries = [{"name": "Brave", "description": "Advantage vs fear."}]
        self.assertEqual(_reduce_descriptions(entries), {"Brave": "Advantage vs fear."})

    def test_duplicate_name_last_wins(self):
        entries = [
            {"name": "X", "description": "first"},
            {"name": "X", "description": "second"},
        ]
        self.assertEqual(_reduce_descriptions(entries), {"X": "second"})


class TestDamageRank(unittest.TestCase):

    def test_full_outranks_half(self):
        self.assertGreater(DAMAGE_RANK["Full"], DAMAGE_RANK["Half"])

    def test_half_outranks_vuln(self):
        self.assertGreater(DAMAGE_RANK["Half"], DAMAGE_RANK["Vuln"])


# ---------------------------------------------------------------------------
# generate_information - name and personality.
# ---------------------------------------------------------------------------

class TestName(unittest.TestCase):

    def setUp(self):
        # Seed so name selection is reproducible across runs.
        random.seed(0)

    def test_name_generated_when_true(self):
        """A name is produced from the matching gender and race lists."""
        info = generate_information("Elf", True, "Masculine", None, None, None, None, None)
        self.assertIn("name", info)
        name = info["name"]
        first_names = information_logic.NAMES["Masculine"]["Elf"]["First"]
        last_names = information_logic.NAMES["Masculine"]["Elf"]["Last"]
        self.assertIn(" ", name)
        self.assertIn(name.split(" ")[0], first_names)
        self.assertIn(name.split(" ", 1)[1], last_names)

    def test_name_absent_when_false(self):
        """No name key is added when name generation is off."""
        info = generate_information("Elf", False, "Masculine", None, None, None, None, None)
        self.assertNotIn("name", info)

    def test_gender_defaults_to_neutral(self):
        """A None gender falls back to the Neutral name lists."""
        info = generate_information("Elf", True, None, None, None, None, None, None)
        self.assertIn("name", info)
        neutral_first = information_logic.NAMES["Neutral"]["Elf"]["First"]
        self.assertIn(info["name"].split(" ")[0], neutral_first)


class TestPersonality(unittest.TestCase):

    def setUp(self):
        random.seed(0)
        # Use a real personality category so the lookup is valid.
        self.category = next(iter(data["personalities"]))

    def test_personality_when_provided(self):
        info = generate_information("Human", False, None, self.category, None, None, None, None)
        self.assertIn("personality", info)
        descriptions = [entry["description"]
                        for entry in information_logic.PERSONALITIES[self.category]["entries"]]
        self.assertIn(info["personality"], descriptions)

    def test_personality_absent_when_none(self):
        info = generate_information("Human", False, None, None, None, None, None, None)
        self.assertNotIn("personality", info)


# ---------------------------------------------------------------------------
# generate_information - senses.
# ---------------------------------------------------------------------------

class TestSenses(unittest.TestCase):

    def test_race_sense_present(self):
        """An Elf's darkvision is carried through to the senses section."""
        info = generate_information("Elf", False, None, None, None, None, None, None)
        self.assertEqual(info["senses"], {"Darkvision": 60})

    def test_sense_shape_is_flat(self):
        """Senses are stored as {name: int}, matching the speed shape."""
        info = generate_information("Elf", False, None, None, None, None, None, None)
        for value in info["senses"].values():
            self.assertIsInstance(value, int)

    def test_absent_when_race_has_none(self):
        """A race with no senses and no other source produces no senses key."""
        info = generate_information("Human", False, None, None, None, None, None, None)
        self.assertNotIn("senses", info)

    def test_combat_kit_sense_is_read(self):
        """Senses from a combat kit are gathered for a race that has none."""
        info = generate_information("Human", False, None, None, ["Grave Digger"], None, None, None)
        self.assertEqual(info["senses"], {"Darkvision": 60})

    def test_max_range_kept_higher_from_kit(self):
        """When two sources share a sense, the longer range wins."""
        race = {"senses": [{"name": "Darkvision", "range": 30}]}
        kit = {"senses": [{"name": "Darkvision", "range": 120}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", False, None, None, ["_K"], None, None, None)
        self.assertEqual(info["senses"], {"Darkvision": 120})

    def test_max_range_kept_higher_from_race(self):
        race = {"senses": [{"name": "Darkvision", "range": 120}]}
        kit = {"senses": [{"name": "Darkvision", "range": 30}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", False, None, None, ["_K"], None, None, None)
        self.assertEqual(info["senses"], {"Darkvision": 120})

    def test_environment_sense_is_read(self):
        """Environment senses combine with the race senses."""
        env = {"senses": [{"name": "Blindsight", "range": 30}]}
        with mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("Elf", False, None, None, None, None, None, "_E")
        self.assertEqual(info["senses"], {"Darkvision": 60, "Blindsight": 30})


# ---------------------------------------------------------------------------
# generate_information - damage modifiers (resistance / immunity / vulnerability).
# ---------------------------------------------------------------------------

class TestDamage(unittest.TestCase):

    def test_race_resistance(self):
        """A Dwarf's poison resistance lands in the resistances list."""
        info = generate_information("Dwarf", False, None, None, None, None, None, None)
        self.assertEqual(info["resistances"], ["Poison"])
        self.assertNotIn("immunities", info)
        self.assertNotIn("vulnerabilities", info)

    def test_race_immunity(self):
        """A Yuan-ti's full poison reduction lands in immunities."""
        info = generate_information("Yuan-ti", False, None, None, None, None, None, None)
        self.assertEqual(info["immunities"], ["Poison"])
        self.assertNotIn("resistances", info)

    def test_no_damage_keys_when_none(self):
        """A race with no damage modifiers produces none of the three keys."""
        info = generate_information("Human", False, None, None, None, None, None, None)
        for key in ("resistances", "immunities", "vulnerabilities"):
            self.assertNotIn(key, info)

    def test_distinct_types_split_into_buckets(self):
        race = {"resistances": [
            {"name": "Fire", "damage_reduction": "Half"},
            {"name": "Cold", "damage_reduction": "Full"},
            {"name": "Acid", "damage_reduction": "Vuln"},
        ]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}):
            info = generate_information("_R", False, None, None, None, None, None, None)
        self.assertEqual(info["resistances"], ["Fire"])
        self.assertEqual(info["immunities"], ["Cold"])
        self.assertEqual(info["vulnerabilities"], ["Acid"])

    def test_full_beats_half(self):
        """Immunity from one source overrides resistance from another."""
        race = {"resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        kit = {"resistances": [{"name": "Fire", "damage_reduction": "Full"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", False, None, None, ["_K"], None, None, None)
        self.assertEqual(info["immunities"], ["Fire"])
        self.assertNotIn("resistances", info)

    def test_half_beats_vuln(self):
        """Resistance overrides vulnerability for the same type."""
        race = {"resistances": [{"name": "Fire", "damage_reduction": "Vuln"}]}
        kit = {"resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.MAGIC_KITS, {"_K": kit}):
            info = generate_information("_R", False, None, None, None, ["_K"], None, None)
        self.assertEqual(info["resistances"], ["Fire"])
        self.assertNotIn("vulnerabilities", info)

    def test_full_beats_vuln(self):
        race = {"resistances": [{"name": "Fire", "damage_reduction": "Vuln"}]}
        kit = {"resistances": [{"name": "Fire", "damage_reduction": "Full"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", False, None, None, ["_K"], None, None, None)
        self.assertEqual(info["immunities"], ["Fire"])
        self.assertNotIn("vulnerabilities", info)

    def test_same_type_same_strength_dedup(self):
        """The same type at the same strength from two sources appears once."""
        race = {"resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        env = {"resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("_R", False, None, None, None, None, None, "_E")
        self.assertEqual(info["resistances"], ["Fire"])


# ---------------------------------------------------------------------------
# generate_information - speed.
# ---------------------------------------------------------------------------

class TestSpeed(unittest.TestCase):

    def test_race_speed(self):
        """An Elf's walking speed is carried through."""
        info = generate_information("Elf", False, None, None, None, None, None, None)
        self.assertEqual(info["speed"], {"Walking": 30})

    def test_multiple_movement_types(self):
        """A race with two movement types keeps both."""
        info = generate_information("Triton", False, None, None, None, None, None, None)
        self.assertEqual(info["speed"], {"Walking": 30, "Swimming": 30})

    def test_environment_adds_speed(self):
        """An environment speed is merged with the race speed."""
        env = {"speed": [{"name": "Climbing", "distance": 20}]}
        with mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("Human", False, None, None, None, None, None, "_E")
        self.assertEqual(info["speed"], {"Walking": 30, "Climbing": 20})

    def test_environment_max_wins(self):
        """A faster environment speed replaces the race value for that type."""
        env = {"speed": [{"name": "Walking", "distance": 40}]}
        with mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("Human", False, None, None, None, None, None, "_E")
        self.assertEqual(info["speed"], {"Walking": 40})

    def test_walking_listed_first(self):
        """Race is gathered first, so Walking leads the speed ordering."""
        info = generate_information("Triton", False, None, None, None, None, None, None)
        self.assertEqual(list(info["speed"].keys())[0], "Walking")


# ---------------------------------------------------------------------------
# generate_information - proficiencies and tool proficiencies.
# ---------------------------------------------------------------------------

class TestProficiencies(unittest.TestCase):

    def test_role_kit_proficiencies(self):
        """Role kit skill and tool proficiencies feed the right sections."""
        info = generate_information("Human", False, None, None, None, None, ["Sailor"], None)
        expected = information_logic.ROLE_KITS["Sailor"]
        self.assertEqual(set(info["proficiencies"]), set(expected["proficiencies"]))
        self.assertEqual(set(info["tool_proficiencies"]), set(expected["proficiencies_t"]))

    def test_dedup_across_kit_types(self):
        """A proficiency shared by two kits appears only once."""
        combat = {"proficiencies": ["Stealth"], "proficiencies_t": []}
        role = {"proficiencies": ["Stealth", "Perception"], "proficiencies_t": []}
        with mock.patch.dict(information_logic.COMBAT_KITS, {"_C": combat}), \
             mock.patch.dict(information_logic.ROLE_KITS, {"_R": role}):
            info = generate_information("Human", False, None, None, ["_C"], None, ["_R"], None)
        self.assertEqual(info["proficiencies"], ["Stealth", "Perception"])

    def test_tool_and_skill_kept_separate(self):
        """Tool proficiencies do not bleed into the skill proficiency list."""
        kit = {"proficiencies": ["Stealth"], "proficiencies_t": ["Thieves' Tools"]}
        with mock.patch.dict(information_logic.COMBAT_KITS, {"_C": kit}):
            info = generate_information("Human", False, None, None, ["_C"], None, None, None)
        self.assertEqual(info["proficiencies"], ["Stealth"])
        self.assertEqual(info["tool_proficiencies"], ["Thieves' Tools"])

    def test_absent_when_no_kits(self):
        info = generate_information("Human", False, None, None, None, None, None, None)
        self.assertNotIn("proficiencies", info)
        self.assertNotIn("tool_proficiencies", info)


# ---------------------------------------------------------------------------
# generate_information - out-of-combat traits.
# ---------------------------------------------------------------------------

class TestTraits(unittest.TestCase):

    def test_environment_traits(self):
        """Environment traits are stored as a name to description dict."""
        info = generate_information("Human", False, None, None, None, None, None, "Mountain")
        expected = {t["name"]: t["description"]
                    for t in information_logic.ENVIRONMENTS["Mountain"]["traits"]}
        self.assertEqual(info["environmental_traits"], expected)

    def test_environment_trait_shape_is_dict(self):
        info = generate_information("Human", False, None, None, None, None, None, "Mountain")
        self.assertIsInstance(info["environmental_traits"], dict)
        for value in info["environmental_traits"].values():
            self.assertIsInstance(value, str)

    def test_role_traits(self):
        """A role kit with a trait surfaces it under role_traits."""
        info = generate_information("Human", False, None, None, None, None, ["Pirate"], None)
        expected = {t["name"]: t["description"]
                    for t in information_logic.ROLE_KITS["Pirate"]["traits"]}
        self.assertEqual(info["role_traits"], expected)

    def test_role_kit_without_traits_omits_key(self):
        """A role kit that has only proficiencies adds no role_traits key."""
        info = generate_information("Human", False, None, None, None, None, ["Sailor"], None)
        self.assertNotIn("role_traits", info)
        self.assertIn("proficiencies", info)

    def test_environment_traits_absent_when_none(self):
        info = generate_information("Human", False, None, None, None, None, None, None)
        self.assertNotIn("environmental_traits", info)


# ---------------------------------------------------------------------------
# Source scoping - role kits must not contribute senses, damage, or speed.
# ---------------------------------------------------------------------------

class TestSourceScoping(unittest.TestCase):

    def test_role_kit_ignored_for_senses_damage_speed(self):
        """Role kits feed only proficiencies and traits, never senses,
        damage, or speed, even when those keys are present on the entry."""
        role = {
            "senses": [{"name": "Darkvision", "range": 999}],
            "resistances": [{"name": "Fire", "damage_reduction": "Full"}],
            "speed": [{"name": "Flying", "distance": 99}],
        }
        with mock.patch.dict(information_logic.ROLE_KITS, {"_R": role}):
            info = generate_information("Human", False, None, None, None, None, ["_R"], None)
        self.assertNotIn("senses", info)
        self.assertNotIn("immunities", info)
        self.assertNotIn("Flying", info.get("speed", {}))


# ---------------------------------------------------------------------------
# Shape and empty-section guarantees.
# ---------------------------------------------------------------------------

class TestStructure(unittest.TestCase):

    def test_minimal_call_only_has_speed(self):
        """A bare race with no options yields only the race-derived speed."""
        info = generate_information("Human", False, None, None, None, None, None, None)
        self.assertEqual(info, {"speed": {"Walking": 30}})

    def test_no_empty_sections(self):
        """No section is ever present as an empty container."""
        info = generate_information("Elf", False, None, None, None, None, None, None)
        for value in info.values():
            self.assertTrue(value)

    def test_returns_dict(self):
        info = generate_information("Human", False, None, None, None, None, None, None)
        self.assertIsInstance(info, dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)