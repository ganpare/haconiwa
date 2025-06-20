#!/usr/bin/env python3
"""
Git コミット前セキュリティチェックツール
公開リポジトリへの安全なコミットを保証するためのチェックプログラム
"""

import os
import re
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
import argparse
from datetime import datetime

class CommitSecurityChecker:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.script_dir = Path(__file__).parent
        
        # 危険なパターン定義
        self.dangerous_patterns = {
            'full_paths': {
                'patterns': [
                    r'/Users/[^/\s]+(?:/[^\s]*)?',
                    r'/home/[^/\s]+(?:/[^\s]*)?',
                    r'C:\\\\Users\\\\[^\\\\]+(?:\\\\[^\\s]*)?',
                    r'/opt/[^/\s]+/[^/\s]+(?:/[^\s]*)?',
                ],
                'severity': 'ERROR',
                'description': 'ハードコードされたフルパス'
            },
            'api_keys': {
                'patterns': [
                    r'["\']?[A-Za-z0-9_-]{20,}["\']?\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']',  # API key assignments
                    r'api[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']',
                    r'secret[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']',
                    r'access[_-]?token\s*[=:]\s*["\'][^"\']{10,}["\']',
                    r'bearer\s+[A-Za-z0-9_-]{20,}',
                ],
                'severity': 'ERROR',
                'description': '実際のAPIキーやトークン'
            },
            'passwords': {
                'patterns': [
                    r'password\s*[=:]\s*["\'][^"\']{3,}["\']',
                    r'passwd\s*[=:]\s*["\'][^"\']{3,}["\']',
                    r'pwd\s*[=:]\s*["\'][^"\']{3,}["\']',
                ],
                'severity': 'ERROR',
                'description': 'ハードコードされたパスワード'
            },
            'private_urls': {
                'patterns': [
                    r'https?://localhost[:/]',
                    r'https?://127\.0\.0\.1[:/]',
                    r'https?://192\.168\.\d+\.\d+[:/]',
                    r'https?://10\.\d+\.\d+\.\d+[:/]',
                    r'https?://172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+[:/]',
                    r'\.local[:/]',
                ],
                'severity': 'WARNING',
                'description': 'プライベートIPアドレスやローカルURL'
            },
            'emails': {
                'patterns': [
                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?!\.(com|org|net|example))',
                ],
                'severity': 'WARNING',
                'description': '実在するメールアドレス'
            },
            'sensitive_files': {
                'patterns': [
                    r'\.env(?:\.[^/\s]*)?$',
                    r'\.aws/credentials',
                    r'\.ssh/id_[a-z]+$',
                    r'private.*\.key$',
                    r'\.p12$',
                    r'\.pfx$',
                ],
                'severity': 'ERROR',
                'description': '機密ファイル'
            }
        }
        
        # 除外すべきファイル/ディレクトリ
        self.excluded_patterns = [
            r'\.git/',
            r'node_modules/',
            r'__pycache__/',
            r'\.venv/',
            r'venv/',
            r'\.env\.',
            r'\.DS_Store',
            r'\.pyc$',
            r'\.log$',
            r'\.tmp$',
            r'\.cache/',
            r'dist/',
            r'build/',
        ]
        
        # 基本の許可されたプレースホルダー
        self.allowed_placeholders = [
            'your_api_key',
            'your_secret_key',
            'your_token',
            'example.com',
            'test@example.com',
            'placeholder',
            'dummy',
            'sample',
            '/users/username',
            'username',
            'project',
        ]
        
        # 個人用NGリストを読み込み
        self.env_files = []
        self.env_values = set()  # .envファイルから読み取った値を保存
        self.load_env_values()
        self.load_personal_nglist()
    
    def log(self, message: str, level: str = 'INFO'):
        """ログ出力"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        if level == 'ERROR':
            self.errors.append(message)
            print(f"❌ [{timestamp}] {message}")
        elif level == 'WARNING':
            self.warnings.append(message)
            print(f"⚠️ [{timestamp}] {message}")
        else:
            self.info.append(message)
            if self.verbose:
                print(f"ℹ️ [{timestamp}] {message}")
    
    def is_excluded_file(self, file_path: str) -> bool:
        """ファイルが除外対象かチェック"""
        for pattern in self.excluded_patterns:
            if re.search(pattern, file_path):
                return True
        return False
    
    def is_env_file(self, file_path: str) -> bool:
        """環境変数ファイルかチェック"""
        file_name = Path(file_path).name
        return file_name in self.env_files
    
    def load_env_values(self):
        """プロジェクト内の.envファイルから値を読み取る"""
        project_root = Path.cwd()
        
        # 一般的な.envファイル名
        env_files_to_check = [
            '.env', '.env.local', '.env.development', 
            '.env.production', '.env.staging', '.env.test'
        ]
        
        for env_file in env_files_to_check:
            env_path = project_root / env_file
            if env_path.exists():
                try:
                    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            # コメント行や空行をスキップ
                            if not line or line.startswith('#'):
                                continue
                            
                            # KEY=VALUE 形式を解析
                            if '=' in line:
                                key, value = line.split('=', 1)
                                value = value.strip('"\'')
                                
                                # 値が一定の長さ以上で、明らかに機密情報の場合のみ追加
                                if (len(value) > 8 and 
                                    not value.lower() in ['localhost', '127.0.0.1', 'true', 'false'] and
                                    not value.startswith('${')):
                                    self.env_values.add(value)
                                    
                    self.log(f".envファイルから値を読み取り: {env_file} ({len(self.env_values)}個の値)")
                    
                except Exception as e:
                    self.log(f".envファイル読み取りエラー ({env_file}): {e}", 'WARNING')
        
        if self.env_values:
            self.log(f"監視対象の.env値: {len(self.env_values)}個")
    
    def load_personal_nglist(self):
        """個人用NGリストを読み込み"""
        nglist_file = self.script_dir / 'nglist.json'
        
        if nglist_file.exists():
            try:
                with open(nglist_file, 'r', encoding='utf-8') as f:
                    nglist = json.load(f)
                
                # 個人用パターンを追加
                user_patterns = nglist.get('user_specific_patterns', {})
                for category, config in user_patterns.items():
                    if category not in self.dangerous_patterns:
                        self.dangerous_patterns[category] = config
                    else:
                        # 既存カテゴリに追加
                        self.dangerous_patterns[category]['patterns'].extend(config.get('patterns', []))
                
                # ホワイトリストを追加
                whitelist = nglist.get('whitelist_patterns', {})
                safe_placeholders = whitelist.get('safe_placeholders', [])
                self.allowed_placeholders.extend(safe_placeholders)
                
                # .envファイル一覧を読み込み
                env_config = nglist.get('env_files', {})
                self.env_files = env_config.get('files', [])
                
                self.log(f"個人用NGリストを読み込み: {len(user_patterns)}個のカテゴリ")
                self.log(f"無視対象環境ファイル: {len(self.env_files)}個")
                
            except Exception as e:
                self.log(f"NGリスト読み込みエラー: {e}", 'WARNING')
        else:
            self.log("個人用NGリストが見つかりません (nglist.json)")
            self.log("テンプレートをコピーして作成: cp nglist.json.example nglist.json")
    
    def is_allowed_placeholder(self, text: str) -> bool:
        """許可されたプレースホルダーかチェック"""
        text_lower = text.lower()
        return any(placeholder in text_lower for placeholder in self.allowed_placeholders)
    
    def is_in_code_block(self, lines: List[str], line_index: int) -> bool:
        """指定行がコードブロック内かチェック"""
        code_block_count = 0
        for i in range(line_index):
            if '```' in lines[i]:
                code_block_count += 1
        return code_block_count % 2 == 1
    
    def check_file_content(self, file_path: str, content: str) -> List[Tuple[str, str, int]]:
        """ファイル内容をチェック"""
        issues = []
        lines = content.split('\n')
        
        # .envファイルの場合は全ての行をスキップ
        if self.is_env_file(file_path):
            self.log(f"環境変数ファイルをスキップ: {file_path}")
            return issues
        
        for line_num, line in enumerate(lines, 1):
            # 各危険パターンをチェック
            for category, config in self.dangerous_patterns.items():
                for pattern in config['patterns']:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        matched_text = match.group()
                        
                        # プレースホルダーの場合はスキップ
                        if self.is_allowed_placeholder(matched_text):
                            continue
                        
                        # 環境変数参照の場合はスキップ
                        if 'os.environ.get' in line or 'getenv' in line:
                            continue
                        
                        # コードブロック内のサンプルコードの場合はスキップ
                        if '```' in content and self.is_in_code_block(lines, line_num - 1):
                            continue
                        
                        issue_desc = f"{config['description']}: {matched_text}"
                        issues.append((config['severity'], issue_desc, line_num))
            
            # .envファイルの値がハードコーディングされていないかチェック
            self.check_env_hardcoding(file_path, line, line_num, issues)
        
        return issues
    
    def check_env_hardcoding(self, file_path: str, line: str, line_num: int, issues: List[Tuple[str, str, int]]):
        """.envファイルの値がハードコーディングされていないかチェック"""
        if not self.env_values:
            return
        
        # 環境変数参照の場合はスキップ
        if 'os.environ.get' in line or 'getenv' in line or 'process.env' in line:
            return
        
        # コメント行はスキップ
        if line.strip().startswith('#') or line.strip().startswith('//'):
            return
        
        for env_value in self.env_values:
            if env_value in line:
                # クォートで囲まれた文字列内にある場合のみ警告
                quoted_patterns = [
                    f'"{env_value}"',
                    f"'{env_value}'",
                    f'`{env_value}`'
                ]
                
                if any(pattern in line for pattern in quoted_patterns):
                    issue_desc = f".envファイルの値がハードコーディング: {env_value[:20]}..."
                    issues.append(("ERROR", issue_desc, line_num))
                    break
    
    def get_staged_files(self) -> List[str]:
        """ステージングされたファイル一覧を取得"""
        try:
            result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                                  capture_output=True, text=True, check=True)
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            self.log(f"ステージングファイル数: {len(files)}")
            return files
        except subprocess.CalledProcessError as e:
            self.log(f"Gitコマンドエラー: {e}", 'ERROR')
            return []
    
    def get_file_content(self, file_path: str) -> str:
        """ファイル内容を取得（ステージング版）"""
        try:
            # ステージングされた内容を取得
            result = subprocess.run(['git', 'show', f':{file_path}'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            # ステージングにない場合はワーキングツリーから取得
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                self.log(f"ファイル読み込みエラー ({file_path}): {e}", 'WARNING')
                return ""
    
    def check_sensitive_filenames(self, files: List[str]) -> None:
        """機密ファイル名をチェック"""
        for file_path in files:
            if self.is_excluded_file(file_path):
                continue
            
            # ファイル名パターンをチェック
            for pattern in self.dangerous_patterns['sensitive_files']['patterns']:
                if re.search(pattern, file_path, re.IGNORECASE):
                    self.log(f"機密ファイル: {file_path}", 'ERROR')
    
    def check_git_config(self) -> None:
        """Git設定をチェック"""
        try:
            # ユーザー名とメールアドレスをチェック
            result = subprocess.run(['git', 'config', 'user.email'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                email = result.stdout.strip()
                if email and not email.endswith('@example.com'):
                    self.log(f"Git email設定: {email}", 'INFO')
        except Exception:
            pass
    
    def generate_report(self) -> Dict:
        """チェック結果レポートを生成"""
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'errors': len(self.errors),
                'warnings': len(self.warnings),
                'info': len(self.info)
            },
            'issues': {
                'errors': self.errors,
                'warnings': self.warnings,
                'info': self.info
            },
            'status': 'SAFE' if len(self.errors) == 0 else 'UNSAFE'
        }
    
    def run_security_check(self) -> bool:
        """メインのセキュリティチェック実行"""
        print("🔐 Git コミットセキュリティチェック開始")
        print("=" * 50)
        
        # 個人用NGリストの存在確認
        nglist_file = self.script_dir / 'nglist.json'
        if not nglist_file.exists():
            print("⚠️ 個人用NGリストが見つかりません")
            print("💡 テンプレートから作成: cp tools/security-check/nglist.json.example tools/security-check/nglist.json")
            print("📝 個人のフルパスやメールアドレスを設定してください")
            print()
        
        # ステージングファイルを取得
        staged_files = self.get_staged_files()
        if not staged_files:
            self.log("ステージングされたファイルがありません", 'WARNING')
            return True
        
        # Git設定チェック
        self.check_git_config()
        
        # 機密ファイル名チェック
        self.check_sensitive_filenames(staged_files)
        
        # 各ファイルの内容をチェック
        total_files = 0
        checked_files = 0
        
        for file_path in staged_files:
            total_files += 1
            
            if self.is_excluded_file(file_path):
                self.log(f"スキップ: {file_path} (除外ファイル)")
                continue
            
            self.log(f"チェック中: {file_path}")
            content = self.get_file_content(file_path)
            
            if not content:
                continue
            
            checked_files += 1
            issues = self.check_file_content(file_path, content)
            
            for severity, description, line_num in issues:
                message = f"{file_path}:{line_num} - {description}"
                self.log(message, severity)
        
        # 結果サマリー
        print("\n" + "=" * 50)
        print("📊 チェック結果サマリー")
        print(f"📁 総ファイル数: {total_files}")
        print(f"🔍 チェック済み: {checked_files}")
        print(f"❌ エラー: {len(self.errors)}")
        print(f"⚠️ 警告: {len(self.warnings)}")
        print(f"ℹ️ 情報: {len(self.info)}")
        
        # 結果判定
        is_safe = len(self.errors) == 0
        
        if is_safe:
            print("\n✅ セキュリティチェック合格 - コミット安全")
        else:
            print("\n🚨 セキュリティチェック失敗 - コミット前に修正が必要")
            print("\n修正が必要な問題:")
            for error in self.errors:
                print(f"  ❌ {error}")
        
        return is_safe

def main():
    parser = argparse.ArgumentParser(description='Git コミット前セキュリティチェック')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='詳細な出力を表示')
    parser.add_argument('-r', '--report', type=str, 
                       help='JSON レポートファイルを出力')
    parser.add_argument('--ci', action='store_true',
                       help='CI環境用（非対話モード）')
    
    args = parser.parse_args()
    
    checker = CommitSecurityChecker(verbose=args.verbose)
    
    try:
        is_safe = checker.run_security_check()
        
        # レポート出力
        if args.report:
            report = checker.generate_report()
            with open(args.report, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n📄 レポートを保存: {args.report}")
        
        # CI環境での終了コード
        if args.ci:
            sys.exit(0 if is_safe else 1)
        
        # 対話モード
        if not is_safe:
            if input("\n修正せずにコミットを続行しますか？ [y/N]: ").lower() != 'y':
                print("コミットをキャンセルしました")
                sys.exit(1)
        
        return is_safe
        
    except KeyboardInterrupt:
        print("\n\n🛑 チェックが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()