import sqlite3
import hashlib
from datetime import datetime
import os
import logging

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
        
        # 创建chats表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id VARCHAR(32) PRIMARY KEY,
            chat_type TINYINT,  -- 1:私聊 2:群聊 3:公众号 4:系统账号
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
        
        conn.commit()
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
        msg_id = hashlib.md5(f"{chat_id}_{message['send_time']}_{message['content']}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
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
        except sqlite3.IntegrityError:
            # 消息已存在，忽略
            pass
        finally:
            conn.close() 