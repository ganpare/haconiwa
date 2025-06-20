#!/usr/bin/env python3
"""
GPT-4o API接続テスト
"""

import os
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def test_api_key():
    """APIキーの確認"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print(f"✅ OPENAI_API_KEY が見つかりました")
        print(f"🔑 APIキー（先頭10文字）: {api_key[:10]}...")
        print(f"📏 APIキー長: {len(api_key)} 文字")
        return True
    else:
        print("❌ OPENAI_API_KEY が見つかりません")
        return False

def test_openai_import():
    """OpenAIライブラリのインポートテスト"""
    try:
        import openai
        print(f"✅ openai ライブラリインポート成功")
        print(f"📦 openai バージョン: {openai.__version__}")
        return True
    except ImportError as e:
        print(f"❌ openai ライブラリインポートエラー: {e}")
        return False

def test_gpt4o_simple():
    """GPT-4o 簡単なテスト"""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        print("🌐 GPT-4o テストリクエスト送信中...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは数字分類の専門家です。ユーザーの入力を1、2、3のいずれかで答えてください。"},
                {"role": "user", "content": "「Python実行」と言われたら何番ですか？1=Python、2=Claude、3=やめる"}
            ],
            max_tokens=5,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ GPT-4o レスポンス成功: '{result}'")
        
        return True
        
    except Exception as e:
        print(f"❌ GPT-4o テストエラー: {e}")
        return False

def test_voice_classification():
    """音声分類機能のテスト"""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        test_text = "Python、Python、Python、Pythonだってばー"
        
        system_prompt = """あなたは音声コマンド分類の専門家です。
ユーザーの音声入力を正確に以下の4つのカテゴリに分類してください。

**分類ルール:**
1 = Python実行を意味する発言
2 = Claude実行を意味する発言  
3 = 実行拒否を意味する発言
0 = 判断不可能な発言

**重要:** 必ず数字1つ（1, 2, 3, 0のいずれか）のみで回答してください。説明は不要です。"""

        print(f"🎯 分類テスト: '{test_text}'")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"次の発言を分類してください: 「{test_text}」"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ 分類結果: '{result}' (期待値: 1)")
        
        return True
        
    except Exception as e:
        print(f"❌ 音声分類テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🔧 GPT-4o API接続診断開始")
    print("=" * 50)
    
    # 1. APIキー確認
    print("\n1️⃣ APIキー確認")
    api_ok = test_api_key()
    
    # 2. OpenAIライブラリ確認
    print("\n2️⃣ OpenAIライブラリ確認")
    import_ok = test_openai_import()
    
    if api_ok and import_ok:
        # 3. GPT-4o簡単テスト
        print("\n3️⃣ GPT-4o基本テスト")
        basic_ok = test_gpt4o_simple()
        
        if basic_ok:
            # 4. 音声分類テスト
            print("\n4️⃣ 音声分類テスト")
            classification_ok = test_voice_classification()
            
            if classification_ok:
                print("\n🎉 すべてのテストが成功しました！")
            else:
                print("\n⚠️ 音声分類テストで問題があります")
        else:
            print("\n⚠️ GPT-4o基本テストで問題があります")
    else:
        print("\n❌ 基本設定に問題があります")
    
    print("\n" + "=" * 50)
    print("🔧 診断完了")