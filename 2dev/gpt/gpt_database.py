"""
GPT 账号数据库管理模块
- 独立的 GPT 账号表
- 账号 CRUD 操作
- 订阅状态管理
"""
import sqlite3
import os
import sys
import threading

# 数据库路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
DB_PATH = os.path.join(BASE_DIR, "accounts.db")

lock = threading.Lock()


class GPTDBManager:
    """GPT 账号数据库管理器"""
    
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def init_db():
        """初始化 GPT 账号表"""
        with lock:
            conn = GPTDBManager.get_connection()
            cursor = conn.cursor()
            
            # 创建 GPT 账号表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gpt_accounts (
                    email TEXT PRIMARY KEY,
                    password TEXT,
                    secret_key TEXT,
                    status TEXT DEFAULT 'pending',
                    subscription_type TEXT,
                    card_number TEXT,
                    message TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建绑卡记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gpt_bind_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    card_number TEXT,
                    subscription_type TEXT,
                    bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success INTEGER DEFAULT 0,
                    message TEXT,
                    FOREIGN KEY (email) REFERENCES gpt_accounts(email)
                )
            ''')
            
            conn.commit()
            conn.close()
        
        print("[GPT DB] 数据库初始化完成")
    
    @staticmethod
    def load_from_file(file_path=None):
        """
        从文件加载 GPT 账号
        格式: email----password----secret
        """
        if file_path is None:
            file_path = os.path.join(BASE_DIR, "gpt", "gpt_accounts.txt")
        
        if not os.path.exists(file_path):
            print(f"[GPT DB] 账号文件不存在: {file_path}")
            return 0
        
        count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('----')
                    email = parts[0].strip() if len(parts) > 0 else None
                    password = parts[1].strip() if len(parts) > 1 else None
                    secret = parts[2].strip() if len(parts) > 2 else None
                    
                    if email:
                        GPTDBManager.upsert_account(email, password, secret)
                        count += 1
            
            print(f"[GPT DB] 从文件导入 {count} 个账号")
        except Exception as e:
            print(f"[GPT DB] 导入失败: {e}")
        
        return count
    
    @staticmethod
    def upsert_account(email, password=None, secret_key=None, status=None, 
                       subscription_type=None, card_number=None, message=None):
        """插入或更新账号"""
        if not email:
            return
        
        try:
            with lock:
                conn = GPTDBManager.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM gpt_accounts WHERE email = ?", (email,))
                exists = cursor.fetchone()
                
                if exists:
                    fields = []
                    values = []
                    if password is not None: 
                        fields.append("password = ?"); values.append(password)
                    if secret_key is not None: 
                        fields.append("secret_key = ?"); values.append(secret_key)
                    if status is not None: 
                        fields.append("status = ?"); values.append(status)
                    if subscription_type is not None: 
                        fields.append("subscription_type = ?"); values.append(subscription_type)
                    if card_number is not None: 
                        fields.append("card_number = ?"); values.append(card_number)
                    if message is not None: 
                        fields.append("message = ?"); values.append(message)
                    
                    if fields:
                        fields.append("updated_at = CURRENT_TIMESTAMP")
                        values.append(email)
                        sql = f"UPDATE gpt_accounts SET {', '.join(fields)} WHERE email = ?"
                        cursor.execute(sql, values)
                else:
                    cursor.execute('''
                        INSERT INTO gpt_accounts (email, password, secret_key, status, subscription_type, card_number, message)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (email, password, secret_key, status or 'pending', subscription_type, card_number, message))
                
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[GPT DB ERROR] upsert_account: {e}")
    
    @staticmethod
    def update_status(email, status, message=None):
        """更新账号状态"""
        GPTDBManager.upsert_account(email, status=status, message=message)
    
    @staticmethod
    def get_all_accounts():
        """获取所有账号"""
        with lock:
            conn = GPTDBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gpt_accounts ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_accounts_by_status(status):
        """按状态获取账号"""
        with lock:
            conn = GPTDBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gpt_accounts WHERE status = ?", (status,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_account(email):
        """获取单个账号信息"""
        with lock:
            conn = GPTDBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gpt_accounts WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
    
    @staticmethod
    def delete_account(email):
        """删除账号"""
        try:
            with lock:
                conn = GPTDBManager.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM gpt_accounts WHERE email = ?", (email,))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"[GPT DB ERROR] delete_account: {e}")
            return False
    
    @staticmethod
    def record_bind(email, card_number, subscription_type, success, message=None):
        """记录绑卡操作"""
        try:
            with lock:
                conn = GPTDBManager.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gpt_bind_records (email, card_number, subscription_type, success, message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, card_number, subscription_type, 1 if success else 0, message))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[GPT DB ERROR] record_bind: {e}")
    
    @staticmethod
    def get_bind_records(email=None):
        """获取绑卡记录"""
        with lock:
            conn = GPTDBManager.get_connection()
            cursor = conn.cursor()
            if email:
                cursor.execute("SELECT * FROM gpt_bind_records WHERE email = ? ORDER BY bind_time DESC", (email,))
            else:
                cursor.execute("SELECT * FROM gpt_bind_records ORDER BY bind_time DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_card_usage_count(card_number):
        """获取卡片使用次数"""
        with lock:
            conn = GPTDBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM gpt_bind_records WHERE card_number = ? AND success = 1", 
                (card_number,)
            )
            row = cursor.fetchone()
            conn.close()
            return row['count'] if row else 0
    
    @staticmethod
    def export_to_file(file_path=None):
        """导出账号到文件"""
        if file_path is None:
            file_path = os.path.join(BASE_DIR, "gpt", "gpt_accounts_export.txt")
        
        try:
            accounts = GPTDBManager.get_all_accounts()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# GPT 账号导出\n")
                f.write("# 格式: email----password----secret----status----subscription\n\n")
                for acc in accounts:
                    line = acc['email']
                    if acc.get('password'):
                        line += f"----{acc['password']}"
                    if acc.get('secret_key'):
                        line += f"----{acc['secret_key']}"
                    line += f"  # {acc.get('status', '')} | {acc.get('subscription_type', '')}"
                    f.write(line + "\n")
            
            print(f"[GPT DB] 导出 {len(accounts)} 个账号到 {file_path}")
            return True
        except Exception as e:
            print(f"[GPT DB ERROR] export_to_file: {e}")
            return False


# 初始化
GPTDBManager.init_db()


if __name__ == "__main__":
    print("GPT Database Module")
    print("=" * 40)
    
    # 测试
    accounts = GPTDBManager.get_all_accounts()
    print(f"当前有 {len(accounts)} 个 GPT 账号")
