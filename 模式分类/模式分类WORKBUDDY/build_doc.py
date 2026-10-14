# ---- PROPS:BEGIN ----
# title: build_doc.py — 分章笔记合成器
# aliases: 合成器, 导出脚本
# type: 工具脚本
# tags: 模式分类, 精读, 工具, 导出
# status: 已完成
# created: 2026-10-13
# updated: 2026-10-14
# inputs: 精读/*.md
# outputs: 《模式分类(原书第2版)》精读文档.md, 《模式分类(原书第2版)》精读文档.docx
# note: 纯标准库手写 OOXML；wiki 链接会降级为纯文本，并剥离 Obsidian 导航块
# ---- PROPS:END ----





# -*- coding: utf-8 -*-
"""把精读 Markdown 合订成一份 docx（纯标准库生成 OOXML，无需第三方依赖）。"""
import os, re, zipfile, datetime

VAULT = os.path.dirname(os.path.abspath(__file__))     # 仓库根目录
SRC = os.path.join(VAULT, "精读")
OUT_DIR = os.path.dirname(VAULT)                       # 导出件放在仓库同级目录
OUT_DOCX = os.path.join(OUT_DIR, "《模式分类(原书第2版)》精读文档.docx")
OUT_MD = os.path.join(OUT_DIR, "《模式分类(原书第2版)》精读文档.md")

ORDER = [
    "00_全书总览与精读指南.md",
    "ch01_绪论.md",
    "ch02_贝叶斯决策论.md",
    "ch03_最大似然估计和贝叶斯参数估计.md",
    "ch04_非参数技术.md",
    "ch05_线性判别函数.md",
    "ch06_多层神经网络.md",
    "ch07_随机方法.md",
    "ch08_非度量方法.md",
    "ch09_独立于算法的机器学习.md",
    "ch10_无监督学习和聚类.md",
    "11_附录_数学基础与全书速查.md",
]

# ---------- 1. 合并 Markdown ----------
WIKI_LINK = re.compile(r"\[\[([^\]|#]+)\|([^\]]+)\]\]|\[\[([^\]|#]+)\]\]")
NAV_BLOCK = re.compile(r"<!-- NAV:BEGIN -->.*?<!-- NAV:END -->\n?", flags=re.S)

def wiki_to_text(m):
    return (m.group(2) or m.group(3).split("/")[-1]).strip()

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n+", flags=re.S)

def strip_frontmatter(s):
    return FRONTMATTER.sub("", s)

parts = []
for f in ORDER:
    p = os.path.join(SRC, f)
    parts.append(strip_frontmatter(open(p, encoding="utf-8").read().rstrip()))
md = "\n\n---\n\n".join(parts)
with open(OUT_MD, "w", encoding="utf-8") as fp:
    fp.write(md)
# 仓库内的合订本副本（供 Obsidian 检索）保持同一份内容
VAULT_MD = os.path.join(SRC, os.path.basename(OUT_MD))
with open(VAULT_MD, "w", encoding="utf-8") as fp:
    fp.write(md)

# 供 docx 使用：去掉 Obsidian 导航块，wiki 链接降级为纯文本
md_docx = NAV_BLOCK.sub("", md)
md_docx = WIKI_LINK.sub(wiki_to_text, md_docx)

