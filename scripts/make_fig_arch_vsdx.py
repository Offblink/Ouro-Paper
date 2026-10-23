"""生成论文架构图的 Visio 版（.vsdx），并用 VisioRender 渲染成 PNG。

思路：不手写 Visio 的 document.xml/masters/theme，而是**拿一份 Visio 原生 .vsdx 当骨架**
（默认用团队的 `ouro.vsdx`：里面已有 Rectangle=Master 2、Straight Line=Master 17 母版），
只重写 `visio/pages/page1.xml`（形状）与 `visio/pages/pages.xml`（页面尺寸），其余部件原样保留。
形状从骨架里克隆模板再改单元格，避免漏掉 Visio 需要的 section。

    python scripts/make_fig_arch_vsdx.py --skeleton <骨架.vsdx> --out figs/fig_arch.vsdx
    python -m visiorender figs/fig_arch.vsdx -o figs/fig_arch.png --dpi 200 --mode full

坐标单位 = 英寸，原点在**页面左下角**（y 向上）；文字尺寸单元格单位也是英寸（9pt = 0.125）。
"""
import argparse
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

NS = 'http://schemas.microsoft.com/office/visio/2012/main'
V = f'{{{NS}}}'
PAGE_W, PAGE_H = 13.6, 7.0

# 配色（与 matplotlib 版一致）
INK, MUTED, SOFT = '#1C1917', '#4F5D75', '#8B93A5'
ACCENT, ACCENT_T = '#B5523A', '#F4E6E1'
PANEL_T, GREY_T = '#FBFBFC', '#F2F3F5'

# 字号（英寸；9pt = 0.125）
S_NAME, S_SUB, S_LAB, S_PANEL = 0.125, 0.090, 0.083, 0.118


def cells_of(sh):
    out = {}
    for c in sh:
        if c.tag == V + 'Cell':
            out[c.get('N')] = c.get('V')
    return out


def clone_template(page_root, master):
    """从骨架页里克隆一个指定母版的形状当模板（没有就返回 None）。"""
    for sh in page_root.iter(V + 'Shape'):
        if sh.get('Master') == master and sh.find(V + 'Text') is not None:
            return copy.deepcopy(sh)
    for sh in page_root.iter(V + 'Shape'):
        if sh.get('Master') == master:
            return copy.deepcopy(sh)
    return None


def set_cell(sh, name, value, unit=None):
    for c in sh:
        if c.tag == V + 'Cell' and c.get('N') == name:
            c.set('V', str(value))
            c.attrib.pop('F', None)          # 去掉继承/公式，避免渲染器去别处找值
            if unit:
                c.set('U', unit)
            return c
    attrs = {'N': name, 'V': str(value)}
    if unit:
        attrs['U'] = unit
    return ET.SubElement(sh, V + 'Cell', attrs)


def drop_sections(sh, keep_cells):
    """只保留指定单元格（母版里其余的继续继承）；删掉多余的 Section（Character/Paragraph 重建）。"""
    for c in list(sh):
        if c.tag == V + 'Cell' and c.get('N') not in keep_cells:
            sh.remove(c)
        if c.tag == V + 'Section':
            sh.remove(c)
        if c.tag in (V + 'Text', V + 'Data'):
            sh.remove(c)


def add_character(sh, size, color, bold=False, font='Segoe UI'):
    sec = ET.SubElement(sh, V + 'Section', {'N': 'Character'})
    row = ET.SubElement(sec, V + 'Row', {'IX': '0'})
    for n, v, u in (('Font', font, None), ('Color', color, None),
                    ('Style', '1' if bold else '0', None),
                    ('Size', size, 'PT')):
        a = {'N': n, 'V': str(v)}
        if u:
            a['U'] = u
        ET.SubElement(row, V + 'Cell', a)


def add_paragraph(sh, halign=1):
    """halign: 0=左 1=中 2=右。"""
    sec = ET.SubElement(sh, V + 'Section', {'N': 'Paragraph'})
    row = ET.SubElement(sec, V + 'Row', {'IX': '0'})
    ET.SubElement(row, V + 'Cell', {'N': 'HorzAlign', 'V': str(halign)})


