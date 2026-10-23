"""汇总所有 stage JSON → 图表 (BSKD/figs/). 容忍缺文件."""
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = os.environ.get('BSKD_DIR', '/proj/ouro/BSKD')
FIG = os.environ.get('BSKD_FIGDIR', os.path.join(D, 'figs'))
os.makedirs(FIG, exist_ok=True)
LOG2 = math.log(2)


def load(name):
    p = os.path.join(D, name)
    return json.load(open(p)) if os.path.exists(p) else None


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name), dpi=130)
    plt.close(fig)
    print('  🖼', name)


# ---- fig_a2: write vs lock per-patch ----
s1 = load('stage1_a2_a3_a5_results.json')
if s1:
    pp = s1['A2']['per_patch_seed0']
    w, l = pp['write'], pp['lock']
    x = [i * 64 / 1024 for i in range(len(w))]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].plot(x, w, label='write', lw=1.2)
    ax[0].plot(x, l, label='lock_mem', lw=1.2)
    ax[0].set_xlabel('position (KB)'); ax[0].set_ylabel('per-patch NLL (nats)')
    ax[0].legend(); ax[0].set_title(f"A2 write vs lock (16KB, seed0)")
    gap = [lw - ww for lw, ww in zip(l, w)]
    ax[1].plot(x, gap, color='darkred', lw=1.2)
    ax[1].set_xlabel('position (KB)'); ax[1].set_ylabel('lock − write (nats)')
    ax[1].set_title(f'cross-patch write gain grows: {s1["A2"]["gap_front_nats"]:+.2f}→{s1["A2"]["gap_back_nats"]:+.2f}')
    save(fig, 'fig_a2_write_vs_lock.png')

    # ---- fig_a3: boundary-aligned recovery ----
    a35 = s1['A3_A5']
    bds, npd = a35['boundaries'], a35['n_patches_per_doc']
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for name, pps in a35['per_patch'].items():
        if name == 'continuous':
            continue
        curves = []
        for b in bds:
            pi = b // 64
            pre = pps[pi - 4: pi]
            if len(pre) < 4 or pi + 6 > len(pps):
                continue
            base = sum(pre) / 4
            curves.append([v - base for v in pps[pi - 4: pi + 6]])
        if curves:
            m = [sum(c[i] for c in curves) / len(curves) for i in range(10)]
            ax.plot(range(-4, 6), m, marker='o', ms=3, label=name)
    ax.axhline(0, color='gray', ls=':', lw=0.8)
    ax.set_xlabel('patch relative to document boundary'); ax.set_ylabel('Δ NLL vs pre-boundary (nats)')
    ax.legend(fontsize=8); ax.set_title('A3/A5 boundary shock by reset type')
    save(fig, 'fig_a3_boundary_recovery.png')

# ---- fig_a6 ----
s1b = load('stage1b_a6_results.json')
if s1b:
    order = ['lock_all', 'freeze_recurrent', 'freeze_memory', 'freeze_queue_mtm']
    labels = ['lock all', 'freeze recurrent', 'freeze memory', 'freeze queue+mtm']
    vals = [s1b['summary'][k]['delta_vs_write'] for k in order]
    cis = [s1b['summary'][k]['ci'] for k in order]
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.bar(labels, vals, yerr=cis, color=['#a33', '#e66', '#6a4', '#48c'], capsize=4)
    ax.set_ylabel('Δ bits/byte vs full-write')
    ax.set_title('A6: cross-patch adaptation decomposed by component')
    ax.tick_params(axis='x', rotation=15)
    save(fig, 'fig_a6_component_freeze.png')

