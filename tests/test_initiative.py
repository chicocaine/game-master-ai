from types import SimpleNamespace

from core.resolution.initiative import resolve_start_encounter
from core.states.session import GameSessionState


def _session_with_party(*party_members):
	session = GameSessionState()
	session.party = list(party_members)
	return session


def _encounter_with_enemies(*enemies):
	return SimpleNamespace(enemies=list(enemies))


def test_resolve_start_encounter_rolls_and_sorts_descending(monkeypatch):
	session = _session_with_party(
		SimpleNamespace(player_instance_id="plr_1", hp=10, initiative_mod=2),
		SimpleNamespace(player_instance_id="plr_2", hp=10, initiative_mod=0),
	)
	encounter = _encounter_with_enemies(
		SimpleNamespace(enemy_instance_id="enm_1", hp=10, initiative_mod=1),
	)

	rolls = iter([5, 17, 9])
	monkeypatch.setattr("core.resolution.initiative.roll_d20", lambda rng=None: next(rolls))

	events = resolve_start_encounter(session, encounter)

	assert session.encounter.turn_order == ["plr_2", "enm_1", "plr_1"]
	assert session.encounter.current_turn_index == 0
	assert session.encounter.round_number == 1
	assert [event.payload["actor_instance_id"] for event in events] == ["plr_2", "enm_1", "plr_1"]
	assert [event.payload["initiative"] for event in events] == [17, 10, 7]
	assert [event.payload["roll"] for event in events] == [17, 9, 5]
	assert [event.payload["modifier"] for event in events] == [0, 1, 2]


def test_resolve_start_encounter_ignores_defeated_and_preserves_tie_order(monkeypatch):
	session = _session_with_party(
		SimpleNamespace(player_instance_id="plr_defeated", hp=0, initiative_mod=99),
		SimpleNamespace(player_instance_id="plr_alive", hp=4, initiative_mod=0),
	)
	encounter = _encounter_with_enemies(
		SimpleNamespace(enemy_instance_id="enm_alive", hp=3, initiative_mod=0),
		SimpleNamespace(enemy_instance_id="enm_defeated", hp=0, initiative_mod=99),
	)
	session.encounter.current_turn_index = 7
	session.encounter.round_number = 3

	rolls = iter([10, 10])
	monkeypatch.setattr("core.resolution.initiative.roll_d20", lambda rng=None: next(rolls))

	events = resolve_start_encounter(session, encounter)

	assert session.encounter.turn_order == ["plr_alive", "enm_alive"]
	assert session.encounter.current_turn_index == 0
	assert session.encounter.round_number == 1
	assert [event.payload["actor_instance_id"] for event in events] == ["plr_alive", "enm_alive"]