def add_text(sh, lines):
    """行按 <pp IX> 分段；换字号/颜色时在行前插 <cp IX=n>（对应 Character Row IX=n）。"""
    if isinstance(lines, str):
        lines = [lines]
    t = ET.SubElement(sh, V + 'Text')
    ET.SubElement(t, V + 'cp', {'IX': '0'})
    for i, ln in enumerate(lines):
        if i:
            ET.SubElement(t, V + 'cp', {'IX': str(i)})
        pp = ET.SubElement(t, V + 'pp', {'IX': str(i)})
        pp.tail = ln
    return t


def finish(sh, id_, nameu=None):
    sh.set('ID', str(id_))
    sh.set('NameU', nameu or f'Shape.{id_}')
    sh.set('Type', 'Shape')
    return sh


def make_box(tpl, id_, cx, cy, w, h, name=None, sub=None, kind='step', align='center'):
    sh = copy.deepcopy(tpl)
    drop_sections(sh, set())
    set_cell(sh, 'PinX', round(cx, 4)); set_cell(sh, 'PinY', round(cy, 4))
    set_cell(sh, 'Width', round(w, 4)); set_cell(sh, 'Height', round(h, 4))
    set_cell(sh, 'LocPinX', round(w / 2, 4), 'IN'); set_cell(sh, 'LocPinY', round(h / 2, 4), 'IN')
    set_cell(sh, 'Angle', '0'); set_cell(sh, 'FlipX', '0'); set_cell(sh, 'FlipY', '0')
    fill, edge, lw = {
        'step':  ('#FFFFFF', INK, 0.007),
        'io':    ('#FFFFFF', SOFT, 0.007),
        'focal': (ACCENT_T, ACCENT, 0.011),
        'store': (GREY_T, MUTED, 0.007),
        'panel': (PANEL_T, '#D8DBE0', 0.007),
    }[kind]
    set_cell(sh, 'Rounding', '0.05')
    set_cell(sh, 'FillForegnd', fill)
    set_cell(sh, 'FillBkgnd', fill)
    set_cell(sh, 'FillPattern', '1')
    set_cell(sh, 'LineColor', edge)
    set_cell(sh, 'LineWeight', str(lw), 'PT')
    set_cell(sh, 'LinePattern', '1')
    # 文本：框内只写名字（VisioRender 不解析 <pp>，换行只能靠宽度折行 → 说明另开标签形状）
    if name is not None:
        add_character(sh, S_NAME, INK, bold=True)
        add_paragraph(sh, {'center': 1, 'left': 0}[align])
        add_text(sh, name)
    return finish(sh, id_, f'Box.{id_}')


def make_label(tpl, id_, cx, cy, lines, size=S_LAB, color=MUTED, bold=False,
               font='Consolas', halign=1, w=2.4, h=0.22):
    sh = copy.deepcopy(tpl)
    drop_sections(sh, set())
    set_cell(sh, 'PinX', round(cx, 4)); set_cell(sh, 'PinY', round(cy, 4))
    set_cell(sh, 'Width', round(w, 4)); set_cell(sh, 'Height', round(h, 4))
    set_cell(sh, 'LocPinX', round(w / 2, 4), 'IN'); set_cell(sh, 'LocPinY', round(h / 2, 4), 'IN')
    set_cell(sh, 'Angle', '0'); set_cell(sh, 'Rounding', '0')
    set_cell(sh, 'LinePattern', '0'); set_cell(sh, 'FillPattern', '0')
    add_character(sh, size, color, bold=bold, font=font)
    if halign != 1:
        add_paragraph(sh, halign)
    add_text(sh, lines if isinstance(lines, list) else [lines])
    return finish(sh, id_, f'Label.{id_}')


