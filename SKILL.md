---
name: repo-privacy-guard
description: 在准备将代码推送到公开仓库（GitHub/Gitee/GitLab 等 public repo）前，对仓库做隐私与敏感信息审计和加固。用于检测并清理密钥/Token、环境变量值、用户名、本地绝对路径、硬件机器信息、无关软件信息等本地泄露；并规范本地测试配置（.env/.env.example、config.yaml/config.example.yaml 双文件模式），把本地测试脚本收敛到 local/ 目录，并完善 .gitignore。触发词包括：公开仓库、public repo、开源仓库、推送到GitHub、发布开源、仓库脱敏、隐私检查、敏感信息检查、密钥泄露检查、脱敏、开源前检查、仓库加固、.env.example、config.example.yaml、gitignore 加固、privacy check、secret scan、sanitize repo、open-source prep。当用户提到要把项目/仓库公开、开源、上传到公开平台，或担心本地信息泄露时，必须使用本技能。
---

# Repo Privacy Guard（公开仓库隐私防护）

## 目标

在把本地项目发布到**公开仓库**之前，系统性地识别并消除本地隐私泄露风险，
把「本地运行所需的信息」与「仓库中提交的内容」彻底分离。

核心原则：**公开仓库里只应有可公开的示例，任何本地专属信息都必须留在仓库之外。**

## 防护范围（必须逐项检查）

- **密钥与凭据**：API Key、Token、密码、私钥、证书、云厂商 AK/SK、数据库连接串
- **环境变量值**：`.env` 中的真实值、CI 里硬编码的值、shell 导出语句中的值
- **身份信息**：用户名、真实姓名、邮箱、主机名、公司/组织内部标识
- **本地路径**：`C:\Users\xxx\...`、`/home/xxx/...`、`/Users/xxx/...`、盘符路径、项目外的绝对路径
- **硬件/机器信息**：MAC 地址、设备序列号、机器 ID、GPU/CPU 型号组合、磁盘序列号
- **非相关软件信息**：本地安装的无关软件路径、私有 IDE 配置、个人工具链痕迹
- **其他**：内网 IP、私有域名、内部 API 地址、代理配置、个人备注/日志

## 触发时机

满足以下任一情况即触发本技能：

1. 用户表示要把项目/仓库**公开、开源、发布到公开平台**（推送到 GitHub/Gitee/GitLab public 等）
2. 用户提到**公开仓库 / public repo / 开源仓库**相关的准备工作
3. 用户要求**隐私检查、脱敏、敏感信息扫描、密钥泄露检查、仓库加固**
4. 用户提到 `.env.example`、`config.example.yaml`、`.gitignore` 加固等配置分离需求
5. 用户担心「本地信息会不会泄露」「提交前要不要检查一下」

## 执行逻辑

### 决策树

```
用户请求涉及公开仓库/开源/脱敏
        │
        ├─ 仅「检查/审计」意图 ────────► 流程 A：只扫描，输出报告，不修改
        │
        ├─ 「准备发布/加固」意图 ──────► 流程 B：扫描 + 加固（改配置分离/建 local/写 .gitignore）
        │
        └─ 「已泄露需补救」意图 ───────► 流程 C：加固 + 提交历史清理指导 + 轮换密钥提醒
```

### 流程 A：扫描审计（只读）

1. 运行 `scripts/privacy_scan.py <repo_path>`，得到分级报告（BLOCKER / WARNING / INFO）。
2. **只输出报告，不修改任何文件**。明确告知用户：「以下文件存在风险，需要我处理哪些？」
3. 逐个解释命中的模式属于哪类泄露、为什么危险、如何修复。

### 流程 B：扫描 + 加固（默认流程）

**Step 1 — 扫描**
运行 `scripts/privacy_scan.py <repo_path>`，确认当前风险面。

**Step 2 — 配置分离（本地私有 → 示例公开）**
对每一处本地配置，建立「真实文件 + 示例文件」双文件模式：

