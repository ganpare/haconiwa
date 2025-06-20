#!/usr/bin/env python3
"""
Git pre-commit フックインストーラー
"""

import os
import sys
import stat
from pathlib import Path

def install_pre_commit_hook():
    """pre-commitフックをインストール"""
    
    # Gitリポジトリのルートを検出
    current_dir = Path.cwd()
    git_dir = None
    
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / '.git').exists():
            git_dir = parent / '.git'
            repo_root = parent
            break
    
    if not git_dir:
        print("❌ Gitリポジトリが見つかりません")
        return False
    
    print(f"📁 Gitリポジトリ: {repo_root}")
    
    # hooks ディレクトリを作成
    hooks_dir = git_dir / 'hooks'
    hooks_dir.mkdir(exist_ok=True)
    
    # pre-commit フックファイルのパス
    hook_file = hooks_dir / 'pre-commit'
    
    # セキュリティチェックスクリプトのパス
    security_script = repo_root / 'tools' / 'security-check' / 'commit_security_check.py'
    
    if not security_script.exists():
        print(f"❌ セキュリティチェックスクリプトが見つかりません: {security_script}")
        return False
    
    # pre-commit フックの内容
    hook_content = f'''#!/bin/bash
# Auto-generated pre-commit hook for security checking

echo "🔐 コミット前セキュリティチェック実行中..."

# Python スクリプトを実行
python3 "{security_script}" --ci

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ セキュリティチェック合格"
else
    echo "❌ セキュリティチェック失敗 - コミットをブロックしました"
    echo "修正後に再度コミットしてください"
fi

exit $exit_code
'''
    
    # 既存のフックをバックアップ
    if hook_file.exists():
        backup_file = hook_file.with_suffix('.backup')
        hook_file.rename(backup_file)
        print(f"📋 既存フックをバックアップ: {backup_file}")
    
    # 新しいフックを作成
    with open(hook_file, 'w') as f:
        f.write(hook_content)
    
    # 実行権限を付与
    hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC)
    
    print(f"✅ pre-commit フックをインストール: {hook_file}")
    print("これで、コミット時に自動的にセキュリティチェックが実行されます")
    
    return True

def uninstall_pre_commit_hook():
    """pre-commitフックをアンインストール"""
    
    current_dir = Path.cwd()
    git_dir = None
    
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / '.git').exists():
            git_dir = parent / '.git'
            break
    
    if not git_dir:
        print("❌ Gitリポジトリが見つかりません")
        return False
    
    hook_file = git_dir / 'hooks' / 'pre-commit'
    backup_file = git_dir / 'hooks' / 'pre-commit.backup'
    
    if hook_file.exists():
        hook_file.unlink()
        print(f"🗑️ pre-commit フックを削除: {hook_file}")
    
    if backup_file.exists():
        backup_file.rename(hook_file)
        print(f"📋 バックアップを復元: {backup_file} → {hook_file}")
    
    print("✅ pre-commit フックをアンインストールしました")
    return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'uninstall':
        uninstall_pre_commit_hook()
    else:
        print("🔧 Git pre-commit セキュリティフックインストーラー")
        print("=" * 50)
        
        if install_pre_commit_hook():
            print("\n📖 使用方法:")
            print("  手動チェック: python tools/security-check/commit_security_check.py")
            print("  フック無効化: python tools/security-check/install_hook.py uninstall")
        else:
            print("❌ インストールに失敗しました")
            sys.exit(1)

if __name__ == "__main__":
    main()