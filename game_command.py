from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json
from enum import Enum
from game_message import Position


@dataclass_json
class CommandType(Enum):
    MOVE = "MOVE"
    SPAWN = "SPAWN"
    SUMMON = "SUMMON"
    DROP = "DROP"
    VINE = "VINE"
    ATTACK = "ATTACK"
    NONE = "NONE"


@dataclass_json
@dataclass
class CommandAction:
    action: CommandType
    unitId: str
    target: Position = None
    type: str = "UNIT"
