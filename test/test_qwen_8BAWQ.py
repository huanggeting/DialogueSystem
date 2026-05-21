from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
model_name = "Qwen/Qwen3-8B-AWQ"

# load the tokenizer and the model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

# prepare the model input
prompt = """
你是医学问诊助手，结合问题和回答，按照输出格式中定义的字段，对问题和回答进行结构化，请严格按照下述格式，不要包含markdown块。
- 如果回答是只包括年份，回答格式为YYYY
- 如果回答是只包括年份和月份，回答格式为YYYY-MM
- 如果回答包括年份、月份和日，回答格式为YYYY-MM-DD
- 如果回答存在多少天前这种描述，现在的时间参考是2025年10月28日，回答格式为YYYY-MM-DD
- 问题: 张三女士，您好。请问您之前进行肺部CT检查的时间是多久以前呢？
- 回答: 十天之前。
"""
messages = [
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=True # Switches between thinking and non-thinking modes. Default is True.
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

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

print("thinking content:", thinking_content)
print("content:", content)
