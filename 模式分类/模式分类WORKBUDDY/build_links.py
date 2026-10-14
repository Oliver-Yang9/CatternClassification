# ---- PROPS:BEGIN ----
# title: build_links.py — 双向链接构建器
# aliases: 建链脚本, 链接器
# type: 工具脚本
# tags: 模式分类, 精读, 工具, 链接
# status: 已完成
# created: 2026-10-13
# updated: 2026-10-14
# inputs: 精读/*.md
# outputs: 各章导航块, README.md
# note: 幂等；含对称性 / 断链 / 孤立笔记校验
# ---- PROPS:END ----





# -*- coding: utf-8 -*-
"""
为 WORKBUDDY 仓库（Obsidian vault）构造双向链接。

设计原则：
1. 先对正文中的「第N章」做 wiki 链接化；
2. 汇总**全量出边**（语义依赖 + 正文引用 + 导航固定链接）；
3. 导航块中的「上游依赖 / 下游延伸」直接由全量出边与其反向闭包生成
   —— 因此 A 把 B 列为上游时，B 必定把 A 列为下游，双向性由构造保证；
4. 幂等：用 <!-- NAV:BEGIN/END --> 标记，重复执行不会重复插入。
"""
import os, re, io

VAULT = os.path.dirname(os.path.abspath(__file__))     # 仓库根目录（随脚本位置自动推导）
JD = os.path.join(VAULT, "精读")

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
RNUM = {v: k for k, v in CH.items()}
OVERVIEW, APPENDIX = "00_全书总览与精读指南", "11_附录_数学基础与全书速查"
COLLECTED, HOME = "《模式分类(原书第2版)》精读文档", "README"
ALL_NOTES = [HOME, OVERVIEW, APPENDIX, COLLECTED] + [CH[i] for i in CH]

def wlink(name, label):
    return "[[%s|%s]]" % (name, label)

def chlink(n):
    return wlink(CH[n], "第%d章 %s" % (n, TITLE[n]))

# ---------- 语义依赖（带理由） ----------
DEPS = {
    1: [],
    2: [(1, "分类器的位置与设计循环")],
    3: [(2, "判别函数 $g_i(\\mathbf{x})=\\ln p(\\mathbf{x}|\\omega_i)+\\ln P(\\omega_i)$；多元正态密度")],
    4: [(2, "判别函数与贝叶斯误差基准"), (3, "偏差—方差语言、维数灾难")],
    5: [(2, "等协方差高斯下贝叶斯判别退化为线性"), (3, "Fisher 判别与 PCA；维数灾难"),
        (4, "不估密度的另一条路线")],
    6: [(5, "神经元 = 线性判别 + 非线性激活；MSE 渐近逼近后验"),
        (2, "网络输出即后验、最小错误率判决"),
        (3, "交叉熵 = 最大似然；权衰减 = MAP"),
        (4, "RBF 与核密度估计共享局部基结构")],
    7: [(5, "梯度下降与局部极小"), (6, "反向传播给不出全局最优"),
        (2, "玻耳兹曼学习本质是最大似然 / KL 最小化")],
    8: [(5, "多元树节点查询 = 小型线性判别"),
        (2, "叶标记多数类 = 后验最大化；损失矩阵与先验"),
        (7, "斜分割搜索、文法推断可用随机搜索 / 遗传算法")],
    9: [(2, "贝叶斯误差率是误差分解中「不可约噪声」项的原型"),
        (3, "MDL 与 MAP 的等价；过拟合"),
        (5, "稳定基分类器（线性）"),
        (8, "不稳定基分类器（判定树）")],
    10: [(2, "后验是 E 步输入；贝叶斯分类器形式"),
         (3, "含隐变量的 ML 推广；充分统计量"),
         (5, "Fisher 散布矩阵的对偶使用"),
         (9, "混合成分数 $c$、主成分个数的模型阶数选择")],
}
EXTRA_FWD = {
    1: [(3, "维数问题与过拟合（3.7）；特征抽取（3.8）"),
        (9, "设计循环 → 模型选择 / 交叉验证"),
        (10, "无监督学习范式")],
    2: [(6, "网络输出被视为后验概率的估计"), (9, "ROC、代价与评价协议"),
        (10, "混合密度 = 类标签缺失时的类条件密度估计")],
    3: [(9, "峰值现象与过拟合是第 9 章存在的理由")],
    4: [(9, "维数灾难是降维 / 特征选择存在的核心理由")],
}

