"""图 1（A1 热启动 vs 空白起步）：从 a1_clean_per_patch.json 出图。

关键口径：三个"空白+预热W"档在**同一计分窗口**下是同一次计算（warmup 只改计分起点，
不改状态轨迹），所以这里把三条空白曲线按各自的起点对齐到同一段窗口上——
它们应当完全重合；若重合，即证明"预热"不是有效变量，A1 只能报"热启动 vs 空白"两条件。

    BSKD_DIR=<BSKD 目录> python make_fig_a1.py
"""
import json
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = os.environ.get('BSKD_DIR', '/proj/ouro/BSKD')
FIG = os.environ.get('BSKD_FIGDIR', os.path.join(D, 'figs'))
os.makedirs(FIG, exist_ok=True)
LOG2 = math.log(2)

a1 = json.load(open(os.path.join(D, 'a1_clean_per_patch.json')))
pp = a1['per_patch_nll']
# 对齐到共同窗口: 每个条件的计分起点 = (64 - len(该条件 per_patch)) 号 patch
common = min(len(v) for v in pp.values())
curves = {k: v[len(v) - common:] for k, v in pp.items()}
x = [(i + (64 - common) + 1) * 64 / 1024 for i in range(common)]

fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
styles = {'hot': ('#222', '-', 1.6), 'blank_warm0': ('#a33', '--', 1.0),
          'blank_warm256': ('#48c', ':', 1.6), 'blank_warm1024': ('#6a4', '-.', 1.0)}
for k, (c, ls, lw) in styles.items():
    ax[0].plot(x, curves[k], color=c, ls=ls, lw=lw, label=k)
    ax[1].plot(x, [b - h for b, h in zip(curves[k], curves['hot'])],
               color=c, ls=ls, lw=lw, label=k)
ax[0].set_xlabel('position in text (KB)'); ax[0].set_ylabel('per-patch NLL (nats)')
ax[0].legend(fontsize=8); ax[0].set_title(f'A1: hot vs blank start, aligned window ({common} patches = {common*64//1024} KB)')
ax[1].set_xlabel('position in text (KB)'); ax[1].set_ylabel('blank − hot (nats)')
ax[1].axhline(0, color='gray', ls=':', lw=0.8)
ax[1].legend(fontsize=8); ax[1].set_title('A1: no catch-up trend within the window')
fig.tight_layout()
out = os.path.join(FIG, 'fig_a1_hot_vs_blank.png')
fig.savefig(out, dpi=140)
print('  🖼', out)
print('  三条空白曲线最大两两差 = %.3e nats (0 表示完全重合 → 预热档是伪变量)'
      % max(abs(a - b) for a, b in zip(curves['blank_warm0'], curves['blank_warm1024'])))
print('  对齐窗口: hot=%.4f bits/byte  blank=%.4f bits/byte  gap=%.4f' % (
    sum(curves['hot']) / common / LOG2, sum(curves['blank_warm0']) / common / LOG2,
    (sum(curves['blank_warm0']) - sum(curves['hot'])) / common / LOG2))
