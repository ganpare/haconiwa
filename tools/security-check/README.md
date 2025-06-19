# 🔐 Git Commit Security Check Tool

A security check system to ensure safe commits to public repositories.

## Overview

This tool checks for the following dangerous information before Git commits:

- **Full Paths**: Hardcoded paths like `/Users/username/`
- **API Keys & Tokens**: Actual API keys and access tokens
- **Passwords**: Hardcoded passwords
- **Private URLs**: `localhost`, private IP addresses
- **Sensitive Files**: `.env`, private key files, etc.
- **Real Email Addresses**: Non-test email addresses

## File Structure

```
tools/security-check/
├── README.md                    # English documentation (this file)
├── README.ja.md                 # Japanese documentation
├── commit_security_check.py     # Main security check script
├── install_hook.py              # Pre-commit hook installer
├── setup_personal_config.py     # Personal config setup script
├── config.json                  # Base configuration file
├── nglist.json.example          # Template for personal settings
├── nglist.json                  # Personal NG list (gitignored)
└── .gitignore                   # Excludes personal config files
```

## 🚀 Quick Start

### 0. Initial Setup (First Time Only)

```bash
# Setup personal security configuration
python tools/security-check/setup_personal_config.py

# Or manually copy and edit the template
cp tools/security-check/nglist.json.example tools/security-check/nglist.json
# Edit nglist.json with your personal info
```

### 1. Manual Security Check

```bash
# Check currently staged files
python tools/security-check/commit_security_check.py

# Verbose output
python tools/security-check/commit_security_check.py -v

# JSON report output
python tools/security-check/commit_security_check.py -r security_report.json
```

### 2. Automatic Check (pre-commit hook)

```bash
# Install hook
python tools/security-check/install_hook.py

# Uninstall hook
python tools/security-check/install_hook.py uninstall
```

After installing the hook, security checks will run automatically during `git commit`.

## 📋 Usage Examples

### Basic Usage

```bash
# First-time setup
python tools/security-check/setup_personal_config.py

# Stage files
git add .

# Run security check
python tools/security-check/commit_security_check.py

# Commit if no issues
git commit -m "feat: add new feature"
```

### CI Environment Usage

```bash
# CI mode (non-interactive)
python tools/security-check/commit_security_check.py --ci
```

Exit codes:
- `0`: Check passed
- `1`: Security issues detected

## 🔍 Check Categories

### Error Level (Blocks commit)

| Category | Description | Example |
|----------|-------------|---------|
| Hardcoded Paths | Full path references | `/Users/john/project/` |
| API Keys | Actual API keys | `api_key = "sk-1234..."` |
| Passwords | Hardcoded passwords | `password = "secret123"` |
| Sensitive Files | Private keys, config files | `private.key`, `.env` |

### Warning Level (Alerts only)

| Category | Description | Example |
|----------|-------------|---------|
| Private URLs | Local/internal URLs | `http://localhost:3000` |
| Real Emails | Non-test email addresses | `john@company.com` |

### Allowed Patterns

The following patterns are considered safe and will pass checks:

```python
# Environment variable references
api_key = os.environ.get("OPENAI_API_KEY")

# Placeholders
api_key = "your_api_key"
email = "test@example.com"

# Relative paths
config_path = "config/settings.json"
```

## ⚙️ Configuration

### config.json

```json
{
  "settings": {
    "strict_mode": false,        # Strict mode
    "auto_fix": false,          # Auto-fix (not implemented)
    "ignore_warnings": false    # Ignore warnings
  },
  "custom_patterns": {
    "organization_specific": {
      "patterns": ["internal\\.company\\.com"],
      "severity": "WARNING",
      "description": "Internal organization URLs"
    }
  }
}
```

### Exclusions

The following files/directories are automatically excluded:

- `.git/`, `node_modules/`, `__pycache__/`
- `.venv/`, `venv/`, `dist/`, `build/`
- `.pyc`, `.log`, `.tmp`, `.DS_Store`
- Image files, audio files, archive files

## 🔧 Command Line Options

```bash
python tools/security-check/commit_security_check.py [options]

Options:
  -h, --help            Show help message
  -v, --verbose         Show detailed output
  -r REPORT, --report REPORT
                        Output JSON report file
  --ci                  CI mode (non-interactive)
```

## 📊 Output Examples

### ✅ Success Example

```
🔐 Git コミットセキュリティチェック開始
==================================================
ℹ️ [15:30:45] ステージングファイル数: 3
ℹ️ [15:30:45] チェック中: tools/security-check/README.md
ℹ️ [15:30:45] チェック中: src/main.py
ℹ️ [15:30:45] チェック中: config/settings.py

==================================================
📊 チェック結果サマリー
📁 総ファイル数: 3
🔍 チェック済み: 3
❌ エラー: 0
⚠️ 警告: 0
ℹ️ 情報: 3

✅ セキュリティチェック合格 - コミット安全
```

### ❌ Failure Example

```
🔐 Git コミットセキュリティチェック開始
==================================================
❌ [15:31:20] src/config.py:15 - 実際のAPIキーやトークン: api_key = "sk-proj-abc123..."
⚠️ [15:31:20] src/utils.py:8 - プライベートIPアドレスやローカルURL: http://localhost:8080

==================================================
📊 チェック結果サマリー
📁 総ファイル数: 2
🔍 チェック済み: 2
❌ エラー: 1
⚠️ 警告: 1
ℹ️ 情報: 2

🚨 セキュリティチェック失敗 - コミット前に修正が必要

修正が必要な問題:
  ❌ src/config.py:15 - 実際のAPIキーやトークン: api_key = "sk-proj-abc123..."
```

## 🛠️ For Developers

### Adding Custom Patterns

Add custom check patterns to `config.json`:

```json
{
  "custom_patterns": {
    "social_security": {
      "patterns": ["\\d{3}-\\d{2}-\\d{4}"],
      "severity": "ERROR",
      "description": "Social Security Number"
    }
  }
}
```

### Programmatic Usage

```python
from tools.security_check.commit_security_check import CommitSecurityChecker

checker = CommitSecurityChecker(verbose=True)
is_safe = checker.run_security_check()

if is_safe:
    print("Safe to commit")
else:
    print("Issues found")
```

## 🚨 Troubleshooting

### Common Issues

**Q: Environment variable references trigger errors**
```python
# ❌ Triggers error
API_KEY = "sk-real-key-here"

# ✅ Correct approach
API_KEY = os.environ.get("OPENAI_API_KEY")
```

**Q: Test files trigger errors**
```python
# ❌ Real email address
test_email = "john@company.com"

# ✅ Test placeholder
test_email = "test@example.com"
```

**Q: Relative paths trigger errors**
```python
# ❌ Full path
config_path = "/Users/john/project/config.json"

# ✅ Relative path
config_path = "config/config.json"
```

### Hook Related

**Q: Pre-commit hook not working**
```bash
# Check hook file permissions
ls -la .git/hooks/pre-commit

# Add execute permission if needed
chmod +x .git/hooks/pre-commit
```

**Q: Temporarily disable hook**
```bash
# Skip with --no-verify option
git commit --no-verify -m "Temporary skip"
```

## 📝 License

This tool is provided under the MIT License.

## 🤝 Contributing

Please report bugs and feature requests via GitHub Issues.

## 📚 Related Documentation

- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Security Best Practices](../docs/security-best-practices.md)