def make_line(tpl, id_, x1, y1, x2, y2, arrow_at='end', color=MUTED, lw=0.007,
              dashed=False, weight_scale=4.0):
    """直线/箭头。1-D 形状：PinX/PinY 取中点，Width=长度，Angle=方向角（弧度）。"""
    import math
    sh = copy.deepcopy(tpl)
    drop_sections(sh, set())
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    set_cell(sh, 'PinX', round((x1 + x2) / 2, 4))
    set_cell(sh, 'PinY', round((y1 + y2) / 2, 4))
    set_cell(sh, 'Width', round(length, 4), 'IN')
    set_cell(sh, 'Height', '0')
    set_cell(sh, 'LocPinX', round(length / 2, 4), 'IN'); set_cell(sh, 'LocPinY', '0')
    set_cell(sh, 'Angle', repr(ang))
    set_cell(sh, 'BeginX', round(x1, 4)); set_cell(sh, 'BeginY', round(y1, 4))
    set_cell(sh, 'EndX', round(x2, 4)); set_cell(sh, 'EndY', round(y2, 4))
    set_cell(sh, 'LineColor', color)
    set_cell(sh, 'LineWeight', str(lw), 'PT')
    set_cell(sh, 'LinePattern', '2' if dashed else '1')
    set_cell(sh, 'BeginArrow', '0')
    set_cell(sh, 'EndArrow', '0')
    if arrow_at == 'end':
        set_cell(sh, 'EndArrow', '4')
        set_cell(sh, 'EndArrowSize', '2')
    elif arrow_at == 'begin':
        set_cell(sh, 'BeginArrow', '4')
        set_cell(sh, 'BeginArrowSize', '2')
    return finish(sh, id_, f'Line.{id_}')


