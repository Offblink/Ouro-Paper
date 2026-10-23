"""图 1：持续状态架构与状态读写接口（论文用图）。

产出 figs/fig_arch.pdf（LaTeX 矢量）与 figs/fig_arch.png（预览 / Markdown 版）。

设计约束：单色为主 + 一个强调色；正交折线（annotate + angle connectionstyle，圆角）；
无阴影；英文标签（避免中文字体缺失变方框）；技术名用等宽字体。
坐标单位 = 英寸（figsize 与 xlim/ylim 一致），节点按「中心点 + 宽高」摆放。

    FIGDIR=../论文草稿/figs python make_fig_arch.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK, MUTED, SOFT = '#1c1917', '#4f5d75', '#8b93a5'
ACCENT, ACCENT_T = '#b5523a', '#f4e6e1'
PAPER = 'white'
MONO, SANS = 'DejaVu Sans Mono', 'DejaVu Sans'
FIGDIR = os.environ.get('FIGDIR', 'figs')
os.makedirs(FIGDIR, exist_ok=True)

W, H = 13.6, 7.0
fig, axes = plt.subplots(1, 2, figsize=(W, H), dpi=200,
                         gridspec_kw={'width_ratios': [7.8, 5.8], 'wspace': 0.02})
for ax, (x0, x1) in zip(axes, ((0, 7.8), (7.8, 13.6))):
    ax.set_xlim(x0, x1)
    ax.set_ylim(0, H)
    ax.set_aspect('equal')
    ax.axis('off')

KIND = {
    'step':  (PAPER, INK, 1.0),
    'io':    (PAPER, SOFT, 1.0),
    'focal': (ACCENT_T, ACCENT, 1.3),
    'store': ('#f2f3f5', MUTED, 1.0),
}


def node(ax, cx, cy, w, h, name, sub=None, kind='step', name_color=INK, sub_dy=-0.16):
    fill, edge, lw = KIND[kind]
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle='round,pad=0,rounding_size=0.05',
                                linewidth=lw, edgecolor=edge, facecolor=fill, zorder=3))
    if sub:
        ax.text(cx, cy + h / 2 - 0.19, name, ha='center', va='center', fontsize=8.6,
                fontweight='bold', color=name_color, family=SANS, zorder=4)
        ax.text(cx, cy + sub_dy, sub, ha='center', va='center', fontsize=6.3, color=MUTED,
                family=MONO, zorder=4, linespacing=1.45)
    else:
        ax.text(cx, cy, name, ha='center', va='center', fontsize=8.6, fontweight='bold',
                color=name_color, family=SANS, zorder=4)


def arrow(ax, p0, p1, color=MUTED, lw=1.1, dashed=False, rad=0.09):
    ax.annotate('', xy=p1, xytext=p0,
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, shrinkA=0, shrinkB=0,
                                linestyle='--' if dashed else '-',
                                connectionstyle=f'angle,angleA=0,angleB=90,rad={rad}'),
                zorder=2, annotation_clip=False)


def lab(ax, x, y, text, color=MUTED, size=6.3, ha='center', va='center'):
    ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=color, family=MONO, zorder=6,
            bbox=dict(boxstyle='square,pad=1.2', fc=PAPER, ec='none'))


# ==================== 左：patch 级递归 ====================
ax = axes[0]
ax.text(0.14, H - 0.30, 'patch-wise recurrence   ·   cross-patch history is carried by the state only',
        fontsize=6.6, color=MUTED, family=MONO, va='center')

col, bw, bh = 1.60, 2.56, 0.64
ys = {'in': 1.05, 'tok': 2.02, 'patch': 2.99, 'block': 4.30, 'soft': 5.48, 'dec': 6.15}
node(ax, col, ys['in'], bw, bh, 'Input text', 'UTF-8 bytes', 'io')
node(ax, col, ys['tok'], bw, bh, 'ByteTokenizer', 'vocab = 300 (256 + eos + pad)', 'step')
node(ax, col, ys['patch'], bw, bh, 'patch', r'$x_t \in \mathbb{Z}^{1\times64}$', 'step')
node(ax, col, ys['block'], bw, 1.62, r'OuroBlock   $\times 3$',
     'patch-local attention' '\n' '$+$ linear projections' '\n' 'read / write state',
     'focal', sub_dy=-0.28)
node(ax, col, ys['soft'], bw, bh, 'Softmax', 'logits over 300 bytes', 'step')
node(ax, col, ys['dec'], bw, bh, 'Byte decoder / EOS', 'output text', 'io')
for a, b in (('in', 'tok'), ('tok', 'patch'), ('patch', 'block'), ('block', 'soft'), ('soft', 'dec')):
    arrow(ax, (col, ys[a] + bh / 2), (col, ys[b] - bh / 2), rad=0.0)

# 状态面板
px, py, pw, ph = 5.90, 3.60, 2.90, 2.45
ax.add_patch(FancyBboxPatch((px - pw / 2, py - ph / 2), pw, ph,
                            boxstyle='round,pad=0,rounding_size=0.05',
                            linewidth=1.0, edgecolor=MUTED, facecolor='#fbfbfc', zorder=3))
ax.text(px, py + ph / 2 - 0.20, 'State (fixed shape)', ha='center', va='center', fontsize=8.4,
        fontweight='bold', color=INK, family=SANS, zorder=4)
for i, (nm, sub, c) in enumerate((('memory', 'long   ·  shared', MUTED),
                                  ('recurrent c_state x4', 'short  ·  per-stream', ACCENT),
                                  ('queue (64 slots)', 'short  ·  per-stream', MUTED),
                                  ('MTM matrix', 'medium ·  per-stream', MUTED))):
    ry = py + ph / 2 - 0.60 - i * 0.45
    ax.add_patch(FancyBboxPatch((px - pw / 2 + 0.10, ry - 0.175), pw - 0.20, 0.35,
                                boxstyle='round,pad=0,rounding_size=0.03',
                                linewidth=0.8, edgecolor='#d8dbe0', facecolor='white', zorder=4))
    ax.text(px - pw / 2 + 0.20, ry + 0.065, nm, fontsize=6.4, fontweight='bold', color=c,
            family=MONO, va='center', zorder=5)
    ax.text(px - pw / 2 + 0.20, ry - 0.095, sub, fontsize=5.7, color=SOFT, family=MONO,
            va='center', zorder=5)

# 读 / 写 两条通路
arrow(ax, (col + bw / 2, ys['block'] + 0.42), (px - pw / 2 - 0.05, ys['block'] + 0.42), rad=0.0)
lab(ax, 3.62, ys['block'] + 0.58, r'READ   $qM,\; kM$')
arrow(ax, (px - pw / 2 - 0.05, ys['block'] - 0.42), (col + bw / 2, ys['block'] - 0.42),
      color=ACCENT, lw=1.3, rad=0.0)
lab(ax, 3.30, ys['block'] - 0.60, 'WRITE   (commit)', color=ACCENT)
lab(ax, 3.62, ys['block'] + 0.00, 'lock_mem = True' '\n' r'$\Rightarrow$ write off', color=ACCENT, size=5.9)

# 递归：跨 patch 的唯一通道
ax.annotate('', xy=(col + bw / 2 + 0.02, ys['dec']), xytext=(px, py + ph / 2),
            arrowprops=dict(arrowstyle='-|>', color=SOFT, lw=1.0, shrinkA=0, shrinkB=0,
                            connectionstyle='angle,angleA=90,angleB=180,rad=0.25'),
            zorder=1)
lab(ax, 4.90, 6.24, r'$s_{t+1} = f(x_t,\, s_t)$', color=SOFT, size=6.6, ha='left')
lab(ax, 4.90, 5.94, 'the only channel across patches', color=SOFT, size=6.2, ha='left')

# 底部：本文用到的旋钮
ax.add_patch(FancyBboxPatch((0.14, 0.08), 7.5, 0.46,
                            boxstyle='round,pad=0,rounding_size=0.05',
                            linewidth=0.8, edgecolor='#e4e6ea', facecolor='#fafafa', zorder=1))
ax.text(0.32, 0.31, 'knobs used\nin this paper', fontsize=6.0, color=MUTED, family=MONO,
        va='center', ha='left', zorder=3, linespacing=1.3)
for i, (a, b, c) in enumerate((('start state', 'hot / blank', MUTED),
                               ('read/write path', 'commit / lock', ACCENT),
                               ('component surgery', 'reset / freeze', MUTED))):
    x = 2.75 + i * 1.62
    ax.text(x, 0.40, a, fontsize=6.9, color=c, family=SANS, fontweight='bold', va='center',
            ha='center', zorder=3)
    ax.text(x, 0.22, b, fontsize=6.1, color=SOFT, family=MONO, va='center', ha='center', zorder=3)

# ==================== 右：OuroCell 原语 ====================
ax = axes[1]
ax.text(7.94, H - 0.30, 'OuroCell primitive   ·   delta-rule fast weights',
        fontsize=6.6, color=MUTED, family=MONO, va='center')

bx, bw2, bh2 = 9.15, 2.15, 0.60
ky = {'k': 5.90, 'read': 4.90, 'err': 3.90, 'gate': 2.90}
mx, my = 11.75, 4.90
wx, wy = 11.75, 2.90
node(ax, bx, ky['k'], bw2, bh2, r'$k$   (key)', 'projected input', 'io')
node(ax, bx, ky['read'], bw2, bh2, 'read', r'$\hat v = k\,M$', 'step')
node(ax, bx, ky['err'], bw2, bh2, 'error', r'$\Delta v = v - \hat v$', 'step')
node(ax, bx, ky['gate'], bw2, bh2, 'gate', r'$g \cdot \Delta v$', 'step')
node(ax, mx, my, bw2, bh2, r'$M$   (state)', 'delta-rule memory', 'store')
node(ax, 12.62, ky['err'], 1.30, bh2, r'$v$', 'target bytes', 'io')
node(ax, wx, wy, 2.60, bh2, 'write', r'$M \leftarrow M + k^{\top}(g\,\Delta v)$', 'focal')
node(ax, 9.90, 1.10, 3.10, bh2, 'readout', r'$q\,M + \mathrm{causal}(q,k)\cdot v_{dyn}$', 'step')

for a, b in (('k', 'read'), ('read', 'err'), ('err', 'gate')):
    arrow(ax, (bx, ky[a] - bh2 / 2), (bx, ky[b] + bh2 / 2), rad=0.0)
arrow(ax, (bx + bw2 / 2, ky['gate']), (wx - 1.30, ky['gate']), color=ACCENT, lw=1.3, rad=0.0)
lab(ax, 10.55, ky['gate'] + 0.20, 'gated write', color=ACCENT)
arrow(ax, (wx, ky['gate'] + bh2 / 2), (mx, my - bh2 / 2), color=ACCENT, lw=1.3, rad=0.0)
lab(ax, 11.05, 3.72, 'update', color=ACCENT, size=6.0)
# M -> read（读出即 $kM$）
arrow(ax, (mx - bw2 / 2, my), (bx + bw2 / 2, ky['read']), color=MUTED, lw=1.0, rad=0.0)
# v -> error（目标字节）
arrow(ax, (12.62 - 0.65, ky['err']), (bx + bw2 / 2, ky['err']), color=MUTED, lw=1.0,
      dashed=True, rad=0.0)
# M -> readout（绕右侧外圈：右、下、左 三段）
ax.plot([mx + bw2 / 2, 13.30], [my, my], color=MUTED, lw=1.0, zorder=1)
ax.plot([13.30, 13.30], [my, 1.10], color=MUTED, lw=1.0, zorder=1)
ax.annotate('', xy=(9.90 + 1.55, 1.10), xytext=(13.30, 1.10),
            arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=1.0, shrinkA=0, shrinkB=0),
            zorder=2)
lab(ax, 7.94, 1.62, '$v_{dyn}$ = patch-local' '\n' 'causal term', size=5.8, ha='left')

for ext in ('pdf', 'png'):
    fig.savefig(os.path.join(FIGDIR, f'fig_arch.{ext}'), bbox_inches='tight',
                facecolor='white', dpi=200 if ext == 'png' else None)
print('  🖼', os.path.join(FIGDIR, 'fig_arch.pdf'), '+', os.path.join(FIGDIR, 'fig_arch.png'))
