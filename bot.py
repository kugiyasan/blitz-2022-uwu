from typing import Callable, Dict, List, Tuple
from game_message import Tick, Position, Team, TickMap, TileType
from game_command import CommandAction, CommandType

import random
import heapq


class PositionWrapper:
    def __init__(self, dist: int, position: Position) -> None:
        self.dist = dist
        self.position = position

    def __hash__(self) -> int:
        # x = self.position.x
        # y = self.position.y
        # return hash((x, y))
        return hash(self.position)

    def __lt__(self, other: "PositionWrapper") -> bool:
        return self.dist < other.dist


class Bot:
    def __init__(self) -> None:
        pass

    def get_next_moves(self, tick: Tick) -> List[CommandAction]:
        my_team: Team = tick.get_teams_by_id()[tick.teamId]
        actions: List[CommandAction] = []

        for unit in my_team.units:
            # S'il reste unit à spawner, la faire spawner
            # if tick.tick == 300 and unit.hasDiamond:
            #     for neighbor in self.get_neighbors(u=unit.position, width=1, height=1):
            #         # TODO CHECK IF PLAYER BESIDE
            #         if tick.map.get_tile_type_at(neighbor) == TileType.EMPTY:
            #             action = CommandAction(
            #                 action=CommandType.DROP, unitId=unit.id, target=neighbor
            #             )
            #             actions.append(action)

            if not unit.hasSpawned:
                action = CommandAction(
                    action=CommandType.SPAWN,
                    unitId=unit.id,
                    target=self.get_spawn_near_diamond(tick),
                )
                actions.append(action)
            # elif unit.hasDiamond:
            #     # RUN AWAY
            #     action = CommandAction(
            #         action=CommandType.MOVE,
            #         unitId=unit.id,
            #         target=self.run_away(tick.map),
            #     )
            #     actions.append(action)
            # elif (
            #     self.check_if_enemy_aside_unit(unit.position, tick)[0]
            #     and not unit.hasDiamond
            # ):
            #     # Attack if enemy is adjacent
            #     action = CommandAction(
            #         action=CommandType.ATTACK,
            #         unitId=unit.id,
            #         target=self.check_if_enemy_aside_unit(unit.position, tick)[1],
            #     )
            #     actions.append(action)
            else:
                # Go towards diamond
                action = CommandAction(
                    action=CommandType.MOVE,
                    unitId=unit.id,
                    target=self.get_diamond_nearest_unit(tick, unit.position),
                )
                actions.append(action)
        return actions

    def check_if_enemy_aside_unit(
        self, unit_position: Position, tick: Tick
    ) -> Tuple[bool, Position]:
        other_teams = tick.teams
        for team in other_teams:
            if team.id == tick.get_teams_by_id()[tick.teamId]:
                other_teams.remove(team)

        for team in other_teams:
            for other_unit in team.units:
                if (
                    other_unit.position.x == unit_position.x - 1
                    or other_unit.position.x == unit_position.x + 1
                    or other_unit.position.y == unit_position.y - 1
                    or other_unit.position.y == unit_position.y + 1
                ):
                    return True, other_unit.position

        return False, None

    def run_away(self, tick_map: TickMap) -> Position:
        return Position(
            random.randint(0, tick_map.get_map_size_x() - 1),
            random.randint(0, tick_map.get_map_size_y() - 1),
        )

    # Returns unit ID and diamond's position
    def get_diamond_nearest_unit(self, tick: Tick, unit_position: Position) -> Position:
        tick_map = tick.map
        diamonds = tick_map.diamonds

        def pred(u: Position) -> bool:
            return u == unit_position

        _, path = min(
            self.dijkstra(tick_map, diamond.position, pred) for diamond in diamonds
        )

        return path[0]

    # def get_spawn_near_diamond(self, tick: Tick) -> Tuple[Position, Position]:
    def get_spawn_near_diamond(self, tick: Tick) -> Position:
        """Return the position of the spawn and its nearest diamond"""
        # units = tick.get_teams_by_id()[tick.teamId].units
        diamonds = tick.map.diamonds
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
                min_diamond = diamond.position

        # return min_spawn, min_diamond
        return min_spawn

    def get_neighbors(
        self, u: Tuple[int, int], width: int, height: int
    ) -> Tuple[Position, Position, Position, Position]:
        x, y = u
        return (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        )

    def backtrace(
        self, prev: Dict[Tuple[int, int], Tuple[int, int]], u: Tuple[int, int]
    ) -> Tuple[int, List[Tuple[int, int]]]:
        path = [u]
        while u in prev:
            u = prev[u]
            path.append(u)

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
        # ! CANNOT GO ON WALLS
        width = tick_map.get_map_size_x()
        height = tick_map.get_map_size_y()

        dist = [[-1 for _ in range(width)] for _ in range(height)]
        dist[start.y][start.x] = 0
        prev = {}
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

            for v in self.get_neighbors(curr, width, height):
                (x, y) = v
                if not self.validate_tile_exists(tick_map, Position(x, y)):
                    continue

                new_dist = dist[cy][cx] + 1
                if dist[y][x] == -1 or new_dist < dist[y][x]:
                    dist[y][x] = new_dist
                    prev[v] = curr
                    heapq.heappush(queue, (dist[y][x], v))

        return -1, []

    def calculate_distance(
        self, tick_map: TickMap, start: Position, target: Position
    ) -> Tuple[int, List[Position]]:
        def pred(u: Position) -> bool:
            return u == target

        return self.dijkstra(tick_map, start, pred)

    def validate_tile_exists(self, tick_map: TickMap, position: Position) -> bool:
        # Same function as in game_message.py
        # returns a bool instead of raising an exception
        return not (
            position.x < 0
            or position.y < 0
            or position.x >= tick_map.get_map_size_x()
            or position.y >= tick_map.get_map_size_y()
        )

    def are_we_first(tick: Tick, tick_number: str) -> bool:
        return tick.teamPlayOrderings.tick_number[0] == tick.teamId

    def get_nb_of_turn_order_generated(tick: Tick) -> int:
        return len(tick.teams) ** 2

    def get_nb_of_turns_until_order_generation(tick: Tick) -> int:
        last_turn_order_generated: int = int(tick.teamPlayOrderings.keys()[-1])
        return last_turn_order_generated - tick.tick

    def get_nb_of_turns_where_we_are_first_in_a_row(tick: Tick) -> int:
        x: int = 0
        for turn, order in tick.teamPlayOrderings.items():
            if order[0] == tick.teamId:
                x += 1
            else:
                return x
        return x
