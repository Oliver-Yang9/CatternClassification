# -*- coding: utf-8 -*-
"""
为 WORKBUDDY 仓库（Obsidian vault）所有文件添加"属性标记"（YAML frontmatter）。

- 全部 .md 笔记：在文件顶部写入 frontmatter（title/aliases/type/tags/status/
  chapter/book_pages/upstream/downstream/chars/created/updated…）。
- 两个 .py 脚本：Python 无法承载 YAML，改用统一的 `# ---- PROPS:BEGIN/END ----`
  注释块声明同样的字段（与 README 中的约定一致）。

upstream / downstream 直接**解析各章已有的导航块**，因此属性和双向链接永远一致。
幂等：重复执行只会覆盖旧属性，不会重复插入。
"""
import os, re, io, datetime

VAULT = os.path.dirname(os.path.abspath(__file__))     # 仓库根目录（随脚本位置自动推导）
JD = os.path.join(VAULT, "精读")
TODAY = "2026-10-14"

CH = {
    1: "ch01_绪论", 2: "ch02_贝叶斯决策论", 3: "ch03_最大似然估计和贝叶斯参数估计",
    4: "ch04_非参数技术", 5: "ch05_线性判别函数", 6: "ch06_多层神经网络",
    7: "ch07_随机方法", 8: "ch08_非度量方法", 9: "ch09_独立于算法的机器学习",
    10: "ch10_无监督学习和聚类",
}
TITLE = {
    1: "绪论", 2: "贝叶斯决策论", 3: "最大似然估计和贝叶斯参数估计",
    4: "非参数技术", 5: "线性判别函数", 6: "多层神经网络",
    7: "随机方法", 8: "非度量方法", 9: "独立于算法的机器学习",
    10: "无监督学习和聚类",
}
PAGES = {1: "1-15", 2: "16-65", 3: "67-130", 4: "132-175", 5: "177-229",
         6: "230-280", 7: "284-315", 8: "318-362", 9: "365-412", 10: "416-479"}
OVERVIEW, APPENDIX = "00_全书总览与精读指南", "11_附录_数学基础与全书速查"
COLLECTED, HOME = "《模式分类(原书第2版)》精读文档", "README"
ALL_MD = [HOME, OVERVIEW, APPENDIX, COLLECTED] + [CH[i] for i in CH]
PY_FILES = ["build_doc.py", "build_links.py"]

def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(s)

def path_of(name):
    for d in (VAULT, JD):
        p = os.path.join(d, name + ".md")
        if os.path.exists(p):
            return p
    return None

# ---------- 从导航块解析出链 / 入链 / 前后章 ----------
def parse_nav(t):
    """从导航块解析：出链目标、入链目标、上一章、下一章。"""
    up, down = [], []
    m = re.search(r"\*\*本页出链[^：]*\*\*：(.+)", t)
    if m:
        up = re.findall(r"\[\[([^\]|#]+)", m.group(1))
    m = re.search(r"\*\*本页入链[^：]*\*\*：(.+)", t)
    if m:
        down = re.findall(r"\[\[([^\]|#]+)", m.group(1))
    prev = nxt = None
    m = re.search(r"\[\[([^\]|]+)\|←", t)
    if m:
        prev = m.group(1)
    m = re.search(r"\[\[([^\]|]+)\|[^]]*→", t)
    if m:
        nxt = m.group(1)
    return [x for x in dict.fromkeys(up)], [x for x in dict.fromkeys(down)], prev, nxt

# ---------- YAML 工具 ----------
def q(s):
    s = str(s)
    if re.search(r"[:\[\]{},#&*!|>'\"%@`]", s) or s.strip() != s:
        return '"%s"' % s.replace('"', '\\"')
    return s

def ylist(v):
    return "[" + ", ".join(q(x) for x in v) + "]"

FM_BEGIN = re.compile(r"\A---\n.*?\n---\n+", flags=re.S)
PROP_BEGIN = "# ---- PROPS:BEGIN ----"
PROP_END = "# ---- PROPS:END ----"

