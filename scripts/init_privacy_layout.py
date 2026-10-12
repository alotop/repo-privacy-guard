#!/usr/bin/env python3
"""init_privacy_layout.py — 为仓库铺设隐私防护骨架.

创建:
  local/                本地测试脚本与私有数据目录 (含 README.md)
  .env.example          环境变量示例 (键名齐全, 值全为占位符)
  config.example.yaml   配置示例 (键名齐全, 值全为占位符)
  向 .gitignore 追加隐私防护规则 (幂等)

用法:
    python init_privacy_layout.py <repo_path> [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

GITIGNORE_MARKER = "# === 隐私与本地配置 (repo-privacy-guard) ==="

GITIGNORE_BLOCK = f"""{GITIGNORE_MARKER}
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
*.log
.DS_Store
Thumbs.db
# === end repo-privacy-guard ===
"""

LOCAL_README = """# local/

本目录用于存放**本地专属**内容，不会提交到公开仓库（已在 `.gitignore` 中忽略）。

适合放在这里的内容：

- 本地测试脚本（`smoke_test.py`、`dev_seed.py` 等）
- 个人调试配置、临时数据、抓取缓存
- 仅在本机运行的启停脚本、路径映射文件
- 私有证书、本地数据库文件

不适合放在这里的内容（应放仓库常规位置）：

- 会被别人使用的正式脚本 → 放 `scripts/`
- 示例配置 → 用 `.env.example` / `config.example.yaml`
"""

ENV_EXAMPLE = """# 复制为 .env 后填入真实值；.env 不会被提交。
# .env.example 本身可以提交，其中的值必须全部是占位符。

# --- 应用 ---
APP_ENV=development
APP_PORT=8000
DEBUG=true

# --- 数据库 ---
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/your_db

# --- 第三方服务 ---
OPENAI_API_KEY=YOUR_API_KEY_HERE
OPENAI_BASE_URL=https://api.openai.com/v1

# --- 本地路径 (勿填真实绝对路径) ---
# LOCAL_DATA_DIR=/path/to/your/data
"""

CONFIG_EXAMPLE = """# config.example.yaml — 提交到仓库的示例配置
# 复制为 config.yaml 后填入真实值；config.yaml 不会被提交。

app:
  name: your-app
  env: development
  port: 8000
  debug: true

database:
  host: localhost
  port: 5432
  name: your_db
  user: your_username
  password: your_password

storage:
  # 使用相对路径或环境变量，不要写本机绝对路径
  data_dir: ./data

security:
  jwt_secret: YOUR_SECRET_HERE
  token_ttl: 3600
"""


def ensure_gitignore(repo: Path) -> str:
    gi = repo / ".gitignore"
    if gi.exists():
        content = gi.read_text(encoding="utf-8", errors="ignore")
        if GITIGNORE_MARKER in content:
            return "已存在隐私规则，跳过"
        new = content.rstrip("\n") + "\n\n" + GITIGNORE_BLOCK
        gi.write_text(new, encoding="utf-8")
        return "已追加隐私规则"
    gi.write_text(GITIGNORE_BLOCK, encoding="utf-8")
    return "已创建 .gitignore"


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "已存在，跳过 (用 --force 覆盖)"
    path.write_text(content, encoding="utf-8")
    return "已创建"


def main() -> int:
    ap = argparse.ArgumentParser(description="初始化仓库隐私防护骨架")
    ap.add_argument("repo_path", help="仓库根目录")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的示例文件")
    args = ap.parse_args()

    repo = Path(args.repo_path).expanduser().resolve()
    if not repo.is_dir():
        print(f"错误: 目录不存在 -> {repo}", file=sys.stderr)
        return 2

    local_dir = repo / "local"
    local_dir.mkdir(exist_ok=True)

    actions = {
        "local/": "已存在" if any(local_dir.iterdir()) else "已创建",
        "local/README.md": write_file(local_dir / "README.md", LOCAL_README, args.force),
        ".env.example": write_file(repo / ".env.example", ENV_EXAMPLE, args.force),
        "config.example.yaml": write_file(
            repo / "config.example.yaml", CONFIG_EXAMPLE, args.force),
        ".gitignore": ensure_gitignore(repo),
    }

    print()
    print("=" * 56)
    print("  Repo Privacy Guard — 骨架初始化完成")
    print(f"  目标: {repo}")
    print("=" * 56)
    for name, status in actions.items():
        print(f"  · {name:<22} {status}")
    print("=" * 56)
    print("  下一步: 检查 .env / config.yaml 是否已存在于仓库，")
    print("         若有请移出或改名为示例文件，再运行 privacy_scan.py 复查。")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
