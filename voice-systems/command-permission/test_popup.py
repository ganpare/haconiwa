#!/usr/bin/env python3
"""
ポップアップテスト
"""

import subprocess

def test_popup():
    """ポップアップテスト"""
    print("ポップアップをテストします...")
    
    try:
        subprocess.run([
            "osascript", "-e", 
            'display notification "🎙️ 音声録音中... (5秒間)" with title "Claude Code 音声認識" sound name "Submarine"'
        ], check=False)
        print("✅ ポップアップ送信成功")
    except Exception as e:
        print(f"❌ ポップアップエラー: {e}")

if __name__ == "__main__":
    test_popup()