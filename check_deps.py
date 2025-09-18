#!/usr/bin/env python3
"""
独立的依赖检查脚本
可以在项目的任何时候运行来检查依赖状态
"""

import sys
import os

def main():
    """主函数"""
    print("🔍 Telegram 签到机器人 - 依赖检查")
    print("=" * 50)
    
    # 检查是否在正确目录
    if not os.path.exists('requirements.txt'):
        print("❌ 请在项目根目录运行此脚本")
        print("   (找不到 requirements.txt 文件)")
        sys.exit(1)
    
    # 检查关键文件
    if not os.path.exists('utils/dependency_checker.py'):
        print("❌ 找不到依赖检查模块")
        print("   请确保项目文件完整")
        sys.exit(1)
    
    try:
        # 导入依赖检查器
        sys.path.insert(0, '.')
        from utils.dependency_checker import quick_check
        
        # 执行检查
        success = quick_check()
        
        if success:
            print("\n🎉 检查完成！")
            print("💡 现在可以运行: python main.py")
        else:
            print("\n❌ 检查失败！")
            print("💡 请解决上述问题后重试")
            print("   或运行: python install.py")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请确保项目文件完整")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
