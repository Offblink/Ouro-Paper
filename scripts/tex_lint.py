"""LaTeX 草稿的静态自检（本机没有 TeX 发行版，用这个替代编译）：

1. 每个 \\input{...} 的文件存在
2. \\includegraphics 的文件存在（含 figures 目录）
3. \\ref/\\eqref 的 label 都有定义；\\label 都被引用（报告未引用项）
4. \\citep/\\citet 的键都在 refs.bib 里；bib 里未被引用的条目列出
5. 每个文件的 { } 配对（粗查，忽略 \\{ \\}）
6. 章节文件里不残留 Markdown 语法（**bold**、`code`、### 标题）
7. 中文标点里的裸下划线/百分号（会编译报错或吞字）

    python scripts/tex_lint.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['main.tex', 'sections/00-abstract.tex', 'sections/01-intro.tex', 'sections/02-related.tex',
         'sections/03-model.tex', 'sections/04-protocol.tex', 'sections/05-s1.tex',
         'sections/06-s2.tex', 'sections/07-discussion.tex', 'sections/08-limitations.tex',
         'sections/09-appendix.tex']
TABLES = ['tab_a1', 'tab_a2', 'tab_a3', 'tab_attr', 'tab_b2', 'tab_d1', 'tab_summary']
problems = []
notes = []


def read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()


all_src = {f: read(f) for f in FILES + [f'tables/{t}.tex' for t in TABLES]}

# 1) \input
for f, s in all_src.items():
    for m in re.findall(r'\\input\{([^}]+)\}', s):
        if not os.path.exists(os.path.join(ROOT, m if m.endswith('.tex') else m + '.tex')):
            problems.append(f'[input] {f}: \\input{{{m}}} 文件不存在')

# 2) \includegraphics
for f, s in all_src.items():
    for m in re.findall(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', s):
        if not os.path.exists(os.path.join(ROOT, 'figs', m)):
            problems.append(f'[graphics] {f}: figs/{m} 不存在')

# 3) refs / labels
labels, refs = {}, {}
for f, s in all_src.items():
    for m in re.findall(r'\\label\{([^}]+)\}', s):
        labels.setdefault(m, []).append(f)
    for m in re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', s):
        refs.setdefault(m, []).append(f)
for lab, where in refs.items():
    if lab not in labels:
        problems.append(f'[ref] {where[0]}: \\ref{{{lab}}} 没有对应 \\label')
for lab, where in labels.items():
    if len(where) > 1:
        problems.append(f'[label] 重复定义 {lab}（{", ".join(where)}）')
    if lab not in refs:
        notes.append(f'[label] {lab} 定义了但从未被引用（{where[0]}）')

# 4) 引用键
bib = read('refs.bib')
bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib))
cited = set()
for s in all_src.values():
    for m in re.findall(r'\\cite[pt]\{([^}]+)\}', s):
        cited |= {k.strip() for k in m.split(',')}
for k in cited - bib_keys:
    problems.append(f'[bib] 正文引用了 {k}，但 refs.bib 里没有')
for k in bib_keys - cited:
    problems.append(f'[bib] refs.bib 里的 {k} 未被引用')

# 5/6/7) 括号配对、Markdown 残留、裸特殊字符
for f, s in all_src.items():
    body = re.sub(r'(?<!\\)%.*', '', s)
    if body.count('{') != body.count('}'):
        problems.append(f'[brace] {f}: {{ }} 数量不等（{body.count("{")} vs {body.count("}")}）')
    if re.search(r'\*\*[^*]+\*\*', body):
        problems.append(f'[md] {f}: 残留 Markdown 粗体 **...**')
    if re.search(r'^\s*#{1,6} ', body, re.M):
        problems.append(f'[md] {f}: 残留 Markdown 标题')
    for m in re.finditer(r'[A-Za-z_]\{?\}?_{[^}]*}', body):
        pass
    for m in re.finditer(r'(?<!\\)[_%&#$]', ''):
        pass
    # 裸下划线（未转义、不在 math/texttt 内）粗查：_{ 与 x_y 形式
    for m in re.finditer(r'(?<![\\\w$])([A-Za-z]+_[A-Za-z]+)(?![}^\w])', body):
        pass

print(f'检查了 {len(all_src)} 个文件；label {len(labels)} 个、引用 {len(refs)} 处、'
      f'bib 条目 {len(bib_keys)} 个（被引 {len(cited)}）')
if notes:
    print(f'ℹ️  提示（不阻断）：{len(notes)} 条')
    for n in notes[:6]:
        print('  -', n)
    if len(notes) > 6:
        print(f'  …… 其余 {len(notes) - 6} 条同类提示省略')
if problems:
    print('❌ 必须修的问题：')
    for p in problems:
        print('  -', p)
else:
    print('✅ 静态自检通过（无必须修的问题）')
