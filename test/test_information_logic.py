import unittest
from unittest import mock

import information_logic
from information_logic import (
    generate_information,
    resolve_title,
    generate_name,
    generate_personality,
    enum_name_races,
    enum_personality_options,
    _gather,
    _reduce_max,
    _reduce_unique,
    _reduce_descriptions,
    _map_proficiencies,
    _map_saves,
    _calculate_passive_perception,
    DAMAGE_RANK,
)


# ---------------------------------------------------------------------------
# Shared fixtures used across multiple test classes.
#
# FAKE_MODIFIERS is a standard six-ability modifier dict used wherever a
# modifiers argument is required. Values are chosen to be distinct so any
# wrong-ability lookup produces a visibly wrong number.
# FAKE_PROF is a proficiency bonus used alongside FAKE_MODIFIERS.
# BASE is the base category string used for all generate_information calls;
# "Melee" is a real entry so saving throw proficiencies resolve without
# mocking.
# ---------------------------------------------------------------------------

FAKE_MODIFIERS = {"STR": 1, "DEX": 2, "CON": 3, "INT": 4, "WIS": 5, "CHA": 6}
FAKE_PROF = 3
BASE = "Melee"
CR = "5"


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


class TestMapProficiencies(unittest.TestCase):

    def test_proficient_skill_adds_prof_bonus(self):
        """A mapped skill returns ability modifier plus proficiency bonus."""
        # Stealth maps to DEX; DEX mod is 2, prof bonus is 3, expect 5.
        result = _map_proficiencies(["Stealth"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertEqual(result["Stealth"], 5)

    def test_uses_correct_governing_ability(self):
        """Each skill uses its own governing ability, not a fixed one."""
        # Perception maps to WIS (5), Athletics to STR (1).
        result = _map_proficiencies(["Perception", "Athletics"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertEqual(result["Perception"], 8)
        self.assertEqual(result["Athletics"], 4)

    def test_empty_entries_returns_empty(self):
        self.assertEqual(_map_proficiencies([], FAKE_MODIFIERS, FAKE_PROF), {})

    def test_unmapped_skill_raises_key_error(self):
        """A skill absent from proficiencies_map.json raises loudly."""
        with self.assertRaises(KeyError) as ctx:
            _map_proficiencies(["NotASkill"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertIn("proficiencies_map.json", str(ctx.exception))

    def test_error_message_names_the_missing_skill(self):
        """The KeyError message names the offending skill for fast diagnosis."""
        with self.assertRaises(KeyError) as ctx:
            _map_proficiencies(["BadSkill"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertIn("BadSkill", str(ctx.exception))

    def test_result_shape_is_str_to_int(self):
        result = _map_proficiencies(["Stealth"], FAKE_MODIFIERS, FAKE_PROF)
        for k, v in result.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, int)

    def test_higher_prof_bonus_increases_all_values(self):
        """Doubling the prof bonus raises every skill value by the difference."""
        low = _map_proficiencies(["Stealth"], FAKE_MODIFIERS, 2)
        high = _map_proficiencies(["Stealth"], FAKE_MODIFIERS, 4)
        self.assertEqual(high["Stealth"], low["Stealth"] + 2)


class TestMapSaves(unittest.TestCase):

    def test_proficient_save_adds_prof_bonus(self):
        """A proficient save is ability modifier plus proficiency bonus."""
        result = _map_saves(["STR"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertEqual(result["STR"], FAKE_MODIFIERS["STR"] + FAKE_PROF)

    def test_two_proficient_saves_both_get_bonus(self):
        """Both proficient saves receive the bonus."""
        result = _map_saves(["CON", "WIS"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertEqual(result["CON"], FAKE_MODIFIERS["CON"] + FAKE_PROF)
        self.assertEqual(result["WIS"], FAKE_MODIFIERS["WIS"] + FAKE_PROF)

    def test_only_proficient_keys_are_emitted(self):
        """Non-proficient abilities are absent from the result."""
        result = _map_saves(["STR", "CON"], FAKE_MODIFIERS, FAKE_PROF)
        self.assertEqual(set(result.keys()), {"STR", "CON"})

    def test_empty_list_returns_empty_dict(self):
        """No proficient saves produces an empty dict."""
        self.assertEqual(_map_saves([], FAKE_MODIFIERS, FAKE_PROF), {})

    def test_result_shape_is_str_to_int(self):
        result = _map_saves(["STR"], FAKE_MODIFIERS, FAKE_PROF)
        for k, v in result.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, int)


class TestCalculatePassivePerception(unittest.TestCase):

    def test_base_is_ten_plus_wis(self):
        """Without proficiency the score is 10 + WIS modifier."""
        self.assertEqual(_calculate_passive_perception(3, 2, False), 13)

    def test_proficiency_adds_prof_bonus(self):
        """With proficiency the score is 10 + WIS modifier + prof bonus."""
        self.assertEqual(_calculate_passive_perception(3, 2, True), 15)

    def test_zero_wis_mod(self):
        self.assertEqual(_calculate_passive_perception(0, 2, False), 10)

    def test_negative_wis_mod(self):
        """A negative WIS modifier correctly lowers the score below 10."""
        self.assertEqual(_calculate_passive_perception(-1, 2, False), 9)

    def test_returns_int(self):
        self.assertIsInstance(_calculate_passive_perception(2, 3, True), int)


class TestDamageRank(unittest.TestCase):

    def test_full_outranks_half(self):
        self.assertGreater(DAMAGE_RANK["Full"], DAMAGE_RANK["Half"])

    def test_half_outranks_vuln(self):
        self.assertGreater(DAMAGE_RANK["Half"], DAMAGE_RANK["Vuln"])


# ---------------------------------------------------------------------------
# generate_information - senses.
# ---------------------------------------------------------------------------

class TestSenses(unittest.TestCase):

    def test_race_sense_present(self):
        """An Elf's darkvision is carried through to the senses section."""
        info = generate_information("Elf", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["senses"], {"Darkvision": 60})

    def test_sense_shape_is_flat(self):
        """Senses are stored as {name: int}, matching the speed shape."""
        info = generate_information("Elf", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        for value in info["senses"].values():
            self.assertIsInstance(value, int)

    def test_absent_when_race_has_none(self):
        """A race with no senses and no other source produces no senses key."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertNotIn("senses", info)

    def test_combat_kit_sense_is_read(self):
        """Senses from a combat kit are gathered for a race that has none."""
        info = generate_information("Human", ["Grave Digger"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["senses"], {"Darkvision": 60})

    def test_max_range_kept_higher_from_kit(self):
        """When two sources share a sense, the longer range wins."""
        race = {"size": "Medium", "senses": [{"name": "Darkvision", "range": 30}]}
        kit = {"senses": [{"name": "Darkvision", "range": 120}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", ["_K"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["senses"], {"Darkvision": 120})

    def test_max_range_kept_higher_from_race(self):
        race = {"size": "Medium", "senses": [{"name": "Darkvision", "range": 120}]}
        kit = {"senses": [{"name": "Darkvision", "range": 30}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", ["_K"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["senses"], {"Darkvision": 120})

    def test_environment_sense_is_read(self):
        """Environment senses combine with the race senses."""
        env = {"senses": [{"name": "Blindsight", "range": 30}]}
        with mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("Elf", None, None, None, "_E", FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["senses"], {"Darkvision": 60, "Blindsight": 30})


# ---------------------------------------------------------------------------
# generate_information - damage modifiers (resistance / immunity / vulnerability).
# ---------------------------------------------------------------------------

class TestDamage(unittest.TestCase):

    def test_race_resistance(self):
        """A Dwarf's poison resistance lands in the resistances list."""
        info = generate_information("Dwarf", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["resistances"], ["Poison"])
        self.assertNotIn("immunities", info)
        self.assertNotIn("vulnerabilities", info)

    def test_race_immunity(self):
        """A Yuan-ti's full poison reduction lands in immunities."""
        info = generate_information("Yuan-ti", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["immunities"], ["Poison"])
        self.assertNotIn("resistances", info)

    def test_no_damage_keys_when_none(self):
        """A race with no damage modifiers produces none of the three keys."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        for key in ("resistances", "immunities", "vulnerabilities"):
            self.assertNotIn(key, info)

    def test_distinct_types_split_into_buckets(self):
        race = {"size": "Medium", "resistances": [
            {"name": "Fire", "damage_reduction": "Half"},
            {"name": "Cold", "damage_reduction": "Full"},
            {"name": "Acid", "damage_reduction": "Vuln"},
        ]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}):
            info = generate_information("_R", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["resistances"], ["Fire"])
        self.assertEqual(info["immunities"], ["Cold"])
        self.assertEqual(info["vulnerabilities"], ["Acid"])

    def test_full_beats_half(self):
        """Immunity from one source overrides resistance from another."""
        race = {"size": "Medium", "resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        kit = {"resistances": [{"name": "Fire", "damage_reduction": "Full"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", ["_K"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["immunities"], ["Fire"])
        self.assertNotIn("resistances", info)

    def test_half_beats_vuln(self):
        """Resistance overrides vulnerability for the same type."""
        race = {"size": "Medium", "resistances": [{"name": "Fire", "damage_reduction": "Vuln"}]}
        kit = {"resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.MAGIC_KITS, {"_K": kit}):
            info = generate_information("_R", None, ["_K"], None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["resistances"], ["Fire"])
        self.assertNotIn("vulnerabilities", info)

    def test_full_beats_vuln(self):
        race = {"size": "Medium", "resistances": [{"name": "Fire", "damage_reduction": "Vuln"}]}
        kit = {"resistances": [{"name": "Fire", "damage_reduction": "Full"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.COMBAT_KITS, {"_K": kit}):
            info = generate_information("_R", ["_K"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["immunities"], ["Fire"])
        self.assertNotIn("vulnerabilities", info)

    def test_same_type_same_strength_dedup(self):
        """The same type at the same strength from two sources appears once."""
        race = {"size": "Medium", "resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        env = {"resistances": [{"name": "Fire", "damage_reduction": "Half"}]}
        with mock.patch.dict(information_logic.RACES, {"_R": race}), \
             mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("_R", None, None, None, "_E", FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["resistances"], ["Fire"])


# ---------------------------------------------------------------------------
# generate_information - speed.
# ---------------------------------------------------------------------------

class TestSpeed(unittest.TestCase):

    def test_race_speed(self):
        """An Elf's walking speed is carried through."""
        info = generate_information("Elf", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["speed"], {"Walking": 30})

    def test_multiple_movement_types(self):
        """A race with two movement types keeps both."""
        info = generate_information("Triton", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["speed"], {"Walking": 30, "Swimming": 30})

    def test_environment_adds_speed(self):
        """An environment speed is merged with the race speed."""
        env = {"speed": [{"name": "Climbing", "distance": 20}]}
        with mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("Human", None, None, None, "_E", FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["speed"], {"Walking": 30, "Climbing": 20})

    def test_environment_max_wins(self):
        """A faster environment speed replaces the race value for that type."""
        env = {"speed": [{"name": "Walking", "distance": 40}]}
        with mock.patch.dict(information_logic.ENVIRONMENTS, {"_E": env}):
            info = generate_information("Human", None, None, None, "_E", FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["speed"], {"Walking": 40})

    def test_walking_listed_first(self):
        """Race is gathered first, so Walking leads the speed ordering."""
        info = generate_information("Triton", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(list(info["speed"].keys())[0], "Walking")


# ---------------------------------------------------------------------------
# generate_information - proficiencies and tool proficiencies.
# ---------------------------------------------------------------------------

class TestProficiencies(unittest.TestCase):

    def test_role_kit_proficiencies(self):
        """Role kit skill proficiencies produce modifier values, not raw strings."""
        info = generate_information("Human", None, None, ["Sailor"], None, FAKE_MODIFIERS, CR, BASE)
        self.assertIsInstance(info["proficiencies"], dict)
        for v in info["proficiencies"].values():
            self.assertIsInstance(v, int)

    def test_dedup_across_kit_types(self):
        """A proficiency shared by two kits appears only once in the output."""
        combat = {"proficiencies": ["Stealth"], "proficiencies_t": []}
        role = {"proficiencies": ["Stealth", "Perception"], "proficiencies_t": []}
        with mock.patch.dict(information_logic.COMBAT_KITS, {"_C": combat}), \
             mock.patch.dict(information_logic.ROLE_KITS, {"_R": role}):
            info = generate_information("Human", ["_C"], None, ["_R"], None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(set(info["proficiencies"].keys()), {"Stealth", "Perception"})

    def test_tool_and_skill_kept_separate(self):
        """Tool proficiencies do not bleed into the skill proficiency dict."""
        kit = {"proficiencies": ["Stealth"], "proficiencies_t": ["Thieves' Tools"]}
        with mock.patch.dict(information_logic.COMBAT_KITS, {"_C": kit}):
            info = generate_information("Human", ["_C"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIn("Stealth", info["proficiencies"])
        self.assertEqual(info["tool_proficiencies"], ["Thieves' Tools"])

    def test_absent_when_no_kits(self):
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertNotIn("proficiencies", info)
        self.assertNotIn("tool_proficiencies", info)

    def test_proficiency_value_is_mod_plus_prof_bonus(self):
        """The modifier stored for a skill is ability mod + prof bonus."""
        # Stealth maps to DEX; FAKE_MODIFIERS DEX is 2, CR 5 prof bonus is 3.
        kit = {"proficiencies": ["Stealth"], "proficiencies_t": []}
        with mock.patch.dict(information_logic.COMBAT_KITS, {"_C": kit}):
            info = generate_information("Human", ["_C"], None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["proficiencies"]["Stealth"], FAKE_MODIFIERS["DEX"] + 3)


# ---------------------------------------------------------------------------
# generate_information - passive Perception.
# ---------------------------------------------------------------------------

class TestPassivePerception(unittest.TestCase):

    def test_always_present(self):
        """Passive Perception is on every stat block, even with no kits."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIn("passive_perception", info)

    def test_non_proficient_is_ten_plus_wis(self):
        """Without Perception proficiency the score is 10 + WIS modifier."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["passive_perception"], 10 + FAKE_MODIFIERS["WIS"])

    def test_proficient_adds_prof_bonus(self):
        """A kit granting Perception proficiency raises the passive score."""
        kit = {"proficiencies": ["Perception"], "proficiencies_t": []}
        with mock.patch.dict(information_logic.ROLE_KITS, {"_R": kit}):
            info = generate_information("Human", None, None, ["_R"], None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["passive_perception"], 10 + FAKE_MODIFIERS["WIS"] + 3)

    def test_returns_int(self):
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIsInstance(info["passive_perception"], int)


# ---------------------------------------------------------------------------
# generate_information - saving throws.
# ---------------------------------------------------------------------------

class TestSavingThrows(unittest.TestCase):

    def test_always_present(self):
        """Saving throws are on every stat block, even with no kits."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIn("saving_throws", info)

    def test_only_proficient_saves_emitted(self):
        """Only the two saves from the base category appear as keys."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        proficient = information_logic.BASE_CATEGORIES[BASE]["saving_throws"]
        self.assertEqual(set(info["saving_throws"].keys()), set(proficient))

    def test_proficient_saves_include_prof_bonus(self):
        """Saves listed on the base category include the proficiency bonus."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        proficient = information_logic.BASE_CATEGORIES[BASE]["saving_throws"]
        for ability in proficient:
            self.assertEqual(
                info["saving_throws"][ability],
                FAKE_MODIFIERS[ability] + 3,
            )

    def test_values_are_ints(self):
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        for v in info["saving_throws"].values():
            self.assertIsInstance(v, int)

    def test_different_base_gives_different_proficient_saves(self):
        """Switching base category changes which saves appear."""
        melee = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, "Melee")
        caster = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, "Full Caster")
        # Melee: STR, CON -- Full Caster: INT, WIS -- disjoint sets
        self.assertEqual(set(melee["saving_throws"].keys()), {"STR", "CON"})
        self.assertEqual(set(caster["saving_throws"].keys()), {"INT", "WIS"})


# ---------------------------------------------------------------------------
# generate_information - size.
# ---------------------------------------------------------------------------

class TestSize(unittest.TestCase):

    def test_always_present(self):
        """Size is on every stat block."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIn("size", info)

    def test_medium_race(self):
        """Human is Medium."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["size"], "Medium")

    def test_small_race(self):
        """Halfling is Small."""
        info = generate_information("Halfling", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertEqual(info["size"], "Small")

    def test_returns_string(self):
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIsInstance(info["size"], str)


# ---------------------------------------------------------------------------
# generate_information - out-of-combat traits.
# ---------------------------------------------------------------------------

class TestTraits(unittest.TestCase):

    def test_environment_traits(self):
        """Environment traits are stored as a name to description dict."""
        info = generate_information("Human", None, None, None, "Mountain", FAKE_MODIFIERS, CR, BASE)
        expected = {t["name"]: t["description"]
                    for t in information_logic.ENVIRONMENTS["Mountain"]["traits"]}
        self.assertEqual(info["environmental_traits"], expected)

    def test_environment_trait_shape_is_dict(self):
        info = generate_information("Human", None, None, None, "Mountain", FAKE_MODIFIERS, CR, BASE)
        self.assertIsInstance(info["environmental_traits"], dict)
        for value in info["environmental_traits"].values():
            self.assertIsInstance(value, str)

    def test_role_traits(self):
        """A role kit with a trait surfaces it under role_traits."""
        info = generate_information("Human", None, None, ["Pirate"], None, FAKE_MODIFIERS, CR, BASE)
        expected = {t["name"]: t["description"]
                    for t in information_logic.ROLE_KITS["Pirate"]["traits"]}
        self.assertEqual(info["role_traits"], expected)

    def test_role_kit_without_traits_omits_key(self):
        """A role kit that has only proficiencies adds no role_traits key."""
        info = generate_information("Human", None, None, ["Sailor"], None, FAKE_MODIFIERS, CR, BASE)
        self.assertNotIn("role_traits", info)
        self.assertIn("proficiencies", info)

    def test_environment_traits_absent_when_none(self):
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
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
            info = generate_information("Human", None, None, ["_R"], None, FAKE_MODIFIERS, CR, BASE)
        self.assertNotIn("senses", info)
        self.assertNotIn("immunities", info)
        self.assertNotIn("Flying", info.get("speed", {}))


# ---------------------------------------------------------------------------
# Shape and empty-section guarantees.
# ---------------------------------------------------------------------------

class TestStructure(unittest.TestCase):

    def test_mandatory_keys_always_present(self):
        """Passive Perception, saving throws, and size are always in the output."""
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIn("passive_perception", info)
        self.assertIn("saving_throws", info)
        self.assertIn("size", info)

    def test_no_empty_sections(self):
        """No optional section is ever present as an empty container."""
        info = generate_information("Elf", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        for value in info.values():
            self.assertTrue(value)

    def test_returns_dict(self):
        info = generate_information("Human", None, None, None, None, FAKE_MODIFIERS, CR, BASE)
        self.assertIsInstance(info, dict)


# ---------------------------------------------------------------------------
# resolve_title - the NPC title precedence ladder.
#
# These use controlled fake kits patched into the real tables so the ladder
# logic (tier thresholds, ordering, tie-breaking) is tested independently of
# whatever weights the real kit data happens to carry.
# ---------------------------------------------------------------------------

FAKE_KITS = {
    "Heavy":  {"display_name": "Heavy",  "display_name_weight": 10},
    "Light":  {"display_name": "Light",  "display_name_weight": 5},
    "Mystic": {"display_name": "Mystic", "display_name_weight": 8},
    "Swift":  {"display_name": "Swift",  "display_name_weight": 3},
    "Rogue":  {"display_name": "Rogue",  "display_name_weight": 6},
    "Bard":   {"display_name": "Bard",   "display_name_weight": 4},
}


class TestResolveTitle(unittest.TestCase):

    def setUp(self):
        for table in (
            information_logic.COMBAT_KITS,
            information_logic.MAGIC_KITS,
            information_logic.ROLE_KITS,
        ):
            patcher = mock.patch.dict(table, FAKE_KITS)
            patcher.start()
            self.addCleanup(patcher.stop)

    # Tier 1 - nothing selected.
    def test_no_kits_is_commoner(self):
        self.assertEqual(resolve_title(None, None, None), "Commoner")

    def test_empty_lists_is_commoner(self):
        self.assertEqual(resolve_title([], [], []), "Commoner")

    # Tier 2 - mythical thresholds.
    def test_two_maxed_specialties_is_mythical(self):
        self.assertEqual(
            resolve_title(None, ["Heavy", "Light", "Mystic"], ["Swift", "Rogue", "Bard"]),
            "Mythical Conjuration",
        )

    def test_all_three_at_two_is_mythical(self):
        self.assertEqual(
            resolve_title(["Rogue", "Bard"], ["Heavy", "Light"], ["Mystic", "Swift"]),
            "Mythical Conjuration",
        )

    # Tier 3 - single maxed specialty.
    def test_three_combat_is_master_of_arms(self):
        self.assertEqual(
            resolve_title(None, ["Heavy", "Light", "Mystic"], None),
            "Master of Arms",
        )

    def test_three_magic_is_magus(self):
        self.assertEqual(
            resolve_title(None, None, ["Heavy", "Light", "Mystic"]),
            "Magus",
        )

    def test_three_role_is_jack(self):
        self.assertEqual(
            resolve_title(["Heavy", "Light", "Mystic"], None, None),
            "Jack of All Trades",
        )

    # Tier 4 - weight ordering.
    def test_single_combat_kit_returns_its_name(self):
        self.assertEqual(resolve_title(None, ["Light"], None), "Light")

    def test_combat_and_magic_ordered_by_weight(self):
        # Heavy (10) beats Mystic (8), so Heavy leads.
        self.assertEqual(resolve_title(None, ["Heavy"], ["Mystic"]), "Heavy Mystic")

    def test_combat_and_magic_lower_weight_combat_follows(self):
        # Mystic (8) beats Swift (3), so Mystic leads.
        self.assertEqual(resolve_title(None, ["Swift"], ["Mystic"]), "Mystic Swift")

    def test_two_combat_kits_ordered_by_weight(self):
        # Heavy (10) beats Light (5).
        self.assertEqual(resolve_title(None, ["Heavy", "Light"], None), "Heavy Light")

    def test_tie_keeps_first_arg_ahead(self):
        # Two kits with equal weight: first arg wins.
        kits = {"A": {"display_name": "A", "display_name_weight": 5},
                "B": {"display_name": "B", "display_name_weight": 5}}
        with mock.patch.dict(information_logic.COMBAT_KITS, kits):
            self.assertEqual(resolve_title(None, ["A", "B"], None), "A B")

    # Tier 5 - role only.
    def test_single_role_kit_returns_its_name(self):
        self.assertEqual(resolve_title(["Rogue"], None, None), "Rogue")

    def test_two_role_kits_ordered_by_weight(self):
        # Rogue (6) beats Bard (4).
        self.assertEqual(resolve_title(["Rogue", "Bard"], None, None), "Rogue Bard")


# ---------------------------------------------------------------------------
# Name and personality generation.
# ---------------------------------------------------------------------------

FAKE_NAMES = {
    "Masculine": {
        "TestRace": {"First": ["Mfirst"], "Last": ["Mlast"]},
        "Multi":    {"First": ["A", "B"], "Last": ["X", "Y"]},
    },
    "Feminine": {
        "TestRace": {"First": ["Ffirst"], "Last": ["Flast"]},
        "Multi":    {"First": ["A", "B"], "Last": ["X", "Y"]},
    },
    "Neutral": {
        "TestRace": {"First": ["Nfirst"], "Last": ["Nlast"]},
        "Multi":    {"First": ["A", "B"], "Last": ["X", "Y"]},
    },
}

FAKE_PERSONALITIES = {
    "Brave":    {"entries": [{"description": "Stares down danger."}]},
    "Cowardly": {"entries": [{"description": "Flees at the first sign."},
                             {"description": "Hides behind others."}]},
}


class TestGenerateName(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.dict(information_logic.NAMES, FAKE_NAMES)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_uses_given_gender_and_race(self):
        self.assertEqual(generate_name("TestRace", "Masculine"), "Mfirst Mlast")

    def test_feminine_uses_feminine_lists(self):
        self.assertEqual(generate_name("TestRace", "Feminine"), "Ffirst Flast")

    def test_gender_defaults_to_neutral(self):
        self.assertEqual(generate_name("TestRace", None), "Nfirst Nlast")

    def test_joins_first_and_last_from_lists(self):
        # Multi has two of each; the result must be a valid first + last pair.
        name = generate_name("Multi", "Masculine")
        first, last = name.split(" ")
        self.assertIn(first, ["A", "B"])
        self.assertIn(last, ["X", "Y"])

    def test_returns_single_space_separated_string(self):
        name = generate_name("TestRace", "Masculine")
        self.assertIsInstance(name, str)
        self.assertEqual(name.count(" "), 1)


class TestGeneratePersonality(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.dict(information_logic.PERSONALITIES, FAKE_PERSONALITIES)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_none_returns_none(self):
        self.assertIsNone(generate_personality(None))

    def test_returns_description_string(self):
        self.assertEqual(generate_personality("Brave"), "Stares down danger.")

    def test_picks_from_entries(self):
        result = generate_personality("Cowardly")
        self.assertIn(result, ["Flees at the first sign.", "Hides behind others."])

    def test_returns_str_for_category(self):
        self.assertIsInstance(generate_personality("Brave"), str)


class TestEnumerators(unittest.TestCase):

    def setUp(self):
        for table, fakes in (
            (information_logic.NAMES, FAKE_NAMES),
            (information_logic.PERSONALITIES, FAKE_PERSONALITIES),
        ):
            patcher = mock.patch.dict(table, fakes)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_name_races_sorted_from_neutral(self):
        self.assertEqual(enum_name_races(), sorted(information_logic.NAMES["Neutral"].keys()))

    def test_personality_options_sorted(self):
        self.assertEqual(enum_personality_options(), sorted(information_logic.PERSONALITIES.keys()))


if __name__ == "__main__":
    unittest.main(verbosity=2)