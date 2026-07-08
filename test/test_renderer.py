import unittest

from generator import generate_npc, Selections
from renderer import (
    RenderedNPC,
    render_as_text,
    _format_mod,
    _format_speed,
    _wrap,
    _wrap_entries,
    _join_blocks,
    _header,
    _defence,
    _stats,
    _saving_throws,
    _skills,
    _senses,
    _resistances,
    _languages,
    _challenge,
    _traits,
    _section_header,
    _multiattack,
    _actions,
    _spells,
    _casting_rank,
    _bonus_actions,
    _reactions,
    WIDTH,
    DIVIDER,
    ABILITY_ORDER,
    MA_COUNT_WORDS,
)


# ---------------------------------------------------------------------------
# Shared fixtures.
#
# Stats and modifiers use distinct values per ability so a wrong-ability
# lookup produces a visibly wrong number, matching the convention in the
# other suites. make_npc builds the minimal seven-key dict the renderer
# contract requires; tests override only the piece they exercise.
# ---------------------------------------------------------------------------

FAKE_STATS = {"STR": 17, "DEX": 13, "CON": 14, "INT": 11, "WIS": 12, "CHA": 8}
FAKE_MODS = {"STR": 3, "DEX": 1, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1}


def make_npc(**overrides) -> dict:
    npc = {
        "stats": dict(FAKE_STATS),
        "modifiers": dict(FAKE_MODS),
        "ac": 15,
        "hp": {"hp": 45, "dice_string": "7d8 + 14"},
        "action_data": None,
        "title": "Commoner",
        "information": {
            "size": "Medium",
            "speed": {"Walking": 30},
            "saving_throws": {"STR": 6, "CON": 5},
            "passive_perception": 11,
            "xp": 1800,
        },
    }
    npc.update(overrides)
    return npc


def make_rendered(npc: dict | None = None, **overrides) -> RenderedNPC:
    fields = {
        "npc": npc if npc is not None else make_npc(),
        "name": "Test Name",
        "cr": "5",
        "race": "Human",
        "personality": "Short and testable.",
        "alignment": "True Neutral",
        "languages": ["Common"],
    }
    fields.update(overrides)
    return RenderedNPC(**fields)


def entries_of(lines: list[str]) -> list[str]:
    """Rebuilds original entry strings from wrapped, blank-separated lines.
    Lets tests assert on content without hardcoding where textwrap chose
    to break, so a WIDTH change does not invalidate every assertion."""
    entries, current = [], []
    for line in lines:
        if line == "":
            entries.append(" ".join(current))
            current = []
        else:
            current.append(line)
    if current:
        entries.append(" ".join(current))
    return entries


# ---------------------------------------------------------------------------
# Module constants - the invariants the layout depends on.
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):

    def test_divider_width_matches_width(self):
        """DIVIDER is derived from WIDTH; if they drift the block renders
        ragged, which is the exact bug the single knob exists to prevent."""
        self.assertEqual(len(DIVIDER), WIDTH)

    def test_ability_order_is_canonical(self):
        self.assertEqual(ABILITY_ORDER, ["STR", "DEX", "CON", "INT", "WIS", "CHA"])


# ---------------------------------------------------------------------------
# Pure formatters - fully synthetic input.
# ---------------------------------------------------------------------------

class TestFormatMod(unittest.TestCase):

    def test_positive_gets_plus(self):
        self.assertEqual(_format_mod(3), "+3")

    def test_zero_gets_plus(self):
        """+0 is deliberate: it tells the DM the modifier was applied even
        when it adds nothing, and avoids missing-modifier bug reports."""
        self.assertEqual(_format_mod(0), "+0")

    def test_negative_keeps_minus(self):
        self.assertEqual(_format_mod(-1), "-1")


