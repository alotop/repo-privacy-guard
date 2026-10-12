# 公开仓库发布前隐私核对清单

逐项核对，全部通过后方可推送公开仓库。

## 一、密钥与凭据

- [ ] 仓库内不存在任何 API Key / Token / 密码明文（扫描器 BLOCKER 归零）
- [ ] `.env` 已加入 `.gitignore`，仓库中只有 `.env.example`
- [ ] `.env.example` 的值全部为占位符，无任何真实值
- [ ] `config.yaml` 已加入 `.gitignore`，仓库中只有 `config.example.yaml`
- [ ] 无 `*.pem` / `*.key` / 证书 / 私钥文件
- [ ] 无含账密的数据库/中间件连接串
- [ ] 代码中读取敏感值一律走环境变量，而非硬编码

## 二、身份与路径

- [ ] 无真实用户名（`C:\Users\xxx`、`/home/xxx`、`/Users/xxx`）
- [ ] 无真实邮箱（如需保留，使用 `you@example.com`）
- [ ] 无主机名、机器 ID、MAC 地址等硬件指纹
- [ ] 无项目外的本地绝对路径；路径均为相对路径或环境变量
- [ ] git 提交者邮箱是否为可公开的邮箱（`git config user.email`）

## 三、网络与内网信息

- [ ] 无内网 IP（10.x / 192.168.x / 172.16-31.x）
- [ ] 无私有域名（`.internal` / `.local` / `.corp` 等）
- [ ] 无内部 API 地址、代理配置

## 四、非相关软件信息

- [ ] 无本机已安装的无关软件路径（`AppData`、`/Applications` 等）
- [ ] `.vscode` / `.idea` 中的个人配置已清理或忽略
- [ ] 无个人笔记、待办、日志、临时文件

## 五、结构与配置分离

- [ ] 本地测试脚本与私有数据已归入 `local/`
- [ ] `local/` 已加入 `.gitignore`
- [ ] `.gitignore` 包含全部防护规则，且用 `!` 放行了示例文件
- [ ] `git status` 中不出现任何预期外的本地文件

## 六、Git 历史

- [ ] 历史提交中不含敏感文件（`git log --all --name-only`）
- [ ] 若曾提交过密钥：已用 `git filter-repo` / BFG 清理历史
- [ ] **所有曾泄露的密钥已轮换/吊销**（最重要的一步）

## 七、最终确认

- [ ] 重新运行 `python scripts/privacy_scan.py <repo_path>`，BLOCKER = 0
- [ ] `git ls-files` 人工过目一遍，确认没有意外文件
- [ ] 确认 `.gitignore` 生效：被忽略文件不出现在 `git ls-files` 中
