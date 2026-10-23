"""画 Visio 版论文图的公用套件：拿 Visio 原生 .vsdx 当骨架，只重写页面内容。

设计要点（都是踩过的坑）：
- **page1.xml 的根是 `PageContents > Shapes > Shape`**，没有 Page/PageSheet（那些在 pages.xml）；
  页面尺寸写 pages.xml，并在 Page 里保留 `<Rel r:id='rId1'/>`，否则 VisioRender 找不到页、渲染出 0 个形状。
- **VisioRender 不解析 `<pp>`**（段落标记被忽略），换行只能靠 `\\n` 或另开标签形状 —— 所以
  「框内名字 + 说明」用两个形状叠放，别指望一个文本框里两行。
- 1-D 形状（直线/箭头）用 `PinX/PinY`（中点）+ `Width`（长度）+ `Angle`（弧度）+ `BeginX/Y`、`EndX/Y`；
  箭头用 `EndArrow=4`（实测头画在 End 端）。单元格里的 `F` 公式一律去掉，避免渲染器去找别的 sheet。
- 文字尺寸单元格单位是**英寸**（9pt = 0.125），但 U 属性按 Visio 习惯写 `PT`。

用法：
    kit = VsdxKit(skeleton_path)
    kit.box(cx, cy, w, h, 'read', 'v_hat = k M', kind='step')
    kit.line(x1, y1, x2, y2, arrow=True)
    kit.save(out_vsdx, png_out, dpi=200)
"""
import copy
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

NS = 'http://schemas.microsoft.com/office/visio/2012/main'
V = f'{{{NS}}}'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

# 配色（论文图统一用这一套）
INK, MUTED, SOFT = '#1C1917', '#4F5D75', '#8B93A5'
ACCENT, ACCENT_T = '#B5523A', '#F4E6E1'
PANEL_T, GREY_T, RULE = '#FBFBFC', '#F2F3F5', '#D8DBE0'
SANS, MONO = 'Segoe UI', 'Consolas'

KINDS = {
    'step':  ('#FFFFFF', INK, 0.007),
    'io':    ('#FFFFFF', SOFT, 0.007),
    'focal': (ACCENT_T, ACCENT, 0.011),
    'store': (GREY_T, MUTED, 0.007),
    'panel': (PANEL_T, RULE, 0.007),
}