class TestFormatSpeed(unittest.TestCase):

    def test_walking_prints_bare(self):
        """Walking has no label on a stat block; the Speed prefix is the
        line's job, not the entry's."""
        self.assertEqual(_format_speed({"Walking": 30}), "30ft")

    def test_other_types_get_abbreviated_label(self):
        self.assertEqual(_format_speed({"Swimming": 30}), "Swim 30ft")
        self.assertEqual(_format_speed({"Flying": 60}), "Fly 60ft")

    def test_multiple_types_preserve_dict_order(self):
        """Walking-first is a data-layer invariant; the formatter must not
        re-sort and hide a data file that breaks it."""
        result = _format_speed({"Walking": 30, "Climbing": 20})
        self.assertEqual(result, "30ft Climb 20ft")

    def test_unknown_type_raises_key_error(self):
        """Loud failure on an unmapped movement type, consistent with the
        project's data validation stance."""
        with self.assertRaises(KeyError):
            _format_speed({"Teleporting": 30})


class TestWrapHelpers(unittest.TestCase):

    def test_wrap_respects_width(self):
        lines = _wrap("word " * 40)
        for line in lines:
            self.assertLessEqual(len(line), WIDTH)

    def test_wrap_short_text_is_single_line(self):
        self.assertEqual(_wrap("short"), ["short"])

    def test_wrap_entries_blank_between_entries(self):
        """The blank separator is what keeps wrapped prose blocks from
        blurring into one mass; losing it is a rendering regression."""
        lines = _wrap_entries(["first entry", "second entry"])
        self.assertEqual(lines, ["first entry", "", "second entry"])

    def test_wrap_entries_no_leading_or_trailing_blank(self):
        lines = _wrap_entries(["only entry"])
        self.assertEqual(lines, ["only entry"])

    def test_wrap_entries_rejoins_to_original(self):
        """Wrapping must not lose or reorder words."""
        long_entry = "alpha " * 30
        lines = _wrap_entries([long_entry.strip()])
        self.assertEqual(entries_of(lines), [long_entry.strip()])

    def test_join_blocks_blank_between_nonempty(self):
        self.assertEqual(_join_blocks(["a"], ["b"]), ["a", "", "b"])

    def test_join_blocks_skips_empty_blocks(self):
        """Empty sections contribute nothing; otherwise sparse NPCs grow
        stray blank lines between absent sections."""
        self.assertEqual(_join_blocks(["a"], [], ["b"]), ["a", "", "b"])

    def test_join_blocks_all_empty_returns_empty(self):
        self.assertEqual(_join_blocks([], []), [])


# ---------------------------------------------------------------------------
# Header and defence.
# ---------------------------------------------------------------------------

class TestHeader(unittest.TestCase):

    def test_two_lines(self):
        lines = _header(make_rendered())
        self.assertEqual(len(lines), 2)

    def test_name_line(self):
        lines = _header(make_rendered(name="Grug"))
        self.assertEqual(lines[0], "Grug")

    def test_type_line_composition(self):
        """Size from information, race and alignment from the dataclass,
        Humanoid hardcoded for v1.0."""
        rendered = make_rendered(race="Elf", alignment="Neutral Evil")
        self.assertEqual(_header(rendered)[1], "Medium Humanoid (Elf), Neutral Evil")


class TestDefence(unittest.TestCase):

    def setUp(self):
        self.lines = _defence(make_rendered())

    def test_three_lines(self):
        self.assertEqual(len(self.lines), 3)

    def test_armour_class(self):
        self.assertEqual(self.lines[0], "Armour Class 15")

    def test_hit_points_with_dice_string(self):
        self.assertEqual(self.lines[1], "Hit Points 45 (7d8 + 14)")

    def test_speed_prefix_applied_once(self):
        """The Speed label lives on the line, not in the formatter; a
        second copy inside _format_speed produced 'Speed Speed' once."""
        self.assertEqual(self.lines[2], "Speed 30ft")


# ---------------------------------------------------------------------------
# Ability row.
# ---------------------------------------------------------------------------

