#!/usr/bin/env python3
"""
Claude Code コマンド実行許可システム
コマンド実行前に通知と音声で許可を求める
"""

import sys
import subprocess
import time
import re
import json
import os
from pathlib import Path
import base64
import mimetypes
import struct
import threading
import queue
from datetime import datetime
try:
    import select
except ImportError:
    select = None

# 環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def save_binary_file(file_name, data):
    """バイナリファイルを保存"""
    f = open(file_name, "wb")
    f.write(data)
    f.close()

def play_audio_file(filename: str):
    """音声ファイルを再生"""
    try:
        subprocess.run(["afplay", "-v", "0.2", filename], check=True)
    except subprocess.CalledProcessError as e:
        print(f"音声再生エラー: {e}")
    except FileNotFoundError:
        print("afplayコマンドが見つかりません")

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
                file_extension = mimetypes.guess_extension(inline_data.mime_type)
                
                if file_extension is None:
                    file_extension = ".wav"
                    data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                
                full_filename = f"{file_name}{file_extension}"
                save_binary_file(full_filename, data_buffer)
                audio_files.append(full_filename)

        # 音声ファイルを順次再生
        for audio_file in audio_files:
            play_audio_file(audio_file)
            # ファイルを削除
            try:
                os.remove(audio_file)
            except OSError:
                pass
                
    except Exception as e:
        print(f"音声合成エラー: {e}")

