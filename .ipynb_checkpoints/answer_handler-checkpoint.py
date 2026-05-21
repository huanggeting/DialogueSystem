# 回答处理模型：返回结果给对话管理模型 
import json
from enum import Enum
from datetime import datetime
import json
from prompt_builder import build_extraction_prompt
import re
from client_llm_awq import call_llm_awq

# 返回一个 datetime 对象，包含当前本地日期和时间
now = datetime.now().date()
# print(now)  # 例如：2025-07-29 14:23:45.123456

class AnswerType(Enum):
    KNOWLEDGE_QUERY = "knowledge_query"  # 用户在提问，需要知识回答
    FUZZY = "fuzzy"                      # 完全模糊（不知道/忘记了）
    SEMI_FUZZY = "semi_fuzzy"            # 半模糊（部分信息，需追问）
    VALID = "valid"                      # 有效回答（完整信息）

def is_valid_json(structured: str) -> bool:
    if not structured or not structured.strip():
        return False
    try:
        json.loads(structured)
        return True
    except json.JSONDecodeError:
        return False

def _pick_label(text: str, choices=("FUZZY","VALID")) -> str:
    # 从模型输出里只抽取第一个合法标签，避免“FUZZY/SEMI_FUZZY/…”或多余说明干扰
    m = re.search(r'\b(FUZZY|SEMI_FUZZY|VALID)\b', text.upper())
    return m.group(1) if m else ""

def _is_yes(text: str) -> bool:
    # 只认以 YES 开头的输出，避免 "NO, YES" 或解释性文字
    first = text.strip().upper().split()
    return len(first) > 0 and first[0] == "YES"
    
def classify_answer(prompt_q, user_input):
    text = user_input.strip()

    # 1) 判断是否为知识提问（精确 YES）
    system = (
            "你是医学问诊助手，请在尽可能全面以及严谨的前提下，"
            "判断医患对话中，患者是否是在向医生咨询临床知识，"
            "禁止输出Markdown代码块。"
    )
    hint = (
        f"对话中医生提问内容:{prompt_q}，患者的回答内容为:{text}。"
        f"患者的回答如果是陈述句，就不是在向医生咨询临床知识。除非是类似什么是咯血？这样的疑问句。"
    )
    text = f"{hint}\n请给出最后的结果：yes或者no，两个之一。"
    resp = call_llm_awq(system, text, False)
    if _is_yes(resp):
        return {"type": AnswerType.KNOWLEDGE_QUERY, "data": None, "message": "用户在提问，需要科普回答"}
    return {"type": AnswerType.VALID, "data":None, "message":"用户在回答提出的问题"}



def handle_answer(prompt_q, user_input, slot):
    classify_result = classify_answer(prompt_q, user_input)
    if classify_result["type"] == AnswerType.KNOWLEDGE_QUERY:
        return {"type": AnswerType.KNOWLEDGE_QUERY, "data": None, "message": "用户在提问，需要科普回答"}
    else:
        # 正常的回答问题==》结构化
        structure_format = slot.get("structure_format", {})
        expectations = slot.get("expectations", {})
        system = f"""
        你是一个临床问诊助手。患者对医生特定的问题已经进行了回答，现在需要你根据当前的问题和回答，做出对应临床信息的提取。
        """
        hint = (
        f"对话中医生提问内容:{prompt_q}，患者的回答内容为:{user_input}。需要根据患者回答提取的信息格式是：{structure_format}。在提取过程中需要注意的事项是：{expectations}。已知当前的时间为{now}。"
        )
        text = f"{hint}\n按照需要提取的信息格式以及注意事项，对问题的回答进行json结构化，禁止输出Markdown代码块。"
        # print("system",system)
        # print("text", text)
        structured = call_llm_awq(system, text, False)
        while is_valid_json(structured) == False:
            structured = call_llm_awq(system, text,False)
        return {"type": AnswerType.VALID, "data": {"slot": slot["slot"], "value": structured}, "message": "有效回答"}