class TestStats(unittest.TestCase):

    def setUp(self):
        self.lines = _stats(make_rendered())

    def test_two_rows(self):
        self.assertEqual(len(self.lines), 2)

    def test_columns_in_canonical_order_not_dict_order(self):
        """The stats dict arrives in priority order, which varies by base
        category; the rendered row must always read STR..CHA."""
        header = self.lines[0]
        positions = [header.index(stat) for stat in ABILITY_ORDER]
        self.assertEqual(positions, sorted(positions))

    def test_rows_are_equal_width(self):
        # Six columns at width 7 = 42 characters per row.
        self.assertEqual(len(self.lines[0]), 42)
        self.assertEqual(len(self.lines[1]), 42)

    def test_cell_holds_score_and_signed_mod(self):
        # STR 17 with mod +3 renders as the single centred cell "17(+3)".
        self.assertIn("17(+3)", self.lines[1])

    def test_negative_mod_cell(self):
        # CHA 8 with mod -1.
        self.assertIn("8(-1)", self.lines[1])

    def test_missing_stat_raises(self):
        """A missing ability is a generation bug; the subscript must fail
        loud rather than render a fake zero."""
        npc = make_npc(stats={"STR": 17})
        with self.assertRaises(KeyError):
            _stats(make_rendered(npc))


# ---------------------------------------------------------------------------
# Information cluster - mandatory lines.
# ---------------------------------------------------------------------------

class TestSavingThrows(unittest.TestCase):

    def test_line_format(self):
        lines = _saving_throws(make_rendered())
        self.assertEqual(lines, ["Saving Throws STR +6, CON +5"])

    def test_preserves_stored_order(self):
        """Base categories list the primary save first, which is how the
        bigger modifier leads; the renderer must not re-sort."""
        npc = make_npc()
        npc["information"]["saving_throws"] = {"WIS": 4, "DEX": 3}
        lines = _saving_throws(make_rendered(npc))
        self.assertEqual(lines, ["Saving Throws WIS +4, DEX +3"])


class TestChallenge(unittest.TestCase):

    def test_line_format(self):
        lines = _challenge(make_rendered())
        self.assertEqual(lines, ["Challenge 5 (1,800xp)"])

    def test_large_xp_gets_thousands_separator(self):
        """XP is stored raw in the data layer; the comma is a render
        concern and must be applied here."""
        npc = make_npc()
        npc["information"]["xp"] = 25000
        lines = _challenge(make_rendered(npc, cr="20"))
        self.assertEqual(lines, ["Challenge 20 (25,000xp)"])


class TestLanguages(unittest.TestCase):

    def test_joins_languages(self):
        rendered = make_rendered(languages=["Common", "Elvish"])
        self.assertEqual(_languages(rendered), ["Languages Common, Elvish"])

    def test_single_language(self):
        """No guard by contract: the UI layer guarantees at least Common,
        so the renderer renders whatever it is handed."""
        self.assertEqual(_languages(make_rendered()), ["Languages Common"])


# ---------------------------------------------------------------------------
# Information cluster - optional lines.
# ---------------------------------------------------------------------------

class TestSkills(unittest.TestCase):

    def test_absent_key_returns_empty(self):
        """proficiencies is an absent key when the NPC has none; a
        subscript here was the original bug this guard replaced."""
        self.assertEqual(_skills(make_rendered()), [])

    def test_present_renders_line(self):
        npc = make_npc()
        npc["information"]["proficiencies"] = {"Stealth": 4, "Perception": 4}
        lines = _skills(make_rendered(npc))
        self.assertEqual(lines, ["Skills Stealth +4, Perception +4"])


