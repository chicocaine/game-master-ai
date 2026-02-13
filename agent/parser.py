"""Rule-based intent parser for player input."""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple

from models.actions import ActionType, RestType
from models.entities import Entity
from models.states import EncounterState, GlobalGameState
from models.data_loader import DataLoader


@dataclass
class ParsedIntent:
	"""Structured result from intent parsing."""

	intent: str
	confidence: float
	raw_text: str
	target_id: Optional[str] = None
	target_name: Optional[str] = None
	spell_id: Optional[str] = None
	spell_name: Optional[str] = None
	attack_id: Optional[str] = None
	attack_name: Optional[str] = None
	rest_type: Optional[str] = None
	room_id: Optional[str] = None
	room_name: Optional[str] = None
	is_ambiguous: bool = False
	candidates: Dict[str, float] = field(default_factory=dict)

	def to_dict(self) -> dict:
		"""Serialize intent to dictionary."""
		return {
			"intent": self.intent,
			"confidence": self.confidence,
			"raw_text": self.raw_text,
			"target_id": self.target_id,
			"target_name": self.target_name,
			"spell_id": self.spell_id,
			"spell_name": self.spell_name,
			"attack_id": self.attack_id,
			"attack_name": self.attack_name,
			"rest_type": self.rest_type,
			"room_id": self.room_id,
			"room_name": self.room_name,
			"is_ambiguous": self.is_ambiguous,
			"candidates": self.candidates,
		}


