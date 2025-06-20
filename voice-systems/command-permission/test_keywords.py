#!/usr/bin/env python3
"""
音声認識キーワードテスト用デモスクリプト
"""

def test_keyword_recognition():
    """音声認識キーワードをテスト"""
    
    test_phrases = [
        # Python実行のキーワード
        ("はい", "python"),
        ("OK", "python"), 
        ("オーケー", "python"),
        ("実行", "python"),
        ("python", "python"),
        ("パイソン", "python"),
        ("やる", "python"),
        
        # Claude実行のキーワード
        ("claude", "claude"),
        ("クロード", "claude"),
        ("claude code", "claude"),
        ("クロードコード", "claude"),
        
        # 実行しないのキーワード
        ("no", "no"),
        ("やめ", "no"),
        ("だめ", "no"),
        ("怖い", "no"),
        ("EA", "no"),
        ("キャンセル", "no"),
        ("いいえ", "no"),
        
        # 曖昧なケース
        ("ちょっとpythonで", "python"),
        ("claudeにお任せ", "claude"),
        ("やめておこう", "no"),
        ("怖いのでclaude", "no"),  # 怖い が優先されて no になる
        
        # 音声認識誤認識パターン
        ("配送", "python"),  # Python → 配送
        ("配配", "python"),  # Python → 配配
        ("くらうど", "claude"),  # Claude → くらうど
        ("ハイ", "python"),  # はい → ハイ
    ]
    
    def classify_response(text):
        """音声認識結果を分類（実際のロジックと同じ）"""
        text = text.lower()
        
        # ネガティブワードを最優先でチェック
        if any(word in text for word in ['no', 'ノー', 'やめ', '中止', 'やめる', 'キャンセル', 'きゃんせる', 'いいえ', 'だめ', 'ダメ', 'cia', 'ea', 'えー', 'えい', '怖い', 'こわい']):
            return "no"
        elif any(word in text for word in ['claude', 'クロード', 'くろーど', 'claude code', 'クロードコード', 'くらうど', 'cloud', 'クラウド']):
            return "claude"
        elif any(word in text for word in ['はい', 'ok', 'オーケー', '実行', 'python', 'パイソン', 'ぱいそん', '実行する', 'やる', '配送', 'はいそん', 'パイ', 'pie', 'ハイ', 'hai', 'yes', '配配', '配']):
            return "python"
        else:
            return "unknown"
    
    print("🎯 音声認識キーワードテスト")
    print("=" * 50)
    
    correct = 0
    total = len(test_phrases)
    
    for phrase, expected in test_phrases:
        result = classify_response(phrase)
        status = "✅" if result == expected else "❌"
        
        print(f"{status} '{phrase}' → {result} (期待: {expected})")
        
        if result == expected:
            correct += 1
    
    print("=" * 50)
    print(f"📊 テスト結果: {correct}/{total} ({correct/total*100:.1f}%)")
    
    if correct == total:
        print("🎉 全テストケースが正常に動作しています！")
    else:
        print("⚠️ 一部のテストケースで問題があります。")

if __name__ == "__main__":
    test_keyword_recognition()