import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TypeVar, Union

from core.models.status_effect import StatusEffectDefinition, StatusEffectInstance
from util.json_schema_validator import validate_model_data_files


TModel = TypeVar("TModel")


def _to_root_path(data_dir: Union[str, Path]) -> Path:
	return Path(data_dir)


def load_json(path: Path):
	with path.open("r", encoding="utf-8") as file:
		return json.load(file)


def validate_files(data_dir: Union[str, Path], file_names: List[str]) -> Path:
	root = _to_root_path(data_dir)
	validate_model_data_files(root, file_names)
	return root


def index_by_id(items: Iterable[dict], source: str) -> Dict[str, dict]:
	indexed: Dict[str, dict] = {}
	for item in items:
		if not isinstance(item, dict):
			raise ValueError(f"Invalid item in {source}: expected object")
		item_id = str(item.get("id", ""))
		if not item_id:
			raise ValueError(f"Invalid item in {source}: missing 'id'")
		indexed[item_id] = item
	return indexed


def load_indexed_rows(data_dir: Union[str, Path], file_name: str) -> Dict[str, dict]:
	root = validate_files(data_dir, [file_name])
	rows = load_json(root / file_name)
	return index_by_id(rows, file_name)


def resolve_ids(
	ids: Optional[List[str]],
	index: Dict[str, TModel],
	ref_name: str,
	owner_id: str,
) -> List[TModel]:
	if not ids:
		return []

	resolved: List[TModel] = []
	for ref_id in ids:
		key = str(ref_id)
		if key not in index:
			raise KeyError(f"Unknown {ref_name} id '{key}' referenced by '{owner_id}'")
		resolved.append(index[key])
	return resolved


def resolve_status_effect_instances(
	references: Optional[List[list]],
	index: Dict[str, StatusEffectDefinition],
	owner_id: str,
	field_name: str,
) -> List[StatusEffectInstance]:
	if not references:
		return []

	resolved: List[StatusEffectInstance] = []
	for reference in references:
		if not isinstance(reference, list) or len(reference) != 2:
			raise ValueError(
				f"Invalid status effect reference in '{owner_id}.{field_name}': expected [status_effect_id, duration]"
			)

		status_effect_id = str(reference[0])
		duration = int(reference[1])
		if status_effect_id not in index:
			raise KeyError(
				f"Unknown status_effect id '{status_effect_id}' referenced by '{owner_id}'"
			)

		resolved.append(
			StatusEffectInstance(
				status_effect=index[status_effect_id],
				duration=duration,
			)
		)

	return resolved
