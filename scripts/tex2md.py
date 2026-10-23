"""把 LaTeX 草稿转成 TRead 可直接打开的 Markdown（Markdown + KaTeX）。

TRead 只能读 .md/.txt（markdown-it + KaTeX），不能编译 .tex，所以本脚本把
main.tex + sections/*.tex + tables/*.tex 合成一份单文件 论文草稿.md：
- 章节 → ##/###/####；数学公式整体保留（$...$ / $$...$$），KaTeX 可直接渲染
- 自定义宏展开（\\bits、\\nats、\\pending、\\draftnote）
- \\ref/\\eqref 解析成编号（图 N / 表 N / §x.y），章节/图表编号按 tex 出现顺序计算
- \\input{tables/*} 展开为 Markdown 表格；figure 环境 → 图片 + 斜体图注
- \\citep{k} → [k]

    python scripts/tex2md.py        # 在草稿根目录或任意目录运行

数学片段先被「保护」起来（占位符），所有文本级处理只作用于非公式部分，
最后再还原并展开自定义宏 —— 这样 \\mathrm/\\mathit 等公式命令不会被误删。
"""
import base64
import io as _io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# TRead 用 FileReader 打开文件，相对路径的图片解析不到（会 404）→ 默认把图内联成 data URI
INLINE_IMAGES = '--link-figures' not in sys.argv
MAX_IMG_W = 1200
OUT = os.path.join(ROOT, '论文草稿.md')
FILES = ['main.tex', 'sections/00-abstract.tex', 'sections/01-intro.tex', 'sections/02-related.tex',
         'sections/03-model.tex', 'sections/04-protocol.tex', 'sections/05-s1.tex',
         'sections/06-s2.tex', 'sections/07-discussion.tex', 'sections/08-limitations.tex',
         'sections/09-appendix.tex']
TABLE_FILES = ['tab_a1', 'tab_a2', 'tab_a3', 'tab_attr', 'tab_b2', 'tab_d1', 'tab_summary']
PROTECT = '\x00'


def read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()


def strip_comments(s):
    return '\n'.join(re.sub(r'(?<!\\)%.*$', '', ln) for ln in s.split('\n')
                     if not ln.lstrip().startswith('%'))


src = {f: strip_comments(read(f)) for f in FILES}
tables = {t: strip_comments(read(f'tables/{t}.tex')) for t in TABLE_FILES}


# ============ 编号：章节 / 图表 / 公式 ============
SEC_NO, FIG_NO, TAB_NO, EQ_NO = {}, {}, {}, {}
body_chap = app_idx = sec = sub = 0
chap = 0
for f in FILES:
    appendix = f.endswith('09-appendix.tex')
    for line in src[f].split('\n'):
        st = line.strip()
        if st.startswith('\\section') and not st.startswith('\\section*'):
            if appendix:
                app_idx += 1
                chap = chr(ord('A') + app_idx - 1)
            else:
                body_chap += 1
                chap = body_chap
            sec = sub = 0
        elif st.startswith('\\subsection'):
            sec += 1
            sub = 0
        elif st.startswith('\\subsubsection'):
            sub += 1
        for lab in re.findall(r'\\label\{((?:sec|app):[^}]+)\}', line):
            SEC_NO[lab] = f'{chap}.{sec}.{sub}' if sub else (f'{chap}.{sec}' if sec else str(chap))

fig = tab = eq = 0
for f in FILES:
    for m in re.finditer(r'\\begin\{figure\}.*?\\end\{figure\}', src[f], re.S):
        fig += 1
        for lab in re.findall(r'\\label\{(fig:[^}]+)\}', m.group(0)):
            FIG_NO[lab] = fig
    for m in re.finditer(r'\\begin\{table\}.*?\\end\{table\}|\\input\{tables/(\w+)\}', src[f], re.S):
        tab += 1
        blk = tables.get(m.group(1), '') if m.group(1) else m.group(0)
        for lab in re.findall(r'\\label\{(tab:[^}]+)\}', blk):
            TAB_NO[lab] = tab
    for m in re.finditer(r'\\begin\{equation\}(.*?)\\end\{equation\}', src[f], re.S):
        eq += 1
        for lab in re.findall(r'\\label\{(eq:[^}]+)\}', m.group(1)):
            EQ_NO[lab] = eq


