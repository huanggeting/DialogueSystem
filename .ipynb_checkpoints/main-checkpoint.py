import json
from prompt_builder import build_question_prompt, build_extraction_prompt, build_openanswer_prompt
from client_llm_normal import call_llm_normal
from client_llm_awq import call_llm_awq
from client_llm_14B import call_llm_qwen
from rule_engine import get_next_slot
from answer_handler import handle_answer, AnswerType
from context_update import update_history
from enum import Enum
retry_counts = {}  # FUZZY 的追问次数
MAX_RETRY_FUZZY = 1
import json
from question_generate import generate_question
import os
import re
from datetime import datetime
now = datetime.now().date()

def clean_input(text: str) -> str:
    # 移除非标准字符
    return re.sub(r'[^\x00-\x7F]+', '', text)  # 保留基本的ASCII字符，删除非ASCII字符

print ("处理结果",clean_input("不是。"))

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

def get_format_from_template(template):
    result = {}
    for slot in sorted(template, key = lambda x : x.get("priority", 0)):
        name = slot.get("slot")
        value = slot.get("structure_format")["value"]
        result[name] = value
    return result
# 实现一个单个部分的追问，返回一个memory(格式为slot: value)的字典
"""
params: template模板，当前section的所有问题模板; basic内容，当前患者的基本信息。memory内容，所有结构化的内容。section是该template的名称。
return: memory内容，格式为slot: value
"""
def ask_history(template, basic, memory, section, count):
    # 定义问答历史对话文件
    dialogue_history = []
    # 初始化基本信息
    # print(section)
    sub_memory = memory[section]
    sub_memory["患者姓名"] = basic["患者姓名"]
    sub_memory["性别"] = basic["性别"]
    sub_memory["患者年龄"] = basic["患者年龄"]
    if int(sub_memory["患者年龄"]) >= 50 and sub_memory["性别"] == "女":
        sub_memory["是否已经达到可能绝经年龄"] = "True"
    else:
        sub_memory["是否已经达到可能绝经年龄"] = "False"
    
    current_slot = None
    context = ""
    current_history = {}
    asked = set()    # 已提过的 slot
    print("🤖 问诊开始")
    while True:
        current_dialogue = {}
        sub_memory = memory[section]
        # 1. 获取规则待问的问题slot
        slot = get_next_slot(template, sub_memory, asked)
        # 2. 获取上下文待问的问题
        if slot == None:
            break
        if slot["priority"] == 1:
            current_slot = None
            current_count = 0
        if current_slot != None:
            current_count = count[current_slot["slot"]]
        # print ("rule_slot", slot)
        context_slot = generate_question(slot, current_slot, sub_memory, current_history, current_count)
        count[context_slot["slot"]] = count[context_slot["slot"]] + 1
        # print ("context_slot",context_slot)
        if context_slot["slot"] == None:
            break
    
        print("🤖", context_slot["prompt_q"])
        current_dialogue["问题"] = context_slot["prompt_q"]
        # 3. 人工模拟用户输入
        user_input = input("👤 ")
        current_dialogue["回答"] = user_input
        # 3.5 判断用户回答的类型
        result = handle_answer(
        prompt_q = context_slot["prompt_q"],
        user_input=user_input,
        slot=get_slot_from_template(template, context_slot["slot"]))
        # print (result)
        # 添加次数限制
        
        
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
            current_slot = get_slot_from_template(template, context_slot["slot"])
            current_history["question"] = ""
            current_history["answer"] = ""
            current_history["structured_format"] = ""
            current_history["structured"] = ""
            current_dialogue["知识回答"] = result
        else:
            # 4. 解析用户回答
            structured = result["data"]["value"]
            print ("提取结果:",structured)
            current_dialogue["提取结果"] = structured
            data = json.loads(structured)
            sub_memory[data["slot"]] = data["value"]
            asked.add(data["slot"])
            memory = update_history(context_slot, memory, user_input,now)
            current_slot = get_slot_from_template(template, context_slot["slot"])
            current_history["question"] = context_slot["prompt_q"]
            current_history["answer"] = user_input
            current_history["structured_format"] = current_slot["structure_format"]
            current_history["structured"] = data
        dialogue_history.append(current_dialogue)
    item1 = sub_memory.pop("患者姓名", None)
    item2 = sub_memory.pop("性别", None)
    item3 = sub_memory.pop("患者年龄", None)
    memory[section] = sub_memory
    return memory, dialogue_history

