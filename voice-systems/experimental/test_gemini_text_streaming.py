#!/usr/bin/env python3
"""
Gemini テキストストリーミングテスト
"""

import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def test_gemini_text_streaming():
    """Geminiのテキストストリーミングをテスト"""
    
    # 環境変数からAPI KEYを取得
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEYが設定されていません")
        return
    
    client = genai.Client(api_key=api_key)
    
    print("🤖 Gemini: ", end="", flush=True)
    
    try:
        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents="ハコニワプロジェクトの音声システムについて、簡潔に状況を教えてください"
        ):
            if hasattr(chunk, 'text') and chunk.text:
                print(chunk.text, end="", flush=True)
        
        print()  # 改行
        print("✅ ストリーミング完了")
        
    except Exception as e:
        print(f"\nエラー: {e}")

if __name__ == "__main__":
    test_gemini_text_streaming()