class TestSenses(unittest.TestCase):

    def test_no_senses_still_renders_passive_perception(self):
        """Passive Perception is mandatory; the senses prefix is optional.
        The line must exist even when the senses key is absent."""
        lines = _senses(make_rendered())
        self.assertEqual(lines, ["Senses Passive Perception 11"])

    def test_senses_prefix_then_passive_perception(self):
        npc = make_npc()
        npc["information"]["senses"] = {"Darkvision": 60}
        lines = _senses(make_rendered(npc))
        self.assertEqual(lines, ["Senses Darkvision 60ft, Passive Perception 11"])

    def test_multiple_senses_joined(self):
        npc = make_npc()
        npc["information"]["senses"] = {"Darkvision": 120, "Tremorsense": 30}
        lines = _senses(make_rendered(npc))
        self.assertEqual(
            lines,
            ["Senses Darkvision 120ft, Tremorsense 30ft, Passive Perception 11"],
        )


class TestResistances(unittest.TestCase):

    def test_absent_key_returns_empty(self):
        self.assertEqual(_resistances(make_rendered(), "resistances", "Resistances"), [])

    def test_present_renders_with_label(self):
        npc = make_npc()
        npc["information"]["resistances"] = ["Fire", "Cold"]
        lines = _resistances(make_rendered(npc), "resistances", "Resistances")
        self.assertEqual(lines, ["Resistances Fire, Cold"])

    def test_parameterized_across_all_three_lines(self):
        """One helper serves all three damage lines; the key and label
        arrive as data, so each pairing must resolve independently."""
        npc = make_npc()
        npc["information"]["immunities"] = ["Poison"]
        npc["information"]["vulnerabilities"] = ["Radiant"]
        rendered = make_rendered(npc)
        self.assertEqual(_resistances(rendered, "immunities", "Immunities"), ["Immunities Poison"])
        self.assertEqual(_resistances(rendered, "vulnerabilities", "Vulnerabilities"), ["Vulnerabilities Radiant"])


# ---------------------------------------------------------------------------
# Traits - the three-source merge.
# ---------------------------------------------------------------------------

class TestTraits(unittest.TestCase):

    def test_all_sources_empty_returns_empty(self):
        self.assertEqual(_traits(make_rendered()), [])

    def test_none_action_data_does_not_crash(self):
        """action_data is None on a no-actions NPC; the or-{} guard is
        what keeps the .get from raising AttributeError."""
        npc = make_npc(action_data=None)
        npc["information"]["role_traits"] = {"Steady": "Never surprised."}
        entries = entries_of(_traits(make_rendered(npc)))
        self.assertEqual(entries, ["Steady. Never surprised."])

    def test_merges_all_three_sources(self):
        npc = make_npc(action_data={"traits": {"Brave": "No fear."}})
        npc["information"]["environmental_traits"] = {"Sure Footed": "No prone."}
        npc["information"]["role_traits"] = {"Sea Legs": "No slipping."}
        entries = entries_of(_traits(make_rendered(npc)))
        self.assertEqual(len(entries), 3)
        self.assertIn("Brave. No fear.", entries)
        self.assertIn("Sure Footed. No prone.", entries)
        self.assertIn("Sea Legs. No slipping.", entries)

    def test_reads_environmental_traits_key(self):
        """The key is environmental_traits; a shortened environment_traits
        lookup silently dropped the section once."""
        npc = make_npc()
        npc["information"]["environmental_traits"] = {"Hold Breath": "One hour."}
        self.assertNotEqual(_traits(make_rendered(npc)), [])

    def test_long_trait_wraps_within_width(self):
        npc = make_npc(action_data={"traits": {"Wordy": "description " * 20}})
        for line in _traits(make_rendered(npc)):
            self.assertLessEqual(len(line), WIDTH)


# ---------------------------------------------------------------------------
# Section headers.
# ---------------------------------------------------------------------------

class TestSectionHeader(unittest.TestCase):

    def test_no_matching_key_returns_empty(self):
        self.assertEqual(_section_header(make_rendered(), ["weapons"], "Actions"), [])

    def test_none_action_data_returns_empty(self):
        npc = make_npc(action_data=None)
        self.assertEqual(_section_header(make_rendered(npc), ["weapons"], "Actions"), [])

    def test_any_key_triggers_header(self):
        """Actions is gated by any of several keys; a caster with spells
        but no weapons must still get the heading."""
        npc = make_npc(action_data={"spells": {}})
        lines = _section_header(make_rendered(npc), ["weapons", "spells"], "Actions")
        self.assertEqual(lines, ["", "Actions", DIVIDER])


