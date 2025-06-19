#!/usr/bin/env python3
"""
ストリーミング音声出力システム - 文字出力と音声を同時並行
"""

import os
import pyaudio
import threading
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

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
    chars_printed = 0
    text_complete = False
    
    def print_text_gradually():
        """文字を徐々に出力"""
        nonlocal chars_printed, text_complete
        print("🤖 Claude: ", end="", flush=True)
        
        for char in text:
            print(char, end="", flush=True)
            chars_printed += 1
            time.sleep(0.05)  # 50ms間隔で文字出力
        
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
            print(f"\n音声エラー: {e}")
        
        finally:
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
            pya.terminate()
    
    # 文字出力と音声出力を同時開始
    text_thread = threading.Thread(target=print_text_gradually)
    audio_thread = threading.Thread(target=play_streaming_audio)
    
    print("🔊 文字出力と音声出力を同時開始...")
    
    text_thread.start()
    audio_thread.start()
    
    # 両方の処理が完了するまで待機
    text_thread.join()
    audio_thread.join()
    
    print("✅ 出力完了")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        test_message = "これは文字出力と音声出力の同時実行テストです。テキストが画面に表示されると同時に音声でも読み上げられます。"
    else:
        test_message = " ".join(sys.argv[1:])
    
    streaming_voice_output(test_message)