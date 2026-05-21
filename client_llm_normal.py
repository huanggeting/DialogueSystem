# llm_client_instruct.py

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
import os

def clean_json_mark(text):
    text = re.sub(r"^```.*$\n?", "", text, flags=re.MULTILINE)
    return text.strip()

model_dir = os.getenv("CONSULTATION_MODEL_NORMAL", "Qwen/Qwen3-8B")

# 加载 tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_dir)

# 加载模型
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    torch_dtype="auto",
    device_map="auto"
)



def call_llm_normal(system:str, prompt: str) -> str:
    """
    使用 "Qwen/Qwen3-8B" 模型生成对话回复。

    参数:
        prompt (str): 用户的提问或输入文本。
    返回:
        str: 模型生成的回复文本。
    """
    # 构造对话格式输入
    messages = [{"role": "user", "content": prompt},{"role": "system", "content": system}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False )# Switches between thinking and non-thinking modes. Default is True.
        # 确保 text 是一个字符串
    model_inputs = tokenizer(text, return_tensors="pt").to(model.device)


    # conduct text completion
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=32768
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 
    # parsing thinking content
    try:
        # rindex finding 151668 (</think>)
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0
    
    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
    
    # print("thinking content:", thinking_content)
    # print("content:", content)

    return content.strip()
