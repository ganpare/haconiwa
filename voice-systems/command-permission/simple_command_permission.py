#!/usr/bin/env python3
"""
シンプル版コマンド実行許可システム（警告音対応）
キーボード入力 + クロスプラットフォーム警告音
"""

import sys
import subprocess
import time
import json
import os
from pathlib import Path
from datetime import datetime
import base64
import mimetypes
import struct

# 環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 警告音システムをインポート
sys.path.append(str(Path(__file__).parent.parent / "alert-sounds"))
try:
    from alert_system import AlertSystem
    alert = AlertSystem()
except ImportError:
    alert = None
    print("⚠️ 警告音システムが見つかりません")

def save_binary_file(file_name, data):
    """バイナリファイルを保存"""
    f = open(file_name, "wb")
    f.write(data)
    f.close()

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """WAVファイルヘッダーを生成"""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size
        1,                # AudioFormat
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict:
    """音声MIME typeから設定を解析"""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}

def speak_with_gemini(text: str):
    """Gemini Flash TTSで音声合成"""
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model = "gemini-2.5-flash-preview-tts"
        
        # 早口で冷静なプロンプト
        enhanced_text = f"以下のメッセージを冷静で落ち着いたトーンで、早口で話してください。プロフェッショナルで集中した雰囲気を保ちながら、テンポよく読み上げてください：\n\n{text}"
        
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=enhanced_text)],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            ),
        )

        file_index = 0
        audio_files = []
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
                
            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                file_name = f"permission_voice_{file_index}"
                file_index += 1
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                data_buffer = inline_data.data
                
                import mimetypes
                file_extension = mimetypes.guess_extension(inline_data.mime_type)
                
                if file_extension is None:
                    file_extension = ".wav"
                    data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                
                full_filename = f"{file_name}{file_extension}"
                save_binary_file(full_filename, data_buffer)
                audio_files.append(full_filename)

        # 音声ファイルを順次再生
        for audio_file in audio_files:
            try:
                subprocess.run(["afplay", "-v", "0.2", audio_file], check=True)
            except:
                pass
            # ファイルを削除
            try:
                os.remove(audio_file)
            except OSError:
                pass
                
    except Exception as e:
        print(f"音声合成エラー: {e}")

def load_claude_settings():
    """Claude Codeの設定ファイルを読み込む"""
    settings_path = Path(".claude/settings.local.json")
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 設定ファイル読み込みエラー: {e}")
            return {}
    return {}

def check_command_whitelist(command: str):
    """コマンドがホワイトリストに含まれているかチェック"""
    settings = load_claude_settings()
    
    # Claude Codeの実際の設定形式に対応
    allow_list = settings.get("permissions", {}).get("allow", [])
    
    if not allow_list:
        print("📋 ホワイトリストが見つかりません - デフォルト安全コマンドをチェック")
        # デフォルトの安全なコマンド
        safe_commands = [
            "echo", "cat", "ls", "pwd", "whoami", "date", "which", "type",
            "git status", "git log", "git diff", "git branch",
            "npm --version", "python --version", "node --version",
            "pip list", "pip show"
        ]
        command_base = command.split()[0] if command.split() else ""
        return any(command.startswith(safe) for safe in safe_commands)
    
    # Claude Code形式のチェック: "Bash(command:*)"
    for permission in allow_list:
        if permission.startswith("Bash("):
            # "Bash(ls:*)" -> "ls"を抽出
            bash_pattern = permission[5:-1]  # "Bash(" と ")" を除去
            if ":" in bash_pattern:
                allowed_cmd = bash_pattern.split(":")[0]
                if command.startswith(allowed_cmd):
                    return True
    
    return False

