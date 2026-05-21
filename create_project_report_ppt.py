import os
import zipfile
from datetime import date
from html import escape


OUT = "肺部多轮智能问诊系统项目汇报.pptx"

SLIDE_W = 12192000
SLIDE_H = 6858000


def emu(x):
    return int(x * 914400)


def color(hex_color):
    return hex_color.replace("#", "").upper()


def text_runs(lines, font_size=24, font_color="1F2937", bold=False):
    if isinstance(lines, str):
        lines = [lines]
    paragraphs = []
    for line in lines:
        paragraphs.append(
            f"""
            <a:p>
              <a:r>
                <a:rPr lang="zh-CN" sz="{font_size * 100}" b="{str(bold).lower()}">
                  <a:solidFill><a:srgbClr val="{color(font_color)}"/></a:solidFill>
                  <a:latin typeface="Microsoft YaHei"/>
                  <a:ea typeface="Microsoft YaHei"/>
                </a:rPr>
                <a:t>{escape(str(line))}</a:t>
              </a:r>
              <a:endParaRPr lang="zh-CN" sz="{font_size * 100}"/>
            </a:p>
            """
        )
    return "\n".join(paragraphs)


def shape_xml(shape_id, x, y, w, h, text="", fill="FFFFFF", line="D1D5DB",
              font_size=22, font_color="111827", bold=False, radius=True,
              align="l", valign="mid"):
    shape_type = "roundRect" if radius else "rect"
    anchor = {"l": "", "ctr": '<a:bodyPr anchor="mid"/>'}.get(align, "")
    body_pr = f'<a:bodyPr anchor="{valign}"><a:spAutoFit/></a:bodyPr>'
    paragraphs = text_runs(text, font_size, font_color, bold)
    if align == "ctr":
        paragraphs = paragraphs.replace("<a:p>", '<a:p><a:pPr algn="ctr"/>')
    return f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Shape {shape_id}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
        <a:prstGeom prst="{shape_type}"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{color(fill)}"/></a:solidFill>
        <a:ln w="12700"><a:solidFill><a:srgbClr val="{color(line)}"/></a:solidFill></a:ln>
      </p:spPr>
      <p:txBody>
        {body_pr}
        <a:lstStyle/>
        {paragraphs}
      </p:txBody>
    </p:sp>
    """


def title_xml(title, subtitle="", tag="项目汇报"):
    return (
        shape_xml(20, emu(0.5), emu(0.35), emu(2.2), emu(0.45), tag, "0F766E", "0F766E", 18, "FFFFFF", True, True, "ctr")
        + shape_xml(21, emu(0.65), emu(1.4), emu(11.8), emu(1.0), title, "FFFFFF", "FFFFFF", 38, "0F172A", True, False)
        + (shape_xml(22, emu(0.7), emu(2.35), emu(10.5), emu(0.55), subtitle, "FFFFFF", "FFFFFF", 20, "475569", False, False) if subtitle else "")
    )


def bullets_xml(shape_id, x, y, w, h, items, font_size=22):
    lines = [f"• {item}" for item in items]
    return shape_xml(shape_id, x, y, w, h, lines, "FFFFFF", "E5E7EB", font_size, "1F2937", False, True)


def slide_xml(contents):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F8FAFC"/></a:solidFill></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm></p:grpSpPr>
      {contents}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""


def empty_tree_xml(root_tag, extra=""):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<{root_tag} xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm></p:grpSpPr>
    </p:spTree>
  </p:cSld>
  {extra}
</{root_tag}>"""