# ---------- 工具 ----------
def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(s)

def find_note(name):
    for d in (VAULT, JD):
        p = os.path.join(d, name + ".md")
        if os.path.exists(p):
            return p
    return None

def strip_nav(t):
    return re.sub(r"<!-- NAV:BEGIN -->.*?<!-- NAV:END -->\n?", "", t, flags=re.S)

def strip_fences(t):
    """去掉围栏代码块与行内代码，避免把 Python 的 [[0.0]*n] 当成链接。"""
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`\n]*`", "", t)
    return t

def section_targets(t, header="## 与其他章的连接", ends=("## 术语表", "## 本章必背")):
    """按方向解析「与其他章的连接」：
    返回 (向前依赖=本页依赖谁, 向后铺垫=谁依赖本页)。"""
    m = re.search(re.escape(header), t)
    if not m:
        return set(), set()
    start, end = m.end(), len(t)
    for h in ends:
        k = t.find(h, start)
        if k != -1:
            end = min(end, k)
    seg = strip_fences(t[start:end])
    idx = seg.find("向后铺垫")
    up_seg, down_seg = (seg, "") if idx == -1 else (seg[:idx], seg[idx:])

    def targets(s):
        out = set()
        for x in re.findall(r"\[\[([^\]|#]+)", s):
            x = x.strip().split("/")[-1]
            if x in ALL_NOTES:
                out.add(x)
        return out
    return targets(up_seg), targets(down_seg)

def nav_block(text):
    return "<!-- NAV:BEGIN -->\n" + text.rstrip() + "\n<!-- NAV:END -->\n"

def insert_before(t, anchor, block):
    t = strip_nav(t)
    idx = t.find(anchor)
    if idx == -1:
        m = re.search(r"^# .*?$", t, flags=re.M)
        idx = m.end() if m else 0
    return t[:idx] + block + t[idx:]

# ---------- 步骤 1：正文「第N章」链接化 ----------
def linkify(t, header="## 与其他章的连接", ends=("## 术语表", "## 本章必背")):
    m = re.search(re.escape(header), t)
    if not m:
        return t
    start, end = m.end(), len(t)
    for h in ends:
        k = t.find(h, start)
        if k != -1:
            end = min(end, k)
    seg = t[start:end]
    if "[[" in seg:
        return t
    def rep(mo):
        n = int(mo.group(1))
        return "[[%s|第%d章]]" % (CH[n], n) if n in CH else mo.group(0)
    return t[:start] + re.sub(r"第\s*(\d+)\s*章", rep, seg) + t[end:]

for n in CH:
    p = find_note(CH[n])
    t = read(p)
    t2 = linkify(t)
    if t2 != t:
        write(p, t2)
print("步骤1 正文链接化：完成")

# ---------- 步骤 2：汇总全量出边 ----------
out_edges = {name: {} for name in ALL_NOTES}   # 起点 -> {终点: 理由}

