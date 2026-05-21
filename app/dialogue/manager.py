import json
import os
from datetime import datetime

from app.config import ProjectConfig
from app.storage import write_results
from app.templates import (
    get_format_from_template,
    get_slot_from_template,
    load_section_templates,
)


def _build_section_count(section_memory: dict) -> dict[str, int]:
    return {key: 0 for key in section_memory}


def _with_patient_context(sub_memory: dict, patient: dict[str, str]) -> None:
    sub_memory["患者姓名"] = patient["患者姓名"]
    sub_memory["性别"] = patient["性别"]
    sub_memory["患者年龄"] = patient["患者年龄"]
    if int(sub_memory["患者年龄"]) >= 50 and sub_memory["性别"] == "女":
        sub_memory["是否已经达到可能绝经年龄"] = "True"
    else:
        sub_memory["是否已经达到可能绝经年龄"] = "False"


def _remove_patient_context(sub_memory: dict) -> None:
    sub_memory.pop("患者姓名", None)
    sub_memory.pop("性别", None)
    sub_memory.pop("患者年龄", None)


def answer_medical_question(user_input: str) -> str:
    from client_llm_normal import call_llm_normal

    system = (
        "你是医学问诊助手，请在尽可能全面以及严谨的前提下，"
        "回答患者对你的提问，"
        "禁止输出Markdown代码块。"
    )
    prompt = f"回答尽可能地简单易懂。\n问题：{user_input}，\n请给出最后的回答。"
    return call_llm_normal(system, prompt)


def ask_history(
    template: list[dict],
    patient: dict[str, str],
    memory: dict,
    section: str,
    count: dict[str, int],
) -> tuple[dict, list[dict]]:
    from answer_handler import AnswerType, handle_answer
    from context_update import update_history
    from question_generate import generate_question
    from rule_engine import get_next_slot

    dialogue_history: list[dict] = []
    sub_memory = memory[section]
    _with_patient_context(sub_memory, patient)

    current_slot = None
    current_history = {}
    asked = set()
    now = datetime.now().date()

    print(f"🤖 {section} 问诊开始")
    while True:
        current_dialogue = {}
        sub_memory = memory[section]
        slot = get_next_slot(template, sub_memory, asked)
        if slot is None:
            break

        if slot["priority"] == 1:
            current_slot = None
            current_count = 0
        elif current_slot is not None:
            current_count = count.get(current_slot["slot"], 0)
        else:
            current_count = 0

        context_slot = generate_question(
            slot, current_slot, sub_memory, current_history, current_count
        )
        if context_slot["slot"] is None:
            break

        count[context_slot["slot"]] = count.get(context_slot["slot"], 0) + 1

        print("🤖", context_slot["prompt_q"])
        current_dialogue["问题"] = context_slot["prompt_q"]
        user_input = input("👤 ")
        current_dialogue["回答"] = user_input

        slot_template = get_slot_from_template(template, context_slot["slot"])
        result = handle_answer(
            prompt_q=context_slot["prompt_q"],
            user_input=user_input,
            slot=slot_template,
        )

        if result["type"] == AnswerType.KNOWLEDGE_QUERY:
            knowledge_answer = answer_medical_question(user_input)
            print("🤖 (知识回答)", knowledge_answer)
            current_slot = slot_template
            current_history = {
                "question": "",
                "answer": "",
                "structured_format": "",
                "structured": "",
            }
            current_dialogue["知识回答"] = knowledge_answer
        else:
            structured = result["data"]["value"]
            print("提取结果:", structured)
            current_dialogue["提取结果"] = structured
            data = json.loads(structured)
            sub_memory[data["slot"]] = data["value"]
            asked.add(data["slot"])
            memory = update_history(context_slot, memory, user_input, now)
            current_slot = slot_template
            current_history = {
                "question": context_slot["prompt_q"],
                "answer": user_input,
                "structured_format": current_slot["structure_format"],
                "structured": data,
            }

        dialogue_history.append(current_dialogue)

    _remove_patient_context(sub_memory)
    memory[section] = sub_memory
    return memory, dialogue_history


def initialize_memory(patient: dict[str, str], templates: dict[str, list[dict]]) -> dict:
    memory = {"basic": patient}
    for section, template in templates.items():
        memory[section] = get_format_from_template(template)
    return memory


def run_consultation(config: ProjectConfig) -> tuple[dict, dict[str, list[dict]]]:
    os.environ.setdefault(
        "CONSULTATION_MODEL_NORMAL",
        config.models.get("normal", "Qwen/Qwen3-8B"),
    )
    os.environ.setdefault(
        "CONSULTATION_MODEL_AWQ",
        config.models.get("awq", "Qwen/Qwen3-8B-AWQ"),
    )
    os.environ.setdefault(
        "CONSULTATION_MODEL_14B",
        config.models.get("qwen14b", "Qwen/Qwen3-14B"),
    )

    templates = load_section_templates(config)
    memory = initialize_memory(config.patient, templates)
    dialogue: dict[str, list[dict]] = {}

    for section, template in templates.items():
        count = _build_section_count(memory[section])
        memory, section_dialogue = ask_history(
            template=template,
            patient=config.patient,
            memory=memory,
            section=section,
            count=count,
        )
        dialogue[section] = section_dialogue

    output_dir = write_results(
        result_dir=config.result_dir,
        patient=config.patient,
        memory=memory,
        dialogue=dialogue,
    )
    print(f"结果已写入: {output_dir}")
    print(memory)
    return memory, dialogue
