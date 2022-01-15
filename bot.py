from typing import Callable, Dict, List, Tuple
from game_message import Tick, Position, Team, TickMap, TileType
from game_command import CommandAction, CommandType

import random
import heapq


class Bot:
    def __init__(self) -> None:
        print("Initializing your super mega duper bot")

    def get_next_moves(self, tick: Tick) -> List[CommandAction]:
        my_team: Team = tick.get_teams_by_id()[tick.teamId]
        actions: List[CommandAction] = []

        for unit in my_team.units:
            # S'il reste unit à spawner, la faire spawner
            if tick.tick == 300 and unit.hasDiamond:
                for neighbor in self.get_neighbors(u=unit.position, width=1, height=1):
                    # TODO CHECK IF PLAYER BESIDE
                    if tick.map.get_tile_type_at(neighbor) == TileType.EMPTY:
                        action = CommandAction(
                            action=CommandType.DROP, unitId=unit.id, target=neighbor
                        )
                        actions.append(action)

            if not unit.hasSpawned:
                action = CommandAction(
                    action=CommandType.SPAWN,
                    unitId=unit.id,
                    target=self.get_spawn_near_diamond(tick),
                )
                actions.append(action)
            elif unit.hasDiamond:
                # RUN AWAY
                action = CommandAction(
                    action=CommandType.MOVE,
                    unitId=unit.id,
                    target=self.run_away(tick.map),
                )
                actions.append(action)
            elif (
                self.check_if_enemy_aside_unit(unit.position, tick)[0]
                and not unit.hasDiamond
            ):
                # Attack if enemy is adjacent
                action = CommandAction(
                    action=CommandType.ATTACK,
                    unitId=unit.id,
                    target=self.check_if_enemy_aside_unit(unit.position, tick)[1],
                )
                actions.append(action)
            else:
                # Go towards diamond
                action = CommandAction(
                    action=CommandType.MOVE,
                    unitId=unit.id,
                    target=self.get_diamond_nearest_unit(
                        unit.position
                    ),  # include djikstra
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
    def get_diamond_nearest_unit(self, unit_position: Position, tick: Tick) -> Position:
        diamonds = tick.map.diamonds

        def pred(u: Position) -> bool:
            return u == unit_position

        _, path = min(
            self.dijkstra(tick_map, diamond.position, pred) for diamond in diamonds
        )

        return path[-1]

    def get_spawn_near_diamond(self, tick: Tick) -> Tuple[Position, Position]:
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
            print(diamond.position, dist, path)
            if dist == -1:
                continue
            if dist < min_dist:
                min_dist = dist
                min_spawn = path[0]
                min_diamond = diamond.position

        return min_spawn, min_diamond

    def get_neighbors(
        self, u: Position, width: int, height: int
    ) -> Tuple[Position, Position, Position, Position]:
        x = u.x
        y = u.y
        p1 = Position(x - 1, y)
        p2 = Position(x + 1, y)
        p3 = Position(x, y - 1)
        p4 = Position(x, y + 1)

        return p1, p2, p3, p4

    def backtrace(
        self, prev: Dict[Position, Position], u: Position
    ) -> Tuple[int, List[Position]]:
        path = [u]
        while u in prev:
            u = prev[u]
            path.append(u)
        return len(path), reversed(path)

    def dijkstra(
        self, tick_map: TickMap, start: Position, pred: Callable[[Position], bool]
    ) -> Tuple[int, List[Position]]:
        # https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
        width = tick_map.get_map_size_x()
        height = tick_map.get_map_size_y()

        dist = {}
        prev = {}
        queue = []

        while len(queue):
            u = heapq.heappop(queue)

            if pred(u):
                return self.backtrace(prev, u)

            for v in self.get_neighbors(u, width, height):
                if not self.validate_tile_exists(tick_map, v):
                    continue

                new_dist = dist[u] + 1
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = v

                heapq.heappush(queue, v)

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
