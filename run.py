import os
import sys
import subprocess

"""
Cosmic MVP 便捷运行脚本
封装了常用的开发指令。
"""

def print_help():
    print("\n--- Cosmic MVP 便捷运行脚本 ---")
    print("用法: python run.py [命令]")
    print("-" * 30)
    print("  dev   : 🚀 启动开发服务器")
    print("  test  : 🧪 运行全量异步自动化测试")
    print("  mig   : 📜 生成并执行数据库迁移 (Alembic)")
    print("  help  : ❓ 显示此帮助信息")
    print("-" * 30)

def run_command(command: str):
    """执行 Shell 命令并捕获异常"""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 命令执行失败: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1].lower()

    if cmd == "dev":
        print("🚀 正在启动服务器...")
        print("💡 如果是首次运行，请访问 http://localhost:8000/install 进行安装向导。")
        run_command("uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    
    elif cmd == "test":
        print("🧪 正在运行异步测试套件...")
        run_command("pytest -v")
    
    elif cmd == "mig":
        print("📜 正在处理数据库结构同步...")
        msg = input("请输入此次迁移的简短描述: ") or "manual_migration"
        run_command(f'alembic revision --autogenerate -m "{msg}"')
        run_command("alembic upgrade head")
        print("✅ 数据库已同步。")
    
    else:
        print_help()

if __name__ == "__main__":
    main()
