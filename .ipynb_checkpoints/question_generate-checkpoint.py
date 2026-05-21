# 根据回答生成问题
from client_llm_normal import call_llm_normal
import json
from datetime import datetime
now = datetime.now().date()
def _is_yes(text: str) -> bool:
    # 只认以 YES 开头的输出，避免 "NO, YES" 或解释性文字
    first = text.strip().upper().split()
    return len(first) > 0 and first[0] == "YES"


def polish_question(ask_slot, memory):
    # 调用生成这个ask_slot的相关问题
    system = (
        "你是医学问诊助手，请在**不违背问题本意**的前提下，"
        "让问题更自然、简洁，必要时补充1-2个例子或可选项使得受访者能够往期望的回答上靠近。"
        "禁止输出Markdown代码块。"
    )
    structured_format = ask_slot["structure_format"] 
    hint = (
        "若问题涉及日期时间，请提示：1年内精确到月、1月内精确到日，也可说“X天前/周前”。\n"
        f"当前已知关于患者的信息片段：{json.dumps(memory, ensure_ascii=False)}，注意一下对话对象身份，尽可能提问针对患者的问题，语气亲切自然。"
        f"最后希望的提取信息格式为：{json.dumps(structured_format, ensure_ascii=False)}。"
    )
    prompt = ask_slot["prompt"]
    text = f"{hint}\n原问题：{prompt}\n请给出最终要对患者提的问题："
    return {"slot": ask_slot["slot"], "prompt_q":call_llm_normal(system, text)}

def generate_question(rule_slot, current_slot, memory, current_history, current_count):
    """
    rule_slot:按照规则制定的下一个问题
    current_slot:最近的一个slot
    memory：已经提取的上下文
    current_history:最近的slot回答结构化结果
    """
    # print ("rule_slot", rule_slot)
    # print ("current_slot", current_slot)
    # print ("memory", memory)
    # print ("current_history", current_history)
    # 判断current_slot是否为空
    ask_slot = None
    if current_slot == None and rule_slot != None:
        ask_slot = rule_slot
        return polish_question(ask_slot, memory)
    elif current_slot != None and rule_slot != None:
        if current_slot != rule_slot and current_count < 3:
            # 利用大模型判断是否需要继续追问
            system = (
                "你是医学问诊助手，请在尽可能全面以及严谨的前提下，"
                "认为患者的回答以及提取信息是否达到了预期的效果，"
                "禁止输出Markdown代码块。"
            )
            expectations = current_slot["expectations"]
            current_question = current_history["question"]
            current_answer = current_history["answer"]
            current_structured = current_history["structured"]
            hint = (
                f"已知医生希望该问题的回答的预期效果为{expectations}，问题是{current_question}，受访者的回答是{current_answer}，最后结构化的信息是{json.dumps(current_structured, ensure_ascii=False)}。"
            )
            text = f"{hint}\n请给出最后的结果：yes或者no，两个之一。yes表示已经达到了预期效果，no表示没有达到预期效果。"
            result = call_llm_normal(system, text)
            print ("模型判断患者的问题是否达到预期", result)
            if _is_yes(result):
                ask_slot = rule_slot
                return polish_question(ask_slot, memory)
            else:
                ask_slot = current_slot
                # 实现对current_slot的继续追问
                system = (
                    "你是医学问诊助手，你已经向患者提了问题，但是患者的回答没有提供你想要的完整信息。请在不改变问题原来意思的前提下，"
                    "对患者进行一个该问题的追问，以收集有效的完整信息。让问题更自然、简洁，必要时补充1-2个例子或可选项。"
                    "禁止输出Markdown代码块。"
                )
                current_question = current_history["question"]
                current_answer = current_history["answer"]
                structured_format = current_slot["structure_format"]
                hint = (f"已知既往的对话历史为:问题为{current_question}，患者回答为{current_answer}，医生期望的效果是提取出{structured_format}中的内容。")
                text = f"{hint}\n你可以根据医生提取的期望效果中举相关的例子，方便患者更好理解问题的意图。请给出一句最终对患者的追问。"
                return {"slot": ask_slot["slot"], "prompt_q":call_llm_normal(system, text)}
        else:
            ask_slot = rule_slot
            return polish_question(ask_slot, memory)
    else:
        return {"slot": None, "prompt_q":None}
            