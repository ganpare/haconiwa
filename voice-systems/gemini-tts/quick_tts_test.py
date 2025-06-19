#!/usr/bin/env python3
"""
元のGemini TTSプログラムをベースにした即座音声テスト
"""

import base64
import mimetypes
import os
import re
import struct
import subprocess
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def save_binary_file(file_name, data):
    f = open(file_name, "wb")
    f.write(data)
    f.close()
    print(f"File saved to: {file_name}")

def play_audio_file(filename: str):
    """音声ファイルを再生"""
    try:
        subprocess.run(["afplay", "-v", "0.2", filename], check=True)
        print(f"音声再生完了: {filename}")
    except subprocess.CalledProcessError as e:
        print(f"音声再生エラー: {e}")
    except FileNotFoundError:
        print("afplayコマンドが見つかりません")

def generate(input_text: str):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-preview-tts"
    
    # プロンプト追加
    enhanced_text = f"以下のテキストを普通に早口で読み上げてください：\n\n{input_text}"
    
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
        response_modalities=[
            "audio",
        ],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Zephyr"
                )
            )
        ),
    )

    file_index = 0
    audio_files = []
    
    print("🎤 音声生成中...")
    
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is None
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue
        if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
            file_name = f"quick_tts_{file_index}"
            file_index += 1
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            data_buffer = inline_data.data
            file_extension = mimetypes.guess_extension(inline_data.mime_type)
            if file_extension is None:
                file_extension = ".wav"
                data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
            
            full_filename = f"{file_name}{file_extension}"
            save_binary_file(full_filename, data_buffer)
            audio_files.append(full_filename)
        else:
            if hasattr(chunk, 'text') and chunk.text:
                print(chunk.text)
    
    # 音声ファイルを順次再生
    print("🔊 音声再生開始...")
    for audio_file in audio_files:
        play_audio_file(audio_file)
        # ファイルを削除
        try:
            os.remove(audio_file)
            print(f"ファイル削除: {audio_file}")
        except OSError:
            pass

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python quick_tts_test.py <メッセージ>")
        print("例: python quick_tts_test.py 'テスト音声です'")
        sys.exit(1)
    
    input_text = " ".join(sys.argv[1:])
    generate(input_text)