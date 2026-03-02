from collections import deque
from typing import Dict, List, Set
from core.models.dungeon import Dungeon, Room

def _validate_required_rooms(dungeon: Dungeon, room_ids: Set[str]) -> None:
	if dungeon.start_room not in room_ids:
		raise ValueError(
			f"Dungeon '{dungeon.id}' has unknown start_room '{dungeon.start_room}'"
		)
	if dungeon.end_room not in room_ids:
		raise ValueError(
			f"Dungeon '{dungeon.id}' has unknown end_room '{dungeon.end_room}'"
		)


def _validate_room_connections(dungeon: Dungeon, room_ids: Set[str]) -> None:
	for room in dungeon.rooms:
		for connection in room.connections:
			if connection not in room_ids:
				raise ValueError(
					f"Dungeon '{dungeon.id}' room '{room.id}' references unknown connection '{connection}'"
				)


def _validate_unique_room_ids(dungeon: Dungeon) -> Dict[str, Room]:
	indexed_rooms: Dict[str, Room] = {}
	for room in dungeon.rooms:
		if room.id in indexed_rooms:
			raise ValueError(f"Dungeon '{dungeon.id}' has duplicate room id '{room.id}'")
		indexed_rooms[room.id] = room
	return indexed_rooms


def _validate_unique_encounter_ids(dungeon: Dungeon) -> None:
	encounter_ids: Set[str] = set()
	for room in dungeon.rooms:
		for encounter in room.encounters:
			if encounter.id in encounter_ids:
				raise ValueError(
					f"Dungeon '{dungeon.id}' has duplicate encounter id '{encounter.id}'"
				)
			encounter_ids.add(encounter.id)


def _is_end_reachable(dungeon: Dungeon, rooms_by_id: Dict[str, Room]) -> bool:
	visited: Set[str] = set()
	queue: deque[str] = deque([dungeon.start_room])

	while queue:
		room_id = queue.popleft()
		if room_id in visited:
			continue
		if room_id == dungeon.end_room:
			return True

		visited.add(room_id)
		room = rooms_by_id.get(room_id)
		if room is None:
			continue

		for next_room_id in room.connections:
			if next_room_id not in visited:
				queue.append(next_room_id)

	return False


def validate_dungeon(dungeon: Dungeon) -> None:
	if not dungeon.rooms:
		raise ValueError(f"Dungeon '{dungeon.id}' must contain at least one room")

	rooms_by_id = _validate_unique_room_ids(dungeon)
	room_ids = set(rooms_by_id.keys())

	_validate_required_rooms(dungeon, room_ids)
	_validate_room_connections(dungeon, room_ids)
	_validate_unique_encounter_ids(dungeon)

	if not _is_end_reachable(dungeon, rooms_by_id):
		raise ValueError(
			f"Dungeon '{dungeon.id}' end_room '{dungeon.end_room}' is not reachable from start_room '{dungeon.start_room}'"
		)


def validate_dungeons(dungeons: List[Dungeon]) -> None:
	for dungeon in dungeons:
		validate_dungeon(dungeon)
