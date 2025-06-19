#!/usr/bin/env python3
"""
個人用セキュリティ設定セットアップスクリプト
"""

import json
import os
import getpass
from pathlib import Path

def setup_personal_nglist():
    """個人用NGリストを対話的にセットアップ"""
    
    script_dir = Path(__file__).parent
    nglist_file = script_dir / 'nglist.json'
    example_file = script_dir / 'nglist.json.example'
    
    print("🔧 個人用セキュリティ設定セットアップ")
    print("=" * 50)
    
    # 既存ファイルの確認
    if nglist_file.exists():
        print(f"⚠️ 既存の設定ファイルが見つかりました: {nglist_file}")
        if input("上書きしますか？ [y/N]: ").lower() != 'y':
            print("セットアップをキャンセルしました")
            return
    
    # テンプレートを読み込み
    if not example_file.exists():
        print(f"❌ テンプレートファイルが見つかりません: {example_file}")
        return
    
    with open(example_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n📝 個人情報を設定します（この情報はローカルにのみ保存されます）")
    
    # ユーザー名取得
    current_user = getpass.getuser()
    print(f"\n👤 現在のユーザー名: {current_user}")
    
    # フルパス設定
    home_dir = str(Path.home())
    print(f"🏠 ホームディレクトリ: {home_dir}")
    
    personal_paths = [
        home_dir,
        f"/Users/{current_user}",
        f"/home/{current_user}",
        f"C:\\\\Users\\\\{current_user}"
    ]
    
    # メールアドレス設定
    print("\n📧 メールアドレスを設定してください")
    email = input("メールアドレス（空Enter でスキップ）: ").strip()
    
    personal_emails = []
    if email:
        # エスケープして正規表現用に変換
        escaped_email = email.replace(".", "\\.").replace("@", "@")
        personal_emails.append(escaped_email)
    
    # 組織ドメイン設定
    print("\n🏢 組織固有のドメインがあれば設定してください")
    domain = input("内部ドメイン（例: internal.company.com）（空Enter でスキップ）: ").strip()
    
    personal_domains = []
    if domain:
        escaped_domain = domain.replace(".", "\\.")
        personal_domains.append(escaped_domain)
    
    # 設定を更新
    config['user_specific_patterns']['personal_paths']['patterns'] = personal_paths
    
    if personal_emails:
        config['user_specific_patterns']['personal_emails']['patterns'] = personal_emails
    else:
        # メールアドレスが設定されていない場合は削除
        del config['user_specific_patterns']['personal_emails']
    
    if personal_domains:
        config['user_specific_patterns']['personal_domains']['patterns'] = personal_domains
    else:
        # ドメインが設定されていない場合は削除
        del config['user_specific_patterns']['personal_domains']
    
    # ホワイトリストにユーザー名を追加
    config['whitelist_patterns']['safe_placeholders'].extend([
        current_user,
        current_user.lower(),
        "username",
        "your_username"
    ])
    
    # 重複を除去
    config['whitelist_patterns']['safe_placeholders'] = list(set(
        config['whitelist_patterns']['safe_placeholders']
    ))
    
    # ファイルに保存
    with open(nglist_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 個人用設定を保存しました: {nglist_file}")
    print("\n📋 設定内容:")
    print(f"  🚫 チェック対象パス: {len(personal_paths)}件")
    print(f"  📧 チェック対象メール: {len(personal_emails)}件") 
    print(f"  🌐 チェック対象ドメイン: {len(personal_domains)}件")
    print(f"  ✅ 許可プレースホルダー: {len(config['whitelist_patterns']['safe_placeholders'])}件")
    
    print("\n🔐 この設定ファイルは .gitignore に含まれており、コミットされません")
    print("🧪 テスト実行: python tools/security-check/commit_security_check.py")

def main():
    try:
        setup_personal_nglist()
    except KeyboardInterrupt:
        print("\n\n🛑 セットアップが中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()