def set_frontmatter(text, props):
    body = FM_BEGIN.sub("", text)
    lines = ["---"]
    for k, v in props.items():
        if isinstance(v, list):
            lines.append("%s: %s" % (k, ylist(v)))
        else:
            lines.append("%s: %s" % (k, q(v)))
    lines += ["---", ""]
    return "\n".join(lines) + body

def set_props_block(text, props):
    if PROP_BEGIN in text:
        text = re.sub(re.escape(PROP_BEGIN) + r".*?" + re.escape(PROP_END) + r"\n?",
                      "", text, flags=re.S)
    lines = [PROP_BEGIN]
    for k, v in props.items():
        if isinstance(v, list):
            lines.append("# %s: %s" % (k, ", ".join(str(x) for x in v)))
        else:
            lines.append("# %s: %s" % (k, v))
    lines.append(PROP_END)
    block = "\n".join(lines) + "\n"
    # 插到模块 docstring 之后（第一个 """ 结束后）
    m = re.search(r'^"""[\s\S]*?"""\n?', text)
    idx = m.end() if m else 0
    return text[:idx] + block + "\n" + text[idx:]

# ---------- 组装各文件属性 ----------
def common(title, aliases, typ, tags, **extra):
    d = {"title": title, "aliases": aliases, "type": typ, "tags": tags,
         "status": "已完成", "created": "2026-10-13", "updated": TODAY}
    d.update(extra)
    return d

props = {}

# 首页
props[HOME] = common(
    "WORKBUDDY 空间首页", ["首页", "HOME", "导航页"], "首页",
    ["模式分类", "精读", "导航", "MOC"],
    hub=True, notes_count=len(ALL_MD),
    downstream=[OVERVIEW, APPENDIX, COLLECTED] + [CH[i] for i in CH],
    purpose="全书精读笔记库的入口索引")

# 总览
props[OVERVIEW] = common(
    "全书总览与精读指南", ["总览", "00", "全书地图", "精读指南"], "总览",
    ["模式分类", "精读", "总览", "导航"],
    chapters=[i for i in CH], reading_routes=3,
    downstream=[CH[i] for i in CH] + [APPENDIX, COLLECTED])

# 各章
for n in CH:
    p = path_of(CH[n])
    up, down, prev, nxt = parse_nav(read(p))
    body = re.sub(r"<!-- NAV:BEGIN -->.*?<!-- NAV:END -->\n?", "", read(p), flags=re.S)
    chars = len(FM_BEGIN.sub("", body))
    props[CH[n]] = common(
        "第%d章 %s" % (n, TITLE[n]),
        ["第%d章" % n, TITLE[n], CH[n]], "章节笔记",
        ["模式分类", "精读", "第%d章" % n, TITLE[n]],
        chapter=n, book_pages=PAGES[n], sections=None,
        prev_chapter=prev, next_chapter=nxt,
        upstream=up, downstream=down, chars=chars,
        obsidian="精读" if n in (2, 3, 5, 6, 9, 10) else "选读为主")
    props[CH[n]].pop("sections")
    props[CH[n]].pop("obsidian")
    for k in ("prev_chapter", "next_chapter"):        # 首章无上一章、末章无下一章
        if props[CH[n]].get(k) is None:
            props[CH[n]].pop(k)

# 附录
props[APPENDIX] = common(
    "附录·数学基础与全书速查", ["附录", "速查", "11", "公式速查"], "附录",
    ["模式分类", "精读", "速查", "附录"],
    covers=[i for i in CH], downstream=[CH[i] for i in CH])

# 合订本
props[COLLECTED] = common(
    "完整合订本（导出用）", ["合订本", "全文", "导出版"], "合订本",
    ["模式分类", "精读", "导出"],
    status="已导出", source=[OVERVIEW] + [CH[i] for i in CH] + [APPENDIX],
    note="由 build_doc.py 合成，阅读请优先用分章笔记")

# ---------- 写入 md 前端 ----------
for name in ALL_MD:
    p = path_of(name)
    t = read(p)
    write(p, set_frontmatter(t, props[name]))
    print("frontmatter ->", name)

