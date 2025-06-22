#!/usr/bin/env python3
"""
クロスプラットフォーム対応の警告音・通知音システム
WSL/Linux/macOS/Windows環境で動作する音響アラートシステム
"""

import os
import sys
import subprocess
import platform
import tempfile
import time
from pathlib import Path

class AlertSystem:
    """警告音・通知音システム"""
    
    def __init__(self):
        self.system = platform.system()
        self.temp_dir = Path(tempfile.gettempdir())
        
    def play_system_beep(self, count=1, interval=0.5):
        """システムビープ音を再生"""
        try:
            if self.system == "Darwin":  # macOS
                for _ in range(count):
                    subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=True)
                    if count > 1 and _ < count - 1:
                        time.sleep(interval)
            elif self.system == "Linux":  # Linux/WSL
                # ターミナルベル音
                for _ in range(count):
                    print("\a", end="", flush=True)  # ASCII bell
                    if count > 1 and _ < count - 1:
                        time.sleep(interval)
            elif self.system == "Windows":  # Windows
                import winsound
                for _ in range(count):
                    winsound.Beep(800, 200)  # 800Hz, 200ms
                    if count > 1 and _ < count - 1:
                        time.sleep(interval)
        except Exception as e:
            print(f"システムビープエラー: {e}")
    
    def play_warning_sound(self):
        """警告音を再生（Sosumi相当）"""
        try:
            if self.system == "Darwin":  # macOS
                subprocess.run(["afplay", "/System/Library/Sounds/Sosumi.aiff"], check=True)
            elif self.system == "Linux":  # Linux/WSL
                # ffplayで警告音を生成・再生
                self._generate_warning_tone()
            elif self.system == "Windows":  # Windows
                import winsound
                # 警告音のパターン
                winsound.Beep(1000, 200)
                time.sleep(0.1)
                winsound.Beep(800, 300)
        except Exception as e:
            print(f"警告音エラー: {e}")
            # フォールバック: 複数ビープ
            self.play_system_beep(count=3, interval=0.2)
    
    def play_success_sound(self):
        """成功音を再生（Tink相当）"""
        try:
            if self.system == "Darwin":  # macOS
                subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=True)
            elif self.system == "Linux":  # Linux/WSL
                # ffplayで成功音を生成・再生
                self._generate_success_tone()
            elif self.system == "Windows":  # Windows
                import winsound
                winsound.Beep(1200, 200)  # 高音の短いビープ
        except Exception as e:
            print(f"成功音エラー: {e}")
            # フォールバック: 単一ビープ
            self.play_system_beep(count=1)
    
    def _generate_warning_tone(self):
        """Linux/WSL用の警告音をffplayで生成・再生"""
        try:
            # 実際の音声ファイルを使用
            error_file = "/home/conta/media/error.wav"
            if os.path.exists(error_file):
                subprocess.run([
                    "ffplay", "-nodisp", "-autoexit", "-v", "quiet",
                    "-af", "volume=0.5", error_file
                ], check=True, timeout=3)
            else:
                # フォールバック: 生成音
                subprocess.run([
                    "ffplay", "-f", "lavfi", "-i", "sine=frequency=1000:duration=0.5",
                    "-nodisp", "-autoexit"
                ], check=True, timeout=2, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # フォールバック: ターミナルベル
            print("\a\a\a", end="", flush=True)
    
    def _generate_success_tone(self):
        """Linux/WSL用の成功音をffplayで生成・再生"""
        try:
            # 実際の音声ファイルを使用
            notice_file = "/home/conta/media/notice.wav"
            if os.path.exists(notice_file):
                subprocess.run([
                    "ffplay", "-nodisp", "-autoexit", "-v", "quiet",
                    "-af", "volume=0.4", notice_file
                ], check=True, timeout=3)
            else:
                # フォールバック: 生成音
                subprocess.run([
                    "ffplay", "-f", "lavfi", "-i", "sine=frequency=1200:duration=0.3",
                    "-nodisp", "-autoexit"
                ], check=True, timeout=1, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # フォールバック: ターミナルベル
            print("\a", end="", flush=True)

def test_alert_system():
    """警告音システムのテスト"""
    alert = AlertSystem()
    
    print(f"🔊 {alert.system}環境での警告音システムテスト")
    print()
    
    print("1. 成功音テスト...")
    alert.play_success_sound()
    time.sleep(1)
    
    print("2. 警告音テスト...")
    alert.play_warning_sound()
    time.sleep(1)
    
    print("3. システムビープテスト...")
    alert.play_system_beep(count=2, interval=0.3)
    
    print("✅ 警告音システムテスト完了")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        alert = AlertSystem()
        
        if sys.argv[1] == "warning":
            print("⚠️ 警告音再生")
            alert.play_warning_sound()
        elif sys.argv[1] == "success":
            print("✅ 成功音再生")
            alert.play_success_sound()
        elif sys.argv[1] == "beep":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            print(f"🔔 システムビープ({count}回)")
            alert.play_system_beep(count=count)
        elif sys.argv[1] == "test":
            test_alert_system()
        else:
            print("使用方法: python alert_system.py [warning|success|beep|test] [count]")
    else:
        test_alert_system()