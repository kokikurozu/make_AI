from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CardType(Enum):
    LEADER    = "leader"
    CHARACTER = "character"
    EVENT     = "event"
    STAGE     = "stage"


class Color(Enum):
    RED    = "red"
    BLUE   = "blue"
    GREEN  = "green"
    PURPLE = "purple"
    BLACK  = "black"
    YELLOW = "yellow"


@dataclass(frozen=True)
class Card:
    card_id: str
    name: str
    card_type: CardType
    color: Color
    cost: int
    power: int
    counter: Optional[int] = None
    has_rush: bool = False
    has_blocker: bool = False
    don_requirement: int = 0
    image_url: str = ""

    def __repr__(self):
        return f"[{self.name} / cost:{self.cost} / pow:{self.power}]"