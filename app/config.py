import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "project.json"


@dataclass(frozen=True)
class SectionConfig:
    name: str
    template_file: str
    enabled_for_female_only: bool = False


@dataclass(frozen=True)
class ProjectConfig:
    patient: dict[str, str]
    models: dict[str, str]
    template_dir: Path
    result_dir: Path
    sections: list[SectionConfig]


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_config(config_path: str | Path | None = None) -> ProjectConfig:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    with path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    sections = [
        SectionConfig(
            name=item["name"],
            template_file=item["template_file"],
            enabled_for_female_only=item.get("enabled_for_female_only", False),
        )
        for item in raw["sections"]
    ]

    return ProjectConfig(
        patient=raw["patient"],
        models=raw.get("models", {}),
        template_dir=_resolve_path(raw.get("template_dir", "question_logic")),
        result_dir=_resolve_path(raw.get("result_dir", "result_files")),
        sections=sections,
    )
