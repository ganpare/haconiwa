#!/usr/bin/env python3
"""
Gemini Live API 音声対話テスト - 簡易版
"""

import os
import asyncio
import pyaudio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-exp-native-audio-thinking-dialog"

class GeminiLiveAudio:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")
        
        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=self.api_key,
        )
        
        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            ),
        )
        
        self.pya = pyaudio.PyAudio()
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self.audio_stream = None
        
    async def send_text_message(self, message: str):
        """テキストメッセージを送信"""
        print(f"💬 送信: {message}")
        if self.session:
            await self.session.send(input=message, end_of_turn=True)
    
    async def listen_audio(self):
        """マイク音声を取得してGeminiに送信"""
        try:
            mic_info = self.pya.get_default_input_device_info()
            self.audio_stream = await asyncio.to_thread(
                self.pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            
            print("🎤 音声入力開始...")
            while True:
                data = await asyncio.to_thread(
                    self.audio_stream.read, 
                    CHUNK_SIZE, 
                    exception_on_overflow=False
                )
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                
        except Exception as e:
            print(f"音声入力エラー: {e}")
    
    async def send_realtime(self):
        """リアルタイムデータ送信"""
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)
    
    async def receive_audio(self):
        """Geminiからの音声応答を受信"""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(f"🤖 Gemini: {text}", end="", flush=True)
            
            # 割り込み時の音声キューをクリア
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
    
    async def play_audio(self):
        """音声を再生"""
        try:
            stream = await asyncio.to_thread(
                self.pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
            )
            
            print("🔊 音声出力開始...")
            audio_count = 0
            while True:
                bytestream = await self.audio_in_queue.get()
                await asyncio.to_thread(stream.write, bytestream)
                audio_count += 1
                print(f"🎵 音声チャンク再生: {audio_count}")
                
        except Exception as e:
            print(f"音声再生エラー: {e}")
    
    async def single_message_mode(self, message: str):
        """単一メッセージモード"""
        print(f"📝 単一メッセージモード: {message}")
        await self.send_text_message(message)
        
        # 応答を待つ（10秒程度に延長）
        await asyncio.sleep(10)
        
        print("✅ 応答完了")
        raise asyncio.CancelledError("メッセージ送信完了")
    
    async def run_single_message(self, message: str):
        """単一メッセージで実行"""
        try:
            async with self.client.aio.live.connect(model=MODEL, config=self.config) as session:
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                
                async with asyncio.TaskGroup() as tg:
                    # 単一メッセージタスクブランチを作成
                    text_task = tg.create_task(self.single_message_mode(message))
                    
                    # 音声関連タスクブランチを作成
                    tg.create_task(self.send_realtime())
                    tg.create_task(self.receive_audio())
                    tg.create_task(self.play_audio())
                    
                    # テキストタスクブランチの完了を待機
                    await text_task
                    
        except asyncio.CancelledError:
            print("✅ セッション終了")
        except Exception as e:
            print(f"❌ エラー: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.close()
            self.pya.terminate()

async def main():
    """メイン関数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python gemini_live_audio_test.py <メッセージ>")
        print("例: python gemini_live_audio_test.py 'ハコニワプロジェクトについて教えて'")
        return
    
    message = " ".join(sys.argv[1:])
    
    try:
        live_audio = GeminiLiveAudio()
        await live_audio.run_single_message(message)
    except Exception as e:
        print(f"初期化エラー: {e}")

if __name__ == "__main__":
    print("🚀 Gemini Live API 音声対話テスト")
    print("必要なパッケージ: pip install opencv-python mss")
    
    # 必要なパッケージをチェック
    try:
        import cv2
        import mss
        print("✅ 必要パッケージが揃っています")
    except ImportError as e:
        print(f"⚠️ パッケージが不足しています: {e}")
        print("pip install opencv-python mss を実行してください")
    
    asyncio.run(main())