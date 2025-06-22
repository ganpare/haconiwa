#!/usr/bin/env python3
"""
音声通知システム - osascriptと同時に音声通知を送信
"""

import base64
import mimetypes
import os
import re
import struct
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# ログファイルのパス
LOG_FILE = Path.home() / "voice_notification.log"


def write_log(message: str, level: str = "INFO"):
    """ログファイルにメッセージを記録"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"ログ書き込みエラー: {e}")


def save_binary_file(file_name, data):
    """バイナリファイルを保存"""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"音声ファイル保存: {file_name}")
    write_log(f"音声ファイル保存: {file_name}")


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


def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """MIMEタイプから音声パラメータを解析"""
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


def generate_speech(text: str, output_filename: str = None):
    """音声を生成して保存"""
    write_log(f"音声生成開始: {text}")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error_msg = "エラー: GEMINI_API_KEYが設定されていません"
        print(error_msg)
        write_log(error_msg, "ERROR")
        return None

    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash-preview-tts"
    
    # 感情豊かな音声生成のためのプロンプト
    enhanced_text = f"以下のメッセージを冷静で落ち着いたトーンで、早口で話してください。プロフェッショナルで集中した雰囲気を保ちながら、テンポよく読み上げてください：\n\n{text}"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=enhanced_text),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Zephyr"
                )
            )
        ),
    )

    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"voice_notification_{timestamp}"

    file_index = 0
    saved_files = []
    
    try:
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
                
            if (chunk.candidates[0].content.parts[0].inline_data and 
                chunk.candidates[0].content.parts[0].inline_data.data):
                
                file_name = f"{output_filename}_{file_index}"
                file_index += 1
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                data_buffer = inline_data.data
                file_extension = mimetypes.guess_extension(inline_data.mime_type)
                
                if file_extension is None:
                    file_extension = ".wav"
                    data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                
                full_filename = f"{file_name}{file_extension}"
                save_binary_file(full_filename, data_buffer)
                saved_files.append(full_filename)
            else:
                if hasattr(chunk, 'text') and chunk.text:
                    print(chunk.text)
    
    except Exception as e:
        error_msg = f"音声生成エラー: {e}"
        print(error_msg)
        write_log(error_msg, "ERROR")
        return None
    
    write_log(f"音声生成完了: {len(saved_files)}ファイル生成")
    return saved_files


def play_audio_file(filename: str):
    """音声ファイルを再生（クロスプラットフォーム対応）"""
    import platform
    
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            # 音量を20%に下げて再生
            subprocess.run(["afplay", "-v", "0.2", filename], check=True)
            write_log(f"音声再生（macOS, 音量20%）: {filename}")
        elif system == "Linux":  # Linux/WSL
            # ffplayを使用（音量調整付き）
            subprocess.run([
                "ffplay", "-nodisp", "-autoexit", "-v", "quiet", 
                "-af", "volume=0.2", filename
            ], check=True)
            write_log(f"音声再生（Linux/WSL, 音量20%）: {filename}")
        elif system == "Windows":  # Windows
            # WindowsMediaPlayerやffplayを試行
            try:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-v", "quiet", 
                               "-af", "volume=0.2", filename], check=True)
                write_log(f"音声再生（Windows, ffplay）: {filename}")
            except FileNotFoundError:
                # フォールバック: Windowsデフォルト音声再生
                os.startfile(filename)
                write_log(f"音声再生（Windows, デフォルト）: {filename}")
        else:
            error_msg = f"未対応のOS: {system}"
            print(error_msg)
            write_log(error_msg, "WARNING")
            
    except subprocess.CalledProcessError as e:
        error_msg = f"音声再生エラー: {e}"
        print(error_msg)
        write_log(error_msg, "ERROR")
    except FileNotFoundError:
        error_msg = f"音声再生ツールが見つかりません（OS: {system}）"
        print(error_msg)
        write_log(error_msg, "ERROR")
    except Exception as e:
        error_msg = f"予期しない音声再生エラー: {e}"
        print(error_msg)
        write_log(error_msg, "ERROR")


def send_notification_with_voice(message: str, title: str = "Claude Code", sound: str = "Funk"):
    """クロスプラットフォーム対応の通知と音声通知を同時に送信"""
    import platform
    
    write_log(f"通知開始 - タイトル: {title}, メッセージ: {message}")
    
    system = platform.system()
    
    # プラットフォーム別通知
    if system == "Darwin":  # macOS
        notification_cmd = f'display notification "{message}" with title "{title}" sound name "{sound}"'
        try:
            subprocess.run(["osascript", "-e", notification_cmd], check=True)
            print(f"通知送信（macOS）: {message}")
            write_log(f"osascript通知送信成功: {message}")
        except subprocess.CalledProcessError as e:
            error_msg = f"通知送信エラー: {e}"
            print(error_msg)
            write_log(error_msg, "ERROR")
    elif system == "Linux":  # Linux/WSL
        try:
            # notify-sendを試行（Ubuntu/Debianでは一般的）
            subprocess.run(["notify-send", title, message], check=True)
            print(f"通知送信（Linux）: {message}")
            write_log(f"notify-send通知送信成功: {message}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # WSLでは通知システムが使えない場合があるのでログのみ
            print(f"WSL環境 - コンソール通知: [{title}] {message}")
            write_log(f"WSL環境コンソール通知: {message}")
    elif system == "Windows":  # Windows
        try:
            # PowerShellでWindows通知を送信
            ps_cmd = f'[reflection.assembly]::loadwithpartialname("System.Windows.Forms");[System.Windows.Forms.MessageBox]::Show("{message}","{title}")'
            subprocess.run(["powershell", "-Command", ps_cmd], check=True)
            print(f"通知送信（Windows）: {message}")
            write_log(f"Windows通知送信成功: {message}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Windows - コンソール通知: [{title}] {message}")
            write_log(f"Windows環境コンソール通知: {message}")
    else:
        print(f"未対応OS - コンソール通知: [{title}] {message}")
        write_log(f"未対応OS({system})コンソール通知: {message}")
    
    # 音声を生成して再生
    print("音声生成中...")
    audio_files = generate_speech(message)
    
    if audio_files:
        for audio_file in audio_files:
            print(f"音声再生: {audio_file}")
            play_audio_file(audio_file)
            # 一時ファイルを常に削除
            try:
                os.remove(audio_file)
                print(f"一時ファイル削除: {audio_file}")
                write_log(f"一時ファイル削除: {audio_file}")
            except OSError as e:
                error_msg = f"ファイル削除エラー: {audio_file} - {e}"
                print(error_msg)
                write_log(error_msg, "WARNING")
    
    write_log(f"通知処理完了: {message}")


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python voice_notification.py <メッセージ> [タイトル] [サウンド]")
        print("例: python voice_notification.py 'タスクブランチ完了しました' 'Claude Code' 'Funk'")
        sys.exit(1)
    
    message = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "Claude Code"
    sound = sys.argv[3] if len(sys.argv) > 3 else "Funk"
    
    send_notification_with_voice(message, title, sound)


if __name__ == "__main__":
    main()