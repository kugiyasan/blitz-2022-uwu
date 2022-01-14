from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum
from typing import List


class MessageType(Enum):
    COMMAND = "COMMAND"
    REGISTER = "REGISTER"


@dataclass_json
@dataclass
class BotMessage:
    type: MessageType
    actions: List = None
    tick: int = None