# ============ 文本工具 ============
def apply_cmd(text, cmd, fn):
    """替换 \\cmd{...}，花括号配对（能正确处理嵌套）。"""
    pat = '\\' + cmd + '{'
    out, i = [], 0
    while True:
        j = text.find(pat, i)
        if j < 0:
            out.append(text[i:])
            return ''.join(out)
        out.append(text[i:j])
        k = j + len(pat)
        depth = 1
        while k < len(text) and depth:
            if text[k] == '{':
                depth += 1
            elif text[k] == '}':
                depth -= 1
            k += 1
        out.append(fn(text[j + len(pat):k - 1]))
        i = k


MATHBOX = []          # 全局公式盒：整篇共用，避免嵌套 protect/restore 丢索引


def protect_math(text):
    def repl(m):
        MATHBOX.append(m.group(0))
        return f'{PROTECT}{len(MATHBOX) - 1}{PROTECT}'

    text = re.sub(r'\$\$.*?\$\$', repl, text, flags=re.S)
    text = re.sub(r'(?<!\$)\$(?!\$)[^\n$]*?\$(?!\$)', repl, text)
    return text


def restore_math(text):
    def repl(m):
        i = int(m.group(1))
        if i >= len(MATHBOX):
            return m.group(0)                     # 不是我们的占位符：原样留下
        return MATHBOX[i].replace('\\bits', r'\,\mathrm{bit/byte}').replace('\\nats', r'\,\mathrm{nat}')
    return re.sub(f'{PROTECT}(\\d+){PROTECT}', repl, text)


def ref_text(lab):
    if lab in FIG_NO:
        return f'图 {FIG_NO[lab]}'
    if lab in TAB_NO:
        return f'表 {TAB_NO[lab]}'
    return f'§{SEC_NO.get(lab, "?")}'


