# # -*- coding: utf-8 -*-
# import json
# import datetime
# from typing import Any, Dict, List, Optional, Tuple, Callable
# from client_llm_normal import call_llm_normal
# from client_llm_awq import call_llm_awq

# # ============ 1) 工具函数：取值 / 条件判断 / 时间规范化 ============

# def dot_get(data: Dict[str, Any], path: str, default=None):
#     """支持 'a.b.c' 取值；若不存在返回 default。"""
#     cur = data
#     for key in path.split("."):
#         if isinstance(cur, dict) and key in cur:
#             cur = cur[key]
#         else:
#             return default
#     return cur

# def eval_condition(ans: Dict[str, Any], cond: Dict[str, Any]) -> bool:
#     """支持 operator: '=' / 'contains'"""
#     slot = cond["slot"]
#     op = cond.get("operator", "=")
#     val = cond.get("value")
#     got = dot_get(ans, slot)
#     if op == "=":
#         return str(got) == str(val)
#     if op == "contains":
#         if got is None:
#             return False
#         return str(val) in str(got)
#     raise ValueError(f"Unsupported operator: {op}")

# def eval_conditions(ans: Dict[str, Any], conds: List[Dict[str, Any]]) -> bool:
#     """全部满足才返回 True（AND）"""
#     if not conds:
#         return True
#     return all(eval_condition(ans, c) for c in conds)

# def normalize_relative_date(raw: str, base_date: str = "2025-10-28") -> Optional[str]:
#     """
#     将“X天前/周前/月前/年前”粗略标准化为 YYYY-MM-DD。
#     简化实现：仅处理中文 '天/周/月/年' + '前'；失败返回 None。
#     """
#     raw = (raw or "").strip()
#     if not raw:
#         return None
#     try:
#         base = datetime.datetime.strptime(base_date, "%Y-%m-%d").date()
#         units = {"天": "days", "周": "weeks", "月": "months", "年": "years"}
#         for zh, u in units.items():
#             if raw.endswith(f"{zh}前"):
#                 num = int(raw[:-2])  # 去掉“X”和“前”，只取数字；粗略写法“10天前”
#                 if u == "days":
#                     return str(base - datetime.timedelta(days=num))
#                 if u == "weeks":
#                     return str(base - datetime.timedelta(weeks=num))
#                 # 月/年：用近似30天/365天（足够问诊记录）
#                 if u == "months":
#                     return str(base - datetime.timedelta(days=30 * num))
#                 if u == "years":
#                     return str(base - datetime.timedelta(days=365 * num))
#         # 若不是相对说法，直接尝试解析 YYYY[-MM[-DD]]
#         for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
#             try:
#                 dt = datetime.datetime.strptime(raw, fmt)
#                 if fmt == "%Y":
#                     return f"{dt.year:04d}"
#                 if fmt == "%Y-%m":
#                     return f"{dt.year:04d}-{dt.month:02d}"
#                 return dt.strftime("%Y-%m-%d")
#             except Exception:
#                 pass
#     except Exception:
#         pass
#     return None

# # ============ 2) LLM 封装（可换成自家/本地 OpenAI 兼容服务） ============

# class LLMClient:
#     """
#     你可以替换为任意 OpenAI 兼容接口：
#     - base_url=http://localhost:8000/v1  (vLLM / sglang / TGI)
#     - model="Qwen/Qwen3-4B-Instruct" 等
#     这里给一个“占位实现”，实际接入请改写 generate()。
#     """
#     def __init__(self, enabled: bool = False):
#         self.enabled = enabled

#     def generate(self, system: str, prompt: str, max_tokens: int = 256) -> str:
#         if not self.enabled:
#             # 关闭 LLM 时，直接返回规则提示，保证系统可运行
#             return prompt
#         # ===== 在此处接入你的 LLM =====
#         return call_llm_normal(system, prompt)

# import textwrap
# import re

# SAFE_JSON_PATTERN = re.compile(r"\{.*\}", re.S)

# def _compact_answers(ans: Dict[str, Any], max_kv: int = 30) -> Dict[str, Any]:
#     """把已答内容做个轻量摘要，避免 prompt 过长。"""
#     flat = {}
#     def _walk(prefix, obj):
#         if isinstance(obj, dict):
#             for k, v in obj.items():
#                 _walk(f"{prefix}.{k}" if prefix else k, v)
#         else:
#             flat[prefix] = obj
#     _walk("", ans)
#     # 截断
#     items = list(flat.items())[:max_kv]
#     return {k: v for k, v in items}

