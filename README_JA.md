# 箱庭 (Haconiwa) 🚧 **開発中**

[![PyPI version](https://badge.fury.io/py/haconiwa.svg)](https://badge.fury.io/py/haconiwa)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Development Status](https://img.shields.io/badge/status-alpha--development-red)](https://github.com/dai-motoki/haconiwa)

**箱庭 (Haconiwa)** は、AI協調開発支援Python CLIツールです。tmux会社管理、git-worktree連携、タスク管理、AIエージェント調整機能を統合し、効率的な開発環境を提供する次世代ツールです。

> ⚠️ **注意**: このプロジェクトは現在活発に開発中です。機能やAPIは頻繁に変更される可能性があります。

[🇺🇸 English README](README.md)

## 📋 バージョン管理

このプロジェクトは[Semantic Versioning](https://semver.org/lang/ja/)に従っています。

- **📄 変更履歴**: [CHANGELOG.md](CHANGELOG.md) - 全てのバージョンの変更履歴
- **🏷️ 最新バージョン**: 0.4.0
- **📦 PyPI**: [haconiwa](https://pypi.org/project/haconiwa/)
- **🔖 GitHubリリース**: [Releases](https://github.com/dai-motoki/haconiwa/releases)

## 🚀 今すぐ使える機能

### apply yamlパターン（v1.0 新機能）

宣言型YAMLファイルでのマルチルーム・マルチエージェント環境管理が**今すぐ**利用できます：

```bash
# 1. インストール
pip install haconiwa --upgrade

# 2. YAMLファイルダウンロード（GitHubから直接取得）
wget https://raw.githubusercontent.com/dai-motoki/haconiwa/main/haconiwa-multiroom-test.yaml

# または curlでダウンロード
curl -O https://raw.githubusercontent.com/dai-motoki/haconiwa/main/haconiwa-multiroom-test.yaml

# ファイル内容確認
cat haconiwa-multiroom-test.yaml

# 3. YAML適用でマルチルーム環境作成
haconiwa apply -f haconiwa-multiroom-test.yaml

# 4. スペース一覧確認
haconiwa space list

# 5. スペース一覧確認（短縮形）
haconiwa space ls

# 6. 特定ルームに接続
haconiwa space attach -c test-multiroom-company -r room-01

# 7. 全ペインでclaudeコマンド実行
haconiwa space run -c test-multiroom-company --claude-code

# 8. 特定ルームでカスタムコマンド実行
haconiwa space run -c test-multiroom-company --cmd "echo hello" -r room-01

# 9. ドライランでコマンド確認
haconiwa space run -c test-multiroom-company --claude-code --dry-run

# 10. セッション停止
haconiwa space stop -c test-multiroom-company

# 11. 完全削除（ディレクトリも削除）
haconiwa space delete -c test-multiroom-company --clean-dirs --force

# 12. 完全削除（ディレクトリは保持）
haconiwa space delete -c test-multiroom-company --force
```

**📁 自動作成されるマルチルーム構造（階層的法的フレームワーク）:**
```
./test-multiroom-desks/
├── jp/                                  # 国レベル (Nation Level)
│   ├── law/                            # 国家法ディレクトリ
│   │   ├── global-rules.md            # グローバル規則
│   │   ├── system-prompts/            # システムプロンプト
│   │   │   └── nation-agent-prompt.md
│   │   └── permissions/               # 権限管理
│   │       ├── code-permissions.yaml
│   │       └── file-permissions.yaml
│   └── tokyo/                         # 市レベル (City Level)
│       ├── law/                       # 市法ディレクトリ
│       │   ├── regional-rules.md     # 地域規則
│       │   ├── system-prompts/       # システムプロンプト
│       │   │   └── city-agent-prompt.md
│       │   └── permissions/          # 権限管理
│       │       ├── code-permissions.yaml
│       │       └── file-permissions.yaml
│       └── test-village/              # 村レベル (Village Level)
│           ├── law/                   # 村法ディレクトリ
│           │   ├── local-rules.md    # ローカル規則
│           │   ├── system-prompts/   # システムプロンプト
│           │   │   └── village-agent-prompt.md
│           │   └── permissions/      # 権限管理
│           │       ├── code-permissions.yaml
│           │       └── file-permissions.yaml
│           └── test-multiroom-company/    # 会社レベル (Company Level)
│               ├── law/               # 会社法ディレクトリ
│               │   ├── project-rules.md  # プロジェクト規則
│               │   ├── system-prompts/   # システムプロンプト
│               │   │   └── company-agent-prompt.md
│               │   └── permissions/      # 権限管理
│               │       ├── code-permissions.yaml
│               │       └── file-permissions.yaml
│               └── headquarters/      # 建物レベル (Building Level)
│                   ├── law/           # 建物法ディレクトリ
│                   │   ├── building-rules.md # 建物規則
│                   │   ├── system-prompts/   # システムプロンプト
│                   │   │   └── building-agent-prompt.md
│                   │   └── permissions/      # 権限管理
│                   │       ├── code-permissions.yaml
│                   │       └── file-permissions.yaml
│                   └── floor-1/       # 階層レベル (Floor Level)
│                       ├── law/       # 階層法ディレクトリ
│                       │   ├── floor-rules.md    # 階層規則
│                       │   ├── system-prompts/   # システムプロンプト
│                       │   │   └── floor-agent-prompt.md
│                       │   └── permissions/      # 権限管理
│                       │       ├── code-permissions.yaml
│                       │       └── file-permissions.yaml
│                       ├── room-01/   # 部屋レベル (Room Level)
│                       │   ├── law/   # 部屋法ディレクトリ
│                       │   │   ├── team-rules.md     # チーム規則
│                       │   │   ├── system-prompts/   # システムプロンプト
│                       │   │   │   └── room-agent-prompt.md
│                       │   │   └── permissions/      # 権限管理
│                       │   │       ├── code-permissions.yaml
│                       │   │       └── file-permissions.yaml
│                       │   └── desks/         # デスクレベル (Desk Level)
│                       │       ├── law/       # デスク法ディレクトリ
│                       │       │   ├── agent-rules.md    # エージェント規則
│                       │       │   ├── system-prompts/   # システムプロンプト
│                       │       │   │   └── desk-agent-prompt.md
│                       │       │   └── permissions/      # 権限管理
│                       │       │       ├── code-permissions.yaml
│                       │       │       └── file-permissions.yaml
│                       │       ├── org-01-pm/
│                       │       ├── org-01-worker-a/
│                       │       ├── org-01-worker-b/
│                       │       ├── org-01-worker-c/
│                       │       ├── org-02-pm/
│                       │       ├── org-02-worker-a/
│                       │       ├── org-02-worker-b/
│                       │       ├── org-02-worker-c/
│                       │       ├── org-03-pm/
│                       │       ├── org-03-worker-a/
│                       │       ├── org-03-worker-b/
│                       │       ├── org-03-worker-c/
│                       │       ├── org-04-pm/
│                       │       ├── org-04-worker-a/
│                       │       ├── org-04-worker-b/
│                       │       └── org-04-worker-c/
│                       └── room-02/   # 部屋レベル (Room Level)
│                           ├── law/   # 部屋法ディレクトリ (同様の構成)
│                           └── desks/ # デスクレベル (同様の構成)
├── standby/                # 待機中エージェント（26 agents）
│   └── README.md          # 自動生成説明ファイル
└── tasks/                  # タスク割り当て済みエージェント（6 agents）
    ├── main/              # メインGitリポジトリ
    ├── 20250609061748_frontend-ui-design_01/     # タスク1
    ├── 20250609061749_backend-api-development_02/ # タスク2
    ├── 20250609061750_database-schema-design_03/  # タスク3
    ├── 20250609061751_devops-ci-cd-pipeline_04/   # タスク4
    ├── 20250609061752_user-authentication_05/     # タスク5
    └── 20250609061753_performance-optimization_06/ # タスク6
```

**🏢 tmux構造（マルチルーム）:**
```
test-multiroom-company (Session)
├── Window 0: Alpha Room (16ペイン)
│   ├── org-01 (4ペイン): pm, worker-a, worker-b, worker-c
│   ├── org-02 (4ペイン): pm, worker-a, worker-b, worker-c  
│   ├── org-03 (4ペイン): pm, worker-a, worker-b, worker-c
│   └── org-04 (4ペイン): pm, worker-a, worker-b, worker-c
└── Window 1: Beta Room (16ペイン)
    ├── org-01 (4ペイン): pm, worker-a, worker-b, worker-c
    ├── org-02 (4ペイン): pm, worker-a, worker-b, worker-c
    ├── org-03 (4ペイン): pm, worker-a, worker-b, worker-c
    └── org-04 (4ペイン): pm, worker-a, worker-b, worker-c
```

**✅ YAML適用パターンの実際の機能:**
- 🏢 **宣言型管理**: YAMLファイルによる環境定義
- 🤖 **マルチルーム対応**: Room単位のWindow分離
- 🔄 **自動ルーム分散**: ルーム別Windowでのペイン配置
- 🚀 **一括コマンド実行**: 全ペインまたはルーム別実行
- 🎯 **柔軟なターゲティング**: ルーム指定コマンド実行
- 🏛️ **階層管理**: Nation > City > Village > Company
- 📄 **外部設定**: YAML設定ファイルでの完全管理
- 🗑️ **柔軟なクリーンアップ**: ディレクトリ保持・削除の選択
- 📊 **32ペイン管理**: 2ルーム × 16ペイン構成
- 🔧 **ドライラン対応**: 実行前のコマンド確認
- 🎯 **タスク割り当てシステム**: エージェント自動ディレクトリ移動
- 📋 **ログファイル管理**: agent_assignment.jsonでの割り当て記録

### tmux マルチエージェント環境（従来方式）

4x4グリッドのマルチエージェント開発環境を**今すぐ**作成・管理できます：

```bash
# 1. インストール
pip install haconiwa --upgrade


# 2-1. 直接Tmuxでアタッチする場合はこちらを実行してください（4組織 × 4役割 = 16ペイン）。
haconiwa company build --name my-company \
  --org01-name "フロントエンド開発部" --task01 "UI設計" \
  --org02-name "バックエンド開発部" --task02 "API開発" \
  --org03-name "データベース部門" --task03 "スキーマ設計" \
  --org04-name "DevOps部門" --task04 "インフラ構築"

# 2. マルチエージェント環境作成（4組織 × 4役割 = 16ペイン）
haconiwa company build --name my-company \
  --org01-name "フロントエンド開発部" --task01 "UI設計" \
  --org02-name "バックエンド開発部" --task02 "API開発" \
  --org03-name "データベース部門" --task03 "スキーマ設計" \
  --org04-name "DevOps部門" --task04 "インフラ構築" --no-attach

# 3. 会社一覧確認
haconiwa company list

# 4. 既存の会社に接続
haconiwa company attach my-company

# 5. 会社設定更新（既存会社の組織名変更）
haconiwa company build --name my-company \
  --org01-name "新フロントエンド部" --task01 "React開発"

# 6. 会社を完全に再構築（--rebuildオプション）
haconiwa company build --name my-company \
  --org01-name "リニューアル開発部" \
  --rebuild

# 7. 会社終了（ディレクトリも削除）
haconiwa company kill my-company --clean-dirs --force

# 8. 会社終了（ディレクトリは保持）
haconiwa company kill my-company --force
```

**📁 自動作成されるディレクトリ構造:**
```
/path/to/desks/
├── org-01/
│   ├── 01boss/          # PM用デスク
│   ├── 01worker-a/      # Worker-A用デスク
│   ├── 01worker-b/      # Worker-B用デスク
│   └── 01worker-c/      # Worker-C用デスク
├── org-02/
│   ├── 02boss/
│   ├── 02worker-a/
│   ├── 02worker-b/
│   └── 02worker-c/
├── org-03/ (同様の構造)
└── org-04/ (同様の構造)
```

**✅ 実際に動作する機能:**
- 🏢 **統合buildコマンド**: 新規作成・更新・再構築を一つのコマンドで実現
- 🤖 **自動存在チェック**: 会社の存在を自動判定し適切な動作を選択
- 🔄 **シームレス更新**: 既存会社の設定変更を安全に実行
- 🔨 **強制再構築**: --rebuildオプションで完全な再作成
- 🏗️ **自動ディレクトリ構成**: 組織・役割別デスク自動作成
- 🏷️ **カスタム組織名・タスク名**: 動的なタイトル設定
- 🗑️ **柔軟なクリーンアップ**: ディレクトリ保持・削除の選択可能
- 🏛️ **会社管理**: 作成・一覧・接続・削除の完全サポート
- 📄 **README自動生成**: 各デスクにREADME.md自動作成
- 📊 **4x4マルチエージェント**: 組織的tmuxレイアウト（16ペイン）

## 📚 buildコマンド詳細ガイド

### 基本的な使い方

#### 1. 新規会社作成（最小構成）
```bash
# シンプルな会社作成（デフォルト設定）
haconiwa company build --name my-company

# カスタムベースパス指定
haconiwa company build --name my-company --base-path ./workspace
```

#### 2. 完全カスタム会社作成
```bash
haconiwa company build --name my-company \
  --base-path ./workspace \
  --org01-name "フロントエンド部" --task01 "UI/UX開発" \
  --org02-name "バックエンド部" --task02 "API設計" \
  --org03-name "インフラ部" --task03 "DevOps" \
  --org04-name "QA部" --task04 "品質保証" \
  --no-attach  # 作成後に自動接続しない
```

#### 3. 既存会社の更新
```bash
# 組織名のみ変更（自動検出で更新モード）
haconiwa company build --name my-company \
  --org01-name "新フロントエンド部"

# 複数の設定を同時更新
haconiwa company build --name my-company \
  --org01-name "React開発チーム" --task01 "SPAアプリ開発" \
  --org02-name "Node.js開発チーム" --task02 "RESTful API"
```

#### 4. 強制再構築
```bash
# 既存会社を完全に再作成
haconiwa company build --name my-company \
  --base-path ./workspace \
  --org01-name "リニューアル開発部" \
  --rebuild
```

### 高度な使い方

#### デスクのカスタマイズ
```bash
# 各組織のワークスペース（デスク）を指定
haconiwa company build --name my-company \
  --desk01 "react-frontend-desk" \
  --desk02 "nodejs-backend-desk" \
  --desk03 "docker-infra-desk" \
  --desk04 "testing-qa-desk"
```

#### クリーンアップオプション
```bash
# 会社終了（tmuxセッションのみ削除、ディレクトリ保持）
haconiwa company kill my-company --force

# 完全削除（ディレクトリも削除）
haconiwa company kill my-company \
  --clean-dirs \
  --base-path ./workspace \
  --force
```

### 動作モード自動判定

buildコマンドは会社の存在状況を自動判定し、適切な動作を選択します：

| 状況 | 動作 | メッセージ例 |
|------|------|-------------|
| 会社が存在しない | **新規作成** | 🏗️ Building new company: 'my-company' |
| 会社が存在する + 設定変更あり | **更新** | 🔄 Updating existing company: 'my-company' |
| 会社が存在する + 設定変更なし | **情報表示** | ℹ️ No changes specified for company 'my-company' |
| --rebuildオプション指定 | **強制再構築** | 🔄 Rebuilding company: 'my-company' |

### トラブルシューティング

#### よくある問題と解決方法

**問題**: 会社が応答しない場合
```bash
# 1. 会社の状態確認
haconiwa company list

# 2. 強制終了
haconiwa company kill my-company --force

# 3. 再作成
haconiwa company build --name my-company --rebuild
```

**問題**: ディレクトリの権限エラー
```bash
# ベースパスの権限確認と修正
chmod 755 ./workspace
haconiwa company build --name my-company --base-path ./workspace
```

**問題**: tmuxセッションが残っている
```bash
# 手動でtmuxセッション確認
tmux list-sessions

# 手動削除
tmux kill-session -t my-company
```

## ✨ 主な機能 (開発中)

- 🤖 **AIエージェント管理**: Boss/Workerエージェントの作成・監視
- 📦 **ワールド管理**: 開発環境の構築・管理
- 🖥️ **tmux会社連携**: 開発スペースの効率的な管理
- 📋 **タスク管理**: git-worktreeと連携したタスク管理システム
- 📊 **リソース管理**: DBやファイルパスの効率的なスキャン
- 👁️ **リアルタイム監視**: エージェントやタスクの進捗監視

## 🏗️ アーキテクチャ概念

### スペース規則階層 (Space Rule Hierarchy)

Haconista は、YAML スペース構造に従った**スペース規則階層**を組み込み、シンプルな規則継承を通じてエージェントガバナンスを管理します：

| 階層レベル | 規則文書 | tmux対応 | エージェント統制 | ディレクトリ構造 |
|-----------|---------|-----------|-----------------|-----------------|
| **国 (Nation)** | **グローバル規則 (Global Rules)** | - | 汎用原則・中核標準 | `jp/law/global-rules.md` |
| **市 (City)** | **地域規則 (Regional Rules)** | - | 地域ガイドライン・コンプライアンス | `jp/tokyo/law/regional-rules.md` |
| **村 (Village)** | **ローカル規則 (Local Rules)** | - | コミュニティプラクティス・ワークフロー | `jp/tokyo/test-village/law/local-rules.md` |
| **会社 (Company)** | **プロジェクト規則 (Project Rules)** | **Session** | プロジェクトポリシー・手続き | `jp/tokyo/test-village/test-multiroom-company/law/project-rules.md` |
| **建物 (Building)** | **建物規則 (Building Rules)** | - | 建物固有ガイドライン | `../headquarters/law/building-rules.md` |
| **階層 (Floor)** | **階層規則 (Floor Rules)** | - | フロアレベル管理 | `../floor-1/law/floor-rules.md` |
| **部屋 (Room)** | **チーム規則 (Team Rules)** | **Window** | チーム固有ガイドライン | `../room-01/law/team-rules.md` |
| **デスク (Desk)** | **エージェント規則 (Agent Rules)** | **Pane** | 個人エージェント行動規則 | `../desks/law/agent-rules.md` |

### 規則文書・エージェント管理システム

各階層レベルには `law/` ディレクトリが含まれ、以下を管理：

```
{level}/law/
├── {rule-document}.md      # 規則文書 (Rule Document)
├── system-prompts/         # システムプロンプト (System Prompts)
│   └── {level}-agent-prompt.md
└── permissions/            # 権限管理 (Permissions Management)
    ├── code-permissions.yaml    # コード権限 (Code Permissions)
    └── file-permissions.yaml   # ファイル権限 (File Permissions)
```

**📋 スペース規則フレームワークの特徴:**
- **🏛️ YAML準拠階層**: YAML スペース構造との完全一致 (Nations > Cities > Villages > Companies > Buildings > Floors > Rooms > Desks)
- **🤖 汎用エージェント**: 全エージェントが同じ構造に従いつつ、異なる規則セットで動作
- **📜 分散法管理**: 実際のスペース階層全体に規則文書を分散配置
- **🔐 階層権限**: スペースレベル経由でのコード・ファイルアクセス権継承
- **📋 コンプライアンス追跡**: 全スペースレベルでの自動規則コンプライアンス検証
- **🔄 規則継承**: エージェントは親スペースレベルのすべての規則を順序立てて継承

### tmux ↔ Haconiwa 概念対応

| tmux概念 | Haconiwa概念 | 規則フレームワーク | 説明 |
|----------|-------------|------------------|------|
| **Session** | **Company（会社）** | **プロジェクト規則** | プロジェクトガバナンスを持つ最上位管理単位 |
| **Window** | **Room（部屋）** | **チーム規則** | チーム固有規則を持つ機能別作業領域 |
| **Pane** | **Desk（デスク）** | **エージェント規則** | 個人エージェント規則を持つ個別作業スペース |

### 階層規則管理

```

YAML準拠スペース規則フレームワーク (YAML-Aligned Space Rule Framework)
├── Nation (jp) (国)                    ← グローバル原則 (Global principles)
│   └── City (tokyo) (市)              ← 地域ガイドライン (Regional guidelines)
│       └── Village (test-village) (村) ← ローカルプラクティス (Local practices)
│           └── Company (test-multiroom-company) (会社) ← プロジェクト規則 (Project rules) → tmux Session
│               └── Building (headquarters) (建物) ← 建物規則 (Building rules)
│                   └── Floor (floor-1) (階層) ← 階層規則 (Floor rules)
│                       └── Room (room-01/room-02) (部屋) ← チーム規則 (Team rules) → tmux Window
│                           └── Desk (desks/*) (デスク) ← エージェント規則 (Agent rules) → tmux Pane
```

**スペースガバナンス機能:**
- **国**: グローバル原則、汎用標準、コアアーキテクチャガイドライン
- **市**: 地域開発標準、技術コンプライアンス要件
- **村**: コミュニティガイドライン、ローカルワークフロー標準、チームプロトコル
- **会社**: プロジェクト管理ポリシー、ビジネスロジック制約、リソースルール
- **建物**: 建物固有手続き、物理スペース管理
- **階層**: フロアレベル調整、リソース配分、ルーム間コミュニケーション
- **部屋**: チーム固有手続き、役割ベース責任、タスクガイドライン
- **デスク**: 個人エージェント行動、個人生産性標準、タスク制約



```
Organization（組織）
├── PM（プロジェクトマネージャー）
│   ├── 全体調整
│   ├── タスク割り当て
│   └── 進捗管理
└── Worker（作業者）
    ├── Worker-A（開発担当）
    ├── Worker-B（テスト担当）
    └── Worker-C（デプロイ担当）
```

**役割定義：**
- **PM（Boss）**: 戦略的意思決定、リソース管理、品質保証
- **Worker**: 実装、テスト、デプロイなどの実行業務
- **Organization**: 複数のPM/Workerで構成される論理的なチーム単位
```
    Organization（組織）
## 🚀 インストール

```bash
pip install haconiwa
```

> 📝 **開発ノート**: パッケージはPyPIで利用可能ですが、多くの機能はまだ開発中です。

## ⚡ クイックスタート

> 🎭 **重要**: 以下に示すコマンドは**デモンストレーション用です**。現在、これらのコマンドはヘルプ情報と基本構造を表示するものですが、実際の機能は開発中です。完全な機能の実装に向けて積極的に取り組んでいます。

### 1. 利用可能なコマンドを確認
```bash
haconiwa --help
```

### 2. プロジェクト初期化
```bash
haconiwa core init
```

### 3. 開発ワールド作成
```bash
haconiwa world create local-dev
```

### 4. AIエージェント起動
```bash
# ボスエージェント作成
haconiwa agent spawn boss

# ワーカーエージェント作成
haconiwa agent spawn worker-a
```

### 5. タスク管理
```bash
# 新しいタスク作成
haconiwa task new feature-login

# エージェントにタスク割り当て
haconiwa task assign feature-login worker-a

# 進捗監視
haconiwa watch tail worker-a
```

## 📖 コマンドリファレンス

> 🔧 **開発ノート**: 以下にリストされているコマンドは現在**デモンストレーションとテスト用途**のものです。CLI構造は機能していますが、ほとんどのコマンドはヘルプ情報やプレースホルダーレスポンスを表示します。各コマンドグループの基盤機能を積極的に開発中です。

CLIツールは7つの主要コマンドグループを提供します：

### `agent` - エージェント管理コマンド
協調開発のためのAIエージェント（Boss/Worker）を管理
- `haconiwa agent spawn <type>` - エージェント作成
- `haconiwa agent ps` - エージェント一覧表示
- `haconiwa agent kill <name>` - エージェント停止

### `core` - コア管理コマンド
システムのコア管理と設定
- `haconiwa core init` - プロジェクトの初期化
- `haconiwa core status` - システム状態確認
- `haconiwa core upgrade` - システムアップグレード

### `resource` - リソース管理
プロジェクトリソース（データベース、ファイルなど）のスキャンと管理
- `haconiwa resource scan` - リソーススキャン
- `haconiwa resource list` - リソース一覧表示

### `company` - tmux会社と企業管理
tmuxを使った効率的な開発企業環境管理
- `haconiwa company build <name>` - tmux会社の作成・更新・再構築
- `haconiwa company list` - 会社一覧
- `haconiwa company attach <name>` - 会社接続
- `haconiwa company kill <name>` - 会社終了・削除
- `haconiwa company resize <name>` - 会社レイアウト調整

### `task` - タスク管理コマンド
git-worktreeと連携したタスク管理
- `haconiwa task new <name>` - 新しいタスク作成
- `haconiwa task assign <task> <agent>` - タスク割り当て
- `haconiwa task status` - タスク状態確認

### `watch` - 監視コマンド
エージェントとタスクのリアルタイム監視
- `haconiwa watch tail <target>` - リアルタイム監視
- `haconiwa watch logs` - ログ表示

### `world` - ワールド管理
開発環境とワールドの管理
- `haconiwa world create <name>` - 新しい開発ワールドを作成
- `haconiwa world list` - ワールド一覧表示
- `haconiwa world switch <name>` - ワールド切り替え

## 🛠️ 開発状況

> 🎬 **現在のフェーズ**: **デモンストレーション・プロトタイピング**  
> ほとんどのCLIコマンドは現在、意図された構造とヘルプ情報を示すデモンストレーション用プレースホルダーです。各コマンドの背後にある核となる機能を積極的に開発中です。

### ✅ 完了済み機能
- 7つのコマンドグループを持つ基本CLI構造
- PyPIパッケージ配布とインストール
- コアプロジェクト初期化フレームワーク
- **tmux会社管理システム（company buildコマンド）**
- **マルチエージェント4x4レイアウト自動構築**
- **組織・タスク・デスクカスタマイズ機能**
- **会社の自動存在チェックと更新機能**
- **柔軟なクリーンアップシステム**
- ヘルプシステムとコマンドドキュメント
- コマンドグループの組織化とルーティング

### 🚧 開発中機能
- AIエージェントの生成と管理 (プレースホルダー → 実装)
- git-worktreeとのタスク管理 (プレースホルダー → 実装)
- リソーススキャン機能 (プレースホルダー → 実装)
- リアルタイム監視システム (プレースホルダー → 実装)
- ワールド/環境管理 (プレースホルダー → 実装)

### 📋 計画中機能
- 高度なAIエージェント協調
- 人気の開発ツールとの統合
- 拡張性のためのプラグインシステム
- Webベース監視ダッシュボード

## 🛠️ 開発環境セットアップ

```bash
git clone https://github.com/dai-motoki/haconiwa.git
cd haconiwa
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .[dev]
```

### テスト実行

```bash
pytest tests/
```

## 📝 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルをご覧ください。

## 🤝 コントリビューション

プロジェクトへの貢献を歓迎します！これは活発な開発プロジェクトのため、以下をお勧めします：

1. 既存のissueとディスカッションを確認
2. このリポジトリをフォーク
3. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
4. 変更をコミット (`git commit -m 'Add amazing feature'`)
5. ブランチにプッシュ (`git push origin feature/amazing-feature`)
6. プルリクエストを作成

## 📞 サポート

- GitHub Issues: [Issues](https://github.com/dai-motoki/haconiwa/issues)
- メール: kanri@kandaquantum.co.jp

## ⚠️ 免責事項

このプロジェクトは初期アルファ開発段階かつ**デモンストレーションフェーズ**にあります。現在のCLIコマンドは主に意図されたインターフェースデザインを示すプレースホルダーです。ほとんどの機能は活発に開発中でまだ実装されていません。

**現在動作するもの:**
- CLIのインストールとコマンド構造
- ヘルプシステムとドキュメント
- 基本的なコマンドルーティング

**今後実装予定:**
- 宣伝されている全機能の完全実装
- AIエージェント協調機能
- 開発ツールとの統合
- 実際のタスクと会社管理

現時点では本番環境での使用は推奨されません。これは意図されたユーザーエクスペリエンスを示す開発プレビューです。

---

**箱庭 (Haconiwa)** - AI協調開発の未来 🚧 