# ---------------------------------------------------------------------------
# Multiattack - the branch matrix.
# ---------------------------------------------------------------------------

def make_multiattack_npc(weapons: list[str], has_shield: bool, count: int = 2) -> dict:
    return make_npc(action_data={
        "multiattack": {
            "type": "any_combination",
            "count": count,
            "weapons": weapons,
            "has_shield": has_shield,
        },
    })


class TestMultiattack(unittest.TestCase):

    def test_absent_returns_empty(self):
        self.assertEqual(_multiattack(make_rendered()), [])

    def test_single_weapon(self):
        npc = make_multiattack_npc(["Longsword"], has_shield=False)
        entries = entries_of(_multiattack(make_rendered(npc)))
        self.assertEqual(entries, ["Multiattack. The character makes two attacks with their Longsword."])

    def test_multiple_weapons_any_combination(self):
        npc = make_multiattack_npc(["Longsword", "Longbow"], has_shield=False, count=3)
        entries = entries_of(_multiattack(make_rendered(npc)))
        self.assertEqual(
            entries,
            ["Multiattack. The character makes three attacks, which can be any combination of the following weapons: Longsword, Longbow."],
        )

    def test_shield_suffix_on_single_weapon(self):
        """The suffix is appended independently of the weapon-count branch;
        baking it into select branches dropped it from this case once."""
        npc = make_multiattack_npc(["Longsword", "Shield Bash"], has_shield=True)
        entries = entries_of(_multiattack(make_rendered(npc)))
        self.assertEqual(
            entries,
            ["Multiattack. The character makes two attacks with their Longsword. It can replace one attack with a use of Shield Bash."],
        )

    def test_shield_bash_filtered_from_weapon_join(self):
        """Shield Bash rides in the weapons list and in has_shield; without
        the filter it appears in the combination list and the suffix."""
        npc = make_multiattack_npc(["Longsword", "Longbow", "Shield Bash"], has_shield=True)
        text = entries_of(_multiattack(make_rendered(npc)))[0]
        self.assertIn("Longsword, Longbow.", text)
        # Exactly one mention, in the suffix.
        self.assertEqual(text.count("Shield Bash"), 1)

    def test_shield_only_npc(self):
        """Shield Bash as the sole weapon skips the replace-suffix since
        there is nothing to replace it with."""
        npc = make_multiattack_npc(["Shield Bash"], has_shield=True)
        entries = entries_of(_multiattack(make_rendered(npc)))
        self.assertEqual(entries, ["Multiattack. The character makes two attacks with their Shield Bash."])

    def test_count_rendered_as_word(self):
        npc = make_multiattack_npc(["Longsword"], has_shield=False, count=4)
        self.assertIn("four attacks", entries_of(_multiattack(make_rendered(npc)))[0])

    def test_count_beyond_map_falls_back_to_digits(self):
        self.assertEqual(MA_COUNT_WORDS.get(11, str(11)), "11")


# ---------------------------------------------------------------------------
# Weapon attack lines.
# ---------------------------------------------------------------------------

def make_weapon(**overrides) -> dict:
    weapon = {
        "weapon_type": "melee",
        "num_of_die": 1,
        "die_size": 8,
        "damage_type": "slashing",
        "to_hit": 6,
        "damage_bonus": 3,
        "damage_avg": 7,
        "reach": 5,
        "range_min": None,
        "range_max": None,
        "targets": 1,
    }
    weapon.update(overrides)
    return weapon