class IntentParser:
	"""Simple rule-based intent parser."""

	_INTENT_KEYWORDS: Dict[ActionType, List[str]] = {
		ActionType.MOVE: [
			"move",
			"go",
			"walk",
			"run",
			"head",
			"travel",
			"enter",
			"leave",
		],
		ActionType.ATTACK: [
			"attack",
			"hit",
			"strike",
			"slash",
			"stab",
			"smash",
			"shoot",
		],
		ActionType.CAST_SPELL: [
			"cast",
			"spell",
			"magic",
			"conjure",
			"incant",
		],
		ActionType.REST: [
			"rest",
			"sleep",
			"camp",
			"recover",
		],
		ActionType.END_TURN: [
			"end turn",
			"end my turn",
			"finish",
			"done",
			"pass",
			"wait",
		],
		ActionType.EXPLORE: [
			"explore",
			"look",
			"inspect",
			"examine",
			"search",
			"observe",
		],
	}

	_REST_KEYWORDS = {
		RestType.SHORT.value: ["short", "short rest"],
		RestType.LONG.value: ["long", "long rest", "full rest"],
	}

	def __init__(
		self,
		data_loader: Optional[DataLoader] = None,
	) -> None:
		self.data_loader = data_loader

	def parse(
		self,
		text: str,
		actor: Optional[Entity] = None,
		global_state: Optional[GlobalGameState] = None,
		encounter_state: Optional[EncounterState] = None,
	) -> ParsedIntent:
		"""Parse input text into a ParsedIntent."""
		raw_text = text or ""
		normalized = self._normalize_text(raw_text)

		spell_match = self._find_spell_match(normalized, actor)
		attack_match = self._find_attack_match(normalized, actor)
		room_match = self._find_room_match(normalized, global_state)
		target_match = self._find_target_match(normalized, actor, encounter_state)

		scores = self._score_intents(normalized, spell_match, attack_match, room_match)
		intent, confidence, is_ambiguous = self._pick_intent(scores)

		rest_type = self._extract_rest_type(normalized)
		parsed = ParsedIntent(
			intent=intent,
			confidence=confidence,
			raw_text=raw_text,
			target_id=target_match[0] if target_match else None,
			target_name=target_match[1] if target_match else None,
			spell_id=spell_match[0] if spell_match else None,
			spell_name=spell_match[1] if spell_match else None,
			attack_id=attack_match[0] if attack_match else None,
			attack_name=attack_match[1] if attack_match else None,
			rest_type=rest_type,
			room_id=room_match[0] if room_match else None,
			room_name=room_match[1] if room_match else None,
			is_ambiguous=is_ambiguous,
			candidates=scores,
		)

		return self._apply_intent_defaults(parsed)

	def _apply_intent_defaults(self, parsed: ParsedIntent) -> ParsedIntent:
		if parsed.intent == ActionType.REST.value and parsed.rest_type is None:
			parsed.rest_type = RestType.SHORT.value
		return parsed

	def _score_intents(
		self,
		normalized: str,
		spell_match: Optional[Tuple[str, str]],
		attack_match: Optional[Tuple[str, str]],
		room_match: Optional[Tuple[str, str]],
	) -> Dict[str, float]:
		scores: Dict[str, float] = {}
		for intent, keywords in self._INTENT_KEYWORDS.items():
			score = 0.0
			for keyword in keywords:
				if self._contains_phrase(normalized, keyword):
					score += 1.0
			scores[intent.value] = score

		if spell_match:
			scores[ActionType.CAST_SPELL.value] += 3.0
		if attack_match:
			scores[ActionType.ATTACK.value] += 3.0
		if room_match:
			scores[ActionType.MOVE.value] += 2.0

		if "end turn" in normalized or "end my turn" in normalized:
			scores[ActionType.END_TURN.value] += 3.0

		return scores

	def _pick_intent(self, scores: Dict[str, float]) -> Tuple[str, float, bool]:
		if not scores:
			return "unknown", 0.0, False

		sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
		top_intent, top_score = sorted_scores[0]
		second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

		if top_score <= 0:
			return "unknown", 0.0, False

		is_ambiguous = top_score == second_score
		confidence = 0.6 if is_ambiguous else min(1.0, 0.5 + (top_score / 6.0))
		return top_intent, confidence, is_ambiguous

	def _extract_rest_type(self, normalized: str) -> Optional[str]:
		for rest_type, keywords in self._REST_KEYWORDS.items():
			for keyword in keywords:
				if self._contains_phrase(normalized, keyword):
					return rest_type
		return None

	def _find_spell_match(
		self, normalized: str, actor: Optional[Entity]
	) -> Optional[Tuple[str, str]]:
		spell_map = self._get_spell_name_map(actor)
		return self._find_name_match(normalized, spell_map)

	def _find_attack_match(
		self, normalized: str, actor: Optional[Entity]
	) -> Optional[Tuple[str, str]]:
		attack_map = self._get_attack_name_map(actor)
		return self._find_name_match(normalized, attack_map)

	def _find_room_match(
		self, normalized: str, state: Optional[GlobalGameState]
	) -> Optional[Tuple[str, str]]:
		if not self.data_loader or not state:
			return None
		dungeon = self.data_loader.get_dungeon(state.current_dungeon_id)
		if not dungeon:
			return None
		rooms = dungeon.get("rooms", {})
		name_map = {
			room_id: room.get("name", room_id)
			for room_id, room in rooms.items()
		}
		return self._find_name_match(normalized, name_map)

	def _find_target_match(
		self,
		normalized: str,
		actor: Optional[Entity],
		encounter_state: Optional[EncounterState],
	) -> Optional[Tuple[str, str]]:
		if (
			self._contains_phrase(normalized, "self")
			or self._contains_phrase(normalized, "me")
			or self._contains_phrase(normalized, "myself")
		):
			if actor is not None:
				return actor.entity_id, actor.name

		if encounter_state is None:
			return None

		name_map = {entity.entity_id: entity.name for entity in encounter_state.entities}
		return self._find_name_match(normalized, name_map)

	def _find_name_match(
		self, normalized: str, name_map: Dict[str, str]
	) -> Optional[Tuple[str, str]]:
		if not name_map:
			return None

		normalized_names: List[Tuple[str, str, str]] = []
		for item_id, name in name_map.items():
			normalized_name = self._normalize_text(name)
			normalized_names.append((item_id, name, normalized_name))

		normalized_names.sort(key=lambda item: len(item[2]), reverse=True)

		for item_id, name, normalized_name in normalized_names:
			if normalized_name and normalized_name in normalized:
				return item_id, name

		return None

	def _get_spell_name_map(self, actor: Optional[Entity]) -> Dict[str, str]:
		if not self.data_loader:
			return {}

		known_spells = set(actor.known_spells) if actor else set(self.data_loader.spells.keys())
		name_map = {}
		for spell_id in known_spells:
			spell = self.data_loader.get_spell(spell_id)
			if spell:
				name_map[spell_id] = spell.get("name", spell_id)
		return name_map

	def _get_attack_name_map(self, actor: Optional[Entity]) -> Dict[str, str]:
		if not self.data_loader:
			return {}

		known_attacks = set(actor.known_attacks) if actor else set(self.data_loader.attacks.keys())
		name_map = {}
		for attack_id in known_attacks:
			attack = self.data_loader.get_attack(attack_id)
			if attack:
				name_map[attack_id] = attack.get("name", attack_id)
		return name_map

	@staticmethod
	def _normalize_text(text: str) -> str:
		text = text.lower().strip()
		text = re.sub(r"[^a-z0-9\s]", " ", text)
		text = re.sub(r"\s+", " ", text)
		return text

	@staticmethod
	def _contains_phrase(text: str, phrase: str) -> bool:
		phrase = phrase.strip().lower()
		if not phrase:
			return False
		if " " in phrase:
			return phrase in text
		return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def parse_intent(
	text: str,
	actor: Optional[Entity] = None,
	global_state: Optional[GlobalGameState] = None,
	encounter_state: Optional[EncounterState] = None,
	data_loader: Optional[DataLoader] = None,
) -> ParsedIntent:
	"""Convenience function for parsing intents."""
	parser = IntentParser(data_loader=data_loader)
	return parser.parse(
		text=text,
		actor=actor,
		global_state=global_state,
		encounter_state=encounter_state,
	)