def theme_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Codex Medical">
  <a:themeElements>
    <a:clrScheme name="Medical">
      <a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="0F172A"/></a:dk2><a:lt2><a:srgbClr val="F8FAFC"/></a:lt2>
      <a:accent1><a:srgbClr val="0F766E"/></a:accent1><a:accent2><a:srgbClr val="2563EB"/></a:accent2>
      <a:accent3><a:srgbClr val="F59E0B"/></a:accent3><a:accent4><a:srgbClr val="DB2777"/></a:accent4>
      <a:accent5><a:srgbClr val="7C3AED"/></a:accent5><a:accent6><a:srgbClr val="F43F5E"/></a:accent6>
      <a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Microsoft YaHei">
      <a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Microsoft YaHei"/></a:majorFont>
      <a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Microsoft YaHei"/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Default">
      <a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
      <a:lnStyleLst><a:ln w="9525" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
      <a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
      <a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>"""


def make_slides():
    today = date.today().isoformat()
    slides = []

    slides.append(slide_xml(
        shape_xml(2, 0, 0, SLIDE_W, emu(0.28), "", "0F766E", "0F766E", radius=False)
        + title_xml("肺部多轮智能问诊系统", "面向肺结节/胸外科场景的结构化病史采集与对话管理", "项目汇报")
        + shape_xml(3, emu(0.75), emu(4.7), emu(3.4), emu(0.8), "代码目录：/root/autodl-tmp", "ECFDF5", "99F6E4", 18, "115E59")
        + shape_xml(4, emu(4.45), emu(4.7), emu(3.4), emu(0.8), "本地权重：Qwen3 8B / 8B-AWQ / 14B", "EFF6FF", "BFDBFE", 18, "1D4ED8")
        + shape_xml(5, emu(8.15), emu(4.7), emu(3.4), emu(0.8), f"生成日期：{today}", "FFF7ED", "FED7AA", 18, "C2410C")
    ))

    slides.append(slide_xml(
        title_xml("1. 项目背景与目标", "将传统问诊表单转化为可追问、可结构化、可持续更新的智能问诊流程")
        + bullets_xml(31, emu(0.75), emu(1.85), emu(5.55), emu(3.95), [
            "肺结节患者病史信息分散，涉及现病史、既往史、个人史、家族史等多个维度",
            "真实患者回答常存在口语化、时间模糊、信息跳跃和反问咨询等情况",
            "目标是在多轮对话中自动选择下一问、自然追问并沉淀结构化病历信息"
        ], 21)
        + bullets_xml(32, emu(6.65), emu(1.85), emu(5.55), emu(3.95), [
            "输出 JSON 化 slot-value 结果，便于后续病历生成、质控和临床数据复用",
            "使用规则保证问诊边界与医学覆盖，使用大模型提升自然语言理解与表达",
            "本地部署模型权重，适配医疗场景对数据安全和离线运行的要求"
        ], 21)
    ))

    slides.append(slide_xml(
        title_xml("2. 系统总体架构", "规则模板驱动流程，大模型完成语言理解、追问判断和跨病史更新")
        + shape_xml(40, emu(0.6), emu(1.75), emu(2.05), emu(0.85), "患者回答", "E0F2FE", "7DD3FC", 22, "075985", True, True, "ctr")
        + shape_xml(41, emu(2.95), emu(1.75), emu(2.1), emu(0.85), "回答分类", "DCFCE7", "86EFAC", 22, "166534", True, True, "ctr")
        + shape_xml(42, emu(5.35), emu(1.75), emu(2.1), emu(0.85), "结构化抽取", "FEF3C7", "FDE68A", 22, "92400E", True, True, "ctr")
        + shape_xml(43, emu(7.75), emu(1.75), emu(2.1), emu(0.85), "记忆更新", "FCE7F3", "F9A8D4", 22, "9D174D", True, True, "ctr")
        + shape_xml(44, emu(10.15), emu(1.75), emu(2.1), emu(0.85), "下一问生成", "EDE9FE", "C4B5FD", 22, "5B21B6", True, True, "ctr")
        + bullets_xml(45, emu(0.75), emu(3.25), emu(11.45), emu(2.25), [
            "main.py 串联问诊主流程：读取模板、初始化 memory、逐章节 ask_history",
            "rule_engine.py 根据 priority、conditions 和 asked 集合筛选候选 slot",
            "question_generate.py 对问题做自然化，并判断是否需要围绕上一 slot 继续追问",
            "context_update.py 将用户回答映射到相关病史章节，执行跨字段补充更新"
        ], 20)
    ))

    slides.append(slide_xml(
        title_xml("3. 问诊模板覆盖", "6 大病史模块，共 148 个 slot，覆盖肺结节就诊的主要信息面")
        + shape_xml(50, emu(0.85), emu(1.8), emu(1.7), emu(1.25), "现病史\n59", "CCFBF1", "5EEAD4", 24, "134E4A", True, True, "ctr")
        + shape_xml(51, emu(2.75), emu(1.8), emu(1.7), emu(1.25), "既往史\n46", "DBEAFE", "93C5FD", 24, "1E3A8A", True, True, "ctr")
        + shape_xml(52, emu(4.65), emu(1.8), emu(1.7), emu(1.25), "个人史\n12", "FEF3C7", "FBBF24", 24, "78350F", True, True, "ctr")
        + shape_xml(53, emu(6.55), emu(1.8), emu(1.7), emu(1.25), "月经史\n8", "FCE7F3", "F9A8D4", 24, "831843", True, True, "ctr")
        + shape_xml(54, emu(8.45), emu(1.8), emu(1.7), emu(1.25), "婚育史\n8", "EDE9FE", "C4B5FD", 24, "4C1D95", True, True, "ctr")
        + shape_xml(55, emu(10.35), emu(1.8), emu(1.7), emu(1.25), "家族史\n15", "FFE4E6", "FDA4AF", 24, "881337", True, True, "ctr")
        + bullets_xml(56, emu(0.85), emu(3.55), emu(11.2), emu(2.05), [
            "模板字段包括 slot、question_type、priority、prompt、conditions、structure_format、expectations",
            "conditions 支持基于已抽取字段的分支控制，例如仅当“肺结节相关=True”时询问结节发现时间",
            "structure_format 直接约束抽取结果格式，使对话结果可落入统一数据结构"
        ], 20)
    ))

    slides.append(slide_xml(
        title_xml("4. 多轮问诊流程", "每一轮都围绕“选题、提问、理解、更新、追问”闭环运行")
        + bullets_xml(60, emu(0.8), emu(1.7), emu(5.6), emu(4.2), [
            "1. 读取当前章节模板并注入患者基础信息",
            "2. 规则引擎选择当前优先级最高且条件满足的 slot",
            "3. 大模型将模板问题润色为自然问句",
            "4. 识别患者是在回答问题还是提出医学知识咨询",
            "5. 对有效回答执行 JSON 结构化抽取"
        ], 20)
        + bullets_xml(61, emu(6.75), emu(1.7), emu(5.2), emu(4.2), [
            "6. 若回答不满足 expectations，则围绕当前 slot 继续追问",
            "7. 将抽取结果写入 memory，并标记 asked",
            "8. 根据回答内容判断是否涉及其他病史章节",
            "9. 对相关章节执行信息补全或修正",
            "10. 当前章节无待问 slot 后进入下一章节"
        ], 20)
    ))

    slides.append(slide_xml(
        title_xml("5. 多模型协作策略", "不同模型承担不同任务，兼顾生成质量、结构化稳定性和推理能力")
        + shape_xml(70, emu(0.85), emu(1.65), emu(3.4), emu(1.3), "Qwen3-8B\n16G\n自然提问/知识回答", "ECFDF5", "5EEAD4", 22, "115E59", True, True, "ctr")
        + shape_xml(71, emu(4.95), emu(1.65), emu(3.4), emu(1.3), "Qwen3-8B-AWQ\n5.7G\n回答分类/结构化抽取", "EFF6FF", "93C5FD", 22, "1D4ED8", True, True, "ctr")
        + shape_xml(72, emu(9.05), emu(1.65), emu(3.4), emu(1.3), "Qwen3-14B\n28G\n跨病史匹配/上下文更新", "FFF7ED", "FDBA74", 22, "C2410C", True, True, "ctr")
        + bullets_xml(73, emu(0.85), emu(3.55), emu(11.55), emu(2.05), [
            "8B 用于面向患者的自然语言表达，降低模板化问句的机械感",
            "8B-AWQ 用于高频抽取任务，量化权重降低显存压力并提升部署灵活性",
            "14B 用于更复杂的语义判断，例如回答同时补充既往史、家族史等信息"
        ], 20)
    ))

    slides.append(slide_xml(
        title_xml("6. 核心模块", "代码结构清晰，主流程与模型能力、模板能力解耦")
        + bullets_xml(80, emu(0.8), emu(1.65), emu(5.6), emu(4.6), [
            "main.py：章节级问诊编排，生成 dialogue 与 memory",
            "answer_handler.py：识别知识咨询，调用 AWQ 模型输出严格 JSON",
            "question_generate.py：问题润色、追问必要性判断和追问生成",
            "prompt_builder.py：按 question_type 构建提问和抽取 prompt"
        ], 20)
        + bullets_xml(81, emu(6.75), emu(1.65), emu(5.35), emu(4.6), [
            "context_update.py：判断回答关联的病史类型，并更新对应 memory",
            "client_llm_normal.py：Qwen3-8B 本地模型调用",
            "client_llm_awq.py：Qwen3-8B-AWQ 量化模型调用",
            "client_llm_14B.py：Qwen3-14B 本地模型调用"
        ], 20)
    ))

    slides.append(slide_xml(
        title_xml("7. 样例问诊效果", "以“张三”样例为例，系统能够完成肺结节主诉到结构化信息的沉淀")
        + shape_xml(90, emu(0.75), emu(1.55), emu(5.75), emu(4.7), [
            "问：患者这次来医院主要是因为肺结节的问题吗？",
            "答：肺结节",
            "提取：肺结节相关=True，手术/复查/开药分别结构化",
            "",
            "问：最早什么时候发现肺结节？",
            "答：去年体检的时候",
            "追问：能告诉我具体是哪个月哪一天吗？",
            "答：去年1月1日"
        ], "FFFFFF", "CBD5E1", 18, "334155")
        + shape_xml(91, emu(6.8), emu(1.55), emu(5.4), emu(4.7), [
            "最终结构化片段：",
            "结节发现时间：2025-01-01",
            "发现方式：体检",
            "CT 检查时间：2026-01-19",
            "结节位置：左肺",
            "结节数量：一个",
            "最大直径：0.9厘米",
            "医生建议：手术",
            "当前症状：没有不适"
        ], "F8FAFC", "CBD5E1", 19, "0F172A", False)
    ))

    slides.append(slide_xml(
        title_xml("8. 项目亮点", "规则可控性与大模型灵活性的结合，是本项目最核心的工程价值")
        + bullets_xml(100, emu(0.9), emu(1.65), emu(11.2), emu(4.65), [
            "医学问诊流程可控：priority 与 conditions 明确限定问题顺序和分支条件",
            "追问能力较强：根据 expectations 判断回答是否充分，避免一次性问卷式遗漏",
            "结构化结果可复用：每个 slot 对应明确 JSON 格式，利于后续病历生成和质控",
            "支持患者反问：识别医学知识咨询并切换为科普回答，不打断整体问诊流程",
            "本地模型部署：权重已在本机目录，可支撑离线、安全的医疗数据处理场景"
        ], 21)
    ))

    slides.append(slide_xml(
        title_xml("9. 当前问题与优化方向", "系统已有完整闭环，下一步重点是稳定性、评测和临床可用性提升")
        + bullets_xml(110, emu(0.85), emu(1.65), emu(5.55), emu(4.65), [
            "JSON 输出依赖模型稳定性，仍需增加 schema 校验和自动修复",
            "部分字段默认值会残留模板占位，例如 YYYY-MM-DD、text 等",
            "当前交互仍偏命令行，缺少医生端可视化审阅和一键修正界面"
        ], 21)
        + bullets_xml(111, emu(6.75), emu(1.65), emu(5.35), emu(4.65), [
            "建议补充标准病例集，统计 slot 准确率、追问成功率和问诊轮数",
            "将规则引擎、模型调用、状态管理封装为服务接口",
            "增加医学安全边界：红旗症状优先级、急症提示、隐私脱敏和日志审计"
        ], 21)
    ))

    slides.append(slide_xml(
        title_xml("10. 交付物与演示路径", "项目已具备代码、模板、模型权重和样例结果")
        + bullets_xml(120, emu(0.9), emu(1.75), emu(11.1), emu(4.25), [
            "核心代码：/root/autodl-tmp/main.py 及相关模块",
            "问诊模板：/root/autodl-tmp/question_logic/*.json",
            "本地模型：/root/autodl-tmp/Qwen/Qwen3-8B、Qwen3-8B-AWQ、Qwen3-14B",
            "样例结果：/root/autodl-tmp/result_files/张三/*",
            "建议演示：从现病史开始输入患者回答，展示自然追问、JSON 抽取和 memory 更新"
        ], 21)
        + shape_xml(121, emu(0.9), emu(6.1), emu(11.1), emu(0.5), "汇报重点：这是一个可落地运行的肺部专科多轮问诊原型，而不仅是静态问卷或单轮抽取脚本。", "0F766E", "0F766E", 18, "FFFFFF", True, True, "ctr")
    ))

    return slides


def write_package(slides):
    content_types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                     '<Default Extension="xml" ContentType="application/xml"/>',
                     '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
                     '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
                     '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
                     '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>']
    for i in range(1, len(slides) + 1):
        content_types.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    content_types.append('</Types>')

    pres_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    slide_ids = []
    for i in range(1, len(slides) + 1):
        rid = f"rId{i}"
        slide_ids.append(f'<p:sldId id="{255 + i}" r:id="{rid}"/>')
        pres_rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')
    master_rid = f"rId{len(slides) + 1}"
    pres_rels.append(f'<Relationship Id="{master_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>')
    pres_rels.append('</Relationships>')

    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="{master_rid}"/></p:sldMasterIdLst>
  <p:sldIdLst>{''.join(slide_ids)}</p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "\n".join(content_types))
        z.writestr("_rels/.rels", root_rels)
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", "\n".join(pres_rels))
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        z.writestr(
            "ppt/slideMasters/slideMaster1.xml",
            empty_tree_xml(
                "p:sldMaster",
                '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
                '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
                '<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>',
            ),
        )
        z.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>""",
        )
        z.writestr(
            "ppt/slideLayouts/slideLayout1.xml",
            empty_tree_xml("p:sldLayout", '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>'),
        )
        z.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>""",
        )
        for i, slide in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide)
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", rels_xml())


if __name__ == "__main__":
    write_package(make_slides())
    print(os.path.abspath(OUT))
