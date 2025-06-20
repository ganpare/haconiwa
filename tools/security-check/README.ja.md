# 🔐 Git コミットセキュリティチェックツール

公開リポジトリへの安全なコミットを保証するためのセキュリティチェックシステムです。

## 概要

このツールは、Gitコミット前に以下の危険な情報が含まれていないかチェックします：

- **フルパス**: `/Users/username/` などのハードコードされたパス
- **APIキー・トークン**: 実際のAPIキーやアクセストークン
- **パスワード**: ハードコードされたパスワード
- **プライベートURL**: `localhost`、プライベートIPアドレス
- **機密ファイル**: `.env`、秘密鍵ファイルなど
- **実在メールアドレス**: テスト用以外のメールアドレス

## ファイル構成

```
tools/security-check/
├── README.md                    # 英語版ドキュメント
├── README.ja.md                 # 日本語版ドキュメント（このファイル）
├── commit_security_check.py     # メインチェックスクリプト
├── install_hook.py              # pre-commitフックインストーラー
├── setup_personal_config.py     # 個人設定セットアップスクリプト
├── config.json                  # 基本設定ファイル
├── nglist.json.example          # 個人設定のテンプレート
├── nglist.json                  # 個人用NGリスト（gitignore対象）
└── .gitignore                   # 個人設定ファイルを除外
```

## 🚀 クイックスタート

### 0. 初回セットアップ（初回のみ）

```bash
# 個人用セキュリティ設定をセットアップ
python tools/security-check/setup_personal_config.py

# または手動でテンプレートをコピーして編集
cp tools/security-check/nglist.json.example tools/security-check/nglist.json
# nglist.json を個人情報で編集
```

### 1. 手動でセキュリティチェック実行

```bash
# 現在ステージングされたファイルをチェック
python tools/security-check/commit_security_check.py

# 詳細出力付き
python tools/security-check/commit_security_check.py -v

# JSONレポート出力
python tools/security-check/commit_security_check.py -r security_report.json
```

### 2. 自動チェック（pre-commitフック）の設定

```bash
# フックをインストール
python tools/security-check/install_hook.py

# フックをアンインストール
python tools/security-check/install_hook.py uninstall
```

フックインストール後は、`git commit` 時に自動的にセキュリティチェックが実行されます。

## 📋 使用例

### 基本的な使用方法

```bash
# 初回セットアップ
python tools/security-check/setup_personal_config.py

# ファイルをステージング
git add .

# セキュリティチェック実行
python tools/security-check/commit_security_check.py

# 問題なければコミット
git commit -m "feat: 新機能追加"
```

### CI環境での使用

```bash
# CI環境用（非対話モード）
python tools/security-check/commit_security_check.py --ci
```

終了コード:
- `0`: チェック合格
- `1`: セキュリティ問題検出

## 🔍 チェック項目詳細

### エラーレベル（コミットブロック）

| 項目 | 説明 | 例 |
|------|------|-----|
| ハードコードパス | フルパスの記述 | `/Users/john/project/` |
| APIキー | 実際のAPIキー | `api_key = "sk-1234..."` |
| パスワード | ハードコードされたパスワード | `password = "secret123"` |
| 機密ファイル | 秘密鍵、設定ファイル | `private.key`, `.env` |

### 警告レベル（注意喚起）

| 項目 | 説明 | 例 |
|------|------|-----|
| プライベートURL | ローカル・内部URL | `http://localhost:3000` |
| 実在メール | テスト用以外のメール | `john@company.com` |

### 許可されるパターン

以下は安全とみなされ、チェックをパスします：

```python
# 環境変数参照
api_key = os.environ.get("OPENAI_API_KEY")

# プレースホルダー
api_key = "your_api_key"
email = "test@example.com"

# 相対パス
config_path = "config/settings.json"
```

## ⚙️ 設定

### config.json

```json
{
  "settings": {
    "strict_mode": false,        # 厳格モード
    "auto_fix": false,          # 自動修正（未実装）
    "ignore_warnings": false    # 警告を無視
  },
  "custom_patterns": {
    "organization_specific": {
      "patterns": ["internal\\.company\\.com"],
      "severity": "WARNING",
      "description": "組織内部URL"
    }
  }
}
```

### 除外設定

以下のファイル・ディレクトリは自動的に除外されます：

- `.git/`, `node_modules/`, `__pycache__/`
- `.venv/`, `venv/`, `dist/`, `build/`
- `.pyc`, `.log`, `.tmp`, `.DS_Store`
- 画像ファイル、音声ファイル、圧縮ファイル

## 🔧 コマンドラインオプション

```bash
python tools/security-check/commit_security_check.py [オプション]

オプション:
  -h, --help            ヘルプを表示
  -v, --verbose         詳細な出力を表示
  -r REPORT, --report REPORT
                        JSONレポートファイルを出力
  --ci                  CI環境用（非対話モード）
```

## 📊 出力例

### ✅ 成功例

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

### ❌ 失敗例

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

## 🛠️ 開発者向け

### カスタムパターン追加

`config.json` にカスタムチェックパターンを追加できます：

```json
{
  "custom_patterns": {
    "social_security": {
      "patterns": ["\\d{3}-\\d{2}-\\d{4}"],
      "severity": "ERROR",
      "description": "社会保障番号"
    }
  }
}
```

### プログラムからの利用

```python
from tools.security_check.commit_security_check import CommitSecurityChecker

checker = CommitSecurityChecker(verbose=True)
is_safe = checker.run_security_check()

if is_safe:
    print("安全です")
else:
    print("問題があります")
```

## 🚨 トラブルシューティング

### よくある問題

**Q: 環境変数参照がエラーになる**
```python
# ❌ エラーになる
API_KEY = "sk-real-key-here"

# ✅ 正しい書き方
API_KEY = os.environ.get("OPENAI_API_KEY")
```

**Q: テスト用のファイルがエラーになる**
```python
# ❌ 実在のメールアドレス
test_email = "john@company.com"

# ✅ テスト用プレースホルダー
test_email = "test@example.com"
```

**Q: 相対パスがエラーになる**
```python
# ❌ フルパス
config_path = "/Users/john/project/config.json"

# ✅ 相対パス
config_path = "config/config.json"
```

### フック関連

**Q: pre-commitフックが動作しない**
```bash
# フックファイルの権限を確認
ls -la .git/hooks/pre-commit

# 実行権限がない場合
chmod +x .git/hooks/pre-commit
```

**Q: フックを一時的に無効にしたい**
```bash
# --no-verifyオプションでスキップ
git commit --no-verify -m "一時的にスキップ"
```

## 📝 ライセンス

このツールはMITライセンスの下で提供されています。

## 🤝 貢献

バグ報告や機能提案は、GitHubのIssueでお願いします。

## 📚 関連ドキュメント

- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [セキュリティベストプラクティス](../docs/security-best-practices.md)