if __name__ == "__main__":
    memory = {}      # 已收集的 slot:value
    dialogue = {} #对话内容
    basic = {}
    count = {} #存储询问的次数进行强制限制
    # 在memory中添加被问患者的姓名
    basic["患者姓名"] = "张三"
    basic["性别"] = "女"
    basic["患者年龄"] = "60"
    memory["basic"] = basic
    with open("question_logic/present_history.json", "r", encoding="utf-8") as f1:
        template_present = json.load(f1)
    with open("question_logic/past_history.json", "r", encoding="utf-8") as f2:
        template_past = json.load(f2)
    with open("question_logic/personal_history.json", "r", encoding="utf-8") as f3:
        template_personal = json.load(f3)
    if basic["性别"] == "女":
        with open("question_logic/period_history.json", "r", encoding="utf-8") as f4:
            template_period = json.load(f4)
    with open("question_logic/marital_history.json", "r", encoding="utf-8") as f5:
        template_marital = json.load(f5)
    with open("question_logic/family_history.json", "r", encoding="utf-8") as f6:
        template_family = json.load(f6)
    memory["present_history"] = get_format_from_template(template_present)
    memory["past_history"] = get_format_from_template(template_past)
    memory["personal_history"] = get_format_from_template(template_personal)
    if basic["性别"] == "女":
        memory["period_history"] = get_format_from_template(template_period)
    memory["marital_history"] = get_format_from_template(template_marital)
    memory["family_history"]= get_format_from_template(template_family)

    count = {}
    for key,item in memory["present_history"].items():
        count[key] = 0
    present_history = ask_history(template_present, basic, memory, "present_history", count)
    memory = present_history[0]
    dialogue["present_history"] = present_history[1]

    count = {}
    for key,item in memory["past_history"].items():
        count[key] = 0
    past_history = ask_history(template_past, basic, memory, "past_history", count)
    memory = past_history[0]
    dialogue["past_history"] = past_history[1]

    count = {}
    for key,item in memory["personal_history"].items():
        count[key] = 0
    personal_history = ask_history(template_personal, basic, memory, "personal_history",count)
    memory = personal_history[0]
    dialogue["personal_history"] = personal_history[1]
    
    if basic["性别"] == "女":
        count = {}
        for key,item in memory["period_history"].items():
            count[key] = 0
        period_history = ask_history(template_period, basic, memory, "period_history", count)
        memory = period_history[0]
        dialogue["period_history"] = period_history[1]

    count = {}
    for key,item in memory["marital_history"].items():
        count[key] = 0
    marital_history = ask_history(template_marital, basic, memory, "marital_history", count)
    memory = marital_history[0]
    dialogue["marital_history"] = marital_history[1]

    count = {}
    for key,item in memory["family_history"].items():
        count[key] = 0
    family_history = ask_history(template_family, basic, memory, "family_history", count)
    memory = family_history[0]
    dialogue["family_history"] = family_history[1]

    name = basic["患者姓名"]
    file_path = f"result_files/{name}"
    os.makedirs(file_path, exist_ok=True)

    all_present = {}
    all_present["对话"] = dialogue["present_history"]
    all_present["提取信息"] = memory["present_history"]
    with open(file_path+"/present_history", "w", encoding="utf-8") as f:
        json.dump(all_present, f, ensure_ascii=False, indent=4)

    all_past = {}
    all_past["对话"] = dialogue["past_history"]
    all_present["提取信息"] = memory["past_history"]
    with open(file_path+"/past_history", "w", encoding="utf-8") as f:
        json.dump(all_past, f, ensure_ascii=False, indent=4)

    all_personal = {}
    all_personal["对话"] = dialogue["personal_history"]
    all_personal["提取信息"] = memory["personal_history"]
    with open(file_path+"/personal_history", "w", encoding="utf-8") as f:
        json.dump(all_personal, f, ensure_ascii=False, indent=4)

    if basic["性别"] == "女":
        all_period = {}
        all_period["对话"] = dialogue["period_history"]
        all_period["提取信息"] = memory["period_history"]
        with open(file_path+"/period_history", "w", encoding="utf-8") as f:
            json.dump(all_period, f, ensure_ascii=False, indent=4)

    all_marital = {}
    all_marital["对话"] = dialogue["marital_history"]
    all_marital["提取信息"] = memory["marital_history"]
    with open(file_path+"/marital_history", "w", encoding="utf-8") as f:
        json.dump(all_marital, f, ensure_ascii=False, indent=4)

    all_family = {}
    all_family["对话"] = dialogue["family_history"]
    all_family["提取信息"] = memory["family_history"]
    with open(file_path+"/family_history", "w", encoding="utf-8") as f:
        json.dump(all_family, f, ensure_ascii=False, indent=4)
    print (memory)
    
    

