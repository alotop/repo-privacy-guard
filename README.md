# repo-privacy-guard

> 公开仓库发布前的隐私与敏感信息防护 —— 一个可被 AI Agent 直接调用的 Skill，也可作为独立命令行工具使用。

在把本地项目推送到 GitHub / Gitee / GitLab 等**公开仓库**之前，系统性地揪出并清除
本地隐私泄露风险：密钥、环境变量真实值、用户名、本地绝对路径、硬件信息、内网地址、
无关软件痕迹……让「本地运行所需的信息」和「仓库里提交的内容」彻底分离。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 为什么需要它

开源一件小事，泄露一片隐私。真实项目里最常见的翻车方式：

- `.env` 忘了加进 `.gitignore`，真实 API Key 直接进了提交历史
- 代码里写死了 `C:\Users\你的真名\project\...`，暴露了用户名
- `config.yaml` 里带着生产库密码被一起提交
- 本地测试脚本里留了内网 IP、MAC 地址、公司内部域名
- 曾经提交过密钥，删了文件以为就没事了 —— 其实还躺在 git 历史里

**repo-privacy-guard** 把这一整套检查变成一条命令 / 一次 AI 调用。

## 特性

- **分级报告**：`BLOCKER` / `WARNING` / `INFO` 三级，BLOCKER 直接阻断发布
- **25+ 条内置规则**：AWS / GitHub / Google / Slack / Stripe / OpenAI / Anthropic /
  GitLab / npm 等密钥特征，JWT、含账密连接串、私钥块、MAC 地址、内网 IP、
  用户名路径、无关软件路径……
- **违规文件识别**：`.env`、`config.yaml`、`credentials.*`、`*.pem`、`local/` 等
  不该入库的文件被纳入仓库时直接报警
- **配置双文件模式**：自动帮你在 `.env` ↔ `.env.example`、
  `config.yaml` ↔ `config.example.yaml` 之间做分离
- **一键加固**：铺设 `local/` 目录、示例配置、`.gitignore` 防护规则（幂等）
- **CI 友好**：无 BLOCKER 退出码 `0`，有则 `1`，可直接做流水线卡点；支持 `--json` 输出
- **AI Agent 就绪**：附带 `SKILL.md`，可被 Claude / WorkBuddy 等 Agent 自动触发调用

## 目录结构

```
repo-privacy-guard/
├── SKILL.md                          # Agent 技能定义（触发词 + 执行逻辑）
├── scripts/
│   ├── privacy_scan.py               # 敏感信息扫描器（分级报告 + CI 退出码）
│   └── init_privacy_layout.py        # 隐私防护骨架初始化（幂等）
├── assets/
│   ├── env.example.template          # .env.example 模板
│   ├── config.example.yaml.template  # config.example.yaml 模板
│   └── gitignore.template            # .gitignore 隐私规则模板
├── references/
│   └── privacy-checklist.md          # 发布前人工核对清单
└── LICENSE
```

## 快速开始

无需任何第三方依赖，只用 Python 标准库。

```bash
git clone https://github.com/alotop/repo-privacy-guard.git
cd repo-privacy-guard
```

### 1. 扫描仓库风险

```bash
python scripts/privacy_scan.py /path/to/your/repo
```

输出示例：

```
====================================================================
  Repo Privacy Guard — 敏感信息扫描报告
  目标: /path/to/your/repo
====================================================================
  BLOCKER: 3   WARNING: 2   INFO: 1
--------------------------------------------------------------------

  .env
    [BLOCKER] --     file_policy: .env 真实环境变量文件被纳入仓库
           └─ rule: PRIVATE_FILE

  app.py
    [BLOCKER] L2     credential: 疑似 OpenAI 风格 API Key (sk-...)
           └─ API="sk-live-abc123..."
           └─ rule: OPENAI_KEY
--------------------------------------------------------------------
  ⛔ 存在 BLOCKER, 禁止直接发布。请先执行加固流程。
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--json` | 以 JSON 输出，便于程序化处理 |
| `--quiet` | 只显示 BLOCKER |

退出码：`0` 无 BLOCKER ／ `1` 存在 BLOCKER ／ `2` 参数错误。

### 2. 一键铺设防护骨架

```bash
python scripts/init_privacy_layout.py /path/to/your/repo
```

会创建 `local/`（含 README）、`.env.example`、`config.example.yaml`，
并向 `.gitignore` 追加防护规则。重复运行不会重复写入（幂等）。

### 3. 人工核对

按 [`references/privacy-checklist.md`](references/privacy-checklist.md) 逐项过一遍，
尤其是 git 历史部分 —— 曾经提交过密钥的话，**必须清理历史并轮换密钥**。

## 核心规范

### 配置双文件模式

| 本地私有文件（不入库） | 公开示例文件（入库） |
|---|---|
| `.env` | `.env.example` |
| `config.yaml` | `config.example.yaml` |
| `config.json` | `config.example.json` |
| `credentials.*` | `credentials.example.*` |

示例文件保留**完整键名**，值全部替换为占位符（`YOUR_API_KEY_HERE`、
`/path/to/your/data`、`your_username`）。

### 本地测试内容归置

所有本地测试脚本、临时数据、个人调试配置 → 移入 `local/`，并加入 `.gitignore`。

### `.gitignore` 要点

```gitignore
local/
.env
.env.*
!.env.example          # 反选放行示例文件，否则会被 .env.* 一并忽略
config.yaml
config.*.yaml
!config.example.yaml
credentials.*
!credentials.example.*
*.pem
*.key
```

## 作为 AI Agent Skill 使用

本仓库根目录的 `SKILL.md` 就是一个标准 Skill 定义。将其放入你的 Agent 技能目录即可：

```bash
# WorkBuddy / 兼容 skills 目录的 Agent
cp -r repo-privacy-guard ~/.workbuddy/skills/
```

当你说「帮我把这个项目开源」「推送到 GitHub 前检查一下有没有泄露」
「检查密钥」「仓库脱敏」等，Agent 会自动触发该技能，走
**审计 → 加固 → 复查** 的流程。

## 适用场景

- 把私人项目首次开源到 GitHub
- 项目从私有仓库转为公开仓库
- 例行检查：提交/推送前的自动化卡点
- 已泄露后的补救（清理 git 历史 + 轮换密钥指导）

## 局限与免责

- 扫描基于正则特征匹配，**可能漏报也可能误报**，`INFO` 级别请人工判断
- 它不能替代密钥轮换：**一旦密钥被提交过，即便删了文件也应立即吊销重发**
- 发布前请自行复核 `git ls-files` 的完整文件清单

## 贡献

欢迎提交 Issue / PR 补充新的密钥特征、脱敏规则或误报修正。
新增规则请附上命中示例与用例。

## 许可证

[MIT](LICENSE)