def convert(text):
    # 1) 公式环境 → $$...$$（随后会被 protect 保护起来）
    text = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}',
                  lambda m: '\n$$\n' + re.sub(r'\\label\{[^}]*\}', '', m.group(1)).strip() + '\n$$\n',
                  text, flags=re.S)
    text = protect_math(text)
    # 2) 图表（在保护之后做，单元格里的公式是占位符）
    text = re.sub(r'\\begin\{figure\}.*?\\end\{figure\}', lambda m: figure_md(m.group(0)), text, flags=re.S)
    text = re.sub(r'\\input\{tables/(\w+)\}', lambda m: '\n' + table_md(m.group(1)) + '\n', text)
    text = re.sub(r'\\begin\{table\}.*?\\end\{table\}', lambda m: table_md_inline(m.group(0)), text, flags=re.S)
    # 3) 结构
    text = re.sub(r'\\section\*?\{([^}]*)\}(\\label\{[^}]*\})?', r'\n## \1\n', text)
    text = re.sub(r'\\subsection\{([^}]*)\}(\\label\{[^}]*\})?', r'\n### \1\n', text)
    text = re.sub(r'\\subsubsection\{([^}]*)\}(\\label\{[^}]*\})?', r'\n#### \1\n', text)
    text = re.sub(r'\\appendix\b', '\n# 附录\n', text)
    text = text.replace('\\S\\ref', '\\ref').replace('\\S~\\ref', '\\ref')
    text = re.sub(r'\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}|\\maketitle|\\tableofcontents', '', text)
    # 4) 列表
    text = re.sub(r'\\begin\{itemize\}(\[[^\]]*\])?|\\end\{itemize\}', '', text)
    text = re.sub(r'\\begin\{enumerate\}(\[[^\]]*\])?|\\end\{enumerate\}', '', text)
    text = re.sub(r'\\itemsep[-\d.]+(pt|em|ex)|\\parskip|\\baselineskip', '', text)
    text = re.sub(r'\\item(\[[^\]]*\])?', '- ', text)
    for env in ('center', 'small', 'quote', 'fbox'):
        text = text.replace(f'\\begin{{{env}}}', '').replace(f'\\end{{{env}}}', '')
    text = re.sub(r'\\parbox\{[^}]*\}', '', text)
    # 5) 行内命令 + 清理（公式已被保护为占位符，不会被误伤）
    text = md_inline(text)
    # 6) 还原公式
    text = restore_math(text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def md_inline(text):
    """行内命令替换 + 转义清理。公式先保护成占位符，避免 mathbf/mathrm 被清理规则误删。"""
    text = protect_math(text)
    text = apply_cmd(text, 'draftnote', lambda s: '> 说明：' + s)
    text = apply_cmd(text, 'pending', lambda s: f'⚠️ **[{s}]**')
    text = apply_cmd(text, 'textbf', lambda s: f'**{s}**')
    text = apply_cmd(text, 'emph', lambda s: f'*{s}*')
    text = apply_cmd(text, 'textit', lambda s: f'*{s}*')
    text = apply_cmd(text, 'texttt', lambda s: '`' + s.replace('\\_', '_') + '`')
    text = apply_cmd(text, 'footnote', lambda s: f'（{s}）')
    text = apply_cmd(text, 'citep', lambda s: '[' + s + ']')
    text = apply_cmd(text, 'citet', lambda s: '[' + s + ']')
    text = apply_cmd(text, 'eqref', lambda s: ref_text(s))
    text = apply_cmd(text, 'ref', lambda s: ref_text(s))
    # 6) 清理残余命令与转义
    text = re.sub(r'\\label\{[^}]*\}', '', text)
    text = re.sub(r'\\\\\[[^\]]*\]', '  \n', text)          # 标题/换行里的垂直间距
    text = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?', ' ', text)
    text = text.replace('\\_', '_').replace('\\%', '%').replace('\\&', '&')
    text = text.replace('\\S', '§').replace('\\,', ' ').replace('~', ' ')
    text = text.replace('{\\small', '').replace('}', '}')     # 兜底
    return restore_math(text)


def caption_of(blk):
    m = re.search(r'\\caption\{', blk)
    if not m:
        return None
    i = m.end()
    depth = 1
    while i < len(blk) and depth:
        if blk[i] == '{':
            depth += 1
        elif blk[i] == '}':
            depth -= 1
        i += 1
    return blk[m.end():i - 1]


def img_src(name):
    """Markdown 图片地址：默认内联 data URI（等比缩到 MAX_IMG_W，JPEG q=82）。"""
    path = os.path.join(ROOT, 'figs', name)
    if not INLINE_IMAGES or not os.path.exists(path):
        return 'figs/' + name
    from PIL import Image
    im = Image.open(path)
    if im.width > MAX_IMG_W:
        im = im.resize((MAX_IMG_W, round(im.height * MAX_IMG_W / im.width)), Image.LANCZOS)
    if im.mode not in ('RGB', 'L'):
        im = im.convert('RGB')
    buf = _io.BytesIO()
    im.save(buf, format='JPEG', quality=82, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def figure_md(blk):
    out = []
    img = re.search(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', blk)
    if img:
        out.append(f'\n![{img.group(1)}]({img_src(img.group(1))})\n')
    cap = caption_of(blk)
    if cap:
        out.append('*' + md_inline(cap).strip() + '*\n')
    return '\n'.join(out)


def _unmulticolumn(s):
    """把 \\multicolumn{N}{spec}{content} 还原成 content（spec 里可能有 @{})."""
    out, i = [], 0
    tag = '\\multicolumn{'
    while True:
        j = s.find(tag, i)
        if j < 0:
            out.append(s[i:])
            return ''.join(out)
        out.append(s[i:j])
        k = j + len(tag)
        depth = 1
        while depth:                      # 跳过 {N}
            if s[k] == '{':
                depth += 1
            elif s[k] == '}':
                depth -= 1
            k += 1
        depth = 1
        k += 1                            # 进入 {spec}
        while depth:                      # 跳过 {spec}
            if s[k] == '{':
                depth += 1
            elif s[k] == '}':
                depth -= 1
            k += 1
        k += 1                            # 进入 {content}
        depth, start = 1, k
        while depth:
            if s[k] == '{':
                depth += 1
            elif s[k] == '}':
                depth -= 1
            k += 1
        out.append(s[start:k - 1])
        i = k


def tabular_to_md(tex):
    tex = protect_math(tex)               # 表格文件里的公式同样要保护
    # \begin{tabular} 后的列格式说明可能含 @{}，必须按花括号配对跳过
    key = '\\begin{tabular}'
    i0 = tex.find(key)
    if i0 < 0:
        return ''
    k = i0 + len(key)
    depth = 0
    while k < len(tex):
        if tex[k] == '{':
            depth += 1
        elif tex[k] == '}':
            depth -= 1
            if depth == 0:
                k += 1
                break
        k += 1
    end = tex.find('\\end{tabular}', k)
    if end < 0:
        return ''
    body = tex[k:end]
    rows = []
    for raw in body.split('\\\\'):
        line = re.sub(r'\\(top|mid|bottom)rule|\\addlinespace(\[[^\]]*\])?', '', raw)
        line = re.sub(r'\\caption\{[\s\S]*$', '', line)
        line = re.sub(r'\s+', ' ', line).strip()        # 行内换行 → 空格（否则 Markdown 表格会断）
        if not line:
            continue
        cells = [_unmulticolumn(c).replace('\\ ', ' ').strip() for c in line.split('&')]
        rows.append(cells)
    if not rows:
        return ''
    w = max(len(r) for r in rows)
    rows = [r + [''] * (w - len(r)) for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '|'.join([' --- '] * w) + '|']
    out += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return restore_math('\n'.join(out))


def _table(tex):
    out = []
    cap = caption_of(tex)
    if cap:
        out.append('**' + md_inline(cap).strip() + '**\n')
    out.append(tabular_to_md(tex))
    return '\n'.join(out)


def table_md(name):
    return _table(tables[name])


def table_md_inline(blk):
    return _table(blk)


# ============ 组装 ============
main = strip_comments(read('main.tex'))
title = re.search(r'\\title\{', main).end()
depth, k = 1, title
while depth:
    if main[k] == '{':
        depth += 1
    elif main[k] == '}':
        depth -= 1
    k += 1
raw_title = main[title:k - 1]
zh_title = raw_title.split('\\\\')[0].strip()
sub_title = raw_title.split('\\\\')[1].strip() if '\\\\' in raw_title else ''
sub_title = re.sub(r'\\\[\d+(\.\d+)?(pt|em|ex|mm)\]', '', sub_title).strip()
zh_title = re.sub(r'\\textbf\{|\}', '', zh_title)

head = [
    f'# {convert(zh_title).strip()}',
    '',
    f'*{convert(sub_title).strip()}*' if sub_title else '',
    '',
    '> 本文由《论文大纲-A》+《第 1--3 章详细说明》的结构与 BSKD 实验材料合成，是**论文初稿**。'
    '本 Markdown 版供 TRead 阅读与划线提问；**LaTeX 源稿（`main.tex` + `sections/`）是唯一权威版本**，'
    '两版内容由 `scripts/tex2md.py` 从同一份源生成，数字不靠手抄。',
    '',
    '> ⚠️ 全部数字来自**单一检查点**（step 144000/705600，约 20% 训练进度），只做**条件间**比较，'
    '绝对值不可与外部模型对照；未完成项一律标 ⚠️，已作废实验见「附录 C」。',
    '',
]
parts = head + [convert(src[f]) for f in FILES[1:]]
md = re.sub(r'\n{3,}', '\n\n', '\n'.join(parts))
# 「表 表 6」「图 图 9」「§§5」这类重复前缀（正文已写了「表」，ref 又补了一个）
for a, b in (('表 表 ', '表 '), ('图 图 ', '图 '), ('§§', '§'), ('附录 附录 ', '附录 ')):
    md = md.replace(a, b)
with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(md)

n_img = len(re.findall(r'!\[', md))
n_tab = md.count('| --- ')
n_left = len(re.findall(r'\\(ref|eqref|textbf|pending|emph|texttt|draftnote)', md))
imgs = re.findall(r'!\[[^\]]*\]\((data:image/[^)]+|figs/[^)]+)\)', md)
missing = [p for p in imgs if p.startswith('figs/') and not os.path.exists(os.path.join(ROOT, p))]
inlined = sum(1 for p in imgs if p.startswith('data:image/'))
print(f'✅ {OUT}')
print(f'   {len(md)} 字符 / {md.count(chr(10)) + 1} 行；图片 {n_img} 张；表格 {n_tab} 张')
print(f'   残留 LaTeX 命令 {n_left} 处；图片缺文件 {missing}；内联图片 {inlined}/{len(imgs)}')