# ---------- 写入 py 属性注释 ----------
PY_META = {
    "build_doc.py": common(
        "build_doc.py — 分章笔记合成器", ["合成器", "导出脚本"], "工具脚本",
        ["模式分类", "精读", "工具", "导出"],
        inputs=["精读/*.md"],
        outputs=["《模式分类(原书第2版)》精读文档.md", "《模式分类(原书第2版)》精读文档.docx"],
        note="纯标准库手写 OOXML；wiki 链接会降级为纯文本，并剥离 Obsidian 导航块"),
    "build_links.py": common(
        "build_links.py — 双向链接构建器", ["建链脚本", "链接器"], "工具脚本",
        ["模式分类", "精读", "工具", "链接"],
        inputs=["精读/*.md"], outputs=["各章导航块", "README.md"],
        note="幂等；含对称性 / 断链 / 孤立笔记校验"),
}
for f in PY_FILES:
    p = os.path.join(VAULT, f)
    t = read(p)
    write(p, set_props_block(t, PY_META[f]))
    print("props block ->", f)

# ---------- 在 README 中记录属性约定 ----------
p = path_of(HOME)
t = read(p)
DOC = """<!-- PROPS:DOC:BEGIN -->
## 属性标记约定

本库所有笔记均带 YAML frontmatter（Obsidian「属性」面板可查看、可按属性筛选与排序）：

| 属性 | 含义 |
|---|---|
| `title` | 规范标题 |
| `aliases` | 别名，便于快速跳转（如「第2章」「速查」） |
| `type` | 首页 / 总览 / 章节笔记 / 附录 / 合订本 / 工具脚本 |
| `tags` | 标签，已进入标签面板 |
| `status` | 已完成 / 已导出 / 使用中 |
| `chapter` / `book_pages` | 章号 / 对应原书页码区间 |
| `prev_chapter` / `next_chapter` | 上一章 / 下一章 |
| `upstream` / `downstream` | 本页出链（依赖/引用）与入链（被依赖/被引用），与导航块、反向链接面板完全一致 |
| `chars` | 正文字数 |
| `created` / `updated` | 建立 / 更新日期 |

> `build_doc.py`、`build_links.py` 两个脚本是 Python 文件、无法承载 YAML，
> 因此在文件头用 `# ---- PROPS:BEGIN/END ----` 注释块声明同样的字段。
<!-- PROPS:END -->
"""
if "<!-- PROPS:DOC:BEGIN -->" in t:
    t = re.sub(r"<!-- PROPS:DOC:BEGIN -->.*?<!-- PROPS:END -->\n?", DOC, t, flags=re.S)
else:
    t = t.rstrip() + "\n\n" + DOC
write(p, t)
print("README 属性约定：已写入")

# ---------- 校验 ----------
print("\n=== 属性标记校验 ===")
need = {"title", "aliases", "type", "tags", "status", "created", "updated"}
miss = []
for name in ALL_MD:
    t = read(path_of(name))
    m = re.match(r"\A---\n(.*?)\n---\n", t, flags=re.S)
    if not m:
        miss.append((name, "无 frontmatter"))
        continue
    keys = {ln.split(":")[0].strip() for ln in m.group(1).split("\n") if ln.strip()}
    if not need <= keys:
        miss.append((name, "缺字段 " + str(need - keys)))
for f in PY_FILES:
    t = read(os.path.join(VAULT, f))
    if PROP_BEGIN not in t:
        miss.append((f, "无 PROPS 块"))
    else:
        blk = t[t.find(PROP_BEGIN):t.find(PROP_END)]
        keys = {ln[2:].split(":")[0].strip() for ln in blk.split("\n") if ln.startswith("# ") and ":" in ln}
        if not {"title", "type", "tags", "status"} <= keys:
            miss.append((f, "PROPS 块缺字段"))

n_prop = sum(len(read(path_of(n)).split("\n")[1:40]) for n in [])  # noop
total = 0
for name in ALL_MD:
    t = read(path_of(name))
    m = re.match(r"\A---\n(.*?)\n---\n", t, flags=re.S)
    total += len([ln for ln in m.group(1).split("\n") if ln.strip()])
print("Markdown 笔记 %d 篇，共 %d 个属性字段；Python 脚本 %d 个带 PROPS 块" % (len(ALL_MD), total, len(PY_FILES)))
print("缺失：", miss if miss else "无 ✔")
