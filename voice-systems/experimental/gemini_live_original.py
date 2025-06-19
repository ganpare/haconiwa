#!/usr/bin/env python3
"""
Gemini Live API - 完全オリジナル版（元のドキュメントそのまま）
"""

import os
import asyncio
import base64
import io
import traceback
import sys

import cv2
import pyaudio
import PIL.Image
import mss

import argparse

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

DEFAULT_MODE = "none"  # Noneに変更

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

CONFIG = types.LiveConnectConfig(
    response_modalities=[
        "AUDIO",
    ],
    # media_resolutionを削除（エラー回避）
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    # context_window_compressionも削除（エラー回避）
)

pya = pyaudio.PyAudio()


class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, single_message=None):
        self.video_mode = video_mode
        self.single_message = single_message

        self.audio_in_queue = None
        self.out_queue = None

        self.session = None

        self.send_text_task = None
        self.receive_audio_task = None
        self.play_audio_task = None

    async def send_single_message(self):
        """単一メッセージ送信（Claude Code用）"""
        if self.single_message:
            print(f"💬 送信: {self.single_message}")
            await self.session.send(input=self.single_message, end_of_turn=True)
            # 音声完了まで待機（最大30秒）
            await self.wait_for_audio_completion()
        raise asyncio.CancelledError("Single message sent")
    
    async def wait_for_audio_completion(self):
        """音声受信完了まで待機"""
        last_audio_time = asyncio.get_event_loop().time()
        self.last_audio_received = last_audio_time
        
        while True:
            await asyncio.sleep(1)  # 1秒間隔でチェック
            current_time = asyncio.get_event_loop().time()
            
            # 3秒間音声データが来なければ完了とみなす
            if current_time - self.last_audio_received > 3:
                print(f"\n🏁 音声完了検知（3秒間無受信）")
                break
                
            # 最大30秒でタイムアウト
            if current_time - last_audio_time > 30:
                print(f"\n⏰ タイムアウト（30秒）")
                break

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    def _get_frame(self, cap):
        # Read the frame
        ret, frame = cap.read()
        # Check if the frame was read successfully
        if not ret:
            return None
        # Fix: Convert BGR to RGB color space
        # OpenCV captures in BGR but PIL expects RGB format
        # This prevents the blue tint in the video feed
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)  # Now using RGB frame
        img.thumbnail([1024, 1024])

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        # This takes about a second, and will block the whole program
        # causing the audio pipeline to overflow if you don't to_thread it.
        cap = await asyncio.to_thread(
            cv2.VideoCapture, 0
        )  # 0 represents the default camera

        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

        # Release the VideoCapture object
        cap.release()

    def _get_screen(self):
        sct = mss.mss()
        monitor = sct.monitors[0]

        i = sct.grab(monitor)

        mime_type = "image/jpeg"
        image_bytes = mss.tools.to_png(i.rgb, i.size)
        img = PIL.Image.open(io.BytesIO(image_bytes))

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_screen(self):
        while True:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        # 単一メッセージモードではマイク入力しない
        if self.single_message:
            return
            
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        """Background task to reads from the websocket and write pcm chunks to the output queue"""
        print("🎧 音声受信開始...")
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    print(f"\n🎵 音声データ受信: {len(data)}bytes")
                    # 最新の音声受信時刻を更新
                    self.last_audio_received = asyncio.get_event_loop().time()
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(text, end="", flush=True)

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        print("🔊 音声再生準備完了...")
        chunk_count = 0
        while True:
            bytestream = await self.audio_in_queue.get()
            chunk_count += 1
            print(f"\n🎶 再生中: チャンク#{chunk_count}")
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                # 単一メッセージか対話かを選択
                if self.single_message:
                    send_text_task = tg.create_task(self.send_single_message())
                else:
                    send_text_task = tg.create_task(self.send_text())
                
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                
                if self.video_mode == "camera":
                    tg.create_task(self.get_frames())
                elif self.video_mode == "screen":
                    tg.create_task(self.get_screen())

                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            print("\n✅ セッション終了")
        except ExceptionGroup as EG:
            if hasattr(self, 'audio_stream') and self.audio_stream:
                self.audio_stream.close()
            traceback.print_exception(EG)


if __name__ == "__main__":
    # 引数処理
    if len(sys.argv) < 2:
        print("使用方法: python gemini_live_original.py <メッセージ>")
        print("例: python gemini_live_original.py 'オリジナル版のテストです'")
        sys.exit(1)
    
    single_message = " ".join(sys.argv[1:])
    
    print("🚀 Gemini Live API - 完全オリジナル版")
    print(f"📝 メッセージ: {single_message}")
    
    main = AudioLoop(video_mode=DEFAULT_MODE, single_message=single_message)
    asyncio.run(main.run())