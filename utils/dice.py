"""Dice rolling utilities."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import random
import re


@dataclass
class RollResult:
	"""Represents a dice roll outcome."""
	total: int
	rolls: List[int]
	modifier: int
	expression: str


_DICE_PATTERN = re.compile(r"^(\d+)d(\d+)([+\-]\d+)?$")


def parse_dice_notation(dice_str: str) -> Tuple[int, int, int]:
	"""Parse dice notation like '2d8+1' into components."""
	match = _DICE_PATTERN.match(dice_str.strip())
	if not match:
		raise ValueError(f"Invalid dice notation: {dice_str}")
	count = int(match.group(1))
	sides = int(match.group(2))
	modifier = int(match.group(3)) if match.group(3) else 0
	return count, sides, modifier


def roll_dice(dice_str: str, rng: Optional[random.Random] = None) -> RollResult:
	"""Roll dice using standard notation like '1d6' or '2d8+1'."""
	count, sides, modifier = parse_dice_notation(dice_str)
	rng = rng or random
	rolls = [rng.randint(1, sides) for _ in range(count)]
	total = sum(rolls) + modifier
	return RollResult(
		total=total,
		rolls=rolls,
		modifier=modifier,
		expression=dice_str,
	)


def roll_d20(rng: Optional[random.Random] = None) -> int:
	"""Roll a d20."""
	rng = rng or random
	return rng.randint(1, 20)
