from typing import Callable, Dict, List, Optional, Tuple
from game_message import Tick, Position, Team, TickMap, TileType, Diamond, Unit
from game_command import CommandAction, CommandType

import random
import heapq


class Bot:
    def __init__(self) -> None:
        pass

    def get_next_moves(self, tick: Tick) -> List[CommandAction]:
        actions = self._get_next_moves(tick)
        return actions
        # try:
        #     return self._get_next_moves(tick)
        # except Exception as e:
        #     print(e)
        #     return []

    def _get_next_moves(self, tick: Tick) -> List[CommandAction]:
        my_team: Team = tick.get_teams_by_id()[tick.teamId]
        actions: List[CommandAction] = []
        tick_map = tick.map
        diamonds = tick_map.diamonds

        for unit in my_team.units:
            enemy = self.can_attack_enemy(unit.position, tick)
            if tick.tick == tick.totalTick - 1 and unit.hasDiamond:
                empty_tile = self.find_empty_tile_around_unit(unit.position, tick)
                if empty_tile is not None:
                    action = CommandAction(
                        action=CommandType.DROP, unitId=unit.id, target=empty_tile
                    )
                else:
                    action = CommandAction(action=CommandType.NONE, unitId=unit.id)
            # S'il reste unit à spawner, la faire spawner
            elif not unit.hasSpawned:
                (target, diamond) = self.get_spawn_near_diamond(tick, diamonds)
                diamonds = [d for d in diamonds if d.id != diamond]
                action = CommandAction(
                    action=CommandType.SPAWN,
                    unitId=unit.id,
                    target=target,
                )
            elif unit.hasDiamond:
                action = CommandAction(
                    action=CommandType.SUMMON,
                    unitId=unit.id,
                )
                # if summon max level, run_away
                # check if enough time to summon
            elif enemy is not None:
                action = CommandAction(
                    action=CommandType.ATTACK, unitId=unit.id, target=enemy
                )
            else:
                diamond_position = self.get_diamond_nearest_unit(tick, unit.position)
                action = CommandAction(
                    action=CommandType.MOVE,
                    unitId=unit.id,
                    target=diamond_position,
                )
            actions.append(action)
        return actions

    def find_empty_tile_around_unit(
        self, unit_position: Position, tick: Tick
    ) -> Optional[Position]:
        tick_map = tick.map
        x = unit_position.x
        y = unit_position.y
        if tick_map.get_tile_type_at(Position(x - 1, y)) == TileType.EMPTY:
            return Position(x - 1, y)
        elif tick_map.get_tile_type_at(Position(x + 1, y)) == TileType.EMPTY:
            return Position(x + 1, y)
        elif tick_map.get_tile_type_at(Position(x, y - 1)) == TileType.EMPTY:
            return Position(x, y - 1)
        elif tick_map.get_tile_type_at(Position(x, y + 1)) == TileType.EMPTY:
            return Position(x, y + 1)
        return None

    def can_attack_enemy(
        self, unit_position: Optional[Position], tick: Tick
    ) -> Optional[Position]:
        if unit_position is None:
            return None
        tick_map = tick.map
        if tick_map.get_tile_type_at(unit_position) != TileType.EMPTY:
            return None
        x = unit_position.x
        y = unit_position.y

        for team in tick.teams:
            if team.id == tick.teamId:
                continue
            for unit in team.units:
                if (
                    unit.position is None
                    or tick_map.get_tile_type_at(unit.position) != TileType.EMPTY
                ):
                    continue
                if unit.position == Position(x - 1, y):
                    return unit.position
                elif unit.position == Position(x + 1, y):
                    return unit.position
                elif unit.position == Position(x, y - 1):
                    return unit.position
                elif unit.position == Position(x, y + 1):
                    return unit.position
        return None

    def run_away(self, tick_map: TickMap) -> Position:
        return Position(
            random.randint(0, tick_map.get_map_size_x() - 1),
            random.randint(0, tick_map.get_map_size_y() - 1),
        )

    # Returns diamond's position
    def get_diamond_nearest_unit(self, tick: Tick, unit_position: Position) -> Position:
        tick_map = tick.map
        diamonds = tick_map.diamonds
        free_diamonds = [
            d for d in diamonds if self.who_is_holding_this_diamond(tick, d) is None
        ]
        # ! There might be unachievable diamonds
        if len(free_diamonds) == 0:
            # No diamond is available, ATTACK THE ENEMY
            free_diamonds = [
                d
                for d in diamonds
                if self.who_is_holding_this_diamond(tick, d).teamId != tick.teamId
            ]
        if len(free_diamonds) == 0:
            # Your team got all diamond, ATTACK THE ENEMY
            # Target enemies, not diamonds
            free_diamonds = self.find_nearest_enemy(tick, unit_position)

        def pred(u: Position) -> bool:
            return u == unit_position

        def key(e: Tuple[int, Position]) -> int:
            if e[0] == -1:
                return 420420420420
            return e[0]

        _, path = min(
            (
                self.dijkstra(tick_map, diamond.position, pred)
                for diamond in free_diamonds
            ),
            key=key,
        )

        pos = None
        if len(path) >= 2:
            pos = path[-2]
        elif len(path):
            pos = path[0]

        if (
            pos is not None
            and self.validate_tile_exists(tick_map, pos)
            and all(
                unit.position != pos
                for team in tick.teams
                for unit in team.units
            )
        ):
            return pos

        return self.force_move(tick, unit_position)

    def force_move(self, tick: Tick, unit_position: Position) -> Position:
        tick_map = tick.map
        width = tick_map.get_map_size_x()
        height = tick_map.get_map_size_y()

        for neighbor in self.get_neighbors(unit_position, width, height):
            if self.validate_tile_exists(tick_map, neighbor):
                if any(
                    unit.position == neighbor
                    for team in tick.teams
                    for unit in team.units
                ):
                    continue
        else:
            return neighbor

        return Position(0, 0)

    def get_spawn_near_diamond(self, tick: Tick, diamonds) -> Tuple[Position, str]:
        """Return the position of the spawn and its nearest diamond"""
        # units = tick.get_teams_by_id()[tick.teamId].units
        tick_map = tick.map

        min_dist = 9999999
        min_spawn = None
        min_diamond = None

        # spawn tile le plus proche d'un diam
        def pred(u: Position) -> bool:
            return tick_map.get_tile_type_at(u) == TileType.SPAWN

        for diamond in diamonds:
            dist, path = self.dijkstra(tick_map, diamond.position, pred)
            if dist == -1:
                continue
            if dist < min_dist:
                min_dist = dist
                min_spawn = path[-1]
                min_diamond = diamond.id

        # return min_spawn, min_diamond
        return min_spawn, min_diamond

    def get_neighbors(
        self, u: Position, width: int, height: int
    ) -> Tuple[Position, Position, Position, Position]:
        x = u.x
        y = u.y
        return (
            Position(x - 1, y),
            Position(x, y - 1),
            Position(x + 1, y),
            Position(x, y + 1),
        )

    def backtrace(
        self, prev: Dict[Tuple[int, int], Tuple[int, int]], u: Tuple[int, int]
    ) -> Tuple[int, List[Position]]:
        path = [Position(*u)]
        while u in prev:
            u = prev[u]
            path.append(Position(*u))

        path.reverse()
        return len(path), path

    def dijkstra(
        self, tick_map: TickMap, start: Position, pred: Callable[[Position], bool]
    ) -> Tuple[int, List[Position]]:
        """
        https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
        https://pythonalgos.com/dijkstras-algorithm-in-5-steps-with-python/

        >>> bot = Bot()
        >>> tiles = [["EMPTY" for _ in range(100)] for _ in range(100)]
        >>> tick_map = TickMap(tiles=tiles, diamonds=[])
        >>> def pred(u: Position) -> bool: return u == Position(99, 99)
        >>> bot.dijkstra(tick_map, Position(0, 0), pred)
        """
        width = tick_map.get_map_size_x()
        height = tick_map.get_map_size_y()

        dist = [[-1 for _ in range(width)] for _ in range(height)]
        dist[start.y][start.x] = 0
        prev: Dict[Tuple[int, int], Tuple[int, int]] = {}
        visited = set()
        queue = [(0, (start.x, start.y))]

        while len(queue):
            # print(queue)
            _dist, curr = heapq.heappop(queue)

            if curr in visited:
                continue

            visited.add(curr)
            cx, cy = curr

            if pred(Position(cx, cy)):
                return self.backtrace(prev, curr)

            for v in self.get_neighbors(Position(cx, cy), width, height):
                x, y = v.x, v.y
                if not self.validate_tile_exists(tick_map, v):
                    continue

                new_dist = dist[cy][cx] + 1
                if dist[y][x] == -1 or new_dist < dist[y][x]:
                    dist[y][x] = new_dist
                    prev[(x, y)] = curr
                    heapq.heappush(queue, (dist[y][x], (x, y)))

        return -1, []

    def calculate_distance(
        self, tick_map: TickMap, start: Position, target: Position
    ) -> Tuple[int, List[Position]]:
        def pred(u: Position) -> bool:
            return u == target

        return self.dijkstra(tick_map, start, pred)

    def validate_tile_exists(self, tick_map: TickMap, position: Position) -> bool:
        return not (
            position.x < 0
            or position.y < 0
            or position.x >= tick_map.get_map_size_x()
            or position.y >= tick_map.get_map_size_y()
            or tick_map.get_tile_type_at(position) == TileType.WALL
        )

    def are_we_first(self, tick: Tick, tick_number: str) -> bool:
        return bool(tick.teamPlayOrderings[tick_number][0] == tick.teamId)

    def get_nb_of_turn_order_generated(self, tick: Tick) -> int:
        return len(tick.teams) ** 2

    def get_nb_of_turns_until_order_generation(self, tick: Tick) -> int:
        last_turn_order_generated = int(list(tick.teamPlayOrderings.keys())[-1])
        return last_turn_order_generated - tick.tick

    def get_nb_of_turns_where_we_are_first_in_a_row(self, tick: Tick) -> int:
        x = 0
        for turn, order in tick.teamPlayOrderings.items():
            if order[0] == tick.teamId:
                x += 1
            else:
                return x
        return x

    def who_is_holding_this_diamond(self, tick: Tick, diamond: Diamond) -> Unit:
        for team in tick.teams:
            for unit in team.units:
                if unit.hasDiamond:
                    if unit.position == diamond.position:
                        return unit
        return None

    def find_nearest_enemy(self, tick: Tick, unit_position: Position) -> Position:
        tick_map = tick.map
        other_teams = tick.teams
        enemy_units = []
        for team in other_teams:
            if team.id == tick.get_teams_by_id()[tick.teamId]:
                other_teams.remove(team)
        for unit in team.units:
            enemy_units.append(unit)

        def pred(u: Position) -> bool:
            return u == unit_position

        def key(e: Tuple[int, Position]) -> int:
            if e[0] == -1:
                return 420420420420
            return e[0]

        _, path = min(
            (
                self.dijkstra(tick_map, unit.position, pred)
                for unit in enemy_units
                if unit.position is not None
            ),
            key=key,
        )

        if len(path):
            return path[0]
        return Position(0, 0)
