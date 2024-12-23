import pandas as pd
import json
from datetime import datetime, timedelta
import os
import logging
from collections import Counter
import jieba
import sqlite3

class DataAnalyzer:
    def __init__(self, db_path="data/wx_chat.db", export_path="exports"):
        self.db_path = db_path
        self.export_path = export_path
        os.makedirs(export_path, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
    def export_chat(self, chat_id=None, start_time=None, end_time=None, format='csv'):
        """导出聊天记录"""
        conn = sqlite3.connect(self.db_path)
        
        # 构建查询条件
        conditions = []
        params = []
        if chat_id:
            conditions.append("m.chat_id = ?")
            params.append(chat_id)
        if start_time:
            conditions.append("m.send_time >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("m.send_time <= ?")
            params.append(end_time)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 获取数据
        query = f"""
        SELECT 
            m.msg_id,
            m.chat_id,
            c.chat_name,
            c.chat_type,
            m.msg_type,
            m.content,
            m.sender_name,
            m.send_time
        FROM messages m
        JOIN chats c ON m.chat_id = c.chat_id
        WHERE {where_clause}
        ORDER BY m.send_time
        """
        
        try:
            df = pd.read_sql_query(query, conn, params=params)
            
            # 导出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_export_{timestamp}"
            
            if format == 'csv':
                export_file = os.path.join(self.export_path, f"{filename}.csv")
                df.to_csv(export_file, index=False, encoding='utf-8-sig')
            else:
                export_file = os.path.join(self.export_path, f"{filename}.json")
                df.to_json(export_file, orient='records', force_ascii=False, indent=2)
                
            self.logger.info(f"导出完成: {export_file}")
            return export_file
            
        except Exception as e:
            self.logger.error(f"导出失败: {e}")
            raise
        finally:
            conn.close()
    
    def analyze_chat(self, chat_id=None, days=30):
        """分析聊天记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now() - timedelta(days=days)
        
        # 基础查询条件
        conditions = ["send_time >= ?"]
        params = [start_time]
        if chat_id:
            conditions.append("chat_id = ?")
            params.append(chat_id)
            
        where_clause = " AND ".join(conditions)
        
        # 1. 消息统计
        cursor.execute(f"""
        SELECT 
            COUNT(*) as total_messages,
            COUNT(DISTINCT sender_name) as unique_senders,
            COUNT(DISTINCT date(send_time)) as active_days,
            AVG(LENGTH(content)) as avg_length
        FROM messages
        WHERE {where_clause}
        """, params)
        
        stats = dict(zip(['total_messages', 'unique_senders', 'active_days', 'avg_length'], 
                        cursor.fetchone()))
        
        # 2. 活跃用户排名
        cursor.execute(f"""
        SELECT sender_name, COUNT(*) as msg_count
        FROM messages
        WHERE {where_clause}
        GROUP BY sender_name
        ORDER BY msg_count DESC
        LIMIT 10
        """, params)
        
        active_users = [dict(zip(['name', 'count'], row)) for row in cursor.fetchall()]
        
        # 3. 消息类型分布
        cursor.execute(f"""
        SELECT msg_type, COUNT(*) as type_count
        FROM messages
        WHERE {where_clause}
        GROUP BY msg_type
        """, params)
        
        msg_types = {
            1: '文本',
            2: '图片',
            3: '视频',
            4: '文件'
        }
        type_stats = {msg_types.get(row[0], '其他'): row[1] 
                     for row in cursor.fetchall()}
        
        # 4. 关键词提取（仅处理文本消息）
        cursor.execute(f"""
        SELECT content
        FROM messages
        WHERE {where_clause} AND msg_type = 1
        """, params)
        
        all_text = ' '.join(row[0] for row in cursor.fetchall() if row[0])
        words = jieba.cut(all_text)
        word_count = Counter(w for w in words if len(w) > 1)
        top_keywords = dict(word_count.most_common(20))
        
        # 5. 时间分布
        cursor.execute(f"""
        SELECT strftime('%H', send_time) as hour, COUNT(*) as count
        FROM messages
        WHERE {where_clause}
        GROUP BY hour
        ORDER BY hour
        """, params)
        
        time_dist = dict(cursor.fetchall())
        
        analysis_result = {
            'basic_stats': stats,
            'active_users': active_users,
            'message_types': type_stats,
            'top_keywords': top_keywords,
            'time_distribution': time_dist
        }
        
        return analysis_result
    
    def clean_data(self, before_date=None, chat_id=None):
        """清理聊天记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if before_date:
            conditions.append("send_time < ?")
            params.append(before_date)
        if chat_id:
            conditions.append("chat_id = ?")
            params.append(chat_id)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        try:
            # 获取要删除的消息数量
            cursor.execute(f"SELECT COUNT(*) FROM messages WHERE {where_clause}", params)
            count = cursor.fetchone()[0]
            
            # 删除消息
            cursor.execute(f"DELETE FROM messages WHERE {where_clause}", params)
            conn.commit()
            
            self.logger.info(f"已清理 {count} 条消息")
            return count
            
        except Exception as e:
            self.logger.error(f"清理数据失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close() 