class VsdxKit:
    def __init__(self, skeleton):
        self.skeleton = skeleton
        self.tmp = tempfile.mkdtemp(prefix='vsdxkit-')
        with zipfile.ZipFile(skeleton) as z:
            z.extractall(self.tmp)
        root = ET.parse(os.path.join(self.tmp, 'visio', 'pages', 'page1.xml')).getroot()
        self.rect_tpl = self._clone(root, '2')       # 矩形母版
        self.line_tpl = self._clone(root, '17')      # 直线母版
        if self.rect_tpl is None or self.line_tpl is None:
            raise SystemExit('骨架里找不到 Rectangle(2) / Straight Line(17) 母版')
        self.shapes = []
        self._id = 0

    # ---------- 内部 ----------
    @staticmethod
    def _clone(root, master):
        for sh in root.iter(V + 'Shape'):
            if sh.get('Master') == master and sh.find(V + 'Text') is not None:
                return copy.deepcopy(sh)
        for sh in root.iter(V + 'Shape'):
            if sh.get('Master') == master:
                return copy.deepcopy(sh)
        return None

    def _nid(self):
        self._id += 1
        return self._id

    @staticmethod
    def _strip(sh):
        for c in list(sh):
            if c.tag in (V + 'Cell', V + 'Section', V + 'Text', V + 'Data'):
                sh.remove(c)

    @staticmethod
    def _cell(sh, name, value, unit=None):
        for c in sh:
            if c.tag == V + 'Cell' and c.get('N') == name:
                c.set('V', str(value))
                c.attrib.pop('F', None)
                if unit:
                    c.set('U', unit)
                return c
        a = {'N': name, 'V': str(value)}
        if unit:
            a['U'] = unit
        return ET.SubElement(sh, V + 'Cell', a)

    @staticmethod
    def _character(sh, size, color, bold=False, font=SANS):
        sec = ET.SubElement(sh, V + 'Section', {'N': 'Character'})
        row = ET.SubElement(sec, V + 'Row', {'IX': '0'})
        for n, v, u in (('Font', font, None), ('Color', color, None),
                        ('Style', '1' if bold else '0', None), ('Size', size, 'PT')):
            a = {'N': n, 'V': str(v)}
            if u:
                a['U'] = u
            ET.SubElement(row, V + 'Cell', a)

    @staticmethod
    def _paragraph(sh, halign):
        sec = ET.SubElement(sh, V + 'Section', {'N': 'Paragraph'})
        row = ET.SubElement(sec, V + 'Row', {'IX': '0'})
        ET.SubElement(row, V + 'Cell', {'N': 'HorzAlign', 'V': str(halign)})

    @staticmethod
    def _text(sh, lines):
        lines = lines if isinstance(lines, list) else [lines]
        t = ET.SubElement(sh, V + 'Text')
        ET.SubElement(t, V + 'cp', {'IX': '0'})
        for i, ln in enumerate(lines):
            if i:
                ET.SubElement(t, V + 'cp', {'IX': str(i)})
            pp = ET.SubElement(t, V + 'pp', {'IX': str(i)})
            pp.tail = ln

    # ---------- 公开 API ----------
    def box(self, cx, cy, w, h, name=None, sub=None, kind='step', align='center',
            sub_dy=-0.17, sub_step=0.135, size=0.125, sub_size=0.088, fill=None, edge=None):
        """矩形；给了 name/sub 就在框内叠「名字 + 说明」两个标签（VisioRender 不解析段落换行）。"""
        sh = copy.deepcopy(self.rect_tpl)
        self._strip(sh)
        fill_c, edge_c, lw = KINDS.get(kind, KINDS['step'])
        self._cell(sh, 'PinX', round(cx, 4)); self._cell(sh, 'PinY', round(cy, 4))
        self._cell(sh, 'Width', round(w, 4)); self._cell(sh, 'Height', round(h, 4))
        self._cell(sh, 'LocPinX', round(w / 2, 4), 'IN'); self._cell(sh, 'LocPinY', round(h / 2, 4), 'IN')
        self._cell(sh, 'Angle', '0'); self._cell(sh, 'FlipX', '0'); self._cell(sh, 'FlipY', '0')
        self._cell(sh, 'Rounding', '0.05')
        self._cell(sh, 'FillForegnd', fill or fill_c)
        self._cell(sh, 'FillBkgnd', fill or fill_c)
        self._cell(sh, 'FillPattern', '1' if fill != 'none' else '0')
        self._cell(sh, 'LineColor', edge or edge_c)
        self._cell(sh, 'LineWeight', str(lw), 'PT')
        self._cell(sh, 'LinePattern', '0' if kind == 'none' else '1')
        if kind == 'none':
            self._cell(sh, 'FillPattern', '0')
        sh.set('ID', str(self._nid())); sh.set('NameU', f'Box.{self._id}'); sh.set('Type', 'Shape')
        self.shapes.append(sh)
        if name is not None:
            ly = cy + h / 2 - 0.24
            self.label(cx, ly, name, size=size, color=INK, bold=True, font=SANS)
            if sub:
                for j, ln in enumerate(str(sub).split('\n')):
                    self.label(cx, ly + sub_dy - j * sub_step, ln, size=sub_size, color=MUTED)
        return sh

    def label(self, cx, cy, lines, size=0.083, color=MUTED, bold=False, font=MONO,
              halign=1, w=2.6, h=0.24):
        """halign: 1=居中（cx 是中心）; 0=左对齐（cx 是**左边界**）; 2=右对齐（cx 是右边界）。"""
        sh = copy.deepcopy(self.rect_tpl)
        self._strip(sh)
        if halign == 0:
            cx = cx + w / 2
        elif halign == 2:
            cx = cx - w / 2
        self._cell(sh, 'PinX', round(cx, 4)); self._cell(sh, 'PinY', round(cy, 4))
        self._cell(sh, 'Width', round(w, 4)); self._cell(sh, 'Height', round(h, 4))
        self._cell(sh, 'LocPinX', round(w / 2, 4), 'IN'); self._cell(sh, 'LocPinY', round(h / 2, 4), 'IN')
        self._cell(sh, 'Angle', '0'); self._cell(sh, 'Rounding', '0')
        self._cell(sh, 'LinePattern', '0'); self._cell(sh, 'FillPattern', '0')
        self._character(sh, size, color, bold=bold, font=font)
        if halign != 1:
            self._paragraph(sh, halign)
        self._text(sh, lines)
        sh.set('ID', str(self._nid())); sh.set('NameU', f'Label.{self._id}'); sh.set('Type', 'Shape')
        self.shapes.append(sh)
        return sh

    def line(self, x1, y1, x2, y2, arrow=True, arrow_at='end', color=MUTED, lw=0.007, dashed=False):
        sh = copy.deepcopy(self.line_tpl)
        self._strip(sh)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        self._cell(sh, 'PinX', round((x1 + x2) / 2, 4))
        self._cell(sh, 'PinY', round((y1 + y2) / 2, 4))
        self._cell(sh, 'Width', round(length, 4), 'IN')
        self._cell(sh, 'Height', '0')
        self._cell(sh, 'LocPinX', round(length / 2, 4), 'IN'); self._cell(sh, 'LocPinY', '0')
        self._cell(sh, 'Angle', repr(math.atan2(dy, dx)))
        self._cell(sh, 'BeginX', round(x1, 4)); self._cell(sh, 'BeginY', round(y1, 4))
        self._cell(sh, 'EndX', round(x2, 4)); self._cell(sh, 'EndY', round(y2, 4))
        self._cell(sh, 'LineColor', color)
        self._cell(sh, 'LineWeight', str(lw), 'PT')
        self._cell(sh, 'LinePattern', '2' if dashed else '1')
        self._cell(sh, 'BeginArrow', '0'); self._cell(sh, 'EndArrow', '0')
        if arrow:
            key = 'End' if arrow_at == 'end' else 'Begin'
            self._cell(sh, f'{key}Arrow', '4')
            self._cell(sh, f'{key}ArrowSize', '2')
        sh.set('ID', str(self._nid())); sh.set('NameU', f'Line.{self._id}'); sh.set('Type', 'Shape')
        self.shapes.append(sh)
        return sh

    def rect(self, x, y, w, h, **kw):
        """按左下角定位的矩形（默认可见；kind='none' 才是无边框透明块）。"""
        return self.box(x + w / 2, y + h / 2, w, h, **kw)

    def elbow(self, pts, arrow=True, color=MUTED, lw=0.007, dashed=False):
        """正交折线：pts 为 [(x, y), …]，最后一段带箭头。"""
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            self.line(x1, y1, x2, y2, arrow=arrow and i == len(pts) - 2,
                      color=color, lw=lw, dashed=dashed)

    # ---------- 落盘 ----------
    def save(self, out_vsdx, page_w, page_h, png=None, dpi=200):
        page_path = os.path.join(self.tmp, 'visio', 'pages', 'page1.xml')
        contents = ET.Element(V + 'PageContents', {'xml:space': 'preserve'})
        holder = ET.SubElement(contents, V + 'Shapes')
        for s in self.shapes:
            holder.append(s)
        ET.ElementTree(contents).write(page_path, encoding='utf-8', xml_declaration=True)

        pages_path = os.path.join(self.tmp, 'visio', 'pages', 'pages.xml')
        pages = ET.Element(V + 'Pages', {'xml:space': 'preserve'})
        pg = ET.SubElement(pages, V + 'Page', {'ID': '0', 'NameU': 'Page-1', 'Name': 'Page-1',
                                               'ViewScale': '1', 'ViewCenterX': str(page_w / 2),
                                               'ViewCenterY': str(page_h / 2)})
        ps = ET.SubElement(pg, V + 'PageSheet')
        ET.SubElement(ps, V + 'Cell', {'N': 'PageWidth', 'V': str(page_w), 'U': 'IN'})
        ET.SubElement(ps, V + 'Cell', {'N': 'PageHeight', 'V': str(page_h), 'U': 'IN'})
        rel = ET.SubElement(pg, V + 'Rel'); rel.set(f'{{{R}}}id', 'rId1')
        ET.ElementTree(pages).write(pages_path, encoding='utf-8', xml_declaration=True)

        os.makedirs(os.path.dirname(os.path.abspath(out_vsdx)) or '.', exist_ok=True)
        if os.path.exists(out_vsdx):
            os.remove(out_vsdx)
        with zipfile.ZipFile(out_vsdx, 'w', zipfile.ZIP_DEFLATED) as z:
            for base, _, files in os.walk(self.tmp):
                for f in files:
                    full = os.path.join(base, f)
                    z.write(full, os.path.relpath(full, self.tmp))
        print(f'✅ {out_vsdx}  （{len(self.shapes)} 个形状）')
        if png:
            self.render(out_vsdx, png, dpi)
        return out_vsdx

    @staticmethod
    def render(vsdx, png, dpi=200):
        env = dict(os.environ)
        env.setdefault('PYTHONPATH', r'C:\Users\Blinvo\Desktop\myProject\VisioRender')
        r = subprocess.run([sys.executable, '-m', 'visiorender', vsdx, '-o', os.path.abspath(png),
                            '--dpi', str(dpi), '--mode', 'full'], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        sys.stdout.write(r.stdout or '')
        sys.stderr.write(r.stderr or '')
        if r.returncode:
            raise SystemExit(f'VisioRender 渲染失败（rc={r.returncode}）')

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
