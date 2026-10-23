# 在另一台 Windows 电脑上装 TeX（MiKTeX）——为这份论文草稿

目标：能在这台电脑上**双击 .tex 用 TeXworks 编辑**、并跑 `latexmk -xelatex main` 生成 `main.pdf`。
不需要管理员权限；装完约 440 MB；首次编译会再从镜像拉约 100–300 MB 宏包。

> 本指南数字来自 2026-10-17 在 Windows 11 上的实测：安装器 142 MB（148,882,184 B）、静默安装 121 s、
> 首次完整编译 305 s（含拉 ctex 等包），第二次 43 s。

---

## 0. 先决条件

| 项 | 要求 |
|---|---|
| 系统 | Windows 10/11 x64 |
| 权限 | 普通用户即可（`--private` 用户级安装，不弹 UAC） |
| 磁盘 | ≥ 1 GB（程序 440 MB + 宏包缓存） |
| 网络 | 国内网络走**阿里云 CTAN 镜像**；能访问 `mirrors.aliyun.com` 即可 |
| 论文目录 | 把整个 `论文草稿` 文件夹拷过去（`main.tex`、`sections/`、`tables/`、`figs/`、`refs.bib` 保持相对位置） |

---

## 1. 一条命令（推荐）

把同目录的 `install-miktex.ps1` 和论文文件夹一起拷到对面电脑，然后在**该文件夹**里打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\install-miktex.ps1
```

脚本按顺序做五件事，任何一步失败都会直接报错停下：

1. 从阿里云下载 `basic-miktex-25.12-x64.exe`（`curl -C -` 断点续传，体积校验 >100 MB）；
2. 写 `setupwiz.opt`（用户级、无人值守、A4、自动装包、阿里云仓库）；
3. `basic-miktex-25.12-x64.exe --unattended` 静默安装到 `%LOCALAPPDATA%\Programs\MiKTeX`；
4. 配仓库 `[MPM]RemoteRepository` + `[MPM]AutoInstall=1`；
5. 用 `ctexart` 编一份含中文与公式的样张，确认 `smoke.pdf` 真生成。

装完**新开一个终端**（PATH 才会生效），然后在论文目录：

```powershell
cd 论文草稿
latexmk -xelatex main
```

成功标志：生成 `main.pdf`（实测 32 页），日志里没有 `undefined`。

---

## 2. 手动步骤（脚本不可用 / 想自己控制）

### 2.1 下载安装器

```
https://mirrors.aliyun.com/CTAN/systems/win32/miktex/setup/windows-x64/basic-miktex-25.12-x64.exe
```

- 大小 148,882,184 字节；支持 HTTP Range（断了可以续）。
- 若该电脑能直连 miktex.org，用官网同名文件亦可；**不要用 winget**（实测它会去 miktex.org 拉同一个文件，国内卡死 23 分钟）。

### 2.2 在同一目录写 `setupwiz.opt`

文件名固定为 `setupwiz.opt`，内容逐行如下（**不要加 `--modify-path`，它不是合法选项，带了安装器返回 1**）：

```
--private
--unattended
--auto-install=yes
--package-set=basic
--paper-size=A4
--remote-package-repository=https://mirrors.aliyun.com/CTAN/systems/win32/miktex/tm/packages/
```

### 2.3 静默安装

```powershell
.\basic-miktex-25.12-x64.exe --unattended
```

约 2 分钟。**别加 `--help`**：它弹 GUI 模态框而不是打印帮助，无人值守流程会挂住。

### 2.4 验证

```powershell
$bin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
& "$bin\xelatex.exe" --version
& "$bin\latexmk.exe" -v
& "$bin\mpm.exe" --version
```

### 2.5 配置镜像与自动装包

```powershell
$bin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
& "$bin\mpm.exe" --set-repository=https://mirrors.aliyun.com/CTAN/systems/win32/miktex/tm/packages/
& "$bin\initexmf.exe" "--set-config-value=[MPM]AutoInstall=1"
# 核对
& "$bin\initexmf.exe" "--show-config-value=[MPM]AutoInstall"        # 期望输出 1
& "$bin\initexmf.exe" "--show-config-value=[MPM]RemoteRepository"   # 期望输出阿里云地址
```

装 `basic` 套餐后缺包（如 `neurips.sty`、`titlesec.sty`）会自动从镜像补装——这是 `AutoInstall=1` 的作用。

---

## 3. 编译这份论文

```powershell
cd 论文草稿
latexmk -xelatex main        # 自动跑 bibtex + 多轮 xelatex
```

- **必须是 XeLaTeX**：`main.tex` 是 `ctexart`，pdfLaTeX 会在 `\bits` 处报
  `LaTeX Error: \mathrm allowed only in math mode`（正文里用了 `1.08\bits`；源文件已把
  `\bits/\nats` 改成 `\ensuremath{...}`，不要改回去）。
- 手动等价命令：`xelatex main && bibtex main && xelatex main && xelatex main`。
- 没有 `latexmk`（PATH 没生效）时用绝对路径：
  `"$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\latexmk.exe" -xelatex main`。

---

## 4. 编辑器：TeXworks

MiKTeX 自带 TeXworks，安装器会顺带把 `.tex` 关联到
`%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\miktex-texworks.exe`：

- 双击 `main.tex` 即打开；
- `main.tex` 首行有 `% !TEX program = xelatex`，TeXworks 会自动选中 **XeLaTeX**；
- 按绿色三角排版。**第一次**要在 Typeset 菜单额外执行一次 `BibTeX`（否则引用显示 `[?]`），再排版两次。

> 注意：TeXworks 的自动引擎识别依赖首行 magic comment；若换模板，把那一行一起带上。

---

## 5. 常见故障

| 现象 | 原因与处理 |
|---|---|
| `winget install miktex` 卡住 | 国内拉 miktex.org 失败；改用阿里云 exe（本指南） |
| 安装器返回 1 | `setupwiz.opt` 里有非法选项（常见：`--modify-path`） |
| 命令找不到 `pdflatex/latexmk` | 安装后未开新终端；或直接用以 `$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64` 开头的绝对路径 |
| `File 'xxx.sty' not found` | 仓库没配或 `AutoInstall` 关了；按 2.5 重配；或 `mpm --install=xxx` |
| 编译出 PDF 但中文是方框/乱码 | 用了 pdfLaTeX；改用 `-xelatex` |
| 每次命令都提示 `major issue: So far, you have not checked for MiKTeX updates` | 只是升级提示，不影响编译；想消掉跑一次 `mpm --find-updates` |
| 模板目录里编译后一堆 `.aux/.log` | 正常产物；不要把编译产物提交/打包给别人，建议在副本里编译 |
| 32 位 / ARM 机器 | 本指南针对 x64；ARM64 请改用 TeX Live 或云端 Overleaf |
| 安装器报缺 `VCRUNTIME140.dll` / `MSVCP140.dll` | 装一次 Microsoft VC++ 2015–2022 x64 运行库（微软官网 vc_redist.x64.exe）后重跑 |
| 公司电脑禁止用户级安装 | 改用 Overleaf（上传整个目录即可），或让管理员用 `--shared` 装到 `Program Files` |

---

## 6. 如果对面不是 Windows

| 系统 | 安装 | 中文支持 |
|---|---|---|
| macOS | `brew install --cask mactex-no-gui`（约 4 GB）；或 BasicTeX + `sudo tlmgr install ctex xecjk` | 用 `xelatex`，字体走系统 PingFang |
| Ubuntu/Debian | `sudo apt install texlive-xetex texlive-lang-chinese latexmk` | `xelatex main` |
| 通用 | TeX Live + `tlmgr`；镜像 `https://mirrors.aliyun.com/CTAN/systems/texlive/tlnet` | 同上 |

编译命令一致：`latexmk -xelatex main`。

---

## 7. 不想装 TeX 的替代读法

- **Overleaf**：上传整个目录（保持 `sections/ tables/ figs/`），Menu → Compiler 选 **XeLaTeX**；
- **只看内容**：`论文草稿.md` 用 TRead 打开（公式由 KaTeX 渲染，可划线提问）；
- **pandoc 转 md**：`pandoc main.tex -t markdown+pipe_tables --wrap=none`（复杂宏包可能失真）。
