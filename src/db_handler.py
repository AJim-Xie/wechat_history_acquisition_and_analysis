import sqlite3
import hashlib
from datetime import datetime
import os
import logging
import uuid

class DatabaseHandler:
    def __init__(self, db_path="data/wx_chat.db"):
        # 确保data目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        self.init_db()
        
    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建chats表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id VARCHAR(32) PRIMARY KEY,
                chat_type TINYINT,  -- 1:私聊 2:群聊
                chat_name VARCHAR(128)
            )
            ''')
            
            # 创建messages表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                msg_id VARCHAR(32) PRIMARY KEY,
                chat_id VARCHAR(32),
                msg_type TINYINT,
                content TEXT,
                sender_name VARCHAR(64),
                send_time TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
            ''')
            
            # 创建唯一索引
            cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_message_unique 
            ON messages(chat_id, sender_name, send_time, content)
            ''')
            
            conn.commit()
        except Exception as e:
            self.logger.error(f"初始化数据库失败: {e}")
        finally:
            conn.close()
        
    def get_chat_id(self, chat_name, chat_type):
        """获取或创建chat_id"""
        chat_id = hashlib.md5(f"{chat_name}_{chat_type}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否存在
        cursor.execute("SELECT chat_id FROM chats WHERE chat_id = ?", (chat_id,))
        if not cursor.fetchone():
            # 创建新记录
            cursor.execute(
                "INSERT INTO chats (chat_id, chat_type, chat_name) VALUES (?, ?, ?)",
                (chat_id, chat_type, chat_name)
            )
            conn.commit()
            self.logger.info(f"创建新会话: chat_id={chat_id}, name={chat_name}, type={'群聊' if chat_type == 2 else '私聊'}")
        else:
            self.logger.info(f"使用已有会话: chat_id={chat_id}, name={chat_name}, type={'群聊' if chat_type == 2 else '私聊'}")
            
        conn.close()
        return chat_id
        
    def save_message(self, chat_id, message):
        """保存消息"""
        # 使用更多字段生成消息ID
        msg_id = hashlib.md5(
            f"{chat_id}_{message['sender_name']}_{message['send_time']}_{message['content'][:100]}".encode()
        ).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 先检查消息是否存在
            cursor.execute('''
            SELECT msg_id FROM messages 
            WHERE chat_id = ? 
            AND sender_name = ? 
            AND send_time = ? 
            AND content = ?
            ''', (
                chat_id,
                message['sender_name'],
                message['send_time'],
                message['content']
            ))
            
            if cursor.fetchone():
                self.logger.debug(f"消息已存在，跳过: {message['content'][:20]}...")
                return
                
            # 插入新消息
            cursor.execute('''
            INSERT INTO messages (msg_id, chat_id, msg_type, content, sender_name, send_time)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                msg_id,
                chat_id,
                message['msg_type'],
                message['content'],
                message['sender_name'],
                message['send_time']
            ))
            conn.commit()
            self.logger.debug(f"成功保存消息: {message['content'][:20]}...")
            
        except sqlite3.IntegrityError:
            self.logger.debug(f"消息ID重复，跳过: {msg_id}")
        except Exception as e:
            self.logger.error(f"保存消息失败: {e}")
        finally:
            conn.close()
        
    def get_last_message_time(self, chat_id):
        """获取最后一条消息的时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT send_time FROM messages 
            WHERE chat_id = ? 
            ORDER BY send_time DESC 
            LIMIT 1
            ''', (chat_id,))
            
            result = cursor.fetchone()
            if result:
                return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S.%f')
            return None
        finally:
            conn.close()
        
    def get_all_chats(self):
        """获取所有会话列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT chat_id, chat_name, chat_type 
            FROM chats 
            ORDER BY chat_name
            ''')
            
            chats = []
            for row in cursor.fetchall():
                chats.append({
                    'chat_id': row[0],
                    'chat_name': row[1],
                    'chat_type': row[2]
                })
                
            self.logger.debug(f"获取到 {len(chats)} 个会话")
            return chats
            
        except Exception as e:
            self.logger.error(f"获取会话列表失败: {e}")
            return []
        finally:
            conn.close()
        
    def get_chat_by_name(self, chat_name):
        """根据chat_name查询会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT chat_id, chat_type FROM chats WHERE chat_name = ?", 
                (chat_name,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'chat_id': result[0],
                    'chat_name': chat_name,
                    'chat_type': result[1]
                }
            return None
        finally:
            conn.close()
            
    def create_chat(self, chat_name, chat_type=1):
        """创建新的会话记录"""
        chat_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO chats (chat_id, chat_type, chat_name) VALUES (?, ?, ?)",
                (chat_id, chat_type, chat_name)
            )
            conn.commit()
            self.logger.info(f"创建新会话: chat_id={chat_id}, name={chat_name}")
            return chat_id
        finally:
            conn.close()
            
    def update_chat_name(self, chat_id, new_name):
        """更新会话名称"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE chats SET chat_name = ? WHERE chat_id = ?",
                (new_name, chat_id)
            )
            conn.commit()
            self.logger.info(f"更新会话名称: chat_id={chat_id}, new_name={new_name}")
        finally:
            conn.close() 