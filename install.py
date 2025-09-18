#!/usr/bin/env python3
"""
自动安装脚本
检查并安装项目依赖，创建必要的目录和配置文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class Colors:
    """终端颜色常量"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class Installer:
    """安装器类"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.python_executable = sys.executable
        
    def print_colored(self, text: str, color: str = Colors.WHITE):
        """打印彩色文本"""
        print(f"{color}{text}{Colors.END}")
    
    def print_banner(self):
        """打印横幅"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║            🤖 Telegram 自动签到机器人 安装程序              ║
║                                                              ║
║                      Auto Checkin Bot                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.print_colored(banner, Colors.CYAN)
    
    def check_python_version(self):
        """检查Python版本"""
        self.print_colored("\n🐍 检查Python版本...", Colors.BLUE)
        
        if sys.version_info < (3, 8):
            self.print_colored(
                f"❌ 需要Python 3.8或更高版本，当前版本: {sys.version}",
                Colors.RED
            )
            return False
        
        self.print_colored(
            f"✅ Python版本检查通过: {sys.version.split()[0]}",
            Colors.GREEN
        )
        return True
    
    def check_pip(self):
        """检查pip是否可用"""
        self.print_colored("📦 检查pip...", Colors.BLUE)
        
        try:
            subprocess.run([self.python_executable, "-m", "pip", "--version"], 
                         check=True, capture_output=True)
            self.print_colored("✅ pip可用", Colors.GREEN)
            return True
        except subprocess.CalledProcessError:
            self.print_colored("❌ pip不可用", Colors.RED)
            return False
    
    def install_requirements(self):
        """安装依赖包"""
        self.print_colored("\n📚 安装依赖包...", Colors.BLUE)
        
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            self.print_colored("❌ requirements.txt文件不存在", Colors.RED)
            return False
        
        try:
            cmd = [
                self.python_executable, "-m", "pip", "install", 
                "-r", str(requirements_file), "--upgrade"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_colored("✅ 依赖包安装完成", Colors.GREEN)
                return True
            else:
                self.print_colored("❌ 依赖包安装失败", Colors.RED)
                self.print_colored(f"错误信息: {result.stderr}", Colors.RED)
                return False
                
        except Exception as e:
            self.print_colored(f"❌ 安装依赖时发生错误: {e}", Colors.RED)
            return False
    
    def create_directories(self):
        """创建必要的目录"""
        self.print_colored("\n📁 创建项目目录...", Colors.BLUE)
        
        directories = [
            "data",
            "logs",
            "backups",
            "exports",
            "temp"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            try:
                dir_path.mkdir(exist_ok=True)
                self.print_colored(f"✅ 创建目录: {directory}", Colors.GREEN)
            except Exception as e:
                self.print_colored(f"❌ 创建目录 {directory} 失败: {e}", Colors.RED)
                return False
        
        return True
    
    def setup_config(self):
        """设置配置文件"""
        self.print_colored("\n⚙️ 设置配置文件...", Colors.BLUE)
        
        env_example = self.project_root / ".env.example"
        env_file = self.project_root / ".env"
        
        if not env_example.exists():
            self.print_colored("❌ .env.example文件不存在", Colors.RED)
            return False
        
        if not env_file.exists():
            try:
                shutil.copy2(env_example, env_file)
                self.print_colored("✅ 已创建.env配置文件", Colors.GREEN)
                self.print_colored(
                    "⚠️  请编辑.env文件，填入您的Telegram Bot配置信息",
                    Colors.YELLOW
                )
            except Exception as e:
                self.print_colored(f"❌ 创建配置文件失败: {e}", Colors.RED)
                return False
        else:
            self.print_colored("✅ .env配置文件已存在", Colors.GREEN)
        
        return True
    
    def check_dependencies(self):
        """检查关键依赖是否正确安装"""
        self.print_colored("\n🔍 检查关键依赖...", Colors.BLUE)
        
        critical_deps = [
            "telethon",
            "aiohttp",
            "asyncio",
            "sqlite3",
            "schedule",
            "requests",
            "beautifulsoup4",
            "python-dotenv"
        ]
        
        failed_deps = []
        
        for dep in critical_deps:
            try:
                if dep == "sqlite3":
                    import sqlite3
                elif dep == "asyncio":
                    import asyncio
                else:
                    __import__(dep)
                self.print_colored(f"✅ {dep}", Colors.GREEN)
            except ImportError:
                self.print_colored(f"❌ {dep}", Colors.RED)
                failed_deps.append(dep)
        
        if failed_deps:
            self.print_colored(
                f"\n❌ 以下依赖安装失败: {', '.join(failed_deps)}",
                Colors.RED
            )
            return False
        
        self.print_colored("✅ 所有关键依赖检查通过", Colors.GREEN)
        return True
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        self.print_colored("\n📝 创建启动脚本...", Colors.BLUE)
        
        # Windows启动脚本
        start_bat_content = """@echo off
echo 启动Telegram签到机器人...
python main.py
pause
"""
        
        # Linux/Mac启动脚本
        start_sh_content = """#!/bin/bash
echo "启动Telegram签到机器人..."
python3 main.py
"""
        
        try:
            # 创建Windows脚本
            with open(self.project_root / "start.bat", "w", encoding="utf-8") as f:
                f.write(start_bat_content)
            
            # 创建Linux/Mac脚本
            with open(self.project_root / "start.sh", "w", encoding="utf-8") as f:
                f.write(start_sh_content)
            
            # 设置Linux/Mac脚本为可执行
            if os.name != 'nt':
                os.chmod(self.project_root / "start.sh", 0o755)
            
            self.print_colored("✅ 启动脚本创建完成", Colors.GREEN)
            return True
            
        except Exception as e:
            self.print_colored(f"❌ 创建启动脚本失败: {e}", Colors.RED)
            return False
    
    def print_next_steps(self):
        """打印下一步操作指南"""
        self.print_colored("\n🎉 安装完成！", Colors.GREEN)
        self.print_colored("\n📋 接下来的步骤:", Colors.CYAN)
        
        steps = [
            "1. 编辑 .env 文件，填入您的 Telegram Bot Token 和其他配置",
            "2. 获取 Bot Token: 向 @BotFather 发送 /newbot 创建机器人",
            "3. 获取 API ID 和 Hash: 访问 https://my.telegram.org/apps",
            "4. 运行 python main.py 启动机器人",
            "5. 或者使用启动脚本: start.bat (Windows) 或 ./start.sh (Linux/Mac)"
        ]
        
        for step in steps:
            self.print_colored(f"   {step}", Colors.WHITE)
        
        self.print_colored("\n💡 提示:", Colors.YELLOW)
        self.print_colored("   - 首次运行需要登录Telegram账号", Colors.WHITE)
        self.print_colored("   - 建议在screen或tmux中运行以保持后台运行", Colors.WHITE)
        self.print_colored("   - 遇到问题请查看logs目录下的日志文件", Colors.WHITE)
        
        self.print_colored("\n🔗 相关链接:", Colors.BLUE)
        self.print_colored("   - Telegram Bot Father: https://t.me/BotFather", Colors.WHITE)
        self.print_colored("   - Telegram API: https://my.telegram.org/apps", Colors.WHITE)
        
    def run_installation(self):
        """运行完整安装流程"""
        self.print_banner()
        
        steps = [
            ("检查Python版本", self.check_python_version),
            ("检查pip", self.check_pip),
            ("安装依赖包", self.install_requirements),
            ("创建目录", self.create_directories),
            ("设置配置文件", self.setup_config),
            ("检查依赖", self.check_dependencies),
            ("创建启动脚本", self.create_startup_scripts)
        ]
        
        for step_name, step_func in steps:
            self.print_colored(f"\n{'='*60}", Colors.MAGENTA)
            self.print_colored(f"正在执行: {step_name}", Colors.MAGENTA)
            self.print_colored(f"{'='*60}", Colors.MAGENTA)
            
            if not step_func():
                self.print_colored(f"\n❌ 安装失败于步骤: {step_name}", Colors.RED)
                sys.exit(1)
        
        self.print_next_steps()


def main():
    """主函数"""
    installer = Installer()
    
    try:
        installer.run_installation()
    except KeyboardInterrupt:
        installer.print_colored("\n\n⏹️ 安装被用户中断", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        installer.print_colored(f"\n\n💥 安装过程中发生错误: {e}", Colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()