# ---------- 2. Markdown -> OOXML ----------
def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+?`)")

def runs(text, mono=False):
    """生成 w:r 序列，支持 **粗体** 与 `代码`。"""
    out = []
    for seg in INLINE.split(text):
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**") and len(seg) > 4:
            out.append('<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % esc(seg[2:-2]))
        elif seg.startswith("`") and seg.endswith("`") and len(seg) > 2:
            out.append('<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Consolas" w:cs="Consolas"/><w:sz w:val="20"/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % esc(seg[1:-1]))
        else:
            body = seg.replace("$", "")
            props = ""
            if mono:
                props = '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Consolas" w:cs="Consolas"/><w:sz w:val="20"/></w:rPr>'
            out.append("<w:r>%s<w:t xml:space=\"preserve\">%s</w:t></w:r>" % (props, esc(body)))
    return "".join(out)

def para(text="", style=None, jc=None, ind=None, mono=False, spacing=None, pb=False):
    ppr = []
    if style:
        ppr.append('<w:pStyle w:val="%s"/>' % style)
    if jc:
        ppr.append('<w:jc w:val="%s"/>' % jc)
    if ind:
        ppr.append('<w:ind w:left="%d"/>' % ind)
    if spacing:
        ppr.append('<w:spacing %s/>' % spacing)
    pprs = "<w:pPr>%s</w:pPr>" % "".join(ppr) if ppr else ""
    brk = '<w:r><w:br w:type="page"/></w:r>' if pb else ""
    return "<w:p>%s%s%s</w:p>" % (pprs, brk, runs(text, mono=mono))

def hr():
    return ('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="BFBFBF"/>'
            '</w:pBdr><w:spacing w:after="120"/></w:pPr></w:p>')

CODE_LINE = '<w:p><w:pPr><w:pStyle w:val="Code"/><w:ind w:left="360"/></w:pPr>%s</w:p>'

def table_row(cells, header=False):
    tcs = []
    for c in cells:
        shd = '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>' if header else ""
        tcs.append(
            '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="pct"/>%s'
            '<w:vAlign w:val="center"/>'
            '<w:tcBorders>'
            '<w:top w:val="single" w:sz="4" w:color="BFBFBF"/>'
            '<w:left w:val="single" w:sz="4" w:color="BFBFBF"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="BFBFBF"/>'
            '<w:right w:val="single" w:sz="4" w:color="BFBFBF"/>'
            '</w:tcBorders></w:tcPr>'
            '<w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>%s</w:p></w:tc>'
            % (int(100 / max(len(cells), 1)), shd, runs(c, mono=False))
        )
    return "<w:tr>%s</w:tr>" % "".join(tcs)

def build_body(md_text):
    lines = md_text.split("\n")
    body = []
    i = 0
    in_code = False
    first_h1 = True
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        # 代码块
        if s.startswith("```"):
            if in_code:
                in_code = False
                i += 1
                continue
            in_code = True
            i += 1
            continue
        if in_code:
            if s == "":
                body.append(CODE_LINE % "")
            else:
                body.append(CODE_LINE % ('<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" '
                                         'w:eastAsia="Consolas" w:cs="Consolas"/><w:sz w:val="19"/></w:rPr>'
                                         '<w:t xml:space="preserve">%s</w:t></w:r>' % esc(s)))
            i += 1
            continue

        if s == "":
            i += 1
            continue

        if s in ("---", "***"):
            body.append(hr())
            i += 1
            continue

        # 表格
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-\|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in s.strip("|").split("|")]
            body.append("<w:tbl><w:tblPr>"
                        '<w:tblW w:w="5000" w:type="pct"/>'
                        '<w:tblBorders>'
                        '<w:top w:val="single" w:sz="4" w:color="BFBFBF"/>'
                        '<w:left w:val="single" w:sz="4" w:color="BFBFBF"/>'
                        '<w:bottom w:val="single" w:sz="4" w:color="BFBFBF"/>'
                        '<w:right w:val="single" w:sz="4" w:color="BFBFBF"/>'
                        '<w:insideH w:val="single" w:sz="4" w:color="BFBFBF"/>'
                        '<w:insideV w:val="single" w:sz="4" w:color="BFBFBF"/>'
                        '</w:tblBorders></w:tblPr>')
            body.append(table_row(header, header=True))
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                body.append(table_row(cells))
                i += 1
            body.append("</w:tbl>")
            body.append(para(""))
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2).replace("$", "")
            pb = (lvl == 1 and not first_h1)
            if lvl == 1:
                first_h1 = False
            body.append(para(txt, style="Heading%d" % min(lvl, 6), pb=pb,
                             spacing='w:before="240" w:after="120"'))
            i += 1
            continue

        # 引用
        if s.startswith(">"):
            txt = s.lstrip(">").strip().replace("$", "")
            body.append(para(txt, style="Quote"))
            i += 1
            continue

        # 独立公式
        if s.startswith("$$") and s.endswith("$$"):
            body.append(para(s.strip("$").strip(), jc="center", mono=True,
                             spacing='w:before="120" w:after="120"'))
            i += 1
            continue

        # 列表
        m = re.match(r"^([-*+])\s+(.*)$", s)
        if m:
            body.append(para("• " + m.group(2).replace("$", ""), ind=420,
                             spacing='w:before="20" w:after="20"'))
            i += 1
            continue
        m = re.match(r"^(\s*)([*+-])\s+(.*)$", line)
        if m:
            lvl = len(m.group(1)) // 2
            body.append(para("• " + m.group(3).replace("$", ""), ind=420 + 360 * lvl,
                             spacing='w:before="20" w:after="20"'))
            i += 1
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m:
            body.append(para(m.group(1) + ". " + m.group(2).replace("$", ""), ind=420,
                             spacing='w:before="20" w:after="20"'))
            i += 1
            continue

        # 普通段落
        body.append(para(s.replace("$", ""), spacing='w:before="60" w:after="60" w:line="300" w:lineRule="auto"'))
        i += 1
    return "".join(body)