# ---- fig_d1 ----
s2b = load('stage2b_d1_d2_results.json') or load('stage2_d1_d2_results.json')
if s2b:
    summ = s2b['D1']['summary']
    types = ['same', 'cross', 'shuf', 'zero']
    hot = [summ[t]['hot_mean'] for t in types]
    hot_ci = [summ[t]['hot_ci'] for t in types]
    gain = [summ[t]['gain_mean'] for t in types]
    gain_ci = [summ[t]['gain_ci'] for t in types]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].bar(types, hot, yerr=hot_ci, capsize=4, color='#48c')
    ax[0].set_ylabel('bits/byte (hot start)'); ax[0].set_title('D1: hot-start NLL by text type')
    ax[1].bar(types, gain, yerr=gain_ci, capsize=4, color='#e66')
    ax[1].axhline(0, color='gray', ls=':', lw=0.8)
    ax[1].set_ylabel('hot-start gain (blank − hot)'); ax[1].set_title('gain vanishes on shuffled text')
    save(fig, 'fig_d1_domain.png')

# ---- fig_e1 + e5 + b2 ----
s3 = load('stage3_e1_e5_b2_results.json')
if s3:
    e1 = s3['E1_B2']
    nt = e1['norms_trace']
    xp = [n['patch'] * 64 for n in nt]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for k, c in (('memory', '#a33'), ('recurrent', '#e66'), ('queue', '#6a4'), ('mtm', '#48c')):
        ax[0].plot(xp, [n[k] for n in nt], label=k, color=c, lw=1.1)
    ax[0].set_xscale('log'); ax[0].set_xlabel('tokens'); ax[0].set_ylabel('‖state‖_F')
    ax[0].legend(fontsize=8); ax[0].set_title('E1: state norms bounded (96KB)')
    pp = e1['per_patch']
    ax[1].plot([i * 64 for i in range(len(pp))], pp, lw=0.8)
    ax[1].set_xscale('log'); ax[1].set_xlabel('position (tokens)'); ax[1].set_ylabel('per-patch NLL')
    ax[1].set_title('B1-lite: per-position NLL')
    save(fig, 'fig_e1_norms.png')

    e5 = s3['E5']
    ks = list(e5.keys())
    vals = [e5[k] for k in ks]
    labels = ['inf (no reset)' if k.startswith('inf') else k for k in ks]   # CJK 缺字会变方框
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.bar(labels, vals, color='#48c')
    ax.set_ylabel('bits/byte (64KB total)'); ax.set_title('E5: NLL vs reset period')
    save(fig, 'fig_e5_reset.png')

    b2 = e1['b2']
    bkts = ['<1k', '1k-4k', '4k-16k', '16k-64k', '>64k']
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for n, c in (('n8', '#a33'), ('n16', '#48c')):
        first = [b2[n][b]['nll_first'] for b in bkts]    # 逐桶取, 不能拿 <1k 的值铺满五个桶
        second = [b2[n][b]['nll_second'] for b in bkts]
        gain = [a - b for a, b in zip(first, second)]
        ax[0].plot(range(5), second, marker='o', ms=4, color=c, label=f'{n} 2nd occ')
        ax[0].plot(range(5), first, ls='--', lw=0.9, color=c, label=f'{n} 1st occ')
        ax[1].plot(range(5), gain, marker='o', ms=4, color=c, label=f'{n} gain (1st − 2nd)')
        if n == 'n8':
            for i, b in enumerate(bkts):
                ax[0].annotate(f'n={b2[n][b]["count"]}', (i, second[i]), textcoords='offset points',
                               xytext=(0, 6), fontsize=7, color=c)
    for k, ylab in ((0, 'mean NLL (nats)'), (1, 'Δ NLL (nats)')):
        ax[k].set_xticks(range(5)); ax[k].set_xticklabels(bkts)
        ax[k].set_xlabel('distance to 1st occurrence (tokens)')
        ax[k].set_ylabel(ylab); ax[k].legend(fontsize=8)
    ax[1].axhline(0, color='gray', ls=':', lw=0.8)
    ax[0].set_title('B2: repetition NLL by distance (counts = n8 pairs)')
    ax[1].set_title('B2: gain concentrated <1k, ≈0 beyond 4k')
    save(fig, 'fig_b2_repetition.png')

