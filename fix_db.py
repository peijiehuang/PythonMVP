import sqlite3
import os

def fix():
    db_path = 'database.db'
    if not os.path.exists(db_path):
        print("未发现数据库文件。")
        return

    print(f"正在修复数据库: {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 尝试增加列
        cursor.execute('ALTER TABLE tasklog ADD COLUMN output TEXT')
        conn.commit()
        print("✅ 成功为 tasklog 表增加 output 字段。")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ 字段已存在，无需修改。")
        else:
            print(f"❌ 错误: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix()