# def _llm_choose_next(llm: LLMClient,
#                      answers: Dict[str, Any],
#                      candidates: List[Dict[str, Any]]) -> Optional[str]:
#     """
#     让 LLM 在候选中选一个 slot（返回 slot 字符串）。
#     若失败返回 None。
#     """
#     ctx = _compact_answers(answers)
#     # 只给 LLM 必要字段，避免越权
#     brief = [
#         {
#             "slot": c["slot"],
#             "question_type": c.get("question_type", "text"),
#             "prompt": c.get("prompt", ""),
#             "priority": c.get("sub_priority", 9999)
#         } for c in candidates
#     ]
#     system = (
#         "你是医疗问诊流程控制器。任务：在候选问题中选出下一题。\n"
#         "硬规则：\n"
#         "1) 只能从候选列表中选择；\n"
#         "2) 选出最能提升信息增益/安全优先级的一个；\n"
#         "3) 若没有必要继续提问，返回 stop=true；\n"
#         "4) 仅输出 JSON，字段：{\n"
#         '  "slot": "<必须是候选里的slot>",\n'
#         '  "reason": "<简短理由>",\n'
#         '  "stop": false\n'
#         "}\n"
#         "不要输出多余文本或 Markdown。"
#     )
#     user = textwrap.dedent(f"""
#     已有答案摘要(截断)：{json.dumps(ctx, ensure_ascii=False)}
#     候选问题（请二选一/多选一地“只选一个”）：{json.dumps(brief, ensure_ascii=False)}
#     输出 JSON（utf-8 无注释，无换行花哨）。
#     """).strip()

#     raw = llm.generate(system, user, max_tokens=256)
#     m = SAFE_JSON_PATTERN.search(raw)
#     if not m:
#         return None
#     try:
#         obj = json.loads(m.group(0))
#         if obj.get("stop") is True:
#             return "__STOP__"
#         slot = obj.get("slot")
#         # 只允许选择在候选里的 slot
#         if slot and any(c["slot"] == slot for c in candidates):
#             return slot
#     except Exception:
#         pass
#     return None

# # ============ 3) 生成器主体：读取 schema / 选题 / LLM 辅助生成 ============

# class QuestionGenerator:
#     def __init__(self, schema: Dict[str, Any], llm: Optional[LLMClient] = None):
#         self.schema = schema
#         self.llm = llm or LLMClient(enabled=False)
#         # 预展开成 [ (group_name, group_priority, question_dict) ... ]
#         self.index: List[Tuple[str, int, Dict[str, Any]]] = []
#         for group_name, group_body in schema.items():
#             if not isinstance(group_body, dict) or "questions" not in group_body:
#                 # 跳过 meta 等非问题节点
#                 continue
#             gprio = group_body.get("priority", 9999)
#             for q in group_body["questions"]:
#                 self.index.append((group_name, gprio, q))
#         # 按 group_priority -> sub_priority 排序
#         self.index.sort(key=lambda x: (x[1], x[2].get("sub_priority", 9999)))

#     def _llm_polish(self, question_prompt: str, context: Dict[str, Any]) -> str:
#         """
#         让 LLM 在不改变医学语义的情况下做：
#         - 口吻自然化
#         - 自动追加可选项举例（若 question_type 是 enum-like）
#         - 若是 datetime，提醒“可说‘X天前/周前’”
#         """
#         system = (
#             "你是医学问诊助手，请在**不改变医学含义**的前提下，"
#             "让问题更自然、简洁，必要时补充1-2个例子或可选项。"
#             "禁止输出Markdown代码块。"
#         )
#         hint = (
#             "若问题涉及日期时间，请提示：1年内精确到月、1月内精确到日，也可说“X天前/周前”。\n"
#             f"当前已知信息片段：{json.dumps(context, ensure_ascii=False)[:400]}"
#         )
#         text = f"{hint}\n原问题：{question_prompt}\n请给出最终要对患者说的一句话："
#         return self.llm.generate(system, text, max_tokens=160)

#     def next_question(self, answers: Dict[str, Any],
#                   llm_topk: int = 6) -> Optional[Dict[str, Any]]:
#         """
#         规则筛选 -> LLM 决策（从 top-k 候选中挑一个）。
#         """
#         # 1) 规则层：筛出“未回答且条件成立”的候选
#         candidates = []
#         for group_name, _, q in self.index:
#             slot = q["slot"]
#             # 未回答才入候选
#             if dot_get(answers, slot) in (None, "") and eval_conditions(answers, q.get("conditions", [])):
#                 # 缓存 group 以便返回
#                 qq = dict(q)
#                 qq["group"] = group_name
#                 candidates.append(qq)
    
#         if not candidates:
#             return None
    
#         # 2) 优先级初排：sub_priority 越小越靠前；取前 k 交给 LLM
#         candidates.sort(key=lambda c: c.get("sub_priority", 9999))
#         topk = candidates[:llm_topk]
    