| 本地私有文件（不入库） | 公开示例文件（入库） |
|---|---|
| `.env` | `.env.example` |
| `config.yaml` | `config.example.yaml` |
| `config.json` | `config.example.json` |
| `credentials.*` | `credentials.example.*` |

示例文件规则：
- 保留**完整键名**，值替换为占位符（如 `YOUR_API_KEY_HERE`、`/path/to/your/project`、`your_username`）
- 不得包含任何真实值、真实路径、真实用户名
- 可参考 `assets/env.example.template` 与 `assets/config.example.yaml.template`

**Step 3 — 本地测试内容归置到 `local/`**
- 所有本地测试脚本、临时数据、个人配置、调试脚本 → 移入 `local/` 目录
- 仓库根目录不保留任何本地专属文件
- 创建 `local/README.md` 说明该目录用途（可入库，因为不含隐私）

**Step 4 — 加固 `.gitignore`**
将以下条目写入（或合并进）`.gitignore`，参考 `assets/gitignore.template`：
```gitignore
# === 隐私与本地配置（repo-privacy-guard）===
local/
.env
.env.*
!.env.example
config.yaml
config.*.yaml
!config.example.yaml
config.json
config.*.json
!config.example.json
credentials.*
!credentials.example.*
*.pem
*.key
*.p12
*.pfx
.DS_Store
Thumbs.db
*.log
```
注意：`.env.example` 等示例文件必须用 `!` 反选放行，否则会被一并忽略。

**Step 5 — 显性信息清理**
替换代码/文档中硬编码的：
- 绝对路径 → 相对路径或环境变量
- 用户名/主机名 → 占位符
- 内网 IP/域名 → `localhost` 或 `example.com`
- 真实密钥 → 环境变量读取

**Step 6 — 复查**
再次运行 `scripts/privacy_scan.py <repo_path>`，确认 BLOCKER 归零。
输出加固前后对比与剩余项说明。

### 流程 C：已泄露补救

1. 先执行流程 B 完成当前工作区加固。
2. **明确警告**：仅删除文件不够，敏感信息仍存在于 git 历史中。
3. 引导清理历史（`git filter-repo` 或 BFG），并说明这些操作会改写历史、需要强推。
4. **强烈建议立即轮换/吊销所有已泄露的密钥**——这是最重要的一步。

## 使用脚本

### scripts/privacy_scan.py

扫描仓库中的敏感信息，输出分级报告。

```bash
python scripts/privacy_scan.py <repo_path> [--json] [--quiet]
```

- `--json`：以 JSON 输出，便于程序化处理
- `--quiet`：只输出 BLOCKER 级别

退出码：`0` 无 BLOCKER；`1` 存在 BLOCKER（可用于 CI 卡点）。

该脚本覆盖：密钥/Token 模式、`.env` 真实值、用户名与本地路径、MAC/IP/内网地址、
硬件信息、已提交的私有文件（`.env`、`config.yaml`、`local/` 内文件）。

### scripts/init_privacy_layout.py

在指定仓库中一键铺设隐私防护骨架。

```bash
python scripts/init_privacy_layout.py <repo_path> [--force]
```

会创建：`local/`（含 README）、`.env.example`、`config.example.yaml`，
并向 `.gitignore` 追加防护规则（幂等，重复运行不会重复追加）。

## 交付要求

- 加固完成后，向用户给出**简明清单**：改了什么、新增了什么、还剩什么风险。
- 涉及密钥泄露时，**必须**提醒轮换密钥并清理 git 历史，不能只做文件级处理。
- 不擅自修改与隐私无关的业务代码。

## Resources

- `scripts/privacy_scan.py` — 敏感信息扫描器（分级报告 + CI 退出码）
- `scripts/init_privacy_layout.py` — 隐私防护骨架初始化
- `assets/env.example.template` — `.env.example` 模板
- `assets/config.example.yaml.template` — `config.example.yaml` 模板
- `assets/gitignore.template` — `.gitignore` 隐私规则模板
- `references/privacy-checklist.md` — 发布前人工核对清单
