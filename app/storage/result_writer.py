import json
from pathlib import Path


def _write_json(path: Path, payload: dict | list) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


def write_results(
    result_dir: Path,
    patient: dict[str, str],
    memory: dict,
    dialogue: dict[str, list[dict]],
) -> Path:
    patient_name = patient["患者姓名"]
    patient_dir = result_dir / patient_name
    patient_dir.mkdir(parents=True, exist_ok=True)

    for section, section_dialogue in dialogue.items():
        payload = {
            "对话": section_dialogue,
            "提取信息": memory.get(section, {}),
        }
        _write_json(patient_dir / f"{section}.json", payload)

    _write_json(patient_dir / "dialogue.json", dialogue)
    _write_json(patient_dir / "final_record.json", memory)
    return patient_dir
