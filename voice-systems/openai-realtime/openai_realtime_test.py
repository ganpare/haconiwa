#!/usr/bin/env python3
"""
OpenAI Realtime API - 読み上げ復唱AIテスト
"""

import os
import json
import asyncio
import websocket
import threading
import sys
import base64
import pyaudio
from dotenv import load_dotenv

load_dotenv()

class OpenAIRealtimeReadout:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません")
        
        self.ws = None
        self.connected = False
        
        # PyAudio設定
        self.pya = pyaudio.PyAudio()
        self.audio_stream = None
        self.volume_scale = 0.5  # 音量を半分に
        self.initial_buffer = []  # 初期バッファ
        self.buffer_threshold = 3  # 最初の3チャンクまでバッファ
        self.chunk_count = 0
        self.buffering_complete = False
        self.setup_audio()
    
    def setup_audio(self):
        """音声出力設定"""
        try:
            # OpenAI Realtime APIの音声フォーマットに合わせて設定
            self.audio_stream = self.pya.open(
                format=pyaudio.paInt16,  # 16-bit PCM
                channels=1,              # モノラル
                rate=24000,              # 24kHz サンプリングレート
                output=True,
                frames_per_buffer=4096,  # 安定性のためバッファサイズを大きく
                stream_callback=None
            )
            print("🔊 音声出力準備完了 (16bit PCM, 24kHz, Mono)")
        except Exception as e:
            print(f"❌ 音声設定エラー: {e}")
            self.audio_stream = None
        
    def on_open(self, ws):
        print("🔗 OpenAI Realtime API接続完了")
        self.connected = True
        
        # セッション設定
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "あなたは感情豊かな読み上げ専用AIです。与えられたテキストを早口で、喜びや活力に満ちた明るいトーンで読み上げてください。感情豊かで生き生きとした表現力を込めながら、テンポよく高速で話してください。楽しそうな声色とエネルギッシュな口調を保ちつつ、早口で読み上げることを重視してください。追加のコメントや説明は一切せず、与えられた文章をそのまま感情豊かに読み上げるだけにしてください。",
                "voice": "shimmer",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": [],
                "tool_choice": "none",
                "temperature": 0.6,
            }
        }
        
        ws.send(json.dumps(session_config))
        print("📝 セッション設定送信完了")
        # 即座に続行可能にするため、セッション更新の完了を待たない
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("type", "")
            
            if event_type == "session.created":
                print("✅ セッション作成完了")
            elif event_type == "session.updated":
                print("✅ セッション更新完了")
            elif event_type == "response.audio.delta":
                # 音声データ受信
                audio_data = data.get("delta", "")
                if audio_data and self.audio_stream:
                    try:
                        # Base64デコードして音声再生
                        audio_bytes = base64.b64decode(audio_data)
                        # デバッグ情報を表示
                        print(f"\n🎵 音声データ: {len(audio_bytes)}bytes", end="", flush=True)
                        
                        # 音声データの処理（初期バッファリング対応）
                        try:
                            # 音量調整
                            import numpy as np
                            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                            audio_array = (audio_array * self.volume_scale).astype(np.int16)
                            adjusted_audio = audio_array.tobytes()
                            
                            self.chunk_count += 1
                            
                            # 最初の数チャンクはバッファに蓄積
                            if not self.buffering_complete and self.chunk_count <= self.buffer_threshold:
                                self.initial_buffer.append(adjusted_audio)
                                print(" 📦", end="", flush=True)  # バッファ中
                                
                                # バッファ閾値に達したら一括再生開始
                                if self.chunk_count == self.buffer_threshold:
                                    print(" 🚀", end="", flush=True)  # 再生開始
                                    if self.audio_stream:
                                        for buffered_audio in self.initial_buffer:
                                            self.audio_stream.write(buffered_audio, exception_on_underflow=False)
                                    self.buffering_complete = True
                                    self.initial_buffer = []  # バッファクリア
                            else:
                                # バッファリング完了後は即座に再生
                                if self.audio_stream and len(adjusted_audio) > 0:
                                    self.audio_stream.write(adjusted_audio, exception_on_underflow=False)
                                print(" ✓", end="", flush=True)
                                
                        except Exception as play_error:
                            print(f" ⚠️", end="", flush=True)
                            # 音声再生エラーでも処理を継続
                    except Exception as e:
                        print(f"\n❌ 音声処理エラー: {e}")
            elif event_type == "response.audio.done":
                # 音声ストリームの完了を待つ
                if self.audio_stream:
                    import time
                    time.sleep(1.2)  # 1.2秒待機して音声バッファを完全に再生
                print("\n🔊 音声再生完了")
            elif event_type == "response.done":
                print("✅ 応答完了")
            elif event_type == "error":
                print(f"❌ エラー: {data}")
                print("⚠️ API エラーが発生しました")
            elif event_type == "session.created":
                print("✅ セッション作成完了")
            elif event_type == "session.updated":
                print("✅ セッション更新完了")
            elif event_type == "rate_limits.updated":
                print("📊 レート制限更新")
            else:
                print(f"📨 受信イベント: {event_type}")
                
        except json.JSONDecodeError:
            print(f"⚠️ JSON解析エラー: {message}")
    
    def on_error(self, ws, error):
        print(f"❌ WebSocketエラー: {error}")
        print("🔄 接続エラーが発生しました")
    
    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 接続終了")
        if close_status_code:
            print(f"終了コード: {close_status_code}")
        if close_msg:
            print(f"終了メッセージ: {close_msg}")
        self.connected = False
    
    def connect(self):
        """WebSocket接続開始"""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        headers = [
            f"Authorization: Bearer {self.api_key}",
            "OpenAI-Beta: realtime=v1"
        ]
        
        self.ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        
        # 別スレッドで接続
        def run():
            self.ws.run_forever()
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
        # 接続完了まで待機
        import time
        while not self.connected:
            time.sleep(0.1)
        
        return thread
    
    def send_text_for_readout(self, text: str):
        """テキストを送信して読み上げさせる"""
        if not self.connected:
            print("❌ 接続されていません")
            return
        
        print(f"📤 送信テキスト: {text}")
        
        # 会話アイテム作成
        conversation_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }
        
        # 応答作成要求
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "与えられたテキストを可能な限り最高速度で早口で読み上げてください。ラップのような超高速で間を空けずに読み上げてください。"
            }
        }
        
        self.ws.send(json.dumps(conversation_item))
        self.ws.send(json.dumps(response_create))
    
    def close(self):
        """接続を閉じる"""
        if self.ws:
            self.ws.close()
        if self.audio_stream:
            # 残りの音声データを完全に再生するまで待機
            try:
                import time
                time.sleep(0.8)  # 最終的な音声再生完了を確実にする
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception as e:
                print(f"音声ストリーム終了エラー: {e}")
        if self.pya:
            self.pya.terminate()

def main():
    if len(sys.argv) < 2:
        print("使用方法: python openai_realtime_test.py <読み上げテキスト>")
        print("例: python openai_realtime_test.py 'こんにちは、これはOpenAI Realtime APIのテストです'")
        return
    
    text_to_read = " ".join(sys.argv[1:])
    
    print("🚀 OpenAI Realtime API - 読み上げテスト")
    print(f"📝 読み上げテキスト: {text_to_read}")
    
    try:
        readout_ai = OpenAIRealtimeReadout()
        thread = readout_ai.connect()
        
        # 接続後即座にテキスト送信
        
        readout_ai.send_text_for_readout(text_to_read)
        
        # 15秒待機（より長い音声にも対応）
        import time
        time.sleep(15)
        
        readout_ai.close()
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()