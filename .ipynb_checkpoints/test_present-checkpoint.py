import json
from prompt_builder import build_question_prompt, build_extraction_prompt, build_openanswer_prompt
from client_llm_normal import call_llm_normal
from client_llm_awq import call_llm_awq
from rule_engine import get_next_slot
from answer_handler import handle_answer, AnswerType, context_update, context_future
from enum import Enum
retry_counts = {}  # FUZZY 的追问次数
MAX_RETRY_FUZZY = 1
import json
from question_generate import generate_question

def is_valid_json(structured: str) -> bool:
    if not structured or not structured.strip():
        return False
    try:
        json.loads(structured)
        return True
    except json.JSONDecodeError:
        return False

def get_slot_from_template(template, slot_name):
    # 按优先级排序
    for slot in sorted(template, key=lambda x: x.get("priority", 0)):
        name = slot.get("slot")
        if name == slot_name:
            return slot
    return None


memory = {}      # 已收集的 slot:value
asked = set()    # 已提过的 slot
future_memory = {}

# 在memory中添加被问患者的姓名
memory["患者姓名"] = "张三"
memory["性别"] = "女"
memory["患者年龄"] = "60"


# 1. 加载模板
with open("question_logic/present_history.json", "r", encoding="utf-8") as f:
    template1 = json.load(f)


# 按优先级排序
for slot in sorted(template1, key=lambda x: x.get("priority", 0)):
    name = slot.get("slot")
    structured_format = slot.get("structure_format")
    if name in asked:
        continue
    else:
        future_memory[name] = structured_format


current_slot = None
context = ""
current_history = {}
print("🤖 问诊开始")
while True:
    # 1. 获取规则待问的问题slot
    slot = get_next_slot(template1, memory, asked)
    # 2. 获取上下文待问的问题
    if slot["priority"] == 1:
        current_slot = None
    # print ("rule_slot", slot)
    context_slot = generate_question(slot, current_slot, memory, current_history)
    # print ("context_slot",context_slot)
    if context_slot["slot"] == None:
        break

    print("🤖", context_slot["prompt_q"])

    # 3. 人工模拟用户输入
    user_input = input("👤 ")
    
    # 3.5 判断用户回答的类型
    result = handle_answer(
    prompt_q = context_slot["prompt_q"],
    user_input=user_input,
    slot=get_slot_from_template(template1, context_slot["slot"]),
    call_llm_fn=call_llm_awq)
    # print (result)
    
    if result["type"] == AnswerType.KNOWLEDGE_QUERY:
        # 回答用户的开放性问题
        system = (
            "你是医学问诊助手，请在尽可能全面以及严谨的前提下，"
            "回答患者对你的提问，"
            "禁止输出Markdown代码块。"
        )
        hint = (
            f"回答尽可能地简单易懂。"
        )
        text = f"{hint}\n问题：{user_input}，\n请给出最后的回答。"
        result = call_llm_normal(system, text)
        print("🤖 (知识回答)", result)
        current_slot = get_slot_from_template(template1, context_slot["slot"])
        current_history["question"] = ""
        current_history["answer"] = ""
        current_history["structured_format"] = ""
        current_history["structured"] = ""
    else:
        # 4. 解析用户回答
        structured = result["data"]["value"]
        print (structured)
        data = json.loads(structured)
        memory[data["slot"]] = data["value"]
        # del future_memory[data["slot"]]
        # print (context_update(user_input, memory, call_llm_normal))
        # print (context_future(user_input, future_memory, call_llm_normal))
        asked.add(data["slot"])
        current_slot = get_slot_from_template(template1, context_slot["slot"])
        current_history["question"] = context_slot["prompt_q"]
        current_history["answer"] = user_input
        current_history["structured_format"] = current_slot["structure_format"]
        current_history["structured"] = data
    # print(memory)
# 5. 结束
print("✅ 问诊结束，结果：", memory)