class TestActions(unittest.TestCase):

    def test_absent_weapons_returns_empty(self):
        self.assertEqual(_actions(make_rendered()), [])

    def test_melee_line_2024_phrasing(self):
        npc = make_npc(action_data={"weapons": {"Longsword": make_weapon()}})
        entries = entries_of(_actions(make_rendered(npc)))
        self.assertEqual(
            entries,
            ["Longsword. Melee Attack Roll: +6, reach 5 ft. Hit: 7 (1d8 + 3) Slashing damage."],
        )

    def test_ranged_line_uses_range_not_reach(self):
        weapon = make_weapon(weapon_type="ranged", die_size=8, to_hit=5,
                             damage_bonus=2, damage_avg=6, damage_type="piercing",
                             range_min=150, range_max=600)
        npc = make_npc(action_data={"weapons": {"Longbow": weapon}})
        entries = entries_of(_actions(make_rendered(npc)))
        self.assertEqual(
            entries,
            ["Longbow. Ranged Attack Roll: +5, range 150/600 ft. Hit: 6 (1d8 + 2) Piercing damage."],
        )

    def test_thrown_line_carries_both_reach_and_range(self):
        weapon = make_weapon(weapon_type="thrown", die_size=4, to_hit=5,
                             damage_bonus=2, damage_avg=4, damage_type="piercing",
                             range_min=20, range_max=60)
        npc = make_npc(action_data={"weapons": {"Dagger": weapon}})
        text = entries_of(_actions(make_rendered(npc)))[0]
        self.assertIn("Melee or Ranged Attack Roll", text)
        self.assertIn("reach 5 ft. or range 20/60 ft.", text)

    def test_zero_bonus_kept_as_plus_zero(self):
        """Deliberate product decision: + 0 is ugly but stops missing-
        modifier bug reports from DMs."""
        weapon = make_weapon(damage_bonus=0, damage_avg=4)
        npc = make_npc(action_data={"weapons": {"Club": weapon}})
        self.assertIn("(1d8 + 0)", entries_of(_actions(make_rendered(npc)))[0])

    def test_negative_bonus_renders_minus(self):
        """A hardcoded plus sign produced '+ -1' here once; the dice
        expression must carry its own sign."""
        weapon = make_weapon(damage_bonus=-1, damage_avg=3)
        npc = make_npc(action_data={"weapons": {"Club": weapon}})
        self.assertIn("(1d8 - 1)", entries_of(_actions(make_rendered(npc)))[0])

    def test_damage_type_capitalized(self):
        """Data stores lowercase damage types; 2024 blocks print them
        capitalized, so the transform happens at render."""
        npc = make_npc(action_data={"weapons": {"Longsword": make_weapon()}})
        text = entries_of(_actions(make_rendered(npc)))[0]
        self.assertIn("Slashing damage.", text)
        self.assertNotIn("slashing", text)

    def test_unknown_weapon_type_raises_value_error(self):
        """The generator only emits three types; anything else is a data
        or generation bug that must fail loud, not vanish silently."""
        weapon = make_weapon(weapon_type="psychic")
        npc = make_npc(action_data={"weapons": {"Oddity": weapon}})
        with self.assertRaises(ValueError):
            _actions(make_rendered(npc))

    def test_multiple_weapons_blank_separated(self):
        npc = make_npc(action_data={"weapons": {
            "Longsword": make_weapon(),
            "Club": make_weapon(die_size=4, damage_avg=5),
        }})
        entries = entries_of(_actions(make_rendered(npc)))
        self.assertEqual(len(entries), 2)


# ---------------------------------------------------------------------------
# Spellcasting.
# ---------------------------------------------------------------------------

def make_spells_npc() -> dict:
    return make_npc(action_data={"spells": {
        "spells_list": {
            "Fire Bolt": {"level": 0, "casting_amount": "at will"},
            "Shield": {"level": 1, "casting_amount": "3/day"},
            "Misty Step": {"level": 2, "casting_amount": "3/day"},
            "Fireball": {"level": 3, "casting_amount": "1/day"},
        },
        "spell_save_dc": 14,
        "spell_attack_bonus": 6,
        "spell_budget": 999,
        "spellcasting_stat": "INT",
    }})


