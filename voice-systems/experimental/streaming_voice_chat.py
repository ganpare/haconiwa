#!/usr/bin/env python3
"""
Gemini TTS ストリーミング対話システム
"""

import os
import pyaudio
import json
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ログファイルのパス
LOG_FILE = Path.home() / "streaming_voice_chat.log"

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

def streaming_speak(text: str):
    """ストリーミングTTSで音声を再生"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEYが設定されていません")
        return False

    # PyAudio設定
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RECEIVE_SAMPLE_RATE = 24000
    
    # PyAudioの初期化
    pya = pyaudio.PyAudio()
    
    try:
        write_log(f"ストリーミング音声開始: {text}")
        
        # 音声ストリームを開く
        stream = pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True
        )
        
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
        
        print("🔊 音声再生中...", end="", flush=True)
        
        # ストリーミング生成と再生
        chunk_count = 0
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates and
                chunk.candidates[0].content and
                chunk.candidates[0].content.parts and
                chunk.candidates[0].content.parts[0].inline_data and
                chunk.candidates[0].content.parts[0].inline_data.data
            ):
                # 音声データを直接ストリームに書き込み
                audio_data = chunk.candidates[0].content.parts[0].inline_data.data
                stream.write(audio_data)
                chunk_count += 1
                print(".", end="", flush=True)
        
        print(f" 完了 ({chunk_count}チャンク)")
        write_log(f"ストリーミング音声完了: {chunk_count}チャンク")
        return True
        
    except Exception as e:
        error_msg = f"ストリーミングエラー: {e}"
        print(error_msg)
        write_log(error_msg, "ERROR")
        return False
    
    finally:
        # クリーンアップ
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        pya.terminate()

def interactive_chat():
    """対話モード"""
    print("🎤 ストリーミング音声対話モード")
    print("メッセージを入力してください（'quit'で終了）")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n💬 あなた: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '終了', 'q']:
                print("👋 対話を終了します")
                streaming_speak("対話を終了します。お疲れさまでした。")
                break
            
            if not user_input:
                continue
            
            print("🤖 Claude:", end=" ")
            
            # ここではシンプルに入力をそのまま読み上げ
            # 実際のClaude応答を組み込む場合は、ここでAPIコールを追加
            response = f"あなたのメッセージを確認しました。{user_input}"
            print(response)
            
            # ストリーミング音声で応答
            streaming_speak(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 対話を終了します")
            streaming_speak("対話を終了します。")
            break
        except Exception as e:
            print(f"\nエラー: {e}")
            write_log(f"対話エラー: {e}", "ERROR")

if __name__ == "__main__":
    interactive_chat()