from pathlib import Path
from typing import Dict, Optional, Union

from models.entity import Entity
from registry.entity_registry import load_entity_registry


from registry.catalog_registry import DataCatalog


def load_player_registry(
	data_dir: Union[str, Path] = "data",
	catalog: Optional["DataCatalog"] = None,
) -> Dict[str, Entity]:
	return load_entity_registry("players.json", data_dir=data_dir, catalog=catalog)