class TestSpells(unittest.TestCase):

    def test_absent_returns_empty(self):
        self.assertEqual(_spells(make_rendered()), [])

    def test_intro_carries_stat_dc_and_bonus(self):
        text = " ".join(_spells(make_rendered(make_spells_npc())))
        self.assertIn("using Intelligence as their spellcasting ability", text)
        self.assertIn("spell save DC 14", text)
        self.assertIn("+6 to hit with spell attacks", text)

    def test_stat_abbreviation_expanded(self):
        """The prose wants Intelligence, not the raw INT the data carries;
        an unmapped stat must raise, not leak the abbreviation."""
        text = " ".join(_spells(make_rendered(make_spells_npc())))
        self.assertNotIn("INT", text)

    def test_buckets_grouped_by_frequency(self):
        text = " ".join(_spells(make_rendered(make_spells_npc())))
        self.assertIn("3/Day Each: Shield, Misty Step", text)

    def test_at_will_label_no_each(self):
        """Official phrasing: At Will has no Each, X/Day buckets do."""
        text = " ".join(_spells(make_rendered(make_spells_npc())))
        self.assertIn("At Will: Fire Bolt", text)
        self.assertNotIn("At Will Each", text)

    def test_buckets_ordered_most_available_first(self):
        text = " ".join(_spells(make_rendered(make_spells_npc())))
        at_will = text.index("At Will:")
        three_day = text.index("3/Day Each:")
        one_day = text.index("1/Day Each:")
        self.assertLess(at_will, three_day)
        self.assertLess(three_day, one_day)

    def test_blank_line_after_intro(self):
        lines = _spells(make_rendered(make_spells_npc()))
        self.assertIn("", lines)


class TestCastingRank(unittest.TestCase):

    def test_at_will_outranks_everything(self):
        self.assertGreater(_casting_rank("at will"), _casting_rank("9/day"))

    def test_numeric_rank_from_prefix(self):
        self.assertEqual(_casting_rank("3/day"), 3)


# ---------------------------------------------------------------------------
# Bonus actions and reactions - the pass-through dumps.
# ---------------------------------------------------------------------------

class TestBonusActionsAndReactions(unittest.TestCase):

    def test_absent_returns_empty(self):
        self.assertEqual(_bonus_actions(make_rendered()), [])
        self.assertEqual(_reactions(make_rendered()), [])

    def test_values_are_descriptions_not_objects(self):
        """These dicts are {name: description}; indexing the value with
        ['description'] crashed here once because the value is the string."""
        npc = make_npc(action_data={
            "bonus_actions": {"Dash": "Move again."},
            "reactions": {"Parry": "Add 2 to AC."},
        })
        rendered = make_rendered(npc)
        self.assertEqual(entries_of(_bonus_actions(rendered)), ["Dash. Move again."])
        self.assertEqual(entries_of(_reactions(rendered)), ["Parry. Add 2 to AC."])


# ---------------------------------------------------------------------------
# Full assembly - render_as_text end to end on synthetic NPCs.
# ---------------------------------------------------------------------------

