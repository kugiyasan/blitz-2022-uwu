from __future__ import annotations

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum
from typing import List, Dict, Optional


class TileType(Enum):
    EMPTY = "EMPTY"
    WALL = "WALL"
    SPAWN = "SPAWN"

    @staticmethod
    def get_tile_type(raw_tile: str) -> TileType:
        for tile_type in TileType:
            if raw_tile == tile_type.value:
                return tile_type
        else:
            raise Exception(f"Tile '{raw_tile}'' is not a valid tile.")


@dataclass_json
@dataclass
class Position:
    x: int
    y: int


@dataclass_json
@dataclass
class TickMap:
    tiles: List[List[str]]
    diamonds: List[Diamond]

    def get_map_size_x(self):
        return len(self.tiles)

    def get_map_size_y(self):
        return len(self.tiles[0])

    def validate_tile_exists(self, position: Position):
        if (
            position.x < 0
            or position.y < 0
            or position.x >= self.get_map_size_x()
            or position.y >= self.get_map_size_y()
        ):
            raise Exception("Position is out of map")

    def get_raw_tile_value_at(self, position: Position) -> str:
        self.validate_tile_exists(position)
        return self.tiles[position.x][position.y]

    def get_tile_type_at(self, position: Position) -> TileType:
        raw_tile = self.get_raw_tile_value_at(position)
        if raw_tile == "SPAWN":
            return TileType.SPAWN
        elif raw_tile == "EMPTY":
            return TileType.EMPTY
        elif raw_tile == "WALL":
            return TileType.WALL
        else:
            raise Exception("Not a valid tile")


@dataclass_json
@dataclass
class Diamond:
    id: str
    position: Position
    summonLevel: int
    points: int
    ownerId: Optional[str] = None


@dataclass_json
@dataclass
class Unit:
    id: str
    teamId: str
    path: List[Position]
    hasDiamond: bool
    hasSpawned: bool
    isSummoning: bool
    lastState: TickTeamUnitState
    diamondId: Optional[str] = None
    position: Optional[Position] = None


@dataclass_json
@dataclass
class TickTeamUnitState:
    wasVinedBy: Optional[str] = None
    positionBefore: Optional[Position] = None
    wasAttackedBy: Optional[str] = None


@dataclass_json
@dataclass
class UnitType(Enum):
    UNIT = "UNIT"


@dataclass_json
@dataclass
class Team:
    id: str
    name: str
    score: int
    units: List[Unit]
    errors: List[str]

@dataclass_json
@dataclass
class GameConfig:
    pointsPerDiamond: int
    maximumDiamondSummonLevel: int
    initialDiamondSummonLevel: int


@dataclass_json
@dataclass
class Tick:
    tick: int
    totalTick: int
    teamId: str
    teams: List[Team]
    map: TickMap
    gameConfig: GameConfig
    teamPlayOrderings: dict

    def get_teams_by_id(self) -> Dict[str, Team]:
        return {team.id: team for team in self.teams}
