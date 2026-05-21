from client_llm_14B import call_llm_qwen
import json
import ast
# 实现对回答内容的一个history匹配，返回具体匹配的字段列表
def match_history(question, answer):
    """
    params: question:当前对话的问题，answer:当前患者的回答。
    return: 匹配history的列表。
    """
    extend_information = {}
    extend_information["现病史"] = "当前就诊的原因及发现时间，如肺结节的发现、检查及症状的情况（如咳嗽、胸痛、呼吸困难等）。是否曾进行胸部CT检查、结节的位置、大小等影像学描述。结节的处理与复查情况，是否有药物治疗等。"
    extend_information["既往史"] = "包括患者的基础疾病历史，如高血压、糖尿病、冠心病等以及其病程、治疗方式及药物使用情况。"
    extend_information["个人史"] = "长期居住的地方、吸烟、饮酒习惯等。是否有其他危险行为如不良的生活习惯、接触环境等。"
    extend_information["月经史"] = "适用于女性患者，主要涉及月经初潮、绝经时间、月经周期的规律性、是否有痛经等信息。"
    extend_information["婚育史"] = "包括结婚情况、子女情况及其健康状况。"
    extend_information["家族史"] = "患者家族中是否有遗传疾病史、癌症史等。包括父母、兄弟姐妹的健康状况及遗传疾病的情况。"

    system = (
                "你是医学问诊助手，请在尽可能全面以及严谨的前提下，"
                "认为患者的回答是否与现病史，既往史，个人史，月经史，婚育史，家族史相关。"
                "禁止输出Markdown代码块。"
            )
    present_history = extend_information["现病史"]
    past_history = extend_information["既往史"]
    personal_history = extend_information["个人史"]
    period_history = extend_information["月经史"]
    marital_history = extend_information["婚育史"]
    family_history = extend_information["家族史"]
    hint = (
        f"已知现病史的内容一般是{present_history}，既往史的内容一般是{past_history}，个人史的内容一般是{personal_history}，月经史的内容一般是{period_history}，婚育史的内容一般是{marital_history}，家族史的内容一般包括{family_history}。对患者的提问是{question},患者的回答是{answer}。"
    )
    text = f"{hint}\n请根据提示内容，给出最后认为患者的回答与哪些临床内容相关。如果是相关的内容，请返回一个列表，比如[\"现病史\",\"既往史\"]。如果没有任何相关的内容，则返回None。"
    model_result = call_llm_qwen(system, text)

    result = []
    print ("模型判断患者的回答与哪些内容相关联", model_result)
    if "现病史" in model_result:
        result.append("present_history")
    if "既往史" in model_result:
        result.append("past_history")
    if "个人史" in model_result:
        result.append("personal_history")
    if "月经史" in model_result:
        result.append("period_history")
    if "婚育史" in model_result:
        result.append("marital_history")
    if "家族史" in model_result:
        result.append("family_history")
    return result

def update_section(context_slot, answer, sub_memory, now):
    system = (
                "你是医学问诊助手，请在尽可能全面以及严谨的前提下，"
                "将患者的回答与已经的提取的信息进行对比，然后对已经提取的信息进行一个更新。"
                "禁止输出Markdown代码块。"
            )
    question = context_slot["prompt_q"]
    hint = (
        f"已知对患者的问题是{question}，患者的回答是{answer}，已经提取的信息是{json.dumps(sub_memory, ensure_ascii=False)}。如果患者回答中没有严格出现提取信息的相关内容，请直接跳过该字段。已知当前的时间为{now}。"
    )
    text = f"{hint}\n请根据提示内容，给出最后认为需要更新的内容。如果是需要更新的内容，请只需要修改value部分的值即可，返回一个严格的字典格式的修改结果，保持格式的原样。如果没有任何相关的内容，则返回空字典。"
    model_result = call_llm_qwen(system, text)
    model_result_dict = ast.literal_eval(model_result)
    print ("更新的值", model_result_dict)
    if context_slot["slot"] in model_result_dict.keys():
        del model_result_dict[context_slot["slot"]]
    if not model_result_dict:
        return sub_memory
    for key, new_value in model_result_dict.items():
        print(key, new_value)
        if key not in sub_memory.keys():
            for old_key, old_value in sub_memory.items():
                if isinstance(old_value, dict):
                    if key in old_value.keys():
                        old_value[key] = new_value
            continue         
        old_value = sub_memory[key]
        if new_value == old_value:
            continue
        if key == context_slot["slot"]:
            continue
        if type(new_value) != type(old_value):
            if key in old_value.keys():
                old_value[key] = new_value
        sub_memory[key] = new_value
        print (f"{key}的值由{old_value}更新成{new_value}")
    return sub_memory
# 对不同的history进行修改
def update_history(context_slot, memory, answer, now):
    """
    params: memory为需要修改和预置的history，answer是患者的回答
    return: 修改后的memory
    """
    match_history_list = match_history(context_slot["prompt_q"], answer)
    for item in match_history_list:
        sub_update = update_section(context_slot, answer, memory[item], now)
        memory[item] = sub_update
    return memory