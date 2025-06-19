#!/usr/bin/env python3
"""
Claude APIと連携したストリーミング応答システム
"""

import os
import pyaudio
import threading
import time
import anthropic
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def claude_streaming_response(user_message: str):
    """Claude APIで応答を生成し、文字出力と音声出力を同時並行で実行"""
    
    # Claude APIで応答を生成
    anthropic_client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    
    try:
        print(f"💬 あなた: {user_message}")
        print("🤖 Claude応答生成中...")
        
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        
        claude_response = response.content[0].text
        print("✅ Claude応答完了")
        
    except Exception as e:
        claude_response = f"申し訳ありません。Claude APIでエラーが発生しました: {e}"
        print(f"❌ Claude APIエラー: {e}")
    
    # ストリーミング音声出力
    streaming_voice_output(claude_response)

def streaming_voice_output(text: str):
    """文字出力と音声出力を同時並行で実行"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEYが設定されていません")
        return

    # PyAudio設定
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RECEIVE_SAMPLE_RATE = 24000
    
    # 文字出力用の変数
    text_complete = False
    
    def print_text_gradually():
        """文字を徐々に出力"""
        nonlocal text_complete
        print("🤖 Claude: ", end="", flush=True)
        
        for char in text:
            print(char, end="", flush=True)
            time.sleep(0.03)  # 30ms間隔で文字出力（少し速く）
        
        text_complete = True
        print()  # 改行
    
    def play_streaming_audio():
        """ストリーミング音声を再生"""
        pya = pyaudio.PyAudio()
        
        try:
            # 音声ストリームを開く
            stream = pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True
            )
            
            client = genai.Client(api_key=api_key)
            model = "gemini-2.5-flash-preview-tts"
            
            # プロンプト
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
            
            # ストリーミング生成と再生
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
        
        except Exception as e:
            print(f"\n🔊 音声エラー: {e}")
        
        finally:
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
            pya.terminate()
    
    # 文字出力と音声出力を同時開始
    print("🔊 文字出力と音声出力を同時開始...")
    
    text_thread = threading.Thread(target=print_text_gradually)
    audio_thread = threading.Thread(target=play_streaming_audio)
    
    text_thread.start()
    audio_thread.start()
    
    # 両方の処理が完了するまで待機
    text_thread.join()
    audio_thread.join()
    
    print("✅ 応答完了\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方法: python claude_streaming_response.py <メッセージ>")
        print("例: python claude_streaming_response.py 'こんにちは、調子はどうですか？'")
        sys.exit(1)
    
    user_message = " ".join(sys.argv[1:])
    claude_streaming_response(user_message)