for n in CH:
    src = CH[n]
    for (tgt, why) in DEPS.get(n, []):          # 本页依赖 tgt
        if tgt in CH:
            out_edges[src][CH[tgt]] = why
    for (tgt, why) in EXTRA_FWD.get(n, []):     # tgt 建立在本页之上（方向相反）
        if tgt in CH:
            out_edges[CH[tgt]][src] = why
    p = find_note(src)
    up, down = section_targets(read(p))
    # 方向规则：本书的依赖基本是「后者依赖前者」。
    # 若被引用的章节 x 在本页之后 → x 依赖本页；否则本页依赖 x。
    def add(x, kind):
        if x not in CH.values() or x == src:
            return
        m = RNUM[x]
        why = "第%d章「%s」" % (n, kind)
        if m > n:
            out_edges[x].setdefault(src, why)
        else:
            out_edges[src].setdefault(x, why)
    for x in up:
        add(x, "向前依赖")
    for x in down:
        add(x, "向后铺垫")

# 导航固定链接（每章 → 首页 / 总览 / 附录 / 合订本 / 相邻章）
for n in CH:
    src = CH[n]
    for tgt in (HOME, OVERVIEW, APPENDIX, COLLECTED):
        out_edges[src].setdefault(tgt, "导航固定链接")
    if n > 1:
        out_edges[src].setdefault(CH[n - 1], "SEQ:章节序列（上一章）")
    if n < 10:
        out_edges[src].setdefault(CH[n + 1], "SEQ:章节序列（下一章）")

# 总览 / 附录 / 合订本 / 首页 的出边
for i in CH:
    out_edges[OVERVIEW].setdefault(CH[i], "全书索引")
    out_edges[APPENDIX].setdefault(CH[i], "公式与方法出处")
    out_edges[COLLECTED].setdefault(CH[i], "合成来源（分章笔记）")
    out_edges[HOME].setdefault(CH[i], "空间首页索引")
for tgt in (OVERVIEW, APPENDIX, COLLECTED):
    out_edges[HOME].setdefault(tgt, "空间首页索引")
out_edges[OVERVIEW].setdefault(HOME, "导航固定链接")
out_edges[OVERVIEW].setdefault(APPENDIX, "导航固定链接")
out_edges[OVERVIEW].setdefault(COLLECTED, "导航固定链接")
out_edges[APPENDIX].setdefault(HOME, "导航固定链接")
out_edges[APPENDIX].setdefault(OVERVIEW, "导航固定链接")
out_edges[APPENDIX].setdefault(COLLECTED, "导航固定链接")
out_edges[COLLECTED].setdefault(HOME, "导航固定链接")
out_edges[COLLECTED].setdefault(OVERVIEW, "导航固定链接")
out_edges[COLLECTED].setdefault(APPENDIX, "导航固定链接")

# ---------- 步骤 3：生成各章导航（上游 = 出边；下游 = 反向闭包） ----------
def reason(a, b):
    return out_edges.get(a, {}).get(b, "相关主题")

for n in CH:
    src = CH[n]
    up = [(t, w) for (t, w) in out_edges[src].items()
          if t in CH.values() and not w.startswith("SEQ:")]
    down = [(a, reason(a, src)) for a in [CH[i] for i in CH]
            if src in out_edges[a] and a != src
            and not out_edges[a][src].startswith("SEQ:")]

    lines = ["## 🔗 链接导航\n",
             "%s ｜ %s ｜ %s ｜ %s\n"
             % (wlink(HOME, "🏠 空间首页"), wlink(OVERVIEW, "📖 全书总览"),
                wlink(APPENDIX, "📐 附录速查"), wlink(COLLECTED, "📄 完整合订本"))]
    seq = []
    if n > 1:
        seq.append(wlink(CH[n - 1], "← 第%d章 %s" % (n - 1, TITLE[n - 1])))
    seq.append("**第%d章 %s（本页）**" % (n, TITLE[n]))
    if n < 10:
        seq.append(wlink(CH[n + 1], "第%d章 %s →" % (n + 1, TITLE[n + 1])))
    lines.append("- **章节序列**：" + " ｜ ".join(seq))
    if up:
        lines.append("- **本页出链（依赖 / 引用到的章节）**："
                     + "；".join("%s（%s）" % (chlink([k for k, v in CH.items() if v == t][0]), w)
                                             for (t, w) in sorted(up, key=lambda x: x[0])))
    else:
        lines.append("- **本页出链**：无（全书起点）")
    if down:
        lines.append("- **本页入链（依赖 / 引用本页的章节）**："
                     + "；".join("%s（%s）" % (chlink([k for k, v in CH.items() if v == a][0]), w)
                                             for (a, w) in sorted(down, key=lambda x: x[0])))
    lines.append("")
    p = find_note(src)
    write(p, insert_before(read(p), "## 章节地图", nav_block("\n".join(lines))))
