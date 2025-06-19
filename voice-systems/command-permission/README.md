# コマンド実行許可システム

Claude Codeでのコマンド実行前に、安全性をチェックして実行方法を選択できるシステムです。

## 概要

このシステムは以下の機能を提供します：
- **ホワイトリストチェック**: Claude Codeの設定に基づく安全性確認
- **音声認識**: 音声でコマンド実行方法を選択
- **キーボード入力**: テキストでの選択も可能
- **Python直接実行**: スクリプト内でのコマンド実行
- **音声フィードバック**: 実行結果の音声通知

## ファイル構成

```
voice-systems/command-permission/
├── README.md                      # このファイル
├── simple_command_permission.py   # シンプル版（推奨）
└── command_permission.py          # 高機能版（音声認識対応）
```

## 使用方法

### シンプル版（推奨）

```bash
python voice-systems/command-permission/simple_command_permission.py "<コマンド>" "<説明>"
```

**例:**
```bash
python voice-systems/command-permission/simple_command_permission.py "ls -la" "ファイル一覧表示"
python voice-systems/command-permission/simple_command_permission.py "git status" "Git状態確認"
python voice-systems/command-permission/simple_command_permission.py "npm install" "パッケージインストール"
```

### 高機能版（音声認識対応）

```bash
python voice-systems/command-permission/command_permission.py "<コマンド>" "<説明>"
```

**例:**
```bash
python voice-systems/command-permission/command_permission.py "rm -rf temp" "一時ファイルの削除"
python voice-systems/command-permission/command_permission.py "git push origin main" "メインブランチへのプッシュ"
```

## 実行方法の選択

コマンド実行時に以下の3つの選択肢が提示されます：

### 1. Python実行 [P]
- **特徴**: スクリプト内でコマンドを直接実行
- **利点**: 即座に実行・結果確認・音声フィードバック
- **適用場面**: 安全なコマンド、テスト用途

**音声キーワード:**
- `はい` `OK` `オーケー` `実行` `やる`
- `Python` `パイソン` `ぱいそん` `実行する`

### 2. Claude実行 [C]
- **特徴**: Claude Codeのツールで実行（従来通り）
- **利点**: より安全な環境、Claude Codeの管理下
- **適用場面**: 危険なコマンド、本番環境

**音声キーワード:**
- `Claude` `クロード` `くろーど`
- `Claude Code` `クロードコード`

### 3. 実行しない [N]
- **特徴**: コマンド実行をキャンセル
- **利点**: 安全性重視、誤実行防止

**音声キーワード:**
- `No` `ノー` `やめ` `中止` `やめる` `キャンセル` `きゃんせる`
- `いいえ` `だめ` `ダメ` `CIA` `EA` `えー` `えい` `怖い` `こわい`

## ホワイトリスト設定

システムは Claude Code の `.claude/settings.local.json` を参照してコマンドの安全性を判定します。

### 安全なコマンド（ホワイトリスト内）
- 軽い通知音（Tink）で許可済みを表示
- 実行方法選択画面に移行

### 危険なコマンド（ホワイトリスト外）
- 警告音（Sosumi）+ 音声での確認
- 詳細な実行方法選択画面に移行

## 音声認識機能

高機能版では OpenAI Whisper を使用した音声認識を搭載：

### 必要な環境変数
```bash
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key  # 音声合成用
```

### 必要なライブラリ
```bash
pip install openai pyaudio wave
```

### 音声認識の流れ
1. 3秒間の音声録音
2. OpenAI Whisperで音声をテキスト変換
3. キーワードマッチングで実行方法を決定
4. 10秒タイムアウトでClaude実行を選択

## 実行例

### 安全なコマンドの場合

```bash
$ python voice-systems/command-permission/simple_command_permission.py "git status" "Git状態確認"

🔐 コマンド実行許可をチェック中...
📝 実行コマンド: git status
📄 説明: Git状態確認
✅ ホワイトリストに含まれています - 許可済み

🤔 実行方法を選択してください:
  [P] Python実行 - このスクリプト内で直接実行
  [C] Claude実行 - Claude Codeで実行
  [N] 実行しない - キャンセル

選択 [P/C/N]: p

🐍 Python でコマンドを実行中: git status
📅 実行時刻: 2024-06-18 15:30:45
✅ コマンド実行成功
📤 標準出力:
On branch voice-notification-system
nothing to commit, working tree clean

🟢 Python実行完了
```

### 危険なコマンドの場合

```bash
$ python voice-systems/command-permission/simple_command_permission.py "rm -rf temp" "一時ファイルの削除"

🔐 コマンド実行許可をチェック中...
📝 実行コマンド: rm -rf temp
📄 説明: 一時ファイルの削除
⚠️ ホワイトリストに含まれていません - 注意が必要です
🎤 音声確認: ホワイトリストにございません。一時ファイルの削除を実行しますか？Python実行かClaude実行か選択してください。

🤔 実行方法を選択してください:
  [P] Python実行 - このスクリプト内で直接実行
  [C] Claude実行 - Claude Codeで実行
  [N] 実行しない - キャンセル

選択 [P/C/N]: c

📢 Claude Codeで実行してください: rm -rf temp
📋 Claude Code実行待ち
```

## トラブルシューティング

### 音声認識が動作しない
- OpenAI API キーが設定されているか確認
- pyaudio がインストールされているか確認
- マイクのアクセス許可を確認

### 音声合成が動作しない
- Gemini API キーが設定されているか確認
- afplay コマンドが利用可能か確認（macOS）

### ホワイトリストが読み込まれない
- `.claude/settings.local.json` ファイルが存在するか確認
- JSON形式が正しいか確認

## セキュリティ上の注意

1. **危険なコマンドは Claude 実行を推奨**
   - `rm -rf`、`sudo`、`chmod 777` などの破壊的コマンド
   - 本番環境に影響するコマンド

2. **Python実行の制限**
   - 30秒タイムアウトあり
   - 標準出力/エラー出力をキャプチャ
   - シェルインジェクション対策済み

3. **音声データの取り扱い**
   - 録音データは一時ファイルとして保存
   - 処理後に自動削除
   - OpenAI APIに送信（プライバシーポリシー要確認）

## 今後の改善予定

- [ ] より高精度な音声認識
- [ ] カスタムコマンドプリセット
- [ ] 実行ログの保存
- [ ] Web UI での設定管理
- [ ] 多言語対応