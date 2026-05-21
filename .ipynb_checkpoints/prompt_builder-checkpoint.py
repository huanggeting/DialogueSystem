from jinja2 import Template
from datetime import datetime
import json
now = datetime.now()




QUESTION_TMPL = Template("""
你是医学问诊助手。请根据以下信息，生成一句自然的提问语句（注意患者与被提问者的关系）。生成的提问语句可以参考推荐问题，尽量不要对问题本意做出太大的改变。现在的时间是{{now}}：
- slot: {{ slot }}
- 推荐问题: {{prompt}}
- 类型: {{ question_type }}
- 上下文:
{% for c in context %}
  - {{ c.slot }}: {{ c.value }}
{% endfor %}
""")

EXTRACTION_TMPL_json = Template("""
你是医学问诊助手，你需要以医生的视角进行提问和提取有用信息，并结合问题和回答，按照输出格式中定义的字段，对问题和回答进行json结构化，请严格按照下述格式，不要包含markdown块。现在的时间是{{now}}。请根据：
- 问题: {{question}}
- slot: {{ slot }}
- 类型: {{ question_type }}
- 回答: {{ user_input }}
输出格式：
{{structure_format}}如果回答中没有有效信息，就将value设为Unknown
""")

EXTRACTION_datetime_json = Template("""
你是医学问诊助手，结合问题和回答，按照输出格式中定义的字段，对问题和回答进行结构化，请严格按照下述格式，不要包含markdown块。
- 如果回答是只包括年份，回答格式为YYYY
- 如果回答是只包括年份和月份，回答格式为YYYY-MM
- 如果回答包括年份、月份和日，回答格式为YYYY-MM-DD
- 如果回答存在多少天前这种描述，现在的时间参考是{{now}}，回答格式为YYYY-MM-DD
- 问题: {{question}}
- slot: {{ slot }}
- 类型: {{ question_type }}
- 回答: {{ user_input }}
输出格式：
{{structure_format}}
""")


EXTRACTION_TMPL_OPENQUESTION = Template("""你是一个医学科普助手。用户问的是一个医学知识问题，请用简洁易懂的语言回答。用户问题: {{user_input}}""")

def build_question_prompt(slot, context):
    return QUESTION_TMPL.render(**slot, context=context)

def build_openanswer_prompt(user_input):
    return EXTRACTION_TMPL_OPENQUESTION.render(user_input=user_input)

def build_extraction_prompt(prompt_q, slot, user_input):
    structure_json = json.dumps(slot.get("structure_format", {}), ensure_ascii=False, indent=2)
    if slot["question_type"] == "datetime":
        return EXTRACTION_datetime_json.render(now = now,
                                       question = slot["prompt"],
                                       slot=slot["slot"],
                                 question_type=slot["question_type"],
                                structure_format = structure_json,
                                 user_input=user_input)
    else:
        return EXTRACTION_TMPL_json.render(now = now,
                                       question = slot["prompt"],
                                       slot=slot["slot"],
                                 question_type=slot["question_type"],
                                structure_format = structure_json,
                                 user_input=user_input)