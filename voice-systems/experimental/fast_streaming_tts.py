#!/usr/bin/env python3
"""
高速ストリーミングTTSシステム - Geminiテキスト生成 + リアルタイムTTS
"""

import os
import pyaudio
import threading
import time
import queue
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class FastStreamingTTS:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        
        # PyAudio設定
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RECEIVE_SAMPLE_RATE = 24000
        self.pya = pyaudio.PyAudio()
        self.stream = None
        
    def generate_streaming_text(self, user_input: str):
        """Gemini 2.0 Flashでテキストをストリーミング生成"""
        client = genai.Client(api_key=self.api_key)
        
        accumulated_text = ""
        chunk_text = ""
        
        try:
            for chunk in client.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=user_input
            ):
                if hasattr(chunk, 'text') and chunk.text:
                    print(chunk.text, end="", flush=True)
                    chunk_text += chunk.text
                    accumulated_text += chunk.text
                    
                    # 文章の区切りで音声生成をトリガー
                    if any(punct in chunk_text for punct in ['。', '！', '？', '.', '!', '?']):
                        self.text_queue.put(chunk_text.strip())
                        chunk_text = ""
                        
            # 残りのテキストがあれば追加
            if chunk_text.strip():
                self.text_queue.put(chunk_text.strip())
                
            # 終了シグナル
            self.text_queue.put(None)
            
        except Exception as e:
            print(f"\nテキスト生成エラー: {e}")
            self.text_queue.put(None)
    
    def generate_streaming_audio(self):
        """テキストチャンクから音声をストリーミング生成"""
        client = genai.Client(api_key=self.api_key)
        
        while True:
            text_chunk = self.text_queue.get()
            if text_chunk is None:  # 終了シグナル
                self.audio_queue.put(None)
                break
                
            try:
                # 短いプロンプト
                enhanced_text = f"冷静で落ち着いたトーンで、早口で話してください：{text_chunk}"
                
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
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        )
                    ),
                )
                
                # 音声データを収集
                audio_chunks = []
                for chunk in client.models.generate_content_stream(
                    model="gemini-2.5-flash-preview-tts",
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
                        audio_data = chunk.candidates[0].content.parts[0].inline_data.data
                        audio_chunks.append(audio_data)
                
                # 音声データを再生キューに追加
                if audio_chunks:
                    self.audio_queue.put(audio_chunks)
                    
            except Exception as e:
                print(f"\n音声生成エラー: {e}")
    
    def play_streaming_audio(self):
        """音声をストリーミング再生"""
        try:
            self.stream = self.pya.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RECEIVE_SAMPLE_RATE,
                output=True
            )
            
            while True:
                audio_chunks = self.audio_queue.get()
                if audio_chunks is None:  # 終了シグナル
                    break
                    
                # 音声チャンクを順次再生
                for audio_data in audio_chunks:
                    self.stream.write(audio_data)
                    
        except Exception as e:
            print(f"\n音声再生エラー: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
    
    def chat(self, user_input: str):
        """高速ストリーミング対話"""
        print(f"💬 あなた: {user_input}")
        print("🤖 Gemini: ", end="", flush=True)
        
        # 3つのスレッドで並行処理
        text_thread = threading.Thread(target=self.generate_streaming_text, args=(user_input,))
        audio_thread = threading.Thread(target=self.generate_streaming_audio)
        play_thread = threading.Thread(target=self.play_streaming_audio)
        
        # スレッド開始
        text_thread.start()
        audio_thread.start()
        play_thread.start()
        
        # 全スレッド完了まで待機
        text_thread.join()
        audio_thread.join()
        play_thread.join()
        
        print("\n✅ 対話完了")
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if self.pya:
            self.pya.terminate()

def main():
    import sys
    if len(sys.argv) < 2:
        print("使用方法: python fast_streaming_tts.py <メッセージ>")
        print("例: python fast_streaming_tts.py 'ハコニワプロジェクトについて教えて'")
        return
    
    user_input = " ".join(sys.argv[1:])
    
    tts_system = FastStreamingTTS()
    try:
        tts_system.chat(user_input)
    finally:
        tts_system.cleanup()

if __name__ == "__main__":
    main()