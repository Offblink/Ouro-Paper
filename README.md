# State Is All You Need

以中型 byte 级有状态语言模型 **Gridman/Ouro** 为对象的实证研究：固定大小的持续状态，到底能承载多少跨上下文信息？

> **状态：初稿。** 所有数字来自单一检查点（训练进度约 20%），只做条件间相对比较，不可与外部模型对照。投稿前需补的实验在正文以「待补」标出。

## 两种读法

| 方式 | 文件 | 说明 |
|---|---|---|
| **PDF（最快）** | `main.pdf` | 编译好的成稿，直接看 |
| **LaTeX 源（投稿 / 修改）** | `main.tex` + `sections/` | XeLaTeX 编译，唯一权威版本 |

另有一份 `论文草稿.md`，是 [TRead](https://github.com/Offblink/TRead) 阅读器版（公式内联、可划线提问），由脚本从 LaTeX 源生成，勿手改。

## 编译

需要 **XeLaTeX**（pdfLaTeX 会在 `\bits` 处报错）。

**Overleaf（推荐，无需装环境）**：新建项目 → 上传整个目录（保持 `sections/ tables/ figs/` 结构）→ Menu 里把 Compiler 设为 **XeLaTeX** → 编译。`ctexart` 会自动处理中文字体。

**本地**（MiKTeX / TeX Live）：

```bash
latexmk -xelatex main        # 自动跑 bibtex + 多轮 xelatex
# 或手动
xelatex main && bibtex main && xelatex main && xelatex main
```

Windows 上一键装 MiKTeX 见 `装TeX指南.md` 与 `install-miktex.ps1`。

## 目录结构

```
main.tex              主文件（标题、草稿状态框、引入各章节）
refs.bib              参考文献（26 条）
sections/             10 个章节（00 摘要 … 09 附录）
tables/               结果表
figs/                 图（PNG 成品 + .vsdx / .pdf 源文件）
scripts/              工具脚本
说明.md               详细说明（编译细节、TRead 用法、投稿前待补项）
```

### scripts/

| 脚本 | 作用 |
|---|---|
| `tex_lint.py` | LaTeX 静态自检（引用 / 图表 / 文献 / 括号） |
| `tex2md.py` | 生成 TRead 版 `论文草稿.md` |
| `pdfedit.py` | PDF 直接编辑回迁：`snap` 建基线、`diff` 对比改动 |
| `make_fig*.py` / `vsdx_kit.py` | 生成 `figs/` 下的图 |

## 版式约定

正文每个大标题（第 1–8 章）另起一页、标题在页首；附录 A–F 连续排布不换页；参考文献单独成页。节内首个浮动体用 `[H]` 防止被拉到标题上方压住标题；超过一页高的大表用 `longtable` 跨页。

## 修改流程

LaTeX 源是唯一权威版本，改内容只改 `.tex`，然后：

```bash
python scripts/tex_lint.py     # 自检
latexmk -xelatex main          # 重编译
python scripts/tex2md.py       # 刷新 TRead 版
```

若直接在 `main.pdf` 上改了文字，用 `scripts/pdfedit.py` 把改动回迁进 `.tex`，详见 `说明.md`。