print("步骤2/3 各章导航：完成")

# ---------- 步骤 4：总览 / 附录 / 合订本 / 首页 ----------
p = find_note(OVERVIEW)
t = read(p)
nav = ["## 🔗 链接导航\n",
       "%s ｜ %s ｜ %s\n"
       % (wlink(HOME, "🏠 空间首页"), wlink(APPENDIX, "📐 附录速查"),
          wlink(COLLECTED, "📄 完整合订本")),
       "- **十章笔记**：" + " ｜ ".join(chlink(i) for i in range(1, 11)),
       ""]
t = insert_before(t, "## 0. 这份讲义怎么用", nav_block("\n".join(nav)))
table_map = {
    "| 1 | 绪论 |": "| 1 | %s |" % wlink(CH[1], "绪论"),
    "| 2 | 贝叶斯决策论 |": "| 2 | %s |" % wlink(CH[2], "贝叶斯决策论"),
    "| 3 | 最大似然估计和贝叶斯参数估计 |": "| 3 | %s |" % wlink(CH[3], "最大似然估计和贝叶斯参数估计"),
    "| 4 | 非参数技术 |": "| 4 | %s |" % wlink(CH[4], "非参数技术"),
    "| 5 | 线性判别函数 |": "| 5 | %s |" % wlink(CH[5], "线性判别函数"),
    "| 6 | 多层神经网络 |": "| 6 | %s |" % wlink(CH[6], "多层神经网络"),
    "| 7 | 随机方法 |": "| 7 | %s |" % wlink(CH[7], "随机方法"),
    "| 8 | 非度量方法 |": "| 8 | %s |" % wlink(CH[8], "非度量方法"),
    "| 9 | 独立于算法的机器学习 |": "| 9 | %s |" % wlink(CH[9], "独立于算法的机器学习"),
    "| 10 | 无监督学习和聚类 |": "| 10 | %s |" % wlink(CH[10], "无监督学习和聚类"),
    "| A | 数学基础 |": "| A | %s |" % wlink(APPENDIX, "数学基础（见附录速查）"),
}
for a, b in table_map.items():
    t = t.replace(a, b)
write(p, t)

p = find_note(APPENDIX)
t = read(p)
nav = ["## 🔗 链接导航\n",
       "%s ｜ %s ｜ %s\n"
       % (wlink(HOME, "🏠 空间首页"), wlink(OVERVIEW, "📖 全书总览"),
          wlink(COLLECTED, "📄 完整合订本")),
       "- **公式与方法出处（按章）**：" + " ｜ ".join(chlink(i) for i in range(1, 11)),
       "- **说明**：本页是全书速查表；上面每一章的导航都指回本页。",
       ""]
write(p, insert_before(t, "## A. 数学基础清单", nav_block("\n".join(nav))))

p = find_note(COLLECTED)
t = read(p)
nav = ["## 🔗 链接导航\n",
       "%s ｜ %s ｜ %s\n"
       % (wlink(HOME, "🏠 空间首页"), wlink(OVERVIEW, "📖 全书总览"),
          wlink(APPENDIX, "📐 附录速查")),
       "> 本文件是**导出用合订本**（由 12 个分章文件拼接而成），阅读与检索请优先使用分章笔记。\n",
       "- **合成来源（分章笔记）**：" + " ｜ ".join(chlink(i) for i in range(1, 11)),
       "- **总览与附录**：%s ｜ %s" % (wlink(OVERVIEW, "全书总览"), wlink(APPENDIX, "附录速查")),
       ""]
