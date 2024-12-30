import sqlite3
import hashlib
from datetime import datetime
import os
import logging
import uuid
import csv

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
            
            # 创建唯一引
            cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_message_unique 
            ON messages(chat_id, sender_name, send_time, content)
            ''')
            
            conn.commit()
        except Exception as e:
            self.logger.error(f"初始化数据库失败: {e}")
        finally:
            conn.close()
        
    def get_chat_id(self, chat_name, chat_type, user_input_name=None):
        """获取或创建chat_id
        :param chat_name: 自动获取的聊天名称
        :param chat_type: 聊天类型
        :param user_input_name: 用户输入的聊天名称
        """
        # 确定最终使用的聊天名称
        final_name = chat_name
        if chat_name == "聊天信息" and user_input_name:
            final_name = user_input_name
            self.logger.info(f"使用用户输入的名称: {user_input_name}")
        
        # 使用chat_name生成chat_id
        chat_id = hashlib.md5(f"{final_name}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否存在
            cursor.execute("SELECT chat_id, chat_name FROM chats WHERE chat_name = ?", (final_name,))
            existing = cursor.fetchone()
            
            if existing:
                # 如果存在，返回已有的chat_id
                self.logger.info(f"使用已有会话: chat_id={existing[0]}, name={existing[1]}")
                return existing[0]
            else:
                # 创建新记录
                cursor.execute(
                    "INSERT INTO chats (chat_id, chat_type, chat_name) VALUES (?, ?, ?)",
                    (chat_id, chat_type, final_name)
                )
                conn.commit()
                self.logger.info(f"创建新会话: chat_id={chat_id}, name={final_name}")
                return chat_id
        finally:
            conn.close()
        
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
        """获取所有聊天对象"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT c.chat_id, c.chat_type, c.chat_name,
                       COUNT(m.msg_id) as msg_count,
                       MAX(m.send_time) as last_active
                FROM chats c
                LEFT JOIN messages m ON c.chat_id = m.chat_id
                GROUP BY c.chat_id
                ORDER BY last_active DESC
            ''')
            
            chats = []
            for row in cursor.fetchall():
                chats.append({
                    'chat_id': row[0],
                    'chat_type': row[1],
                    'chat_name': row[2],
                    'msg_count': row[3],
                    'last_active': row[4]
                })
            return chats
        except Exception as e:
            self.logger.error(f"获取聊天列表失败: {str(e)}")
            return []
        finally:
            conn.close()
        
    def get_chat_by_name(self, chat_name):
        """根据chat_name查询会话，支持模糊匹配"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT chat_id, chat_type FROM chats WHERE chat_name LIKE ?", 
                (f"%{chat_name}%",)
            )
            results = cursor.fetchall()
            if results:
                return [{
                    'chat_id': row[0],
                    'chat_name': chat_name,
                    'chat_type': row[1]
                } for row in results]
            return []
        finally:
            conn.close()
            
    def create_chat(self, chat_name, chat_type=1):
        """创建新的会话记录"""
        if not chat_name:
            raise ValueError("聊天名称不能为空")
        
        # 使用chat_name生成chat_id
        chat_id = hashlib.md5(f"{chat_name}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否存在
            cursor.execute("SELECT chat_id, chat_name FROM chats WHERE chat_name = ?", (chat_name,))
            existing = cursor.fetchone()
            
            if existing:
                # 如果存在，返回已有的信息
                self.logger.info(f"使用已有会话: chat_id={existing[0]}, name={existing[1]}")
                return existing[0], existing[1]
            
            # 创建新记录
            cursor.execute(
                "INSERT INTO chats (chat_id, chat_type, chat_name) VALUES (?, ?, ?)",
                (chat_id, chat_type, chat_name)
            )
            conn.commit()
            self.logger.info(f"创建新会话: chat_id={chat_id}, name={chat_name}")
            return chat_id, chat_name
        finally:
            conn.close()
            
    def update_chat_name(self, chat_id, new_name):
        """更新会话名称，处理名称冲突"""
        # 检查新名称是否与其他聊天对象冲突
        existing = self.get_chat_by_name(new_name)
        if existing and any(chat['chat_id'] != chat_id for chat in existing):
            # 如果存在相同名称，添加数字后缀
            base_name = new_name
            counter = 1
            while existing and any(chat['chat_id'] != chat_id for chat in existing):
                new_name = f"{base_name}_{counter}"
                existing = self.get_chat_by_name(new_name)
                counter += 1
            self.logger.info(f"处理名称冲突: {base_name} -> {new_name}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE chats SET chat_name = ? WHERE chat_id = ?",
                (new_name, chat_id)
            )
            conn.commit()
            self.logger.info(f"更新会话名称: chat_id={chat_id}, new_name={new_name}")
            return new_name
        finally:
            conn.close()
            
    def get_chat_messages(self, chat_id):
        """获取指定聊天的所有消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT msg_id, chat_id, sender_name, send_time, content, msg_type
                FROM messages
                WHERE chat_id = ?
                ORDER BY send_time DESC
            ''', (chat_id,))
            
            messages = []
            for row in cursor.fetchall():
                # 处理时间格式
                try:
                    # 先尝试带微秒的格式
                    send_time = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        # 再尝试不带微秒的格式
                        send_time = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S')
                    except ValueError as e:
                        self.logger.error(f"无法解析时间格式: {row[3]}, {str(e)}")
                        continue
                
                messages.append({
                    'msg_id': row[0],
                    'chat_id': row[1],
                    'sender_name': row[2],
                    'send_time': send_time,
                    'content': row[4],
                    'msg_type': row[5]
                })
            return messages
        except Exception as e:
            self.logger.error(f"获取聊天消息失败: {str(e)}")
            return []
        finally:
            conn.close()
            
    def get_chat_by_id(self, chat_id):
        """根据ID获取聊天对象信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT chat_id, chat_type, chat_name
            FROM chats 
            WHERE chat_id = ?
            ''', (chat_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'chat_id': row[0],
                    'chat_type': row[1],
                    'chat_name': row[2]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"获取聊天对象信息失败: {str(e)}")
            raise
        finally:
            conn.close()
            
    def add_message(self, chat_id, msg_type, content, sender_name, send_time):
        """添加新消息"""
        if sender_name == '未知发送者':
            return False, "跳过未知发送者的消息"
        
        # 生成唯一的msg_id
        msg_id = hashlib.md5(f"{chat_id}_{sender_name}_{send_time}_{content[:50]}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入新消息
            cursor.execute('''
            INSERT INTO messages (msg_id, chat_id, msg_type, content, sender_name, send_time)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                msg_id,
                chat_id,
                msg_type,
                content,
                sender_name,
                send_time
            ))
            conn.commit()
            self.logger.debug(f"成功保存消息: {content[:20]}...")
            return True, ""
        except Exception as e:
            self.logger.error(f"保存消息失败: {e}")
            return False, str(e)
        finally:
            conn.close()
            
    def export_chat(self, chat_id, output_path=None, start_date=None, end_date=None):
        """导出聊天记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 准备查询条件
            query_conditions = ["chat_id = ?"]
            query_params = [chat_id]
            
            if start_date:
                query_conditions.append("send_time >= ?")
                query_params.append(start_date)
            if end_date:
                query_conditions.append("send_time <= ?")
                query_params.append(end_date)
            
            # 构建查询语句
            query = f"""
                SELECT sender_name, send_time, content, msg_type, file_id
                FROM messages 
                WHERE {' AND '.join(query_conditions)}
                ORDER BY send_time ASC
            """
            
            cursor.execute(query, query_params)
            messages = cursor.fetchall()
            
            if not messages:
                return False, "未找到聊天记录"
            
            # 如果未指定输出路径，生成默认路径
            if not output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"chat_export_{timestamp}.csv"
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            
            # 写入CSV文件
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['发送者', '发送时间', '内容', '消息类型', '文件ID'])
                
                for msg in messages:
                    sender_name, send_time, content, msg_type, file_id = msg
                    
                    # 统一时间格式为 YYYY-MM-DD HH:MM:SS
                    try:
                        if isinstance(send_time, str):
                            dt = datetime.strptime(send_time, '%Y-%m-%d %H:%M:%S.%f')
                        else:
                            dt = send_time
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        self.logger.error(f"时间格式转换失败: {send_time}, 错误: {e}")
                        formatted_time = send_time  # 保持原始格式
                    
                    writer.writerow([
                        sender_name,
                        formatted_time,
                        content,
                        msg_type,
                        file_id or ''
                    ])
                    
            self.logger.info(f"导出完成: {output_path}")
            return True, output_path
            
        except Exception as e:
            self.logger.error(f"导出失败: {e}")
            return False, str(e)
        finally:
            conn.close()
            
    def get_message_count(self, chat_id=None):
        """获取消息数量
        
        Args:
            chat_id: 聊天ID，如果为None则返回所有消息数量
            
        Returns:
            int: 消息数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if chat_id:
                cursor.execute(
                    "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
                    (chat_id,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM messages")
                
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            self.logger.error(f"获取消息数量失败: {str(e)}")
            return 0 