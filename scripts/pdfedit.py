#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdfedit.py — 「直接改 PDF」工作流的反编译/回迁工具。

背景：论文 LaTeX 是唯一权威版。允许用户临时直接编辑 main.pdf（如 Edge 的
「编辑 PDF」），但那些编辑必须回迁进 .tex，否则下次 latexmk 全丢。

用法：
  python scripts/pdfedit.py snap            # 从 main.pdf 生成/刷新基线（重编译后跑）
  python scripts/pdfedit.py diff [pdf路径]  # 对比编辑后的 PDF 与基线，输出 unified diff

流程约定（agent 执行）：
  1. 用户直接改 main.pdf 并保存；
  2. 用户说「改完了」→ agent 先把改过的 PDF 备份进 C:/tmp/scratch/，再跑 diff；
  3. agent 按 diff 逐条改 sections/*.tex；
  4. latexmk -xelatex main 重编译（main.pdf 被刷新，编辑效果由 LaTeX 重排渲染）；
  5. 重跑 snap 刷新基线，跑 diff 确认收敛到 IDENTICAL。

注意：用户保存编辑后、回迁完成前，任何人不得重编译 main.pdf。
"""
import difflib
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "main.pdf"
BASELINE = ROOT / "main.pdf.edit-baseline.txt"


def extract(pdf: Path) -> str:
    reader = PdfReader(str(pdf))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        parts.append(f"===== PAGE {i} =====")
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def snap() -> None:
    BASELINE.write_text(extract(PDF), encoding="utf-8")
    print(f"baseline written: {BASELINE.name} ({BASELINE.stat().st_size} bytes)")


def diff(pdf_arg: str | None) -> None:
    edited = Path(pdf_arg) if pdf_arg else PDF
    if not BASELINE.exists():
        sys.exit("no baseline; run snap first")
    old = BASELINE.read_text(encoding="utf-8").splitlines()
    new = extract(edited).splitlines()
    delta = list(
        difflib.unified_diff(
            old, new, "baseline(compiled)", f"edited({edited.name})", lineterm="", n=3
        )
    )
    if not delta:
        print("IDENTICAL — no edits detected")
        return
    print("\n".join(delta))
    hunks = sum(1 for line in delta if line.startswith("@@"))
    print(f"\n[stats] changed hunks: {hunks}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "diff"
    if mode == "snap":
        snap()
    elif mode == "diff":
        diff(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        sys.exit("usage: pdfedit.py snap|diff [pdf]")