# ---------- 3. 封面 + 目录域 + 正文 ----------
today = datetime.date.today().strftime("%Y年%m月%d日")
cover = (
    para("", pb=False, spacing='w:before="1200"')
    + para("《模式分类（原书第2版）》", style="Title", jc="center")
    + para("精 读 文 档", style="Title", jc="center")
    + para("")
    + para("Richard O. Duda · Peter E. Hart · David G. Stork  著", jc="center")
    + para("李宏东、姚天翔 等译 · 机械工业出版社", jc="center")
    + para("")
    + para("逐章逐节精读笔记 · 含页码对照 / 关键推导 / 算法清单 / 自测题", jc="center")
    + para("")
    + para("生成日期：%s" % today, jc="center")
    + para("", pb=True)
    + para("目  录", style="Heading1", jc="center")
    + ('<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
       '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
       '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
       '<w:r><w:t>【在 Word 中右键“更新域”可生成目录页码】</w:t></w:r>'
       '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    + para("", pb=True)
)

body_xml = cover + build_body(md_docx)

document = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body>" + body_xml +
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1440" w:right="1418" w:bottom="1440" w:left="1418" '
    'w:header="851" w:footer="992" w:gutter="0"/></w:sectPr>'
    "</w:body></w:document>"
)

def style(sid, name, sz, bold, color, font_ascii, font_ea, before=120, after=120, outline=None, italic=False):
    rpr = ['<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/>' % (font_ascii, font_ascii, font_ea, font_ascii)]
    if bold:
        rpr.append("<w:b/>")
    if italic:
        rpr.append("<w:i/>")
    rpr.append('<w:color w:val="%s"/>' % color)
    rpr.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz))
    ppr = '<w:spacing w:before="%d" w:after="%d"/>' % (before, after)
    if outline is not None:
        ppr += '<w:outlineLvl w:val="%d"/>' % outline
    return ('<w:style w:type="paragraph" w:styleId="%s"><w:name w:val="%s"/><w:basedOn w:val="Normal"/>'
            "<w:pPr>%s</w:pPr><w:rPr>%s</w:rPr></w:style>" % (sid, name, ppr, "".join(rpr)))

styles = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:docDefaults><w:rPrDefault><w:rPr>"
    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体" w:cs="Times New Roman"/>'
    '<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="320" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
    "</w:docDefaults>"
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
    + style("Title", "Title", 44, True, "1F3864", "Times New Roman", "黑体", 240, 240)
    + style("Heading1", "heading 1", 34, True, "1F3864", "Times New Roman", "黑体", 320, 180, 0)
    + style("Heading2", "heading 2", 28, True, "2E5496", "Times New Roman", "黑体", 260, 140, 1)
    + style("Heading3", "heading 3", 24, True, "2E5496", "Times New Roman", "黑体", 200, 120, 2)
    + style("Heading4", "heading 4", 22, True, "44546A", "Times New Roman", "黑体", 160, 100, 3)
    + style("Heading5", "heading 5", 22, True, "44546A", "Times New Roman", "黑体", 140, 100, 4)
    + style("Heading6", "heading 6", 22, True, "44546A", "Times New Roman", "黑体", 140, 100, 5)
    + style("Quote", "Quote", 21, False, "404040", "Times New Roman", "楷体", 80, 80, italic=False)
    + style("Code", "Code", 19, False, "1A1A1A", "Consolas", "Consolas", 0, 0)
    + "</w:styles>"
)

content_types = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    "</Types>"
)

rels = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
    "</Relationships>"
)

doc_rels = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    "</Relationships>"
)

core = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:title>《模式分类（原书第2版）》精读文档</dc:title>"
    "<dc:subject>模式识别 / 机器学习 逐章精读笔记</dc:subject>"
    "<dc:creator>WorkBuddy</dc:creator>"
    "<cp:lastModifiedBy>WorkBuddy</cp:lastModifiedBy>"
    '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
    '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
    "</cp:coreProperties>" % (datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                              datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
)

app = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
    "<Application>WorkBuddy</Application></Properties>"
)

with zipfile.ZipFile(OUT_DOCX, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("_rels/.rels", rels)
    z.writestr("word/document.xml", document)
    z.writestr("word/styles.xml", styles)
    z.writestr("word/_rels/document.xml.rels", doc_rels)
    z.writestr("docProps/core.xml", core)
    z.writestr("docProps/app.xml", app)

print("MD :", OUT_MD, os.path.getsize(OUT_MD), "bytes")
print("DOCX:", OUT_DOCX, os.path.getsize(OUT_DOCX), "bytes")