#         # 3) 让 LLM 在 top-k 中挑一个；失败则回退到第一个
#         chosen_slot = _llm_choose_next(self.llm, answers, topk)
#         if chosen_slot == "__STOP__":
#             return None
#         if not chosen_slot:
#             chosen = topk[0]
#         else:
#             chosen = next(c for c in topk if c["slot"] == chosen_slot)
    
#         # 4) 口吻润色（你已有的逻辑）
#         chosen["polished"] = self._llm_polish(chosen.get("prompt", ""), answers)
#         return chosen


#     def postprocess_answer(self, q: Dict[str, Any], user_text: str) -> Any:
#         """
#         简易后处理：
#         - datetime: 尝试标准化相对时间
#         - 其它类型：原样返回（可接LLM结构化抽取）
#         """
#         qtype = q.get("question_type", "text")
#         if qtype == "datetime":
#             norm = normalize_relative_date(user_text)
#             return {"raw": user_text, "normalized": norm or user_text}
#         return user_text

# # ============ 4) 最小示例：循环问答（可替换为你的前端/对话框架） ============

# def load_schema_from_file(path: str) -> Dict[str, Any]:
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)




# if __name__ == "__main__":
#     # 1) 载入你的 JSON（就是你发来的 present_version2.json）
#     schema = load_schema_from_file("present_version2.json")

#     # 2) 是否启用大模型润色（把 enabled=True 并配置 LLMClient.generate）
#     llm = LLMClient(enabled=True)
#     gen = QuestionGenerator(schema, llm)

#     # 3) 一个最小的命令行问答循环
#     answers: Dict[str, Any] = {}
#     print("【智能问诊·问题生成器】启动\n（输入 'quit' 结束）")
#     while True:
#         q = gen.next_question(answers)
#         if not q:
#             print("\n问诊完成（没有更多问题或条件不触发）。")
#             print("收集到的结构化答案：")
#             print(json.dumps(answers, ensure_ascii=False, indent=2))
#             break
#         print(f"\n[{q['group']}] {q.get('slot')}")
#         print("问：", q["polished"])
#         user = input("答：").strip()
#         if user.lower() == "quit":
#             break
#         # 4) 后处理并写入到 answers（支持点号路径）
#         val = gen.postprocess_answer(q, user)
#         # 写入：若 slot 带点号，按层创建
#         def dot_set(d, path, value):
#             keys = path.split(".")
#             for k in keys[:-1]:
#                 d = d.setdefault(k, {})
#             d[keys[-1]] = value
#         dot_set(answers, q["slot"], val)
def resolve_path(memory, path):
    """
    支持通过路径（如 '槽位.子字段'）从 memory 中获取值。
    :param memory: 存储了槽位信息的字典
    :param path: 字符串形式的路径，使用点号分隔（如 '槽位.子字段'）
    :return: 对应路径的值
    """
    parts = path.split(".")
    value = memory
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None  # 如果路径不正确，返回 None
    return value

def check_conditions(slot_info, memory):
    """
    判断给定槽位的所有条件是否在 memory 中都满足。
    条件格式：
      - {"slot": "key", "operator": "=|contains", "value": ...}
    """
    for cond in slot_info.get("conditions", []):
        key = cond["slot"]
        op = cond.get("operator", "=")
        val = cond["value"]
        mem = resolve_path(memory, key)

        # 如果条件是针对 object 类型槽位的子字段
        if isinstance(mem, dict):  # 判断是否是 object 类型
            # 解析对象的子字段并进行条件判断
            for sub_key, sub_val in mem.items():
                if op == "=":
                    # 精确匹配（布尔或字符串）
                    if str(sub_val) != str(val):
                        return False
                elif op == "contains":
                    # 子串匹配，仅对字符串有效
                    if not isinstance(sub_val, str) or val not in sub_val:
                        return False
                elif op == "not_contains":
                    if not isinstance(sub_val, str) or val in sub_val:
                        return False
        elif isinstance(mem, list):#判断是否是 list 类型
            if op == "=":
                for item in mem:
                    if str(val) == item:
                        return True
                return False
            elif op == "contains":
                for item in mem:
                    if str(val) == item:
                        return True
                return False
            elif op == "not_contians":
                for item in mem:
                    if str(val) == item:
                        return False
                return True
        else:
            # 对于非 object 类型的槽位，继续之前的判断逻辑
            if op == "=":
                if str(mem) != str(val):
                    return False
            elif op == "contains":
                if not isinstance(mem, str) or val not in mem:
                    return False
    return True



def get_next_slot(template, memory, asked):
    """
    按 priority 从小到大，选出第一个未问且条件满足的槽位。
    自动跳过 asked 中已提过的问题。
    """
    # 按优先级排序
    for slot in sorted(template, key=lambda x: x.get("priority", 0)):
        name = slot.get("slot")
        if name in asked:
            continue
        # 条件检查
        if check_conditions(slot, memory):
            return slot
    return None
