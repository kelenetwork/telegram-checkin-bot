"""
依赖检查工具模块
提供完整的依赖管理功能
"""
import sys
import subprocess
import pkg_resources
import importlib.util
import os

class DependencyChecker:
    """依赖检查器"""
    
    REQUIRED_PYTHON_VERSION = (3, 8)
    REQUIREMENTS_FILE = "requirements.txt"
    
    def __init__(self):
        self.missing_packages = []
        self.failed_packages = []
    
    def check_python_version(self) -> bool:
        """检查 Python 版本"""
        current = sys.version_info[:2]
        required = self.REQUIRED_PYTHON_VERSION
        
        print(f"🐍 Python 版本检查...")
        if current >= required:
            print(f"  ✅ Python {current[0]}.{current[1]} (需要 {required[0]}.{required[1]}+)")
            return True
        else:
            print(f"  ❌ Python {current[0]}.{current[1]} (需要 {required[0]}.{required[1]}+)")
            print(f"  请升级到 Python {required[0]}.{required[1]} 或更高版本")
            return False
    
    def get_requirements(self) -> list:
        """读取依赖列表"""
        if not os.path.exists(self.REQUIREMENTS_FILE):
            print(f"❌ 找不到 {self.REQUIREMENTS_FILE} 文件")
            return []
        
        try:
            with open(self.REQUIREMENTS_FILE, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            
            # 过滤注释和空行
            requirements = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
            
            return requirements
        except Exception as e:
            print(f"❌ 读取 {self.REQUIREMENTS_FILE} 失败: {e}")
            return []
    
    def check_package(self, package: str) -> bool:
        """检查单个包是否已安装"""
        try:
            # 处理版本号
            package_name = package.split('>=')[0].split('==')[0].split('<')[0].strip()
            pkg_resources.require(package)
            return True
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
            return False
        except Exception:
            return False
    
    def install_package(self, package: str) -> bool:
        """安装单个包"""
        try:
            print(f"    📦 正在安装 {package}...", end="", flush=True)
            
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(" ✅")
                return True
            else:
                print(" ❌")
                print(f"    错误信息: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print(" ❌ (超时)")
            return False
        except Exception as e:
            print(f" ❌ ({e})")
            return False
    
    def check_and_install_packages(self) -> bool:
        """检查并安装所有依赖包"""
        requirements = self.get_requirements()
        if not requirements:
            print("❌ 没有找到依赖包列表")
            return False
        
        print(f"\n📦 检查 {len(requirements)} 个依赖包...")
        
        # 检查阶段
        for package in requirements:
            if self.check_package(package):
                print(f"  ✅ {package}")
            else:
                self.missing_packages.append(package)
                print(f"  ❌ {package}")
        
        # 安装阶段
        if self.missing_packages:
            print(f"\n🔧 发现 {len(self.missing_packages)} 个缺失包，开始安装...")
            
            for package in self.missing_packages:
                if not self.install_package(package):
                    self.failed_packages.append(package)
            
            # 安装后再次检查
            if self.failed_packages:
                print(f"\n❌ {len(self.failed_packages)} 个包安装失败:")
                for package in self.failed_packages:
                    print(f"  • {package}")
                print("\n请手动安装失败的包:")
                print(f"pip install {' '.join(self.failed_packages)}")
                return False
            else:
                print("\n✅ 所有缺失包安装成功!")
        else:
            print("✅ 所有依赖包都已安装")
        
        return True
    
    def check_system_requirements(self) -> bool:
        """检查系统要求"""
        print("🔍 系统环境检查...")
        
        # 检查是否有网络连接
        try:
            import urllib.request
            urllib.request.urlopen('https://pypi.org', timeout=5)
            print("  ✅ 网络连接正常")
        except:
            print("  ⚠️ 网络连接可能有问题，安装包可能失败")
        
        # 检查pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], 
                         capture_output=True, check=True)
            print("  ✅ pip 可用")
        except:
            print("  ❌ pip 不可用")
            return False
        
        return True
    
    def run_full_check(self) -> bool:
        """运行完整的依赖检查"""
        print("🚀 开始系统依赖检查")
        print("=" * 50)
        
        # 检查系统环境
        if not self.check_system_requirements():
            return False
        
        # 检查Python版本
        if not self.check_python_version():
            return False
        
        # 检查并安装包
        if not self.check_and_install_packages():
            return False
        
        print("\n🎉 依赖检查完成！所有要求都已满足")
        return True

# 便捷函数
def quick_check() -> bool:
    """快速依赖检查"""
    checker = DependencyChecker()
    return checker.run_full_check()

if __name__ == "__main__":
    # 直接运行此文件时进行检查
    success = quick_check()
    if not success:
        print("\n💡 提示: 运行 'python install.py' 获取更多帮助")
        sys.exit(1)
    else:
        print("\n✨ 系统准备就绪！")