def classify_intent_with_gpt4o(recognized_text: str) -> str:
    """GPT-4oで音声認識結果を分類"""
    print(f"🔄 GPT-4o API呼び出し開始...")
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        system_prompt = """あなたは音声コマンド分類の専門家です。
ユーザーの音声入力を正確に以下の4つのカテゴリに分類してください。

**分類ルール:**
1 = Python実行を意味する発言
   - 「はい」「OK」「オーケー」「実行」「やる」「やります」
   - 「Python」「パイソン」「ぱいそん」「配送」（Pythonの誤認識）
   - 「実行する」「お願いします」「進める」「Go」

2 = Claude実行を意味する発言  
   - 「Claude」「クロード」「くろーど」「Claude Code」
   - 「クロードコード」「くらうど」「cloud」「クラウド」
   - 「CC」「シーシー」「C.C.」「cc」

3 = 実行拒否を意味する発言
   - 「やめ」「だめ」「ダメ」「怖い」「こわい」
   - 「いいえ」「no」「ノー」「キャンセル」「中止」
   - 「EA」「えー」「えい」「危険」

0 = 判断不可能な発言

**重要:** 必ず数字1つ（1, 2, 3, 0のいずれか）のみで回答してください。説明は不要です。"""

        print(f"🌐 OpenAI APIリクエスト送信...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"次の発言を分類してください: 「{recognized_text}」"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"🤖 GPT-4o分類結果: '{recognized_text}' → {result}")
        
        return result
        
    except Exception as e:
        print(f"⚠️ GPT-4o分類エラー: {e}")
        print(f"🔧 フォールバックモードでキーワードマッチング実行...")
        # エラー時は従来のキーワードマッチングを使用
        text = recognized_text.lower()
        if any(word in text for word in ['no', 'やめ', 'だめ', '怖い', 'キャンセル', 'ea']):
            fallback_result = "3"
        elif any(word in text for word in ['claude', 'クロード']):
            fallback_result = "2"
        elif any(word in text for word in ['はい', 'ok', 'python', 'パイソン', '実行', 'やる']):
            fallback_result = "1"
        else:
            fallback_result = "0"
        print(f"🔧 フォールバック結果: {fallback_result}")
        return fallback_result


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

def get_user_response_with_voice():
    """音声とキーボード入力の両方を受け付ける（不明応答時は再試行）"""
    print("\n🎤 音声で応答するか、キーボードで入力してください:")
    print("  音声: 'はい'/'OK'/'実行'/'Python'/'やる' → Python実行")
    print("       'CC'/'クロード'/'Claude'/'Claude Code' → Claude Code実行") 
    print("       'No'/'やめ'/'だめ'/'怖い'/'EA'/'キャンセル' → 実行しない")
    print("  キーボード: [P]ython実行 / [C]laude実行 / [N]o実行しない")
    print("  または: 'p' / 'c' / 'n'")
    
    attempt = 0
    max_attempts = 3
    
    while attempt < max_attempts:
        if attempt > 0:
            print(f"\n🔄 再試行 {attempt}/{max_attempts-1}")
        
        # OpenAI Realtime APIで音声認識を開始（バックグラウンド）
        voice_result = {"response": None, "completed": False, "retry_needed": False}
    
        def voice_recognition_worker():
            try:
                # 簡易的な音声認識実装（実際にはより高度な実装が必要）
                import pyaudio
                import wave
                import tempfile
            
            # 5秒間の録音
            print("🎙️ 音声録音開始（5秒間）...")
            
            # 録音開始の通知を表示
            try:
                subprocess.run([
                    "osascript", "-e", 
                    'display notification "🎙️ 音声録音中... (5秒間)" with title "Claude Code 音声認識" sound name "Submarine"'
                ], check=False)
            except:
                pass
            
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 48000  # デバイスのネイティブサンプルレートに合わせる
            RECORD_SECONDS = 5
            
            p = pyaudio.PyAudio()
            
            stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)
            
            frames = []
            for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # 録音完了の通知
            try:
                subprocess.run([
                    "osascript", "-e", 
                    'display notification "🎤 録音完了、音声認識中..." with title "Claude Code 音声認識" sound name "Pop"'
                ], check=False)
            except:
                pass
            
            # 音声ファイル保存
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                wf = wave.open(temp_file.name, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # OpenAI Whisperで音声認識（簡易実装）
                try:
                    import openai
                    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    
                    with open(temp_file.name, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="ja",  # 日本語を明示的に指定
                            prompt="はい、Python、クロード、やめ、だめ、怖い、EA、実行、キャンセル、OK、Claude Code、CC、シーシー"  # 期待される単語を指定
                        )
                    
                    recognized_text = transcript.text
                    print(f"\n🎯 音声認識結果: '{recognized_text}'")
                    
                    # 音声認識結果の通知
                    try:
                        subprocess.run([
                            "osascript", "-e", 
                            f'display notification "認識結果: {recognized_text}" with title "Claude Code 音声認識" sound name "Glass"'
                        ], check=False)
                    except:
                        pass
                    
                    # GPT-4oで意図を分類
                    print(f"🔍 GPT-4o分類を開始: '{recognized_text}'")
                    print("⏳ GPT-4o処理中... しばらくお待ちください")
                    classification = classify_intent_with_gpt4o(recognized_text)
                    print(f"🎯 GPT-4o分類完了: {classification}")
                    
                    if classification == "1":  # Python実行
                        voice_result["response"] = "python"
                        print(f"✅ 音声認識: Python実行を選択 (認識: '{recognized_text}')")
                        # 選択結果の通知
                        try:
                            subprocess.run([
                                "osascript", "-e", 
                                'display notification "🐍 Python実行を選択" with title "Claude Code 選択結果" sound name "Funk"'
                            ], check=False)
                        except:
                            pass
                    elif classification == "2":  # Claude実行
                        voice_result["response"] = "claude"
                        print(f"✅ 音声認識: Claude実行を選択 (認識: '{recognized_text}')")
                        # 選択結果の通知
                        try:
                            subprocess.run([
                                "osascript", "-e", 
                                'display notification "🤖 Claude実行を選択" with title "Claude Code 選択結果" sound name "Hero"'
                            ], check=False)
                        except:
                            pass
                    elif classification == "3":  # 実行しない
                        voice_result["response"] = "no"
                        print(f"✅ 音声認識: 実行しないを選択")
                        # 選択結果の通知
                        try:
                            subprocess.run([
                                "osascript", "-e", 
                                'display notification "❌ 実行しないを選択" with title "Claude Code 選択結果" sound name "Basso"'
                            ], check=False)
                        except:
                            pass
                    else:
                        print(f"❓ 音声認識: 不明な応答 '{recognized_text}'")
                        # 不明な応答の通知
                        try:
                            subprocess.run([
                                "osascript", "-e", 
                                f'display notification "❓ 不明な応答: {recognized_text} - 再試行します" with title "Claude Code 音声認識" sound name "Purr"'
                            ], check=False)
                        except:
                            pass
                        
                        # 再試行の音声案内
                        print("🔄 もう一度お聞きします")
                        speak_with_gemini("不明な応答です。もう一度、Python、CC、またはやめると言ってください。")
                        
                        # 音声認識を再実行
                        print("🎙️ 再録音開始（5秒間）...")
                        
                        # 再録音開始の通知を表示
                        try:
                            subprocess.run([
                                "osascript", "-e", 
                                'display notification "🔄 再録音開始 (5秒間)" with title "Claude Code 音声認識" sound name "Submarine"'
                            ], check=False)
                        except:
                            pass
                        
                        # 再試行の音声案内（複雑な再録音ロジックは削除してシンプルに）
                        print("🔄 再試行します。次の音声認識をお待ちください...")
                        speak_with_gemini("不明な応答です。もう一度、Python、CC、またはやめると言ってください。")
                        # 不明応答フラグを設定（外側ループで処理）
                        voice_result["retry_needed"] = True
                    
                except Exception as e:
                    print(f"\n⚠️ 音声認識エラー: {e}")
                
                # 一時ファイル削除
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
        
        except Exception as e:
            print(f"\n⚠️ 音声処理エラー: {e}")
        
            voice_result["completed"] = True
        
        # 音声認識をバックグラウンドで開始
        voice_thread = threading.Thread(target=voice_recognition_worker)
        voice_thread.daemon = True
        voice_thread.start()
        
        # キーボード入力待機（ノンブロッキング）
        print("\n⌨️ キーボード入力待機中...")
        
        start_time = time.time()
        while time.time() - start_time < 30:  # 30秒タイムアウト（GPT-4o処理時間を考慮）
            # 音声認識結果をチェック
            if voice_result["response"]:
                print(f"\n✅ 音声で '{voice_result['response']}' を選択")
                return voice_result["response"]
            
            # 再試行が必要な場合は次のループへ
            if voice_result["retry_needed"]:
                print("🔄 不明応答のため次の試行に移ります")
                break
            
            # キーボード入力をチェック（ノンブロッキング）
            try:
                if select and sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    user_input = sys.stdin.readline().strip().lower()
                    if user_input in ['p', 'python']:
                        print("\n✅ キーボードで 'Python実行' を選択")
                        return "python"
                    elif user_input in ['c', 'claude']:
                        print("\n✅ キーボードで 'Claude実行' を選択")
                        return "claude"
                    elif user_input in ['n', 'no']:
                        print("\n✅ キーボードで '実行しない' を選択")
                        return "no"
                    elif user_input:
                        print(f"\n⚠️ 無効な入力: {user_input}. [p/c/n] を入力してください")
            except Exception as e:
                # select が使えない場合は単純な input() に切り替え
                pass
            
            time.sleep(0.1)
        
        # タイムアウトまたは不明応答の場合、次の試行へ
        print(f"\n⏰ 試行 {attempt+1} がタイムアウトしました")
        attempt += 1
    
    # 最大試行回数に達した場合は手動入力
    print(f"\n⏰ {max_attempts}回の試行がすべてタイムアウト - 手動でキーボード入力をお願いします")
    while True:
        try:
            choice = input("選択 [P/C/N]: ").strip().lower()
            if choice in ['p', 'python']:
                print("\n✅ キーボードで 'Python実行' を選択")
                return "python"
            elif choice in ['c', 'claude']:
                print("\n✅ キーボードで 'Claude実行' を選択")
                return "claude"
            elif choice in ['n', 'no']:
                print("\n✅ キーボードで '実行しない' を選択")
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

def check_and_execute_with_choice(command: str, description: str = ""):
    """コマンドをチェックして実行方法を選択"""
    print(f"🔐 コマンド実行許可をチェック中...")
    print(f"📝 実行コマンド: {command}")
    if description:
        print(f"📄 説明: {description}")
    
    # まずホワイトリストをチェック
    if check_command_whitelist(command):
        print("✅ ホワイトリストに含まれています - Claude Codeで自動実行")
        # 通常の通知
        try:
            subprocess.run([
                "osascript", "-e", 
                f'display notification "安全なコマンド - Claude Codeで実行: {command[:30]}..." with title "Claude Code ✅" sound name "Tink"'
            ], check=True)
        except:
            pass
        
        # 安全なコマンドは音声確認なしでClaude Codeに委譲
        print("📢 安全なコマンドのため、Claude Codeで自動実行します")
        return "claude_execute"
    
    print("⚠️ ホワイトリストに含まれていません - 注意が必要です")
    
    # 音声で確認（Gemini Flash TTS）
    if description:
        voice_description = description
    else:
        voice_description = f"{command}コマンド"
    
    # コマンド説明付きの音声通知
    detailed_message = f"ホワイトリストにございません。{voice_description}を実行しますか？Python実行かCC実行か選択してください。"
    print(f"🎤 ホワイトリスト確認: {detailed_message}")
    speak_with_gemini(detailed_message)
    
    # 通知も送信
    notification_msg = f"⚠️ 危険コマンド: {command[:30]}..."
    try:
        subprocess.run([
            "osascript", "-e", 
            f'display notification "{notification_msg}" with title "Claude Code ⚠️" sound name "Sosumi"'
        ], check=True)
    except:
        pass
    
    # ユーザー応答を取得
    response = get_user_response_with_voice()
    
    if response == "python":
        return execute_command_directly(command, description or "危険なコマンド")
    elif response == "claude":
        print("📢 Claude Codeで慎重に実行してください")
        return "claude_execute"
    else:
        print("🚫 実行をキャンセルしました")
        return False

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python command_permission.py <コマンド> <分かりやすい説明>")
        print("例:")
        print("  python command_permission.py 'rm -rf old_files' '古いファイルの削除'")
        print("  python command_permission.py 'npm install express' 'Expressパッケージのインストール'")
        print("  python command_permission.py 'git push origin main' 'メインブランチへのプッシュ'")
        print("")
        print("【新機能】音声とキーボード両対応:")
        print("  - 音声: 'はい'/'OK' → Python実行, 'いいえ'/'Claude' → Claude実行")
        print("  - キーボード: [P]ython / [C]laude / [N]oキャンセル")
        print("  - Python実行: このスクリプト内でコマンドを直接実行")
        print("  - Claude実行: Claude Codeで実行（従来通り）")
        return
    
    command = sys.argv[1]
    description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    
    # 新しい実行選択機能
    result = check_and_execute_with_choice(command, description)
    
    if result == "claude_execute":
        print("\n📋 Claude Code実行待ち")
        print(f"実行コマンド: {command}")
        exit(0)  # Claude Codeに制御を返す
    elif result:
        print("\n🟢 Python実行完了")
        exit(0)
    else:
        print("\n🔴 実行キャンセルまたはエラー")
        exit(1)

if __name__ == "__main__":
    main()