def get_user_choice():
    """ユーザーの選択を取得（キーボードのみ）"""
    print("\n🤔 実行方法を選択してください:")
    print("  [P] Python実行 - このスクリプト内で直接実行")
    print("  [C] Claude実行 - Claude Codeで実行")
    print("  [N] 実行しない - キャンセル")
    
    while True:
        try:
            choice = input("選択 [P/C/N]: ").strip().lower()
            if choice in ['p', 'python']:
                return "python"
            elif choice in ['c', 'claude']:
                return "claude"
            elif choice in ['n', 'no', 'cancel']:
                return "no"
            else:
                print("⚠️ 無効な選択です。P、C、Nのいずれかを入力してください。")
        except (KeyboardInterrupt, EOFError):
            print("\n\n🚫 中断されました")
            return "no"

def execute_command_directly(command: str, description: str = ""):
    """Pythonでコマンドを直接実行"""
    print(f"\n🐍 Python でコマンドを実行中: {command}")
    print(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30秒タイムアウト
        )
        
        if result.returncode == 0:
            print(f"✅ コマンド実行成功")
            if result.stdout:
                print(f"📤 標準出力:\n{result.stdout}")
        else:
            print(f"❌ コマンド実行失敗 (終了コード: {result.returncode})")
            if result.stderr:
                print(f"📤 エラー出力:\n{result.stderr}")
        
        # 音声で結果通知
        if result.returncode == 0:
            speak_with_gemini(f"{description}の実行が完了しました")
        else:
            speak_with_gemini(f"{description}の実行でエラーが発生しました")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ コマンド実行タイムアウト（30秒）")
        speak_with_gemini(f"{description}の実行がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ コマンド実行エラー: {e}")
        speak_with_gemini(f"{description}の実行でエラーが発生しました")
        return False

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python simple_command_permission.py <コマンド> <分かりやすい説明>")
        print("例:")
        print("  python simple_command_permission.py 'ls -la' 'ファイル一覧表示'")
        print("  python simple_command_permission.py 'git status' 'Git状態確認'")
        print("")
        print("【新機能】キーボード選択:")
        print("  [P] Python実行 - このスクリプト内で直接実行")
        print("  [C] Claude実行 - Claude Codeで実行（従来通り）")
        print("  [N] 実行しない - キャンセル")
        return
    
    command = sys.argv[1]
    description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    
    print(f"🔐 コマンド実行許可をチェック中...")
    print(f"📝 実行コマンド: {command}")
    if description:
        print(f"📄 説明: {description}")
    
    # ホワイトリストをチェック
    is_whitelisted = check_command_whitelist(command)
    
    if is_whitelisted:
        print("✅ ホワイトリストに含まれています - 許可済み")
        # 成功音を再生
        if alert:
            alert.play_success_sound()
        print("🔊 成功音再生完了")
    else:
        print("⚠️ ホワイトリストに含まれていません - 注意が必要です")
        # 警告音を再生
        if alert:
            alert.play_warning_sound()
        print("🔊 警告音再生完了")
        
        # 音声で確認
        if description:
            voice_description = description
        else:
            voice_description = f"{command}コマンド"
        
        voice_message = f"ホワイトリストにございません。{voice_description}を実行しますか？Python実行かClaude実行か選択してください。"
        print(f"🎤 音声確認: {voice_message}")
        speak_with_gemini(voice_message)
        
        # 通知も送信
        notification_msg = f"⚠️ 危険コマンド: {command[:30]}..."
        try:
            subprocess.run([
                "osascript", "-e", 
                f'display notification "{notification_msg}" with title "Claude Code ⚠️" sound name "Sosumi"'
            ], check=True)
        except:
            pass
    
    # ユーザー選択を取得
    choice = get_user_choice()
    
    if choice == "python":
        success = execute_command_directly(command, description or ("安全なコマンド" if is_whitelisted else "危険なコマンド"))
        if success:
            print("\n🟢 Python実行完了")
        else:
            print("\n🔴 Python実行エラー")
    elif choice == "claude":
        print(f"\n📢 Claude Codeで実行してください: {command}")
        print("📋 Claude Code実行待ち")
    else:
        print("\n🚫 実行をキャンセルしました")

if __name__ == "__main__":
    main()