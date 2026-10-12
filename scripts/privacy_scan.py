#!/usr/bin/env python3
"""privacy_scan.py — 公开仓库隐私与敏感信息扫描器.

扫描仓库中的密钥、环境变量真实值、用户名、本地路径、硬件信息、
非相关软件信息等本地泄露风险, 输出分级报告.

用法:
    python privacy_scan.py <repo_path> [--json] [--quiet]

退出码:
    0  未发现 BLOCKER
    1  存在 BLOCKER (可用于 CI 卡点)
    2  参数或路径错误
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

BLOCKER = "BLOCKER"
WARNING = "WARNING"
INFO = "INFO"

# ---------------------------------------------------------------------------
# 目录 / 文件过滤
# ---------------------------------------------------------------------------

# 这些目录默认跳过 (第三方依赖、构建产物、版本控制内部)
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "venv", ".venv", "env", ".env",
    "dist", "build", ".idea", ".vscode", ".tox", ".eggs", "site-packages",
}

# 这些文件本身允许包含占位符, 无需深入报告 (示例文件)
EXAMPLE_SUFFIXES = (".example", ".sample", ".template", ".dist")

# 二进制 / 大文件扩展名, 不按文本读
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z", ".jar", ".war",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".pyc", ".pyo",
    ".mp3", ".mp4", ".mov", ".avi", ".woff", ".woff2", ".ttf", ".eot",
    ".lock", ".sum",
}

MAX_FILE_BYTES = 2 * 1024 * 1024  # 超过 2MB 的文本文件跳过


# ---------------------------------------------------------------------------
# 规则定义
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """一条检测规则."""
    id: str
    severity: str
    category: str
    pattern: re.Pattern
    message: str


@dataclass
class Finding:
    """一处命中结果."""
    rule_id: str
    severity: str
    category: str
    file: str
    line: int
    message: str
    excerpt: str


def _r(rid: str, sev: str, cat: str, pattern: str, msg: str, flags=0) -> Rule:
    return Rule(rid, sev, cat, re.compile(pattern, flags), msg)


RULES: list[Rule] = [
    # ---------------- 密钥 / 凭据 (BLOCKER) ----------------
    _r("AWS_AKID", BLOCKER, "credential",
       r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",
       "疑似 AWS Access Key ID"),
    _r("AWS_SECRET", BLOCKER, "credential",
       r"(?i)aws[_\-]?secret[_\-]?(access[_\-]?)?key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})",
       "疑似 AWS Secret Access Key"),
    _r("GOOGLE_API", BLOCKER, "credential",
       r"\bAIza[0-9A-Za-z\-_]{35}\b",
       "疑似 Google API Key"),
    _r("GITHUB_TOKEN", BLOCKER, "credential",
       r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b",
       "疑似 GitHub Token"),
    _r("SLACK_TOKEN", BLOCKER, "credential",
       r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b",
       "疑似 Slack Token"),
    _r("STRIPE_KEY", BLOCKER, "credential",
       r"\b(sk|rk)_(live|test)_[0-9A-Za-z]{16,}\b",
       "疑似 Stripe Key"),
    _r("OPENAI_KEY", BLOCKER, "credential",
       r"\bsk-[A-Za-z0-9\-_]{20,}\b",
       "疑似 OpenAI 风格 API Key (sk-...)"),
    _r("ANTHROPIC_KEY", BLOCKER, "credential",
       r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b",
       "疑似 Anthropic API Key"),
    _r("GITLAB_TOKEN", BLOCKER, "credential",
       r"\bglpat-[A-Za-z0-9\-_]{20,}\b",
       "疑似 GitLab Token"),
    _r("NPM_TOKEN", BLOCKER, "credential",
       r"\bnpm_[A-Za-z0-9]{36}\b",
       "疑似 npm Token"),
    _r("PRIVATE_KEY_BLOCK", BLOCKER, "credential",
       r"-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
       "内嵌私钥内容"),
    _r("JWT", WARNING, "credential",
       r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
       "疑似 JWT / Bearer Token"),
    _r("GENERIC_SECRET_ASSIGN", BLOCKER, "credential",
       r"(?i)\b(api[_\-]?key|apikey|secret[_\-]?key|secret|passwd|password|pwd|"
       r"access[_\-]?token|auth[_\-]?token|refresh[_\-]?token|token|"
       r"client[_\-]?secret|private[_\-]?key|db[_\-]?password|"
       r"aws[_\-]?access[_\-]?key[_\-]?id|smtp[_\-]?password)\b\s*[:=]\s*"
       r"['\"]([^'\"]{8,})['\"]",
       "疑似硬编码的密钥/密码"),
    _r("CONN_STRING", WARNING, "credential",
       r"(?i)\b(mongodb(\+srv)?|postgres(ql)?|mysql|redis|amqp|mssql)://[^\s'\"]*:[^\s'\"]*@",
       "疑似含账密的连接串"),
    _r("BEARER_HEADER", WARNING, "credential",
       r"(?i)authorization\s*[:=]\s*['\"]?Bearer\s+[A-Za-z0-9\-._~+/=]{16,}",
       "疑似 Bearer 凭据"),

    # ---------------- 本地路径 (WARNING/BLOCKER) ----------------
    _r("WIN_USERPATH", WARNING, "local_path",
       r"[A-Za-z]:\\Users\\([^\\\s\"']+)",
       "Windows 用户绝对路径 (含用户名)"),
    _r("MAC_USERPATH", WARNING, "local_path",
       r"/Users/([A-Za-z0-9._\-]+)/",
       "macOS 用户绝对路径 (含用户名)"),
    _r("LINUX_HOME", WARNING, "local_path",
       r"/home/([A-Za-z0-9._\-]+)/",
       "Linux 用户绝对路径 (含用户名)"),
    _r("NONC_DRIVE", INFO, "local_path",
       r"\b[A-Za-z]:\\\\(?!Users|Program Files|Windows)[^\s\"']{3,}",
       "非 C 盘本地绝对路径"),

    # ---------------- 硬件 / 网络信息 (WARNING) ----------------
    _r("MAC_ADDR", WARNING, "hardware",
       r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
       "疑似 MAC 地址 (硬件指纹)"),
    _r("SERIAL", WARNING, "hardware",
       r"(?i)\b(serial[_\-]?number|machine[_\-]?id|device[_\-]?id|uuid)\s*[:=]\s*"
       r"['\"]?[A-Za-z0-9\-]{8,}['\"]?",
       "疑似设备/机器标识"),
    _r("PRIVATE_IP", INFO, "network",
       r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|"
       r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b",
       "内网 IP 地址"),
    _r("INTERNAL_HOST", INFO, "network",
       r"(?i)\bhttps?://[A-Za-z0-9.\-]*\.(internal|local|corp|lan|intra)\b",
       "内网/私有域名"),

    # ---------------- 身份信息 (INFO/WARNING) ----------------
    _r("EMAIL", INFO, "identity",
       r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
       "邮箱地址"),

    # ---------------- 非相关软件 / 个人环境 (INFO) ----------------
    _r("SOFTWARE_PATH", INFO, "environment",
       r"(?i)\b(C:\\\\(Program Files( \(x86\))?|ProgramData|AppData\\Local)\\\\[^\s\"']+"
       r"|/Applications/[^\s\"']+\.app)",
       "本机已安装软件路径 (非项目相关)"),
]

# 明确禁止入库的私有文件 (命中即 BLOCKER)
PRIVATE_FILE_PATTERNS = [
    (re.compile(r"(^|/)\.env$"), BLOCKER, ".env 真实环境变量文件被纳入仓库"),
    (re.compile(r"(^|/)\.env\.(?!example|sample|template|dist)[^/]+$"), BLOCKER,
     "私有 .env.* 文件被纳入仓库"),
    (re.compile(r"(^|/)config\.ya?ml$"), BLOCKER,
     "config.yaml 真实配置被纳入仓库 (应改名为 config.example.yaml)"),
    (re.compile(r"(^|/)config\.json$"), BLOCKER,
     "config.json 真实配置被纳入仓库 (应改用 config.example.json)"),
    (re.compile(r"(^|/)credentials\.[^/]+$"), BLOCKER,
     "凭据文件被纳入仓库"),
    (re.compile(r"\.(pem|key|p12|pfx|keystore|jks)$", re.I), BLOCKER,
     "私钥/证书文件被纳入仓库"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$"), BLOCKER,
     "SSH 私钥被纳入仓库"),
    (re.compile(r"(^|/)local/"), WARNING,
     "local/ 目录内容被纳入仓库 (应加入 .gitignore)"),
    (re.compile(r"(^|/)\.credentials$"), BLOCKER,
     "凭据文件被纳入仓库"),
]


# ---------------------------------------------------------------------------
# 扫描逻辑
# ---------------------------------------------------------------------------

def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def is_example_or_ignored(path: Path, root: Path) -> bool:
    name = path.name.lower()
    if any(name.endswith(s) or f".{s}" in name for s in EXAMPLE_SUFFIXES):
        return True
    return False


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def scan_file(path: Path, root: Path, findings: list[Finding]) -> None:
    rel = path.relative_to(root).as_posix()

    # 1) 私有文件检测 (按路径)
    for fpat, fsev, fmsg in PRIVATE_FILE_PATTERNS:
        if fpat.search(rel) or fpat.search("/" + rel):
            findings.append(Finding(
                "PRIVATE_FILE", fsev, "file_policy", rel, 0, fmsg, rel))
            break

    if path.suffix.lower() in SKIP_EXTS:
        return
    text = read_text(path)
    if text is None:
        return

    example = is_example_or_ignored(path, root)
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        for rule in RULES:
            m = rule.pattern.search(line)  # noqa: F841 (pattern is precompiled)
            if not m:
                continue
            # 示例文件里的占位符降级
            sev = rule.severity
            if example and sev == BLOCKER:
                sev = INFO
            findings.append(Finding(
                rule.id, sev, rule.category, rel, lineno,
                rule.message, stripped[:160]))
            break  # 一行只报一条, 避免噪音


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen = set()
    out = []
    for f in findings:
        key = (f.rule_id, f.file, f.line, f.excerpt)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


SEV_ORDER = {BLOCKER: 0, WARNING: 1, INFO: 2}


def report(findings: list[Finding], repo: Path, as_json: bool, quiet: bool) -> int:
    findings = sorted(findings, key=lambda f: (SEV_ORDER[f.severity], f.file, f.line))
    blockers = [f for f in findings if f.severity == BLOCKER]
    warnings = [f for f in findings if f.severity == WARNING]
    infos = [f for f in findings if f.severity == INFO]

    if as_json:
        print(json.dumps({
            "repo": str(repo),
            "summary": {
                "blocker": len(blockers),
                "warning": len(warnings),
                "info": len(infos),
            },
            "findings": [asdict(f) for f in findings],
        }, ensure_ascii=False, indent=2))
        return 1 if blockers else 0

    use_color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    def c(txt, code):
        return f"\033[{code}m{txt}\033[0m" if use_color else txt

    shown = blockers if quiet else findings
    print()
    print(c("=" * 68, "1"))
    print(c("  Repo Privacy Guard — 敏感信息扫描报告", "1"))
    print(f"  目标: {repo}")
    print(c("=" * 68, "1"))
    print(f"  {c('BLOCKER', '31;1')}: {len(blockers)}   "
          f"{c('WARNING', '33;1')}: {len(warnings)}   "
          f"{c('INFO', '36')}: {len(infos)}")
    print(c("-" * 68, "1"))

    if not shown:
        print(c("  未发现风险项。可以安全推进公开仓库准备。", "32;1"))
        print()
        return 0

    current_file = None
    for f in shown:
        if f.file != current_file:
            current_file = f.file
            print(f"\n  {c(f.file, '1')}")
        tag = {BLOCKER: c("[BLOCKER]", "31;1"),
               WARNING: c("[WARN]   ", "33;1"),
               INFO: c("[INFO]   ", "36")}[f.severity]
        loc = f"L{f.line}" if f.line else "--"
        print(f"    {tag} {loc:<6} {f.category}: {f.message}")
        print(f"           └─ {f.excerpt}")
        print(f"           └─ rule: {f.rule_id}")

    print()
    print(c("-" * 68, "1"))
    if blockers:
        print(c("  ⛔ 存在 BLOCKER, 禁止直接发布。"
                "请先执行加固流程 (配置分离 / local/ 归置 / .gitignore)。", "31;1"))
    else:
        print(c("  ✅ 无 BLOCKER。建议复核 WARNING 项后发布。", "32;1"))
    if infos and not quiet:
        print("  ℹ  INFO 项可能为误报, 请人工判断。")
    print()
    return 1 if blockers else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="扫描公开仓库前的隐私/敏感信息风险")
    ap.add_argument("repo_path", help="仓库根目录")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--quiet", action="store_true", help="只显示 BLOCKER")
    args = ap.parse_args()

    repo = Path(args.repo_path).expanduser().resolve()
    if not repo.is_dir():
        print(f"错误: 目录不存在 -> {repo}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for path in iter_files(repo):
        scan_file(path, repo, findings)

    return report(dedupe(findings), repo, args.json, args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