def build(skeleton, out_vsdx):
    tmp = tempfile.mkdtemp(prefix='vsdxbuild-')
    try:
        with zipfile.ZipFile(skeleton) as z:
            z.extractall(tmp)
        page_path = os.path.join(tmp, 'visio', 'pages', 'page1.xml')
        root = ET.parse(page_path).getroot()
        rect_tpl = clone_template(root, '2')       # 矩形母版
        line_tpl = clone_template(root, '17')      # 直线母版
        if rect_tpl is None or line_tpl is None:
            sys.exit('骨架里找不到 Rectangle(Master=2) / Straight Line(Master=17) 母版')

        shapes, sid = [], [0]

        def nid():
            sid[0] += 1
            return sid[0]

        def box(cx, cy, w, h, name=None, sub=None, kind='step', align='center',
                name_dy=-0.24, sub_dy=-0.17, sub_step=0.135):
            """框 + 框内名字；sub 里的每行**单独一个标签形状**（顺序：名字、第 1 行、第 2 行…）。"""
            if name is not None and sub is not None:
                name_shape = make_box(rect_tpl, nid(), cx, cy, w, h, None, None, kind, align)
                shapes.append(name_shape)
                ly = cy + h / 2 + name_dy
                shapes.append(make_label(rect_tpl, nid(), cx, ly, name, size=S_NAME, color=INK,
                                         bold=True, font='Segoe UI'))
            else:
                shapes.append(make_box(rect_tpl, nid(), cx, cy, w, h, name, None, kind, align))
                ly = cy + h / 2 + name_dy
            if sub:
                for j, ln in enumerate(str(sub).split('\n')):
                    shapes.append(make_label(rect_tpl, nid(), cx, ly + sub_dy - j * sub_step, ln,
                                             size=S_SUB, color=MUTED))

        def label(cx, cy, lines, **kw):
            shapes.append(make_label(rect_tpl, nid(), cx, cy, lines, **kw))

        def line(x1, y1, x2, y2, **kw):
            shapes.append(make_line(line_tpl, nid(), x1, y1, x2, y2, **kw))

        # ---------------- 左：patch 级递归 ----------------
        col, bw, bh = 1.60, 2.56, 0.64
        ys = {'in': 1.05, 'tok': 2.02, 'patch': 2.99, 'block': 4.30, 'soft': 5.48, 'dec': 6.15}
        box(col, ys['in'], bw, bh, 'Input text', 'UTF-8 bytes', 'io')
        box(col, ys['tok'], bw, bh, 'ByteTokenizer', 'vocab = 300 (256 + eos + pad)', 'step')
        box(col, ys['patch'], bw, bh, 'patch', r'x_t  in  Z^(1x64)', 'step')
        box(col, ys['block'], bw, 1.62, 'OuroBlock  x3',
            'patch-local attention\n+ linear projections\nread / write state', 'focal')
        box(col, ys['soft'], bw, bh, 'Softmax', 'logits over 300 bytes', 'step')
        box(col, ys['dec'], bw, bh, 'Byte decoder / EOS', 'output text', 'io')
        for a, b in (('in', 'tok'), ('tok', 'patch'), ('patch', 'block'), ('block', 'soft'), ('soft', 'dec')):
            line(col, ys[a] + bh / 2, col, ys[b] - bh / 2, arrow_at='end')

        # 状态面板
        px, py, pw, ph = 5.90, 3.60, 2.90, 2.45
        box(px, py, pw, ph, None, None, 'panel')
        label(px, py + ph / 2 - 0.22, 'State (fixed shape)', size=S_PANEL, color=INK, bold=True,
              font='Segoe UI')
        rows = [('memory', 'long   -  shared', MUTED),
                ('recurrent c_state x4', 'short  -  per-stream', ACCENT),
                ('queue (64 slots)', 'short  -  per-stream', MUTED),
                ('MTM matrix', 'medium -  per-stream', MUTED)]
        for i, (nm, sb, c) in enumerate(rows):
            ry = py + ph / 2 - 0.60 - i * 0.45
            box(px, ry, pw - 0.20, 0.35, None, None, 'step')
            label(px - pw / 2 + 1.20, ry + 0.05, nm, size=S_SUB, color=c, bold=True, halign=0)
            label(px - pw / 2 + 1.20, ry - 0.09, sb, size=0.075, color=SOFT, halign=0)
        # 读 / 写
        line(col + bw / 2, ys['block'] + 0.42, px - pw / 2, ys['block'] + 0.42, arrow_at='end')
        label(3.62, ys['block'] + 0.60, 'READ   qM, kM')
        line(px - pw / 2, ys['block'] - 0.42, col + bw / 2, ys['block'] - 0.42,
             arrow_at='end', color=ACCENT, lw=0.011)
        label(3.30, ys['block'] - 0.60, 'WRITE   (commit)', color=ACCENT, bold=True)
        label(2.55, ys['block'] - 0.92, 'lock_mem = True  ->  write off', color=ACCENT, size=0.075)
        # 递归通道（两段折线 + 箭头）
        line(px, py + ph / 2, px, ys['dec'])
        line(px, ys['dec'], col + bw / 2, ys['dec'], arrow_at='end', color=SOFT, lw=0.007)
        label(4.90, 6.22, 's_t+1 = f(x_t, s_t)', color=SOFT, size=0.090, halign=0)
        label(4.90, 5.96, 'the only channel across patches', color=SOFT, size=0.080, halign=0)

        # 底部旋钮条
        box(3.89, 0.31, 7.50, 0.46, None, None, 'panel')
        label(0.98, 0.31, 'knobs used\nin this paper', size=0.080, color=MUTED, halign=0)
        for i, (a, b, c) in enumerate((('start state', 'hot / blank', MUTED),
                                       ('read/write path', 'commit / lock', ACCENT),
                                       ('component surgery', 'reset / freeze', MUTED))):
            x = 2.75 + i * 1.62
            label(x, 0.40, a, size=0.095, color=c, bold=True, font='Segoe UI')
            label(x, 0.21, b, size=0.080, color=SOFT)

        # ---------------- 右：OuroCell 原语 ----------------
        bx, bw2, bh2 = 9.15, 2.15, 0.60
        ky = {'k': 5.90, 'read': 4.90, 'err': 3.90, 'gate': 2.90}
        mx, my, wx, wy = 11.75, 4.90, 11.75, 2.90
        box(bx, ky['k'], bw2, bh2, 'k   (key)', 'projected input', 'io')
        box(bx, ky['read'], bw2, bh2, 'read', 'v_hat = k M', 'step')
        box(bx, ky['err'], bw2, bh2, 'error', 'd_v = v - v_hat', 'step')
        box(bx, ky['gate'], bw2, bh2, 'gate', 'g . d_v', 'step')
        box(mx, my, bw2, bh2, 'M   (state)', 'delta-rule memory', 'store')
        box(12.62, ky['err'], 1.30, bh2, 'v', 'target bytes', 'io')
        box(wx, wy, 2.60, bh2, 'write', 'M <- M + k^T (g . d_v)', 'focal')
        box(9.90, 1.10, 3.10, bh2, 'readout', 'q M + causal(q,k) . v_dyn', 'step')
        for a, b in (('k', 'read'), ('read', 'err'), ('err', 'gate')):
            line(bx, ky[a] - bh2 / 2, bx, ky[b] + bh2 / 2, arrow_at='end')
        line(bx + bw2 / 2, ky['gate'], wx - 1.30, ky['gate'], arrow_at='end', color=ACCENT, lw=0.011)
        label(9.95, ky['gate'] + 0.22, 'gated write', color=ACCENT)
        line(wx, ky['gate'] + bh2 / 2, mx, my - bh2 / 2, arrow_at='end', color=ACCENT, lw=0.011)
        label(11.05, 3.72, 'update', color=ACCENT)
        line(mx - bw2 / 2, my, bx + bw2 / 2, ky['read'], arrow_at='end')
        line(12.62 - 0.65, ky['err'], bx + bw2 / 2, ky['err'], arrow_at='end', dashed=True)
        line(mx + bw2 / 2, my, 13.30, my)
        line(13.30, my, 13.30, 1.10)
        line(13.30, 1.10, 9.90 + 1.55, 1.10, arrow_at='end')
        label(8.60, 1.62, 'v_dyn = patch-local\ncausal term', size=0.075, halign=0)

        # 重写页面
        # page1.xml 的根就是 PageContents > Shapes > Shape（没有 Page/PageSheet —— 那些在 pages.xml）
        contents = ET.Element(V + 'PageContents', {'xml:space': 'preserve'})
        holder = ET.SubElement(contents, V + 'Shapes')
        for s in shapes:
            holder.append(s)
        ET.ElementTree(contents).write(page_path, encoding='utf-8', xml_declaration=True)

        # 页面属性：只要一张页面、尺寸与上面一致
        pages_path = os.path.join(tmp, 'visio', 'pages', 'pages.xml')
        pages = ET.Element(V + 'Pages', {'xml:space': 'preserve'})
        R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        pg = ET.SubElement(pages, V + 'Page', {'ID': '0', 'NameU': 'Page-1', 'Name': 'Page-1',
                                               'ViewScale': '1', 'ViewCenterX': str(PAGE_W / 2),
                                               'ViewCenterY': str(PAGE_H / 2)})
        ps = ET.SubElement(pg, V + 'PageSheet')
        ET.SubElement(ps, V + 'Cell', {'N': 'PageWidth', 'V': str(PAGE_W), 'U': 'IN'})
        ET.SubElement(ps, V + 'Cell', {'N': 'PageHeight', 'V': str(PAGE_H), 'U': 'IN'})
        rel = ET.SubElement(pg, V + 'Rel')
        rel.set(f'{{{R}}}id', 'rId1')          # → visio/pages/_rels/pages.xml.rels 的 rId1 = page1.xml
        ET.ElementTree(pages).write(pages_path, encoding='utf-8', xml_declaration=True)

        os.makedirs(os.path.dirname(os.path.abspath(out_vsdx)) or '.', exist_ok=True)
        if os.path.exists(out_vsdx):
            os.remove(out_vsdx)
        with zipfile.ZipFile(out_vsdx, 'w', zipfile.ZIP_DEFLATED) as z:
            for base, _, files in os.walk(tmp):
                for f in files:
                    full = os.path.join(base, f)
                    z.write(full, os.path.relpath(full, tmp))
        return len(shapes)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skeleton', default=r'C:\Users\Blinvo\Documents\xwechat_files\wxid_y99ua687dk0d22_7317\msg\file\2026-10\ouro.vsdx')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'figs', 'fig_arch.vsdx'))
    ap.add_argument('--png', default=None, help='给了就用 VisioRender 渲染成 PNG')
    ap.add_argument('--dpi', type=int, default=200)
    a = ap.parse_args()
    n = build(a.skeleton, a.out)
    print(f'✅ {a.out}  （{n} 个形状）')
    if a.png:
        env = dict(os.environ)
        env.setdefault('PYTHONPATH', r'C:\Users\Blinvo\Desktop\myProject\VisioRender')
        r = subprocess.run([sys.executable, '-m', 'visiorender', a.out, '-o', os.path.abspath(a.png),
                            '--dpi', str(a.dpi), '--mode', 'full'], env=env,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        sys.stdout.write(r.stdout or '')
        sys.stderr.write(r.stderr or '')
        if r.returncode:
            sys.exit(f'VisioRender 渲染失败（rc={r.returncode}）: 检查上的容器/形状是否合法')


if __name__ == '__main__':
    main()
