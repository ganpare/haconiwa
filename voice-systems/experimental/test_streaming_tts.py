#!/usr/bin/env python3
"""
Gemini TTS ストリーミング テスト
"""

import os
import pyaudio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def test_streaming_tts():
    """Gemini TTS ストリーミングをテスト"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEYが設定されていません")
        return

    # PyAudio設定
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RECEIVE_SAMPLE_RATE = 24000
    
    # PyAudioの初期化
    pya = pyaudio.PyAudio()
    
    try:
        # 音声ストリームを開く
        stream = pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True
        )
        
        print("ストリーミング開始...")
        
        client = genai.Client(api_key=api_key)
        model = "gemini-2.5-flash-preview-tts"
        
        # テストメッセージ
        test_message = "ストリーミングTTSのテストです。リアルタイムで音声が再生されているか確認します。"
        enhanced_text = f"以下のメッセージを冷静で落ち着いたトーンで、早口で話してください。プロフェッショナルで集中した雰囲気を保ちながら、テンポよく読み上げてください：\n\n{test_message}"
        
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
                print(".", end="", flush=True)  # 進行状況表示
                stream.write(audio_data)
        
        print("\nストリーミング完了")
        
    except Exception as e:
        print(f"ストリーミングエラー: {e}")
    
    finally:
        # クリーンアップ
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        pya.terminate()

if __name__ == "__main__":
    test_streaming_tts()