class TestRenderAsText(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(render_as_text(make_rendered()), str)

    def test_bare_npc_has_no_adjacent_dividers(self):
        """The empty traits and action sections once left two dividers
        stacked with nothing between them."""
        output = render_as_text(make_rendered())
        self.assertNotIn(f"{DIVIDER}\n{DIVIDER}", output)

    def test_no_double_blank_lines_anywhere(self):
        npc = make_spells_npc()
        npc["action_data"]["weapons"] = {"Longsword": make_weapon()}
        output = render_as_text(make_rendered(npc))
        self.assertNotIn("\n\n\n", output)

    def test_info_cluster_order(self):
        npc = make_npc()
        npc["information"]["proficiencies"] = {"Stealth": 4}
        npc["information"]["resistances"] = ["Fire"]
        npc["information"]["senses"] = {"Darkvision": 60}
        output = render_as_text(make_rendered(npc))
        # 2024 order: saves, skills, damage lines, senses, languages, challenge.
        order = [
            output.index("Saving Throws"),
            output.index("Skills"),
            output.index("Resistances"),
            output.index("Senses"),
            output.index("Languages"),
            output.index("Challenge"),
        ]
        self.assertEqual(order, sorted(order))

    def test_actions_heading_present_with_weapons(self):
        npc = make_npc(action_data={"weapons": {"Longsword": make_weapon()}})
        output = render_as_text(make_rendered(npc))
        self.assertIn("Actions", output)
        self.assertLess(output.index("Actions"), output.index("Longsword."))

    def test_actions_heading_present_with_spells_only(self):
        """A pure caster has no weapons; the heading must still appear."""
        output = render_as_text(make_rendered(make_spells_npc()))
        self.assertIn("Actions", output)
        self.assertIn("Spellcasting.", output)

    def test_no_actions_heading_on_bare_npc(self):
        output = render_as_text(make_rendered())
        self.assertNotIn("Actions", output)

    def test_reactions_heading_only_with_reactions(self):
        npc = make_npc(action_data={"reactions": {"Parry": "Add 2 to AC."}})
        output = render_as_text(make_rendered(npc))
        self.assertIn("Reactions", output)
        self.assertNotIn("Bonus Actions", output)

    def test_personality_is_final_content(self):
        output = render_as_text(make_rendered(personality="Gruff but kind."))
        self.assertTrue(output.rstrip().endswith("Gruff but kind."))

    def test_personality_after_final_divider(self):
        output = render_as_text(make_rendered(personality="Gruff but kind."))
        last_divider = output.rindex(DIVIDER)
        self.assertLess(last_divider, output.index("Gruff but kind."))

    def test_multiattack_precedes_weapon_lines(self):
        npc = make_multiattack_npc(["Longsword"], has_shield=False)
        npc["action_data"]["weapons"] = {"Longsword": make_weapon()}
        output = render_as_text(make_rendered(npc))
        self.assertLess(output.index("Multiattack."), output.index("Longsword. Melee"))


# ---------------------------------------------------------------------------
# Integration - a real generated NPC through the full pipeline. Anchored to
# the same Human CR5 Melee build the generator suite uses, so a failure here
# with the unit tests green points at the seam, not the pieces.
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def setUp(self):
        npc = generate_npc(Selections(cr="5", base="Melee", race="Human"))
        self.output = render_as_text(RenderedNPC(
            npc=npc,
            name="Integration Test",
            cr="5",
            race="Human",
            personality="Placeholder.",
            alignment="True Neutral",
            languages=["Common"],
        ))

    def test_renders_without_crashing(self):
        self.assertIsInstance(self.output, str)
        self.assertTrue(self.output)

    def test_core_lines_present(self):
        for label in ["Armour Class", "Hit Points", "Speed",
                      "Saving Throws", "Senses", "Languages Common",
                      "Challenge 5"]:
            self.assertIn(label, self.output)

    def test_no_adjacent_dividers(self):
        self.assertNotIn(f"{DIVIDER}\n{DIVIDER}", self.output)

    def test_loaded_npc_renders(self):
        """Every optional section firing at once must still assemble."""
        npc = generate_npc(Selections(
            cr="9",
            base="Half Caster",
            race="Elf",
            primary="DEX",
            secondary="CON",
            combat_kits=["Skirmisher"],
            magic_kits=["Abjuration"],
            role_kits=["Sailor"],
            environment="Mountain",
        ))
        output = render_as_text(RenderedNPC(
            npc=npc, name="Loaded", cr="9", race="Elf",
            personality="Placeholder.", alignment="Neutral Evil",
            languages=["Common", "Elvish"],
        ))
        self.assertIn("Actions", output)
        self.assertIn("Spellcasting.", output)
        self.assertNotIn("\n\n\n", output)


if __name__ == "__main__":
    unittest.main()