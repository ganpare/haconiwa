# apply コマンド - 環境変数管理

## 概要

`haconiwa apply` コマンドに追加された `--env` フラグにより、Git worktreeを使用する各タスクに環境変数ファイル（.env）を自動配布する機能が実装されました。

## 機能詳細

### 基本的な使用方法

```bash
# .envファイルを指定してapply
haconiwa apply -f haconiwa-dev-company.yaml --env .env

# 複数の.envファイルを指定（マージされる）
haconiwa apply -f haconiwa-dev-company.yaml --env .env.base --env .env.local

# 環境別の.envファイル
haconiwa apply -f haconiwa-dev-company.yaml --env .env.production
```

### 環境変数ファイルの例

#### .env.base - 基本設定
```bash
COMPANY_NAME="Haconiwa Development Company"
API_ENDPOINT="https://api.haconiwa.dev"
LOG_LEVEL="INFO"
TIMEZONE="Asia/Tokyo"
LOCALE="ja_JP.UTF-8"
```

#### .env.local - ローカル開発用（.gitignoreに追加推奨）
```bash
ANTHROPIC_API_KEY="sk-ant-api03-..."
CLAUDE_MODEL="claude-3-opus-20240229"
DEBUG_MODE="true"
DATABASE_URL="postgresql://user:pass@localhost:5432/haconiwa_dev"
REDIS_URL="redis://localhost:6379"
```

## 実装詳細

### 自動コピーの動作フロー

```
1. haconiwa apply実行時に--envフラグを確認
    ↓
2. 指定された.envファイルを読み込み
    ↓
3. 複数ファイルの場合はマージ（後のファイルが優先）
    ↓
4. git worktree作成時に各タスクディレクトリに.envをコピー
    ↓
5. 各エージェントは自分のディレクトリの.envを使用
```

### ファイル配置の結果

```
./haconiwa-dev-world/
└── tasks/
    ├── task_backend_optimization_06/
    │   ├── .env               # 自動コピーされた環境変数ファイル
    │   ├── src/
    │   └── ...
    ├── task_ai_strategy_01/
    │   ├── .env               # 同じ内容がコピーされる
    │   ├── docs/
    │   └── ...
    └── task_frontend_ui_02/
        ├── .env               # 同じ内容がコピーされる
        ├── components/
        └── ...
```

## Space CRDでの環境変数ファイル指定（オプション）

YAMLファイル内でも環境変数ファイルを指定可能：

```yaml
apiVersion: haconiwa.dev/v1
kind: Space
metadata:
  name: haconiwa-dev-world
spec:
  nations:
    - id: jp
      cities:
        - id: tokyo
          villages:
            - id: haconiwa-village
              companies:
                - name: haconiwa-dev-company
                  # 環境変数ファイルの指定（オプション）
                  envFiles:
                    - path: ".env.base"        # 基本設定
                    - path: ".env.production"  # 本番環境設定
                    - path: ".env.secrets"     # シークレット（gitignore推奨）
                  gitRepo:
                    url: "https://github.com/dai-motoki/haconiwa"
                    defaultBranch: "main"
```

## セキュリティ考慮事項

### .gitignoreの推奨設定
```gitignore
# 環境変数ファイル
.env
.env.local
.env.*.local
.env.secrets

# 本番環境の設定は特に注意
.env.production
.env.staging
```

### 環境変数ファイルの管理指針
- `.env.base`: リポジトリにコミット可能（機密情報を含まない）
- `.env.local`: ローカル開発用（.gitignoreに追加）
- `.env.secrets`: API キーなど（絶対にコミットしない）

## CLI実装詳細

### 新しいフラグ

- `--env PATH`: 環境変数ファイルのパスを指定（複数回指定可能）

### 内部処理

1. **ファイル読み込み**: 指定された.envファイルを順次読み込み
2. **マージ処理**: 複数ファイルの環境変数をマージ（後勝ち）
3. **配布処理**: git worktree作成時に各タスクディレクトリに配布
4. **自動.gitignore更新**: タスクディレクトリに.gitignoreも自動生成

### エラーハンドリング

- 指定された.envファイルが存在しない場合は警告表示
- 読み込みエラーが発生した場合は詳細なエラーメッセージ
- 部分的な失敗でも他のタスクは継続処理

## 使用例とベストプラクティス

### 開発環境の設定例

```bash
# 開発用（デバッグ情報を含む）
haconiwa apply -f dev-company.yaml --env .env.base --env .env.dev

# ステージング環境
haconiwa apply -f staging-company.yaml --env .env.base --env .env.staging

# 本番環境（最小限の設定）
haconiwa apply -f prod-company.yaml --env .env.base --env .env.production
```

### 環境変数の読み込み確認

```bash
# 各ペインでclaudeコマンド実行前に.envを読み込み
cd /path/to/task && source .env && claude

# またはdotenvツールを使用
cd /path/to/task && dotenv claude
```

## メリット

1. **シンプル**: 複雑な継承メカニズムが不要
2. **標準的**: .envファイルは多くの開発者が慣れ親しんだ形式
3. **柔軟**: 環境別に異なる.envファイルを簡単に切り替え可能
4. **独立性**: 各タスクが独自の環境変数セットを持つ
5. **互換性**: 既存のツールやライブラリと相性が良い

## 将来の拡張予定

- **テンプレート機能**: 動的な環境変数生成
- **暗号化サポート**: 機密情報の安全な管理
- **環境別プロファイル**: より高度な環境管理機能 