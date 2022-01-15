from typing import Callable, Dict, List, Optional, Tuple
from game_message import Tick, Position, TickMap, TileType, Diamond, Unit
from game_command import CommandAction, CommandType

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
        my_team = tick.get_teams_by_id()[tick.teamId]
        actions = []
        tick_map = tick.map
        diamonds = tick_map.diamonds

        for unit in my_team.units:
            enemy = self.can_attack_enemy(unit.position, tick)
            if tick.tick == tick.totalTick - 1 and unit.hasDiamond:
                action = self.try_dropping(tick, unit)
            # S'il reste unit à spawner, la faire spawner
            elif not unit.hasSpawned:
                target, diamond = self.get_spawn_near_diamond(tick, diamonds)
                diamonds = [d for d in diamonds if d.id != diamond]
                action = CommandAction(
                    action=CommandType.SPAWN,
                    unitId=unit.id,
                    target=target,
                )
            elif unit.isSummoning:
                action = CommandAction(
                    action=CommandType.NONE,
                    unitId=unit.id,
                )
            elif unit.hasDiamond:
                action = self.protecc_strat(tick, unit)
            elif enemy is not None:
                action = CommandAction(
                    action=CommandType.ATTACK, unitId=unit.id, target=enemy
                )
            elif self.can_lasso_list(tick, unit):
                for lasso_victim in self.can_lasso_list(tick, unit):
                    if self.are_we_before_another_team_next_turn(
                        tick, lasso_victim.teamId
                    ):
                        action = CommandAction(
                            action=CommandType.VINE,
                            unitId=unit.id,
                            target=lasso_victim.position,
                        )
            else:
                target = self.normal_move(tick, unit.position)
                action = CommandAction(
                    action=CommandType.MOVE,
                    unitId=unit.id,
                    target=target,
                )
            actions.append(action)
        return actions

    def attack_strat(self, tick: Tick) -> CommandAction:
        pass

    def protecc_strat(self, tick: Tick, unit: Unit) -> CommandAction:
        # You got a diamond
        # OBJECTIVE: SURVIVE
        tick_map = tick.map
        diamonds = tick_map.diamonds
        # This looks shit, but it is 4am
        diamond = [d for d in diamonds if d.id == unit.diamondId][0]

        dist = self.check_dist_from_enemy(tick, unit.position)
        # check if enough time to summon
        # TODO make sure they can't vine
        if dist <= 2:
            # if really not enough, drop
            action = self.try_dropping(tick, unit)
        elif (
            diamond.summonLevel < tick.gameConfig.maximumDiamondSummonLevel
            and dist > diamond.summonLevel + 2
            and tick.totalTick - tick.tick >= diamond.summonLevel + 1
        ):
            action = CommandAction(
                action=CommandType.SUMMON,
                unitId=unit.id,
            )
        else:
            # if not enough, run
            target = self.run_away(tick, unit.position)
            action = CommandAction(
                action=CommandType.MOVE,
                unitId=unit.id,
                target=target,
            )

        return action

    def check_dist_from_enemy(self, tick: Tick, unit_position: Position) -> int:
        tick_map = tick.map
        # my_units = [team.units for team in tick.teams if team == tick.teamId][0]
        my_units = self.get_enemy_units(tick)
        my_units_pos = [unit.position for unit in my_units if unit.position]

        if len(my_units_pos) == 0:
            return 69420

        def pred(u: Position) -> bool:
            return u in my_units_pos

        dist, path = self.dijkstra(tick_map, unit_position, pred)
        return dist

    def try_dropping(self, tick: Tick, unit: Unit) -> CommandAction:
        empty_tile = self.find_empty_tile_around_unit(unit.position, tick)
        if empty_tile is not None:
            action = CommandAction(
                action=CommandType.DROP, unitId=unit.id, target=empty_tile
            )
        else:
            action = CommandAction(action=CommandType.NONE, unitId=unit.id)

        return action

    def find_empty_tile_around_unit(
        self, unit_position: Position, tick: Tick
    ) -> Optional[Position]:
        tick_map = tick.map
        enemy_units = self.get_enemy_units(tick)
        x = unit_position.x
        y = unit_position.y
        combs = (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        )
        for (x, y) in combs:
            pos = Position(x, y)
            if not self.validate_tile_exists(tick_map, pos):
                continue
            if tick_map.get_tile_type_at(pos) == TileType.EMPTY:
                if all(unit.position != pos for unit in enemy_units):
                    return pos
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

    def run_away(self, tick: Tick, unit_position: Position) -> Position:
        # TODO STOP RUNNING AWAY FROM THIS FUNCTION AND COMPLETE IT
        # TODO make sure to not line up for a vine
        # the unit will get stuck in a corner
        # When an enemy is near a unit, move in the opposite direction
        enemy_pos = self.find_nearest_enemy(tick, unit_position)
        dx = unit_position.x - enemy_pos.x
        dy = unit_position.y - enemy_pos.y

        x = unit_position.x
        y = unit_position.y

        if abs(dx) > abs(dy):
            x += 1 if dx > 0 else -1
        else:
            y += 1 if dy > 0 else -1

        position = Position(x, y)
        if self.validate_tile_exists(tick.map, position):
            return position
        return self.force_move(tick, unit_position)

    # Returns diamond's position (old name: get_diamond_nearest_unit)
    def normal_move(self, tick: Tick, unit_position: Position) -> Position:
        tick_map = tick.map
        diamonds = tick_map.diamonds
        # Aim for the lying diamonds
        target_pos = [
            d.position
            for d in diamonds
            if self.who_is_holding_this_diamond(tick, d) is None
        ]
        # ! There might be unachievable diamonds
        if len(target_pos) == 0:
            # No diamond is available, ATTACK THE ENEMY
            target_pos = [
                d.position
                for d in diamonds
                if self.who_is_holding_this_diamond(tick, d).teamId != tick.teamId
            ]
        if len(target_pos) == 0:
            # Your team got all diamond, ATTACK THE ENEMY
            # Target enemies, not diamonds
            target_pos = (self.find_nearest_enemy(tick, unit_position),)

        def pred(u: Position) -> bool:
            return u == unit_position

        def key(e: Tuple[int, Position]) -> int:
            if e[0] == -1:
                return 420420420420
            return e[0]

        _, path = min(
            (
                self.dijkstra(tick_map, position, pred, no_spawn=True)
                for position in target_pos
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
            and all(unit.position != pos for team in tick.teams for unit in team.units)
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

    def get_spawn_near_diamond(
        self, tick: Tick, diamonds: List[Diamond]
    ) -> Tuple[Position, str]:
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
        self,
        tick_map: TickMap,
        start: Position,
        pred: Callable[[Position], bool],
        no_spawn: bool = False,
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
                if not self.validate_tile_in_bound(tick_map, v):
                    if not self.validate_tile_exists(tick_map, v):
                        continue
                    elif no_spawn and tick_map.get_tile_type_at(v) != TileType.WALL:
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

        return self.dijkstra(tick_map, start, pred, no_spawn=True)

    def validate_tile_in_bound(self, tick_map: TickMap, position: Position) -> bool:
        return not (
            position.x < 0
            or position.y < 0
            or position.x >= tick_map.get_map_size_x()
            or position.y >= tick_map.get_map_size_y()
        )

    def validate_tile_exists(self, tick_map: TickMap, position: Position) -> bool:
        return (
            self.validate_tile_in_bound(tick_map, position)
            and tick_map.get_tile_type_at(position) != TileType.WALL
        )

    def are_we_first(self, tick: Tick, tick_number: str) -> bool:
        return bool(tick.teamPlayOrderings[tick_number][0] == tick.teamId)

    def are_we_before_another_team_next_turn(self, tick, e_teamId: str) -> bool:
        teamPlayOrderings = tick.teamPlayOrderings.tick.tick + 1
        return teamPlayOrderings.index(tick.teamId) < teamPlayOrderings.index(e_teamId)

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

    def who_is_holding_this_diamond(
        self, tick: Tick, diamond: Diamond
    ) -> Optional[Unit]:
        for team in tick.teams:
            for unit in team.units:
                if unit.hasDiamond:
                    if unit.position == diamond.position:
                        return unit
        return None

    def find_nearest_enemy(self, tick: Tick, unit_position: Position) -> Position:
        tick_map = tick.map
        enemy_units = self.get_enemy_units(tick)

        def pred(u: Position) -> bool:
            return u == unit_position

        def key(e: Tuple[int, Position]) -> int:
            if e[0] == -1:
                return 420420420420
            return e[0]

        _, path = min(
            (
                self.dijkstra(tick_map, unit.position, pred, no_spawn=True)
                for unit in enemy_units
                if unit.position is not None
            ),
            key=key,
        )

        if len(path):
            return path[0]
        return Position(0, 0)

    def get_enemy_units(self, tick: Tick) -> List[Unit]:
        return [
            unit
            for team in tick.teams
            for unit in team.units
            if team.id != tick.teamId and unit.position
        ]

    def can_lasso_list(self, tick: Tick, unit: Unit) -> List[Unit]:
        enemy_units = self.get_enemy_units(tick)
        can_lasso_units = []
        for e_unit in enemy_units:
            if e_unit.position.x == unit.position.x:
                # Check pour des murs (very lazy)
                dist, _ = self.calculate_distance(
                    tick.map, unit.position, e_unit.position
                )
                if dist == abs(e_unit.position.x - unit.position.x):
                    can_lasso_units.append(e_unit)
                # if all(
                #     tick.map.get_tyle_type_at(Position(x, unit.position.y))
                #     != TileType.WALL
                #     and tick.map.get_tyle_type_at(Position(x, unit.position.y))
                #     != TileType.SPAWN
                #     for x in range(unit.position.x, e_unit.position.x)
                # ):
                #     can_lasso_units.append(e_unit)
            elif e_unit.position.y == unit.position.y:
                # Check pour des murs (very lazy)
                dist, _ = self.calculate_distance(
                    tick.map, unit.position, e_unit.position
                )
                if dist == abs(e_unit.position.y - unit.position.y):
                    can_lasso_units.append(e_unit)
                # if all(
                #     tick.map.get_tyle_type_at(Position(unit.position.x, y))
                #     != TileType.WALL
                #     and tick.map.get_tyle_type_at(Position(unit.position.x, y))
                #     != TileType.SPAWN
                #     for y in range(unit.position.y, e_unit.position.y)
                # ):
                #     can_lasso_units.append(e_unit)
        return can_lasso_units
