"""论文里其余「适合用 Visio 画」的图：状态尺度图、评测协议与状态手术、受控对照一览、C1 流结构。

数据类图（折线/柱状）一律留给 matplotlib —— Visio 不适合画散点/柱状。
产出 figs/*.vsdx（可编辑源）+ figs/*.png（渲染结果）。

    python scripts/make_fig_diagrams_vsdx.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vsdx_kit import VsdxKit, INK, MUTED, SOFT, ACCENT, ACCENT_T, PANEL_T, GREY_T, RULE, SANS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'figs')
SKELETON = r'C:\Users\Blinvo\Documents\xwechat_files\wxid_y99ua687dk0d22_7317\msg\file\2026-10\ouro.vsdx'


def fig_state_scales():
    """一原语三尺度：四个分量 × 时标 × 作用域 + 实测归属。"""
    k = VsdxKit(SKELETON)
    W, H = 12.4, 5.8
    k.label(0.30, H - 0.28, 'one primitive, four state components   ·   time scale vs. scope',
            size=0.098, color=MUTED, halign=0)
    # 前向流
    k.label(0.30, 4.98, 'forward stream  (patch = 64 bytes, cross-patch history only in the state)',
            size=0.095, color=SOFT, halign=0)
    for i, t in enumerate(('t-2', 't-1', 't', 't+1', 't+2')):
        x = 1.05 + i * 1.45
        kind = 'focal' if t == 't' else 'step'
        k.box(x, 4.45, 1.15, 0.52, f'patch {t}', None, kind=kind, size=0.110)
        if i:
            k.line(x - 1.45 + 0.575, 4.45, x - 0.575, 4.45, arrow=True)
    k.label(8.9, 4.45, 'state s_t  carries\nthe only channel', size=0.088, color=MUTED, halign=0)
    k.elbow([(1.05, 4.71), (1.05, 5.22), (7.6, 5.22), (7.6, 4.71)], arrow=True, color=SOFT)

    rows = [
        ('memory', 'long', 'shared across streams', 'delta rule, identity init', 7.6, MUTED),
        ('MTM matrix', 'medium', 'per-stream', 'delta rule, source = pushed-out c_state', 5.2, MUTED),
        ('queue (64 slots)', 'short', 'per-stream', 'FIFO of top-level c_state', 2.8, MUTED),
        ('recurrent c_state x4', 'short', 'per-stream', 'gated LSTM-style cell', 2.8, ACCENT),
    ]
    for i, (name, scale, scope, rule, bar, col) in enumerate(rows):
        y = 3.55 - i * 0.72
        k.box(1.55, y, 2.5, 0.58, name, None, kind='store' if col is MUTED else 'focal',
              size=0.115)
        k.rect(3.05, y - 0.09, bar - 0.55, 0.18, fill=ACCENT_T if col is ACCENT else PANEL_T,
               edge=col, kind='step')
        k.label(3.05 + bar / 2 - 0.27, y - 0.30, scale + '  ·  ' + scope, size=0.088, color=col)
        k.label(3.05 + 0.05, y + 0.02, None, size=0.088)
        k.label(9.35, y, rule, size=0.088, color=SOFT, halign=0)
    k.label(3.05, 3.86, 'time scale  (bar length = how long the component stays informative)',
            size=0.085, color=SOFT, halign=0)
    k.label(9.35, 3.86, 'write rule', size=0.085, color=SOFT, halign=0)

    k.rect(0.30, 0.30, 11.8, 0.78, kind='panel')
    k.label(0.55, 0.86, 'measured attribution (A5 / A6 / B2-freeze):',
            size=0.098, color=INK, bold=True, halign=0)
    k.label(0.55, 0.56, 'freezing recurrent costs +1.02 bit/byte ~= locking all writes (+1.03);  '
                        'freezing the matrix memory costs -0.0005 (noise level)',
            size=0.092, color=MUTED, halign=0)
    k.save(os.path.join(FIG, 'fig_state_scales.vsdx'), W, H,
           os.path.join(FIG, 'fig_state_scales.png'))
    k.close()


def fig_protocol():
    """评测协议与状态手术：patch 循环 + 三个操纵旋钮 + 条件声明。"""
    k = VsdxKit(SKELETON)
    W, H = 12.4, 5.6
    k.label(0.30, H - 0.28, 'teacher-forced evaluation loop   ·   knobs land on the state interface',
            size=0.098, color=MUTED, halign=0)

    k.box(1.45, 4.10, 2.0, 0.58, 'patch x_t', '64 bytes', 'step')
    k.box(4.30, 4.10, 2.6, 0.58, 'model(x, s, lock_mem)', 'bf16 / eval / no grad', 'focal')
    k.box(7.85, 4.55, 2.3, 0.50, 'logits', 'next-byte prediction', 'step')
    k.box(7.85, 3.65, 2.3, 0.50, 's -> s t+1', 'written state', 'store')
    k.box(10.85, 4.10, 1.35, 0.58, 'bits/byte', 'only scored', 'io')
    k.line(2.45, 4.10, 3.00, 4.10, arrow=True)
    k.elbow([(5.60, 4.10), (6.30, 4.10), (6.30, 4.55), (6.68, 4.55)], arrow=True)
    k.elbow([(5.60, 4.10), (6.30, 4.10), (6.30, 3.65), (6.68, 3.65)], arrow=True)
    k.line(9.00, 4.55, 10.18, 4.30, arrow=True)
    k.elbow([(7.85, 3.40), (7.85, 2.62), (1.45, 2.62), (1.45, 3.80)], arrow=True)
    k.label(4.65, 2.48, 'state advances every patch: skip scoring, never skip the forward pass',
            size=0.090, color=SOFT)

    k.label(0.30, 2.18, 'state surgery (applied at any patch boundary; the state is an immutable object)',
            size=0.095, color=MUTED, halign=0)
    ops = [('lock_mem', 'cross-patch writes off\n(patch-local channel still on)'),
           ('reload_hot_memory', 'memory only -> training snapshot'),
           ('zero_recurrent', 'recurrent only -> zeros'),
           ('blank_queue_mtm', 'queue -> zeros, MTM -> identity'),
           ('freeze_<subset>', 'restore that subset\nbefore every patch')]
    for i, (name, sem) in enumerate(ops):
        x = 0.95 + i * 2.30
        k.box(x, 1.55, 2.05, 0.82, name, None, 'store', size=0.105)
        k.label(x, 1.00, sem, size=0.082, color=MUTED)
    k.rect(0.30, 0.28, 11.8, 0.50, kind='panel')
    k.label(0.55, 0.53, 'every result states {starting state, lock on/off, reset points}',
            size=0.095, color=INK, halign=0)
    k.save(os.path.join(FIG, 'fig_protocol.vsdx'), W, H, os.path.join(FIG, 'fig_protocol.png'))
    k.close()


def fig_ablation_matrix():
    """受控对照一览：每组只动一个变量。"""
    k = VsdxKit(SKELETON)
    W, H = 12.4, 6.4
    k.label(0.30, H - 0.28, 'controlled contrasts   ·   each pair differs in exactly one knob',
            size=0.098, color=MUTED, halign=0)
    k.label(1.05, H - 0.62, 'experiment', size=0.085, color=SOFT)
    k.label(4.35, H - 0.62, 'condition A  vs  condition B', size=0.085, color=SOFT)
    k.label(10.05, H - 0.62, 'the single variable / what it isolates', size=0.085, color=SOFT)
    rows = [
        ('A1', 'hot start', 'blank start', 'starting state -> does the state carry anything', MUTED),
        ('A2', 'commit (write)', 'lock_mem (read-only)', 'cross-patch writes -> causal gain of writing', INK),
        ('A3', 'continuous stream', 'reset at doc boundary', 'whether previous docs leak in / help', MUTED),
        ('A5', 'continuous', 'reset one component', 'which component carries the boundary shock', MUTED),
        ('A6', 'write all', 'freeze one component', 'which component carries cross-patch adaptation', ACCENT),
        ('B2', 'write all', 'lock / freeze one component', 'where the repetition memory lives', ACCENT),
    ]
    for i, (tag, a, b, var, col) in enumerate(rows):
        y = 5.05 - i * 0.78
        k.box(1.05, y, 0.72, 0.50, tag, None, 'focal' if col is ACCENT else 'store', size=0.110)
        k.box(2.90, y, 1.90, 0.50, a, None, 'step', size=0.105)
        k.label(4.18, y, 'vs', size=0.095, color=SOFT)
        k.box(5.68, y, 2.60, 0.50, b, None, 'step', size=0.105)
        k.line(7.05, y, 8.35, y, arrow=True, color=SOFT)
        k.label(8.50, y, var, size=0.092, color=col, halign=0)
    k.rect(0.30, 0.30, 11.8, 0.56, kind='panel')
    k.label(0.55, 0.58, 'reading: a component matters only if freezing/resetting it costs what locking '
                        'everything costs (A6: recurrent +1.02 vs lock-all +1.03 bit/byte)',
            size=0.092, color=INK, halign=0)
    k.save(os.path.join(FIG, 'fig_ablation_matrix.vsdx'), W, H,
           os.path.join(FIG, 'fig_ablation_matrix.png'))
    k.close()


def fig_c1_stream():
    """C1 作废说明用的流结构图：正确答案位 vs 代码算出的位置（+66 字节）。"""
    k = VsdxKit(SKELETON)
    W, H = 12.4, 4.4
    k.label(0.30, H - 0.28, 'C1 stream layout and the +66-byte offset (why the curve was invalid)',
            size=0.098, color=MUTED, halign=0)
    segs = [('header + 2 x demo', 66, PANEL_T, MUTED),
            ('probe1', 32, '#FFFFFF', INK),
            ('filler  Δ', 9.2, '#F7F7F8', MUTED),
            ('probe2', 32, '#FFFFFF', INK),
            ('padding  63 x space', 63, ACCENT_T, ACCENT)]
    x = 0.45
    scale = 0.062           # 英寸 / 字节（filler 另行压缩）
    for name, nbytes, fill, edge in segs:
        w = 0.62 if name.startswith('filler') else nbytes * scale
        k.rect(x, 2.72, w, 0.58, fill=fill, edge=edge, kind='step')
        k.label(x + w / 2, 3.58, name, size=0.088, color=edge, w=max(w, 1.6))
        x += w + 0.06
    end = x - 0.06
    p2_start = 0.45 + 66 * scale + 0.06 + 32 * scale + 0.06 + 0.62 + 0.06
    # 正确位置：probe2 块内第 3 个字节
    k.line(p2_start + 3 * scale, 2.72, p2_start + 3 * scale, 1.95, arrow=False, color=ACCENT)
    k.label(p2_start + 0.95, 1.72, 'correct: answer = value byte inside probe2', size=0.090,
            color=ACCENT, halign=0)
    # 旧代码：再 +66 字节 → 落进 padding
    bad = p2_start + 66 * scale
    k.line(bad, 2.72, bad, 2.20, arrow=False, color=ACCENT, dashed=True)
    k.label(min(bad + 0.15, 9.9), 2.06, 'old code: +66 more  ->  lands in the padding', size=0.090,
            color=ACCENT, halign=0)
    k.rect(0.45, 0.30, 11.6, 1.10, kind='panel')
    k.label(0.70, 1.14, 'consequence:', size=0.098, color=INK, bold=True, halign=0)
    k.label(0.70, 0.84, '7 of 8 answer positions fell on the trailing spaces, the 8th went out of '
                        'range and was dropped silently;', size=0.092, color=MUTED, halign=0)
    k.label(0.70, 0.56, 'so "probe2 = 0.6 bit/byte" measured predicting spaces, and '
                        'decay = probe2 - probe1 is not a forgetting quantity.',
            size=0.092, color=MUTED, halign=0)
    k.save(os.path.join(FIG, 'fig_c1_stream.vsdx'), W, H, os.path.join(FIG, 'fig_c1_stream.png'))
    k.close()


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True)
    fig_state_scales()
    fig_protocol()
    fig_ablation_matrix()
    fig_c1_stream()