_t = strip_nav(read(p))
_m = re.search(r"^# .*?$", _t, flags=re.M)
_t = _t[:_m.end()] + "\n\n" + nav_block("\n".join(nav)) + _t[_m.end():]
write(p, _t)

readme = """# 🏠 WORKBUDDY 空间首页

本仓库是《模式分类（原书第2版）》（Duda / Hart / Stork）的**精读笔记库**，笔记之间已全部建立双向链接（在 Obsidian 中打开任意笔记即可在「反向链接」面板看到谁指向它）。

## 全部笔记

| 类型 | 笔记 |
|---|---|
| 总览 | %s |
| 附录 | %s |
| 第1章 | %s |
| 第2章 | %s |
| 第3章 | %s |
| 第4章 | %s |
| 第5章 | %s |
| 第6章 | %s |
| 第7章 | %s |
| 第8章 | %s |
| 第9章 | %s |
| 第10章 | %s |
| 合订本 | %s |

## 链接规则

1. **首页 ↔ 全部**：本页链接所有笔记，每篇笔记顶部可回到本页。
2. **总览 ↔ 各章**：总览索引表指向每一章，每章导航指回总览。
3. **章节序列**：第 N 章与第 N±1 章互链。
4. **语义依赖成对**：A 把 B 列为「出链（依赖/引用）」时，B 必把 A 列为「入链」。
5. **附录 ↔ 各章**：各章指回附录速查，附录按章列出公式出处。
6. **合订本 ↔ 各章**：合订本标注合成来源，各章可跳到合订本。

## 文件说明

- `精读/` —— 12 个分章笔记（本库主体）。
- `精读/%s` —— 由分章笔记拼接的单文件全文（导出 / 打印用）。
- `build_doc.py` —— 把分章笔记合成 Markdown 与 Word 文档的脚本（纯标准库，无需 pandoc）。
""" % (
    wlink(OVERVIEW, "00 全书总览与精读指南"),
    wlink(APPENDIX, "11 附录·数学基础与全书速查"),
    chlink(1), chlink(2), chlink(3), chlink(4), chlink(5),
    chlink(6), chlink(7), chlink(8), chlink(9), chlink(10),
    wlink(COLLECTED, "完整合订本"),
    COLLECTED + ".md",
)
write(os.path.join(VAULT, HOME + ".md"), readme)
print("步骤4 总览/附录/合订本/首页：完成")

# ---------- 步骤 5：校验 ----------
print("\n=== 双向链接校验 ===")
actual = {}
for name in ALL_NOTES:
    p = find_note(name)
    if not p:
        continue
    t = read(p)
    if name == COLLECTED:
        m = re.search(r"<!-- NAV:BEGIN -->(.*?)<!-- NAV:END -->", t, flags=re.S)
        t = m.group(1) if m else ""
    t = strip_fences(t)
    tgt = set()
    for x in re.findall(r"\[\[([^\]|#]+)", t):
        x = x.strip().split("/")[-1]
        if x in ALL_NOTES and x != name:
            tgt.add(x)
    actual[name] = tgt

bad = []
for a, bs in actual.items():
    for b in bs:
        if a not in actual.get(b, set()):
            bad.append((a, b))
print("笔记数：%d ｜ 有向链接边：%d ｜ 去重无向边：%d"
      % (len(actual), sum(len(v) for v in actual.values()),
         len({tuple(sorted((a, b))) for a, bs in actual.items() for b in bs})))
if bad:
    print("❌ 非对称链接 %d 条：" % len(bad))
    for x in bad[:40]:
        print("   ", x[0], "→", x[1])
else:
    print("✅ 全部链接均为双向（A→B 必有 B→A）")

orphan = [n for n in ALL_NOTES if not actual.get(n)]
print("孤立笔记：", orphan if orphan else "无")
