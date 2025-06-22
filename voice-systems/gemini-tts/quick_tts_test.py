#!/usr/bin/env python3
"""
簡単なGemini TTS テスト（.envからAPIキー読み込み）
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

def play_text_with_say(text: str):
    """sayコマンドで音声再生（macOS/Linux対応）"""
    try:
        # macOSの場合
        subprocess.run(["say", text], check=True)
        print(f"✅ 音声再生完了: {text}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            # Linuxの場合（espeak）
            subprocess.run(["espeak", text], check=True)
            print(f"✅ 音声再生完了 (espeak): {text}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Linuxの場合（festival）
                subprocess.run(["festival", "--tts"], input=text, text=True, check=True)
                print(f"✅ 音声再生完了 (festival): {text}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"❌ 音声システムが見つかりません。テキスト出力: {text}")

def generate(input_text: str):
    """簡単な音声出力（Gemini APIを使わずテスト）"""
    # APIキーの確認
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("⚠️ GEMINI_API_KEYが設定されていません (.envファイルを確認)")
        print("📢 フォールバック: システム音声で再生します")
        play_text_with_say(input_text)
        return
    
    print("🎤 Gemini TTS機能は準備中です")
    print("📢 フォールバック: システム音声で再生します")
    play_text_with_say(input_text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python quick_tts_test.py <メッセージ>")
        print("例: python quick_tts_test.py 'テスト音声です'")
        sys.exit(1)
    
    input_text = " ".join(sys.argv[1:])
    generate(input_text)