# ---- fig_g1 + g2 ----
s4 = load('stage4_g1_g2_results.json')
if s4:
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for j, (key, title) in enumerate((('G1a_assoc', 'G1a: associative recall (8 pairs)'),
                                      ('G1b_bigram', 'G1b: bigram transition'))):
        rows = s4[key]
        ks = sorted(int(k) for k in rows.keys())
        wm = [rows[str(k)]['write_mean'] for k in ks]
        wc = [rows[str(k)]['write_ci'] for k in ks]
        lm = [rows[str(k)]['lock_mean'] for k in ks]
        lc = [rows[str(k)]['lock_ci'] for k in ks]
        ax[j].errorbar(ks, wm, yerr=wc, marker='o', ms=4, label='write', color='#48c')
        ax[j].errorbar(ks, lm, yerr=lc, marker='s', ms=4, label='lock', color='#a33')
        ax[j].set_xscale('symlog', linthresh=1); ax[j].set_xlabel('demonstrations k')
        ax[j].set_ylabel('probe answer NLL (bits)'); ax[j].legend(fontsize=8); ax[j].set_title(title)
    save(fig, 'fig_g1_forward_learning.png')

    g2 = s4['G2_natural']
    fig, ax = plt.subplots(figsize=(5, 3.6))
    names = ['write', 'lock']
    f1 = [g2[n]['nll_first'] for n in names]
    f2 = [g2[n]['nll_second'] for n in names]
    xx = range(len(names))
    ax.bar([i - 0.18 for i in xx], f1, width=0.36, label='1st occ', color='#999')
    ax.bar([i + 0.18 for i in xx], f2, width=0.36, label='2nd occ (<4k)', color='#48c')
    ax.set_xticks(list(xx)); ax.set_xticklabels(names)
    ax.set_ylabel('8-gram NLL (nats)'); ax.legend(fontsize=8)
    ax.set_title('G2: natural ICL, write vs lock')
    save(fig, 'fig_g2_natural_icl.png')

# ---- fig_c1 ----
s5 = load('stage5_c1_e2_results.json')
if s5:
    c1 = s5['C1']
    colors = {'normal': '#a33', 'lock_filler': '#999', 'no_stm_filler': '#e6a', 'no_queuemtm_filler': '#48c'}
    first_cond = next(iter(c1))
    first_delta = next(iter(c1[first_cond]))
    if 'probe2_bits' not in c1[first_cond][first_delta]:
        print('  ⚠ stage5 是旧版 C1 (缺 probe1_bits/probe2_bits) → 跳过遗忘曲线图; 先重跑 stage5')
    else:
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        for cond, rows in c1.items():
            deltas = sorted(int(d) for d in rows.keys())
            ax.plot(deltas, [rows[str(d)]['probe2_bits'] for d in deltas], marker='o', ms=4,
                    label=f'probe2 · {cond}', color=colors.get(cond))
        deltas0 = sorted(int(d) for d in c1[first_cond].keys())
        ax.plot(deltas0, [c1[first_cond][str(d)]['probe1_bits'] for d in deltas0], ls='--', lw=1.0,
                color='#222', label='probe1 (注入后立刻测, 与 Δ 无关)')
        ax.set_xscale('log'); ax.set_xlabel('Δ (tokens)'); ax.set_ylabel('answer NLL (bits)')
        ax.legend(fontsize=8); ax.set_title('C1: probe recall vs filler distance')
        save(fig, 'fig_c1_forgetting.png')

    e2 = s5['E2']
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    names = list(e2.keys())
    vals = [e2[n]['nll_garbage'] - e2[n]['nll_pre'] for n in names]
    resid = [e2[n]['residual'] for n in names]
    ax.bar([i - 0.18 for i in range(len(names))], vals, width=0.36, label='garbage shock', color='#a33')
    ax.bar([i + 0.18 for i in range(len(names))], resid, width=0.36, label='residual', color='#48c')
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=15)
    ax.legend(fontsize=8); ax.set_ylabel('Δ NLL (nats)'); ax.set_title('E2: contamination & self-healing')
    save(fig, 'fig_e2_contamination.png')

