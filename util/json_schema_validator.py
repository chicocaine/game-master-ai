import json
from pathlib import Path
from typing import Dict, List

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

DATA_SCHEMA_MAP: Dict[str, str] = {
	"status_effects.json": "status_effect.schema.json",
	"attacks.json": "attack.schema.json",
	"spells.json": "spell.schema.json",
	"weapons.json": "weapon.schema.json",
	"races.json": "race.schema.json",
	"archetypes.json": "archetype.schema.json",
	"players.json": "entity.schema.json",
	"enemies.json": "entity.schema.json",
	"dungeons.json": "dungeon.schema.json",
}


def _load_json(path: Path):
	with path.open("r", encoding="utf-8") as file:
		return json.load(file)


def _format_validation_error(error: ValidationError) -> str:
	if not error.path:
		return "$"
	segments = [str(part) for part in error.path]
	return "$." + ".".join(segments)


def validate_json_data_file(
	data_path: Path,
	schema_path: Path,
) -> None:
	schema = _load_json(schema_path)
	data = _load_json(data_path)

	if not isinstance(data, list):
		raise ValueError(f"Invalid data in '{data_path.name}': expected top-level array")

	validator = Draft202012Validator(schema)
	for index, item in enumerate(data):
		errors = list(validator.iter_errors(item))
		if not errors:
			continue

		first_error = sorted(errors, key=lambda err: list(err.path))[0]
		error_path = _format_validation_error(first_error)
		raise ValueError(
			f"Schema validation failed for '{data_path.name}' item[{index}] at {error_path}: {first_error.message}"
		)


def validate_model_data_files(data_dir: Path, file_names: List[str]) -> None:
	schema_dir = data_dir / "schemata"
	if not schema_dir.exists():
		schema_dir = Path(__file__).resolve().parents[1] / "data" / "schemata"

	for file_name in file_names:
		schema_name = DATA_SCHEMA_MAP.get(file_name)
		if schema_name is None:
			raise KeyError(f"No schema mapping configured for '{file_name}'")

		validate_json_data_file(
			data_path=data_dir / file_name,
			schema_path=schema_dir / schema_name,
		)