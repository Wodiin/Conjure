from dataclasses import dataclass
from generator import generate_npc


@dataclass
class RenderedNPC:
    npc: dict
    name: str
    cr: str
    race: str
    personality: str
    alignment: str
    languages: list[str]


def render_as_text(rendered: RenderedNPC) -> str:










    '''
    ------------------------------------------
    Name:
    Medium Humanoid (race), Chaotic Neutral
    ------------------------------------------
    Armour Class 99
    Hit Points 999 (99d12 + 99)
    Speed 30ft Swim 30ft Fly 60ft
    ------------------------------------------
    STR    DEX    CON    INT    WIS    CHA
    10(+0) 10(+0) 10(+0) 10(+0) 10(+0) 10(+0) 
    ------------------------------------------
    Saving Throws Con +0, Wis +0
    Skills Athletics +5, Deception +5
    Senses passive Perception 10
    Languages Common
    Challenge 1 (200xp)
    ------------------------------------------
    Test Trait.. This test trait grants the 
    character the ability to test traits. How
    fun.

    Actions
    ------------------------------------------
    Multiattack. The character makes three 
    attacks with their Shortsword.

    Shortsword. Melee Weapon Attack: +2 to hit,
    reach 5ft, one target. 
    Hit: 6(1d6 + 3) piercing damage

    Reactions
    ------------------------------------------
    Parry. The character adds 2 to its AC
    against one melee attack that would hit it.
    To do so, the character must see the
    attacker and be wielding a melee weapon.
    '''