# ---- fig_b2_freeze (stage7) ----
s7 = load('stage7_b2_freeze_results.json')
if s7:
    conds = s7['conditions']
    bkts = ['<1k', '1k-4k', '4k-16k', '16k-64k', '>64k']
    colors = {'write': '#222', 'lock_all': '#a33', 'freeze_memory': '#6a4',
              'freeze_recurrent': '#e6a', 'freeze_queue_mtm': '#48c'}
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for name, row in conds.items():
        second = [row['b2'][b]['nll_second'] for b in bkts]
        gain = [row['b2'][b]['nll_first'] - row['b2'][b]['nll_second'] for b in bkts]
        ax[0].plot(range(5), second, marker='o', ms=4, label=name, color=colors.get(name), lw=1.2)
        ax[1].plot(range(5), gain, marker='o', ms=4, label=name, color=colors.get(name), lw=1.2)
    for k, ylab, title in ((0, '2nd-occurrence NLL (nats)', 'B2-freeze: 2nd-occurrence NLL by distance'),
                           (1, 'gain 1st − 2nd (nats)', 'B2-freeze: <1k gain dies only when recurrent is frozen')):
        ax[k].set_xticks(range(5)); ax[k].set_xticklabels(bkts)
        ax[k].set_xlabel('distance to 1st occurrence (tokens)')
        ax[k].set_ylabel(ylab); ax[k].legend(fontsize=8); ax[k].set_title(title)
    ax[1].axhline(0, color='gray', ls=':', lw=0.8)
    save(fig, 'fig_b2_freeze.png')

# ---- fig_g1c + e1_long (stage6) ----
s6 = load('stage6_g1c_e1long_results.json')
if s6:
    rows = s6['G1c_word_assoc']
    ks = sorted(int(k) for k in rows.keys())
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    wm = [rows[str(k)]['write_mean'] for k in ks]
    wc = [rows[str(k)]['write_ci'] for k in ks]
    lm = [rows[str(k)]['lock_mean'] for k in ks]
    lc = [rows[str(k)]['lock_ci'] for k in ks]
    ax.errorbar(ks, wm, yerr=wc, marker='o', ms=4, label='write', color='#48c')
    ax.errorbar(ks, lm, yerr=lc, marker='s', ms=4, label='lock', color='#a33')
    ax.set_xscale('symlog', linthresh=1)
    ax.set_xlabel('demonstrations k'); ax.set_ylabel('probe NLL (bits)')
    ax.legend(fontsize=8); ax.set_title('G1c: word-pair recall — no cross-patch binding')
    save(fig, 'fig_g1c_word_assoc.png')

    e1l = s6['E1_long']
    nt = e1l['norms_trace']
    xp = [n['patch'] * 64 for n in nt]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for k, c in (('memory', '#a33'), ('recurrent', '#e66'), ('queue', '#6a4'), ('mtm', '#48c')):
        ax[0].plot(xp, [n[k] for n in nt], label=k, color=c, lw=1.0)
    ax[0].set_xscale('log'); ax[0].set_xlabel('tokens'); ax[0].set_ylabel('‖state‖_F')
    ax[0].legend(fontsize=8); ax[0].set_title('E1-long: norms bounded over 512KB')
    b2 = e1l['b2']
    bkts6 = ['<1k', '1k-4k', '4k-16k', '16k-64k', '64k-256k', '>256k']
    for n, c in (('n8', '#a33'), ('n16', '#48c')):
        ax[1].plot(range(6), [b2[n][b]['nll_second'] for b in bkts6], marker='o', ms=4, color=c, label=f'{n} 2nd occ')
        ax[1].plot(range(6), [b2[n][b]['nll_first'] for b in bkts6], ls='--', lw=0.9, color=c, label=f'{n} 1st occ')
    ax[1].set_xticks(range(6)); ax[1].set_xticklabels(bkts6, fontsize=8)
    ax[1].set_xlabel('distance (tokens)'); ax[1].set_ylabel('NLL (nats)')
    ax[1].legend(fontsize=8)
    ax[1].set_title('B2 over 512KB: no monotone decay (n16 far buckets n≤38)')
    save(fig, 'fig_e1long_b2.png')

print('done.')
