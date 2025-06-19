#!/usr/bin/env python3
"""
音声入力デバッグ用スクリプト
"""

import pyaudio
import wave
import sys

def test_audio_devices():
    """オーディオデバイスの一覧を表示"""
    print("🎤 利用可能なオーディオデバイス:")
    print("=" * 50)
    
    p = pyaudio.PyAudio()
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        print(f"デバイス {i}: {device_info['name']}")
        print(f"  最大入力チャンネル: {device_info['maxInputChannels']}")
        print(f"  最大出力チャンネル: {device_info['maxOutputChannels']}")
        print(f"  デフォルトサンプルレート: {device_info['defaultSampleRate']}")
        print(f"  ホストAPI: {p.get_host_api_info_by_index(device_info['hostApi'])['name']}")
        print()
    
    # デフォルトデバイスを表示
    try:
        default_input = p.get_default_input_device_info()
        print(f"🎤 デフォルト入力デバイス: {default_input['name']}")
    except OSError:
        print("❌ デフォルト入力デバイスが見つかりません")
    
    try:
        default_output = p.get_default_output_device_info()
        print(f"🔊 デフォルト出力デバイス: {default_output['name']}")
    except OSError:
        print("❌ デフォルト出力デバイスが見つかりません")
    
    p.terminate()

def test_microphone_recording():
    """マイクからの録音テスト"""
    print("\n🎙️ マイク録音テスト開始")
    print("3秒間録音します。何か話してください...")
    
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 3
    
    p = pyaudio.PyAudio()
    
    try:
        # ストリームを開く
        stream = p.open(format=FORMAT,
                      channels=CHANNELS,
                      rate=RATE,
                      input=True,
                      frames_per_buffer=CHUNK)
        
        print("録音中...")
        frames = []
        
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # 音量レベルを表示
            import struct
            import numpy as np
            
            # 音声データを数値に変換
            audio_data = np.frombuffer(data, dtype=np.int16)
            # 音量レベルを計算（RMS）
            if len(audio_data) > 0:
                rms = np.sqrt(np.mean(audio_data**2))
                # プログレスバー的な表示
                volume_bars = int(rms / 1000)  # 適当なスケーリング
                bar = "█" * min(volume_bars, 20)
                print(f"\r音量: [{bar:<20}] {rms:.0f}", end="", flush=True)
        
        print("\n録音完了!")
        
        stream.stop_stream()
        stream.close()
        
        # 録音されたデータを分析
        all_frames = b''.join(frames)
        audio_array = np.frombuffer(all_frames, dtype=np.int16)
        
        if len(audio_array) > 0:
            max_amplitude = np.max(np.abs(audio_array))
            avg_amplitude = np.mean(np.abs(audio_array))
            
            print(f"📊 録音データ分析:")
            print(f"  最大振幅: {max_amplitude}")
            print(f"  平均振幅: {avg_amplitude:.1f}")
            print(f"  データサイズ: {len(all_frames)} bytes")
            
            if max_amplitude < 100:
                print("⚠️ 音声レベルが非常に低いです。マイクの設定を確認してください。")
            elif max_amplitude < 1000:
                print("⚠️ 音声レベルが低いです。")
            else:
                print("✅ 音声レベルは適切です。")
        
        # 録音ファイルを保存
        filename = "audio_test.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(all_frames)
        wf.close()
        
        print(f"📁 録音ファイルを {filename} に保存しました")
        print("afplay audio_test.wav で再生できます")
        
    except Exception as e:
        print(f"❌ 録音エラー: {e}")
    finally:
        p.terminate()

def main():
    print("🔧 音声デバッグツール")
    print("=" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "record":
        test_microphone_recording()
    else:
        test_audio_devices()
        print("\n録音テストを行うには:")
        print("python audio_debug.py record")

if __name__ == "__main__":
    main()