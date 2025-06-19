#!/usr/bin/env python3
"""
シンプルな音声認識テスト
"""

import pyaudio
import wave
import tempfile
import os
import openai
from dotenv import load_dotenv

load_dotenv()

def simple_voice_test():
    """シンプルな音声認識テスト"""
    print("🎙️ 5秒間の音声認識テスト開始")
    print("「はい」「Python」「クロード」「やめ」などを話してください")
    
    # より高品質な録音設定
    CHUNK = 4096  # より大きなチャンク
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 48000  # ネイティブレート
    RECORD_SECONDS = 5  # 長めに録音
    
    p = pyaudio.PyAudio()
    
    try:
        # マイクの情報を表示
        default_mic = p.get_default_input_device_info()
        print(f"使用マイク: {default_mic['name']}")
        
        stream = p.open(format=FORMAT,
                      channels=CHANNELS,
                      rate=RATE,
                      input=True,
                      frames_per_buffer=CHUNK)
        
        print("録音開始...")
        frames = []
        
        import numpy as np
        max_level = 0
        
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # リアルタイムで音量レベルを表示
            audio_data = np.frombuffer(data, dtype=np.int16)
            if len(audio_data) > 0:
                level = np.max(np.abs(audio_data))
                max_level = max(max_level, level)
                bars = int(level / 1000)
                bar = "█" * min(bars, 30)
                print(f"\r音量: [{bar:<30}] {level:5d} (最大: {max_level})", end="", flush=True)
        
        print("\n録音完了!")
        
        stream.stop_stream()
        stream.close()
        
        # WAVファイルに保存
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            wf = wave.open(temp_file.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            print(f"📁 音声ファイル保存: {temp_file.name}")
            
            # OpenAI Whisperで音声認識
            try:
                client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                
                with open(temp_file.name, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ja",
                        prompt="はい、Python、クロード、やめ、だめ、怖い、EA、実行、キャンセル、OK、Claude Code"
                    )
                
                recognized_text = transcript.text
                print(f"🎯 音声認識結果: '{recognized_text}'")
                
                # キーワード判定
                text_lower = recognized_text.lower()
                if any(word in text_lower for word in ['はい', 'ok', '実行', 'python', 'パイソン', 'やる']):
                    print("✅ Python実行キーワードを検出")
                elif any(word in text_lower for word in ['claude', 'クロード', 'claude code']):
                    print("✅ Claude実行キーワードを検出")
                elif any(word in text_lower for word in ['やめ', 'だめ', 'no', 'キャンセル', '怖い']):
                    print("✅ キャンセルキーワードを検出")
                else:
                    print("❓ 不明なキーワード")
                
            except Exception as e:
                print(f"❌ 音声認識エラー: {e}")
            
            # 一時ファイルを削除
            try:
                os.unlink(temp_file.name)
            except:
                pass
    
    except Exception as e:
        print(f"❌ 録音エラー: {e}")
    finally:
        p.terminate()

if __name__ == "__main__":
    simple_voice_test()