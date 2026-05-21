import json
from pathlib import Path

from app.config import ProjectConfig, SectionConfig


def is_section_enabled(section: SectionConfig, patient: dict[str, str]) -> bool:
    if section.enabled_for_female_only:
        return patient.get("性别") == "女"
    return True


def load_section_templates(config: ProjectConfig) -> dict[str, list[dict]]:
    templates: dict[str, list[dict]] = {}
    for section in config.sections:
        if not is_section_enabled(section, config.patient):
            continue
        path = Path(config.template_dir) / section.template_file
        with path.open("r", encoding="utf-8") as f:
            templates[section.name] = json.load(f)
    return templates


def get_slot_from_template(template: list[dict], slot_name: str) -> dict | None:
    for slot in sorted(template, key=lambda x: x.get("priority", 0)):
        if slot.get("slot") == slot_name:
            return slot
    return None


def get_format_from_template(template: list[dict]) -> dict:
    result = {}
    for slot in sorted(template, key=lambda x: x.get("priority", 0)):
        name = slot.get("slot")
        structure_format = slot.get("structure_format", {})
        result[name] = structure_format.get("value")
    return result
