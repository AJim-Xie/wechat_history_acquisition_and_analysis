import pandas as pd
import json
from datetime import datetime, timedelta
import os
import logging
from collections import Counter
import jieba
import sqlite3
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import seaborn as sns
from collections import defaultdict
import jieba.analyse
import numpy as np
import networkx as nx
import graphviz
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import re
from src.dict_manager import DictManager

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class DataAnalyzer:
    def __init__(self, db, export_path="exports"):
        """
        初始化数据分析器
        :param db: DatabaseHandler实例
        :param export_path: 导出文件路径
        """
        self.db = db
        self.export_path = export_path
        os.makedirs(export_path, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
    def export_chat(self, chat_id=None, start_time=None, end_time=None, format='csv'):
        """导出聊天记录"""
        # 确保导出目录存在
        os.makedirs(self.export_path, exist_ok=True)
        
        conn = sqlite3.connect(self.db.db_path)
        
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
        conn = sqlite3.connect(self.db.db_path)
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
        
        # 新增：每日消息趋势
        cursor.execute(f"""
        SELECT date(send_time) as date, COUNT(*) as count
        FROM messages
        WHERE {where_clause}
        GROUP BY date
        ORDER BY date
        """, params)
        daily_trend = dict(cursor.fetchall())
        
        # 新增：互动分析（回复关系）
        cursor.execute(f"""
        SELECT m1.sender_name as from_user, 
               m2.sender_name as to_user,
               COUNT(*) as interaction_count
        FROM messages m1
        JOIN messages m2 ON m2.msg_id = (
            SELECT msg_id 
            FROM messages 
            WHERE send_time > m1.send_time 
            AND chat_id = m1.chat_id
            LIMIT 1
        )
        WHERE {where_clause.replace('send_time', 'm1.send_time')}
        GROUP BY from_user, to_user
        HAVING interaction_count >= 5
        ORDER BY interaction_count DESC
        LIMIT 20
        """, params)
        interactions = [dict(zip(['from_user', 'to_user', 'count'], row)) 
                       for row in cursor.fetchall()]
        
        # 新增：消息长度分布
        cursor.execute(f"""
        SELECT 
            CASE 
                WHEN LENGTH(content) <= 10 THEN '短消息(≤10)'
                WHEN LENGTH(content) <= 50 THEN '中等(11-50)'
                WHEN LENGTH(content) <= 200 THEN '长消息(51-200)'
                ELSE '超长消息(>200)'
            END as length_category,
            COUNT(*) as count
        FROM messages
        WHERE {where_clause} AND msg_type = 1
        GROUP BY length_category
        ORDER BY count DESC
        """, params)
        length_dist = dict(cursor.fetchall())
        
        # 新增：每周活跃度分析
        cursor.execute(f"""
        SELECT 
            CASE strftime('%w', send_time)
                WHEN '0' THEN '周日'
                WHEN '1' THEN '周一'
                WHEN '2' THEN '周二'
                WHEN '3' THEN '周三'
                WHEN '4' THEN '周四'
                WHEN '5' THEN '周五'
                WHEN '6' THEN '周六'
            END as weekday,
            COUNT(*) as count
        FROM messages
        WHERE {where_clause}
        GROUP BY weekday
        ORDER BY strftime('%w', send_time)
        """, params)
        weekly_activity = dict(cursor.fetchall())
        
        # 新增：表情符号使用统计
        cursor.execute(f"""
        SELECT content, COUNT(*) as count
        FROM messages
        WHERE {where_clause} 
        AND msg_type = 1
        AND content LIKE '%[%]%'
        GROUP BY content
        HAVING count >= 3
        ORDER BY count DESC
        LIMIT 20
        """, params)
        emoji_stats = dict(cursor.fetchall())
        
        analysis_result = {
            'basic_stats': stats,
            'active_users': active_users,
            'message_types': type_stats,
            'top_keywords': top_keywords,
            'time_distribution': time_dist,
            'daily_trend': daily_trend,
            'interactions': interactions,
            'length_distribution': length_dist,
            'weekly_activity': weekly_activity,
            'emoji_stats': emoji_stats
        }
        
        return analysis_result
    
    def clean_data(self, before_date=None, chat_id=None):
        """清理聊天记录"""
        conn = sqlite3.connect(self.db.db_path)
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
            
            # 清理无关联消息的chat记录
            cursor.execute("""
                DELETE FROM chats 
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM messages 
                    WHERE messages.chat_id = chats.chat_id
                )
            """)
            
            conn.commit()
            
            self.logger.info(f"已清理 {count} 条消息")
            return count
            
        except Exception as e:
            self.logger.error(f"清理数据失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close() 
    
    def query_messages(self, chat_id=None, start_time=None, end_time=None, limit=100):
        """查询聊天记录"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
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
        
        query = f"""
        SELECT 
            m.msg_id,
            c.chat_name,
            m.msg_type,
            m.content,
            m.sender_name,
            m.send_time
        FROM messages m
        JOIN chats c ON m.chat_id = c.chat_id
        WHERE {where_clause}
        ORDER BY m.send_time DESC
        LIMIT ?
        """
        params.append(limit)
        
        try:
            cursor.execute(query, params)
            messages = []
            for row in cursor.fetchall():
                try:
                    # 尝试多种时间格式
                    time_formats = [
                        '%Y-%m-%d %H:%M:%S.%f',  # 带微秒
                        '%Y-%m-%d %H:%M:%S',     # 不带微秒
                        '%Y-%m-%d %H:%M'         # 只有分钟
                    ]
                    
                    send_time = None
                    for time_format in time_formats:
                        try:
                            send_time = datetime.strptime(row[5], time_format)
                            break
                        except ValueError:
                            continue
                    
                    if send_time is None:
                        self.logger.warning(f"无法解析时间格式: {row[5]}")
                        continue
                    
                    messages.append({
                        'msg_id': row[0],
                        'chat_name': row[1],
                        'msg_type': row[2],
                        'content': row[3],
                        'sender_name': row[4],
                        'send_time': send_time
                    })
                except Exception as e:
                    self.logger.warning(f"处理消息记录时出错: {e}")
                    continue
                
            return messages
            
        except Exception as e:
            self.logger.error(f"查询消息失败: {e}")
            raise
        finally:
            conn.close()
    
    def get_all_chats(self):
        """获取所有聊天对象"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT chat_id, chat_type, chat_name
                FROM chats
                ORDER BY chat_name
            ''')
            
            chats = []
            for row in cursor.fetchall():
                chat_name = row[2]
                # 处理聊天名称
                if chat_name.endswith('聊天信息'):
                    chat_name = chat_name.replace('聊天信息', '').strip()
                
                chats.append({
                    'chat_id': row[0],
                    'chat_type': row[1],
                    'chat_name': chat_name
                })
            return chats
        finally:
            conn.close() 
    
    def get_basic_stats(self):
        """获取基础统计信息"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取总聊天数
            cursor.execute("SELECT COUNT(*) FROM chats")
            chat_count = cursor.fetchone()[0]
            
            # 获取总消息数
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            # 获取活跃用户数（不重复的sender_name）
            cursor.execute("SELECT COUNT(DISTINCT sender_name) FROM messages")
            user_count = cursor.fetchone()[0]
            
            return {
                'chat_count': chat_count,
                'message_count': message_count,
                'user_count': user_count
            }
            
        except Exception as e:
            self.logger.error(f"获取基础统计信息失败: {e}")
            return {
                'chat_count': 0,
                'message_count': 0,
                'user_count': 0
            }
        finally:
            conn.close() 
    
    def query_by_time(self, start_date=None, end_date=None):
        """按时间范围查询信息"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT m.msg_id, m.sender_name, m.content, m.send_time, m.msg_type, c.chat_name
            FROM messages m
            JOIN chats c ON m.chat_id = c.chat_id
            WHERE 1=1
            """
            params = []
            
            if start_date:
                try:
                    start_time = datetime.strptime(start_date, '%Y-%m-%d')
                    # 设置为当天的开时刻
                    start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    query += " AND m.send_time >= ?"
                    params.append(start_time.strftime('%Y-%m-%d %H:%M:%S.%f'))
                except ValueError:
                    raise ValueError("开始日期格式错误，请使用YYYY-MM-DD格式")
                    
            if end_date:
                try:
                    end_time = datetime.strptime(end_date, '%Y-%m-%d')
                    # 设置为当天的最后一刻
                    end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
                    query += " AND m.send_time <= ?"
                    params.append(end_time.strftime('%Y-%m-%d %H:%M:%S.%f'))
                except ValueError:
                    raise ValueError("结束日期格式错误，请使用YYYY-MM-DD格式")
                    
            query += " ORDER BY m.send_time DESC"
            
            cursor.execute(query, params)
            messages = []
            for row in cursor.fetchall():
                try:
                    send_time = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    # 如果时间格式不匹配尝试其他常见格式
                    try:
                        send_time = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        self.logger.warning(f"无法解析时间格式: {row[3]}")
                        continue
                    
                messages.append({
                    'msg_id': row[0],
                    'sender_name': row[1],
                    'content': row[2],
                    'send_time': send_time,
                    'msg_type': row[4],
                    'chat_name': row[5]
                })
            
            return messages
            
        except Exception as e:
            self.logger.error(f"按时间范围查询消息失败: {e}")
            raise
        finally:
            conn.close() 
    
    def query_by_chat(self, chat_id, limit=100):
        """按聊天ID查询消息"""
        try:
            # 复用query_messages方法的功能
            messages = self.query_messages(
                chat_id=chat_id,
                start_time=None,
                end_time=None,
                limit=limit
            )
            return messages
        except Exception as e:
            self.logger.error(f"按聊天ID查询消息失败: {e}")
            raise 
    
    def export_all(self, export_path, is_csv=True):
        """导出所有聊天记录"""
        try:
            # 设置并创建导出路径
            original_export_path = self.export_path
            self.export_path = export_path
            os.makedirs(export_path, exist_ok=True)
            
            # 导出数据
            result = self.export_chat(
                chat_id=None,
                start_time=None,
                end_time=None,
                format='csv' if is_csv else 'json'
            )
            
            # 恢复原始导出路径
            self.export_path = original_export_path
            return result
            
        except Exception as e:
            self.logger.error(f"导出所有数据失败: {e}")
            raise
    
    def export_by_time(self, export_path, start_date, end_date, is_csv=True):
        """按时间范围导出聊天记录"""
        try:
            # 设置并创建导出路径
            original_export_path = self.export_path
            self.export_path = export_path
            os.makedirs(export_path, exist_ok=True)
            
            # 转换日期格式
            start_time = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
            end_time = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
            
            # 导出数据
            result = self.export_chat(
                chat_id=None,
                start_time=start_time,
                end_time=end_time,
                format='csv' if is_csv else 'json'
            )
            
            # 恢复原始导出路径
            self.export_path = original_export_path
            return result
            
        except Exception as e:
            self.logger.error(f"按时间范围导出数据失败: {e}")
            raise
    
    def export_by_chat(self, export_path, chat_id, is_csv=True):
        """按聊天ID导出记录"""
        try:
            # 设置并创建导出路径
            original_export_path = self.export_path
            self.export_path = export_path
            os.makedirs(export_path, exist_ok=True)
            
            # 导出数据
            result = self.export_chat(
                chat_id=chat_id,
                start_time=None,
                end_time=None,
                format='csv' if is_csv else 'json'
            )
            
            # 恢复原始导出路径
            self.export_path = original_export_path
            return result
            
        except Exception as e:
            self.logger.error(f"导出指定聊天记录失败: {e}")
            raise 
    
    def analyze_and_visualize(self, chat_id=None, start_time=None, end_time=None, output_dir=None):
        """分析可视化聊天数据"""
        try:
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 构建查询参数
            params = [chat_id, chat_id]
            if start_time:
                params.extend([start_time.strftime('%Y-%m-%d %H:%M:%S'), start_time.strftime('%Y-%m-%d %H:%M:%S')])
            else:
                params.extend([None, None])
            if end_time:
                params.extend([end_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S')])
            else:
                params.extend([None, None])
            
            conn = sqlite3.connect(self.db.db_path)
            query = """
                SELECT 
                    m.msg_id,
                    m.chat_id,
                    m.sender_name,
                    m.content,
                    m.msg_type,
                    strftime('%Y-%m-%d %H:%M:%S', m.send_time) as send_time,
                    c.chat_name,
                    c.chat_type
                FROM messages m
                JOIN chats c ON m.chat_id = c.chat_id
                WHERE (? IS NULL OR m.chat_id = ?)
                AND (? IS NULL OR m.send_time >= ?)
                AND (? IS NULL OR m.send_time <= ?)
                ORDER BY m.send_time
            """
            
            messages = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if messages.empty:
                raise ValueError("未找到符合条件的消息记录")
            
            # 转换时间列
            messages['send_time'] = pd.to_datetime(messages['send_time'], format='%Y-%m-%d %H:%M:%S')
            
            # 1. 时间维度分析
            self._analyze_time_patterns(messages, output_dir)
            
            # 2. 用户维度分析
            self._analyze_user_patterns(messages, output_dir)
            
            # 3. 内容维度分析
            self._analyze_content_patterns(messages, output_dir)
            
            # 4. 群组维度分析（如是群聊）
            if chat_id and messages.iloc[0]['chat_type'] == 2:
                self._analyze_group_patterns(messages, output_dir)
            
            plt.close('all')
            return output_dir
            
        except Exception as e:
            self.logger.error(f"分析可视化失败: {str(e)}")
            raise ValueError(f"分析失败: {str(e)}")
    
    def _analyze_time_patterns(self, messages, output_dir):
        """分析时间模式"""
        try:
            # 转换为numpy数组进行处理
            messages_np = messages.to_numpy()
            times = pd.to_datetime(messages_np[:, messages.columns.get_loc('send_time')])
            
            # 1. 按小时统计
            hours = np.array([t.hour for t in times])
            hour_counts = np.bincount(hours, minlength=24)
            
            plt.figure(figsize=(12, 6))
            plt.bar(np.arange(24), hour_counts)
            plt.title('每小时消息分布')
            plt.xlabel('小时')
            plt.ylabel('消息数量')
            plt.xticks(np.arange(24))
            plt.savefig(os.path.join(output_dir, 'hourly_dist.png'))
            plt.close()
            
            # 2. 按星期统计
            weekdays = np.array([t.weekday() for t in times])
            weekday_counts = np.bincount(weekdays, minlength=7)
            weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            
            plt.figure(figsize=(10, 6))
            plt.bar(weekday_labels, weekday_counts)
            plt.title('每周消息分布')
            plt.xlabel('星期')
            plt.ylabel('消息数量')
            plt.savefig(os.path.join(output_dir, 'weekly_dist.png'))
            plt.close()
            
            # 3. 按日期统计
            dates = np.array([t.date() for t in times])
            unique_dates = np.unique(dates)
            date_counts = np.array([np.sum(dates == d) for d in unique_dates])
            
            plt.figure(figsize=(15, 6))
            plt.plot(unique_dates, date_counts)
            plt.title('每日消息趋势')
            plt.xlabel('日期')
            plt.ylabel('消息数量')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'daily_trend.png'))
            plt.close()
            
        except Exception as e:
            self.logger.error(f"时间模式分析失败: {str(e)}")
            raise
    
    def _analyze_user_patterns(self, messages, output_dir):
        """分析用户模式"""
        try:
            # 转换为numpy数组
            messages_np = messages.to_numpy()
            senders = messages_np[:, messages.columns.get_loc('sender_name')]
            
            # 1. 用户发言频率
            unique_senders, sender_counts = np.unique(senders, return_counts=True)
            sort_idx = np.argsort(sender_counts)[::-1]
            
            plt.figure(figsize=(12, 6))
            plt.bar(unique_senders[sort_idx][:10], sender_counts[sort_idx][:10])
            plt.title('用户发言频率（前10名）')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'user_activity.png'))
            plt.close()
            
        except Exception as e:
            self.logger.error(f"用户模式分析失败: {str(e)}")
            raise
    
    def _analyze_content_patterns(self, messages, output_dir):
        """分析内容模式"""
        try:
            # 转换为numpy数组
            messages_np = messages.to_numpy()
            contents = messages_np[:, messages.columns.get_loc('content')]
            msg_types = messages_np[:, messages.columns.get_loc('msg_type')]
            
            # 1. 消息类型分布
            unique_types, type_counts = np.unique(msg_types, return_counts=True)
            type_labels = ['文本', '图片', '语音', '视频', '文件', '其他']
            
            plt.figure(figsize=(8, 8))
            plt.pie(type_counts, labels=[type_labels[t-1] if t-1 < len(type_labels) else '其他' for t in unique_types],
                    autopct='%1.1f%%')
            plt.title('消息类型分布')
            plt.savefig(os.path.join(output_dir, 'msg_types.png'))
            plt.close()
            
            # 2. 文本长度分布
            text_lengths = np.array([len(str(c)) for c in contents if isinstance(c, str)])
            
            plt.figure(figsize=(10, 6))
            plt.hist(text_lengths, bins=30)
            plt.title('消息长度分布')
            plt.xlabel('长度')
            plt.ylabel('频率')
            plt.savefig(os.path.join(output_dir, 'content_length.png'))
            plt.close()
            
        except Exception as e:
            self.logger.error(f"内容模式分析失败: {str(e)}")
            raise
    
    def _analyze_group_patterns(self, messages, output_dir):
        """分析群组维度模式"""
        # 1. 群成员活跃度变化
        daily_user_counts = messages.groupby([messages['send_time'].dt.date, 'sender_name']).size().unstack(fill_value=0)
        plt.figure(figsize=(15, 8))
        daily_user_counts.plot(kind='area', stacked=True)
        plt.title('群成员每日发言数量')
        plt.xlabel('日期')
        plt.ylabel('消息数量')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'group_activity.png'))
        plt.close() 
    
    def custom_analyze(self, dimensions, chat_id=None, start_time=None, end_time=None):
        """自定义分析"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            
            # 优化SQL查询，避免重复列名
            query = """
                SELECT 
                    m.msg_id,
                    m.chat_id,
                    m.sender_name,
                    m.content,
                    m.msg_type,
                    m.send_time,
                    c.chat_name,
                    c.chat_type
                FROM messages m
                JOIN chats c ON m.chat_id = c.chat_id
                WHERE (? IS NULL OR m.chat_id = ?)
                AND (? IS NULL OR m.send_time >= ?)
                AND (? IS NULL OR m.send_time <= ?)
                ORDER BY m.send_time
            """
            
            params = [
                chat_id, chat_id,
                start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else None,
                start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else None,
                end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else None,
                end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else None
            ]
            
            messages = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if messages.empty:
                raise ValueError("未找到符合条件的消息记录")
            
            # 转换时间列
            messages['send_time'] = pd.to_datetime(messages['send_time'])
            results = {}
            
            # 时间维度分析
            if '1' in dimensions:
                daily_counts = messages.groupby(messages['send_time'].dt.date).size()
                hourly_counts = messages.groupby(messages['send_time'].dt.hour).size()
                weekday_counts = messages['send_time'].dt.dayofweek.value_counts()
                
                results['time'] = {
                    'daily_avg': daily_counts.mean(),
                    'peak_hour': hourly_counts.idxmax(),
                    'lowest_hour': hourly_counts.idxmin(),
                    'weekday_ratio': weekday_counts[weekday_counts.index < 5].sum() / len(messages),
                    'weekend_ratio': weekday_counts[weekday_counts.index >= 5].sum() / len(messages)
                }
            
            # 用户维度分析
            if '2' in dimensions:
                user_counts = messages.groupby('sender_name').size()
                results['user'] = {
                    'top_users': [{'name': name, 'count': int(count)} 
                                 for name, count in user_counts.nlargest(5).items()],
                    'avg_messages': float(len(messages) / user_counts.size)
                }
            
            # 内容维度分析
            if '3' in dimensions:
                type_counts = messages['msg_type'].value_counts()
                text = ' '.join(messages[messages['msg_type'] == 1]['content'].astype(str))
                keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=True)
                
                results['content'] = {
                    'type_ratio': {str(k): float(v/len(messages)) for k, v in type_counts.items()},
                    'keywords': [(word, float(weight)) for word, weight in keywords]
                }
            
            # 群组维度分析
            if '4' in dimensions and chat_id:
                active_users = messages['sender_name'].unique()
                
                # 计算用户互动
                interactions = defaultdict(int)
                prev_msg = None
                for _, msg in messages.iterrows():
                    if prev_msg is not None:
                        pair = tuple(sorted([prev_msg['sender_name'], msg['sender_name']]))
                        if pair[0] != pair[1]:  # 排除自己和自己动
                            interactions[pair] += 1
                    prev_msg = msg
                
                top_interactions = sorted(
                    [{'users': f"{pair[0]}-{pair[1]}", 'count': count}
                     for pair, count in interactions.items()],
                    key=lambda x: x['count'],
                    reverse=True
                )[:5]
                
                time_range = (messages['send_time'].max() - messages['send_time'].min()).total_seconds() / 86400
                if time_range == 0:
                    time_range = 1  # 避免除以零
                
                results['group'] = {
                    'member_count': int(len(active_users)),
                    'active_member_count': int(len([u for u in active_users 
                        if len(messages[messages['sender_name'] == u]) > 5])),
                    'activity_score': float(len(messages) / time_range),
                    'top_interactions': top_interactions
                }
            
            return results
            
        except Exception as e:
            self.logger.error(f"自定义分析失败: {str(e)}")
            raise ValueError(f"分析失败: {str(e)}") 
    
    def generate_mind_map(self, chat_id=None, start_time=None, end_time=None, output_dir=None):
        """生成聊天内容思维导图"""
        try:
            # 检查Graphviz是否可用
            try:
                import graphviz
                # 测试dot命令是否可用
                test_graph = graphviz.Digraph()
                test_graph.node('test', 'test')
                try:
                    test_graph.render('test', format='png', cleanup=True)
                    if os.path.exists('test.png'):
                        os.remove('test.png')  # 清理测试文件
                except Exception as e:
                    # 如果默认路径不可用，尝试常见的安装路径
                    common_paths = [
                        r'C:\Program Files\Graphviz\bin',
                        r'C:\Program Files (x86)\Graphviz\bin',
                        r'C:\Graphviz\bin'
                    ]
                    
                    graphviz_found = False
                    original_path = os.environ.get("PATH", "")
                    
                    for path in common_paths:
                        if os.path.exists(os.path.join(path, 'dot.exe')):
                            os.environ["PATH"] = path + os.pathsep + original_path
                            try:
                                test_graph.render('test', format='png', cleanup=True)
                                if os.path.exists('test.png'):
                                    os.remove('test.png')
                                graphviz_found = True
                                self.logger.info(f"找到Graphviz路径: {path}")
                                break
                            except:
                                continue
                    
                    if not graphviz_found:
                        raise ValueError(
                            "Graphviz未正确安装或未添加到系统PATH中。\n"
                            "请按照以下步骤检查：\n"
                            "1. 确认Graphviz已正确安装: https://graphviz.org/download/\n"
                            "2. 检查系统环境变量PATH中是否包含Graphviz的bin目录\n"
                            "3. 重启电脑后重试\n"
                            "4. 如果问题仍然存在，请手动将Graphviz安装目录添加到PATH中"
                        )
                    
            except ImportError:
                raise ValueError("请先安装graphviz包：pip install graphviz")
            
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_dir = "analysis_results"
                os.makedirs(output_dir, exist_ok=True)
            
            # 获取聊天记录
            messages = self._get_messages(chat_id, start_time, end_time)
            
            if not messages:
                raise ValueError("未找到符合条件的消息记录")
            
            # 加载并验证自定义词典
            dict_manager = DictManager()
            valid, msg = dict_manager.validate_dict()
            if valid:
                jieba.load_userdict(dict_manager.dict_path)
                self.logger.info("已加载自定义词典")
            else:
                self.logger.warning(f"加载自定义词典失败: {msg}")
            
            # 提取所有文本内容并预处理
            texts = []
            for msg in messages:
                if msg['content'] and isinstance(msg['content'], str):
                    # 移除URL、表情符号等
                    text = re.sub(r'http[s]?://\S+', '', msg['content'])
                    text = re.sub(r'\[.*?\]', '', text)
                    text = text.strip()
                    if text:
                        texts.append(text)
            
            if not texts:
                raise ValueError("没有可分析的文本内容")
            
            # 1. 提取高频短语和专业术语
            phrase_patterns = self._extract_frequent_phrases(texts)
            
            # 2. 动态更新自定义词典
            self._update_custom_dict(texts, dict_manager)
            
            # 3. 使用多种算法提取关键词
            keywords = self._extract_keywords_multi_algorithm(texts)
            
            # 创建思维导图
            dot = graphviz.Digraph(comment='Chat Content Mind Map', encoding='utf-8')
            dot.attr(rankdir='TB')
            
            # 设置节点和边的样式
            dot.attr('node', shape='box', style='rounded,filled', 
                    fontname='SimHei', fontsize='12')
            dot.attr('edge', fontname='SimHei', fontsize='10')
            
            # 添加根节点（聊天名称）
            chat_name = messages[0]['chat_name']
            dot.node('root', chat_name, fillcolor='#e3f2fd')
            
            # 添加高频词分支
            dot.node('keywords', '高频词', fillcolor='#f3e5f5')
            dot.edge('root', 'keywords')
            
            for i, keyword in enumerate(keywords):
                node_id = f'kw_{i}'
                dot.node(node_id, keyword, fillcolor='#fff3e0')
                dot.edge('keywords', node_id)
            
            # 添加典型消息分支
            dot.node('messages', '典型消息', fillcolor='#f3e5f5')
            dot.edge('root', 'messages')
            
            # 选择有代表性的消息（长度适中且包含关键词的消息）
            representative_msgs = []
            for text in texts:
                if 10 <= len(text) <= 50 and any(kw in text for kw in keywords):
                    representative_msgs.append(text)
                    if len(representative_msgs) >= 5:  # 限制显示5条典型消息
                        break
            
            for i, msg in enumerate(representative_msgs):
                node_id = f'msg_{i}'
                # 消息内容截断，避免过长
                display_msg = msg[:30] + '...' if len(msg) > 30 else msg
                dot.node(node_id, display_msg, fillcolor='#e1f5fe')
                dot.edge('messages', node_id)
            
            # 保存思维导图
            if not output_dir:
                output_dir = "analysis_results"
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, 'mind_map')
            dot.render(output_path, format='png', cleanup=True)
            
            return f"{output_path}.png"
            
        except Exception as e:
            self.logger.error(f"生成思维导图失败: {str(e)}")
            raise ValueError(f"生成失败: {str(e)}")
    
    def _extract_frequent_phrases(self, texts, min_freq=3):
        """提取高频短语"""
        try:
            # 使用正则表达式匹配可能的短语模式
            patterns = {
                '专业术语': r'[a-zA-Z0-9\u4e00-\u9fa5]{2,8}(?:系统|平台|设备|技术|方案|模块|功能|服务|数据)',
                '时间词组': r'(?:上午|下午|凌晨|晚上)?\d{1,2}[:|：]\d{1,2}',
                '数字单位': r'\d+(?:年|月|日|天|个|次|台|件|kg|吨|千克)',
                '专有名词': r'(?:[A-Z][a-z]+){2,}|[A-Z]{2,}',
            }
            
            phrases = defaultdict(int)
            for text in texts:
                for pattern_type, pattern in patterns.items():
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        phrase = match.group()
                        phrases[phrase] += 1
            
            # 过滤低频短语
            frequent_phrases = {p: f for p, f in phrases.items() if f >= min_freq}
            return frequent_phrases
            
        except Exception as e:
            self.logger.error(f"提取高频短语失败: {str(e)}")
            return {}
    
    def _update_custom_dict(self, texts, dict_manager):
        """动态更新自定义词典"""
        try:
            # 1. 统计词频
            word_freq = defaultdict(int)
            for text in texts:
                words = jieba.cut(text)
                for word in words:
                    word_freq[word] += 1
            
            # 2. 使用统计信息识别新词
            new_words = set()
            for i in range(len(texts)):
                for j in range(i+1, len(texts)):
                    common_substrings = self._find_common_substrings(texts[i], texts[j])
                    for substr in common_substrings:
                        if len(substr) >= 2 and word_freq[substr] >= 3:
                            new_words.add(substr)
            
            # 3. 更新词典
            for word in new_words:
                if not dict_manager.has_word(word):
                    dict_manager.add_word(word, word_freq[word])
            
        except Exception as e:
            self.logger.error(f"更新自定义词典失败: {str(e)}")
    
    def _extract_keywords_multi_algorithm(self, texts, top_k=20):
        """使用多种算法提取关键词"""
        try:
            # 1. 预处理文本
            processed_texts = []
            for text in texts:
                # 移除特殊字符和标点
                text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    processed_texts.append(text)
            
            combined_text = '\n'.join(processed_texts)
            
            # 定义要保留的词性
            valid_pos = {
                'n',    # 名词
                'nr',   # 人名
                'ns',   # 地名
                'nt',   # 机构名
                'nz',   # 其他专名
                'v',    # 动词
                'vn',   # 动名词
            }
            
            # 2. 使用多种分词算法
            # 2.1 TF-IDF
            tfidf_keywords = set(jieba.analyse.extract_tags(
                combined_text,
                topK=top_k * 2,
                withWeight=True,
                allowPOS=tuple(valid_pos)  # 只允许特定词性
            ))
            
            # 2.2 TextRank
            textrank_keywords = set(jieba.analyse.textrank(
                combined_text,
                topK=top_k * 2,
                withWeight=True,
                allowPOS=tuple(valid_pos)  # 只允许特定词性
            ))
            
            # 2.3 基于词频和词性的分析
            words_with_flags = []
            for text in processed_texts:
                # 只保留指定词性的词
                words = jieba.posseg.cut(text)
                words_with_flags.extend([(word, flag) for word, flag in words if flag in valid_pos])
            
            # 统计词频和词性
            word_stats = defaultdict(lambda: {'freq': 0, 'pos': defaultdict(int)})
            for word, flag in words_with_flags:
                if len(word) >= 2:  # 只考虑长度大于等于2的词
                    word_stats[word]['freq'] += 1
                    word_stats[word]['pos'][flag] += 1
            
            # 3. 融合多种算法结果
            keyword_scores = defaultdict(float)
            
            # 3.1 添加TF-IDF权重
            for word, weight in tfidf_keywords:
                keyword_scores[word] += weight * 0.4
            
            # 3.2 添加TextRank权重
            for word, weight in textrank_keywords:
                keyword_scores[word] += weight * 0.3
            
            # 3.3 添加词频权重
            max_freq = max((stats['freq'] for stats in word_stats.values()), default=1)
            for word, stats in word_stats.items():
                freq_score = stats['freq'] / max_freq
                keyword_scores[word] += freq_score * 0.3
            
            # 4. 选择最终关键词
            sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
            return [word for word, _ in sorted_keywords[:top_k]]
            
        except Exception as e:
            self.logger.error(f"关键词提取失败: {str(e)}")
            return []
    
    def _calculate_context_relevance(self, word, texts, window_size=5):
        """计算词语的上下文相关性"""
        try:
            # 统计共现词
            cooccurrence = defaultdict(int)
            total_windows = 0
            
            for text in texts:
                words = list(jieba.cut(text))
                for i, w in enumerate(words):
                    if w == word:
                        # 获取窗口范围内的词
                        start = max(0, i - window_size)
                        end = min(len(words), i + window_size + 1)
                        window_words = words[start:i] + words[i+1:end]
                        
                        for context_word in window_words:
                            if len(context_word) >= 2:  # 只考虑长度大于等于2的词
                                cooccurrence[context_word] += 1
                        total_windows += 1
            
            if not total_windows:
                return 0
            
            # 计算上下文相关性得分
            max_cooccurrence = max(cooccurrence.values()) if cooccurrence else 1
            context_score = sum(count / max_cooccurrence for count in cooccurrence.values())
            return min(1.0, context_score / (2 * window_size))  # 归一化到[0,1]范围
            
        except Exception as e:
            self.logger.error(f"计算上下文相关性失败: {str(e)}")
            return 0
    
    def _find_common_substrings(self, str1, str2, min_length=2):
        """查找两个字符串的公共子串"""
        common = set()
        for i in range(len(str1)-min_length+1):
            for j in range(i+min_length, len(str1)+1):
                substr = str1[i:j]
                if substr in str2 and len(substr) >= min_length:
                    common.add(substr)
        return common
    
    def _get_high_freq_words(self, texts, top_k=20):
        """获取高频词"""
        word_freq = defaultdict(int)
        for text in texts:
            words = jieba.cut(text)
            for word in words:
                if len(word) >= 2:  # 只统计长度大于等于2的词
                    word_freq[word] += 1
        
        return set([word for word, _ in sorted(word_freq.items(), 
                                             key=lambda x: x[1], 
                                             reverse=True)[:top_k]])
    
    def _get_time_distribution(self, messages):
        """获取消息的时间分布统计"""
        time_dist = defaultdict(int)
        for msg in messages:
            hour = datetime.strptime(msg['send_time'], '%Y-%m-%d %H:%M:%S.%f').hour
            if 0 <= hour < 6:
                period = '凌晨(0-6点)'
            elif 6 <= hour < 12:
                period = '上午(6-12点)'
            elif 12 <= hour < 18:
                period = '下午(12-18点)'
            else:
                period = '晚上(18-24点)'
            time_dist[period] += 1
        return dict(sorted(time_dist.items()))
    
    def preview_clean_data(self, before_date=None, chat_id=None):
        """预览将要清理的数据
        :param before_date: 清理该日期之前的数据
        :param chat_id: 指定聊天对象的ID
        :return: 预览信息字典
        """
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if before_date:
            conditions.append("m.send_time < ?")
            params.append(before_date)
        if chat_id:
            conditions.append("m.chat_id = ?")
            params.append(chat_id)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        try:
            # 获取基本统计信息
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as msg_count,
                    MIN(m.send_time) as earliest_time,
                    MAX(m.send_time) as latest_time,
                    COUNT(DISTINCT m.chat_id) as chat_count,
                    COUNT(DISTINCT m.sender_name) as user_count
                FROM messages m
                WHERE {where_clause}
            """, params)
            
            stats = cursor.fetchone()
            
            # 获取涉及的聊天对象信息
            cursor.execute(f"""
                SELECT DISTINCT 
                    c.chat_name,
                    COUNT(*) as count
                FROM messages m
                JOIN chats c ON m.chat_id = c.chat_id
                WHERE {where_clause}
                GROUP BY c.chat_name
            """, params)
            
            chats = cursor.fetchall()
            
            return {
                'msg_count': stats[0],
                'earliest_time': stats[1],
                'latest_time': stats[2],
                'chat_count': stats[3],
                'user_count': stats[4],
                'chats': [{'name': chat[0], 'count': chat[1]} for chat in chats]
            }
            
        except Exception as e:
            self.logger.error(f"预览清理数据失败: {e}")
            raise
        finally:
            conn.close() 
    
    def _get_messages(self, chat_id=None, start_time=None, end_time=None):
        """获取聊天记录"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            
            # 构建查询条件
            conditions = []
            params = []
            
            if chat_id:
                conditions.append("m.chat_id = ?")
                params.append(chat_id)
                
            if start_time:
                conditions.append("m.send_time >= ?")
                if isinstance(start_time, datetime):
                    params.append(start_time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    params.append(start_time)
                    
            if end_time:
                conditions.append("m.send_time <= ?")
                if isinstance(end_time, datetime):
                    params.append(end_time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    params.append(end_time)
            
            # 构建WHERE子句
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT 
                    m.msg_id,
                    m.sender_name,
                    m.content,
                    m.send_time,
                    m.msg_type,
                    c.chat_name
                FROM messages m
                JOIN chats c ON m.chat_id = c.chat_id
                WHERE {where_clause}
                ORDER BY m.send_time
            """
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            messages = []
            
            for row in cursor.fetchall():
                try:
                    # 尝试多种时间格式
                    send_time = None
                    time_formats = [
                        '%Y-%m-%d %H:%M:%S.%f',
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M'
                    ]
                    
                    for fmt in time_formats:
                        try:
                            send_time = datetime.strptime(row[3], fmt)
                            break
                        except ValueError:
                            continue
                    
                    if send_time is None:
                        self.logger.warning(f"无法解析时间格式: {row[3]}")
                        continue
                    
                    messages.append({
                        'msg_id': row[0],
                        'sender_name': row[1],
                        'content': row[2],
                        'send_time': send_time,
                        'msg_type': row[4],
                        'chat_name': row[5]
                    })
                    
                except Exception as e:
                    self.logger.warning(f"处理消息记录失败: {str(e)}")
                    continue
                
            cursor.close()
            conn.close()
            return messages
            
        except Exception as e:
            self.logger.error(f"获取聊天记录失败: {str(e)}")
            raise
    
    def _get_chat_name(self, chat_id):
        """获取聊天名称
        
        Args:
            chat_id: 聊天ID
        
        Returns:
            str: 聊天名称
        """
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT chat_name FROM chats WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            return result[0] if result else "未知聊天"
        except Exception as e:
            self.logger.error(f"获取聊天名称失败: {e}")
            return "未知聊天"
        finally:
            conn.close() 
    
    def search_messages(self, conditions=None):
        """搜索聊天记录"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        
        if conditions:
            if 'sender' in conditions:
                where_clauses.append("m.sender_name LIKE ?")
                params.append(f"%{conditions['sender']}%")
                
            if 'keyword' in conditions:
                where_clauses.append("m.content LIKE ?")
                params.append(f"%{conditions['keyword']}%")
                
            if 'mention' in conditions:
                where_clauses.append("m.content LIKE ?")
                params.append(f"%@{conditions['mention']}%")
                
            if 'start_time' in conditions:
                where_clauses.append("m.send_time >= ?")
                params.append(conditions['start_time'])
                
            if 'end_time' in conditions:
                where_clauses.append("m.send_time <= ?")
                params.append(conditions['end_time'])
                
            if 'chat_name' in conditions:
                where_clauses.append("c.chat_name LIKE ?")
                params.append(f"%{conditions['chat_name']}%")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        try:
            cursor.execute(f"""
                SELECT m.msg_id, m.chat_id, c.chat_name, m.sender_name, m.content, m.send_time, m.msg_type
                FROM messages m
                LEFT JOIN chats c ON m.chat_id = c.chat_id
                WHERE {where_clause}
                ORDER BY m.send_time DESC
                LIMIT 1000
            """, params)
            
            results = cursor.fetchall()
            return [{
                'msg_id': row[0],
                'chat_id': row[1],
                'chat_name': row[2],
                'sender': row[3],
                'content': row[4],
                'time': row[5],
                'type': row[6]
            } for row in results]
            
        except Exception as e:
            self.logger.error(f"搜索消息失败: {e}")
            return []
        finally:
            conn.close() 
    
    def get_all_senders(self):
        """获取所有去重后的发送者列表"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DISTINCT sender_name 
                FROM messages 
                WHERE sender_name IS NOT NULL 
                AND sender_name != '未知发送者'
                ORDER BY sender_name
            """)
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close() 
    
    def get_all_mentions(self):
        """获取所有被@提及的用户列表"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DISTINCT SUBSTR(content, INSTR(content, '@') + 1) as mention
                FROM messages 
                WHERE content LIKE '%@%'
                AND content NOT LIKE '%@所有人%'
                ORDER BY mention
            """)
            mentions = []
            for row in cursor.fetchall():
                # 提取@后面的用户名（到空格或特殊字符为止）
                mention = re.match(r'^([^\s\n]+)', row[0])
                if mention:
                    mentions.append(mention.group(1))
            return list(set(mentions))  # 去重
        finally:
            conn.close() 
    
    def plot_activity_by_time(self, data, output_path):
        """绘制活跃度时间分布图"""
        try:
            # 转换为numpy数组进行处理
            hour_data = np.array(data['hour_dist'])
            weekday_data = np.array(data['weekday_dist'])
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 小时活跃度
            hours = np.arange(24)
            ax1.bar(hours, hour_data)
            ax1.set_title('每小时消息数量分布')
            ax1.set_xlabel('小时')
            ax1.set_ylabel('消息数量')
            
            # 星期活跃度
            weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            ax2.bar(weekdays, weekday_data)
            ax2.set_title('星期消息数量分布')
            ax2.set_xlabel('星期')
            ax2.set_ylabel('消息数量')
            
            plt.tight_layout()
            plt.savefig(f"{output_path}/activity_dist.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制活跃度分布图失败: {e}")
            raise
    
    def plot_user_activity(self, data, output_path):
        """绘制用户活跃度图"""
        try:
            # 转换为numpy数组
            users = np.array(list(data['user_activity'].keys()))
            counts = np.array(list(data['user_activity'].values()))
            
            # 按消息数量排序
            sort_idx = np.argsort(counts)[::-1]
            users = users[sort_idx]
            counts = counts[sort_idx]
            
            # 只显示前10名用户
            if len(users) > 10:
                users = users[:10]
                counts = counts[:10]
            
            plt.figure(figsize=(12, 6))
            plt.bar(users, counts)
            plt.xticks(rotation=45, ha='right')
            plt.title('用户活跃度排名（前10名）')
            plt.xlabel('用户')
            plt.ylabel('消息数量')
            plt.tight_layout()
            plt.savefig(f"{output_path}/user_activity.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制用户活跃度图失败: {e}")
            raise
    
    def plot_message_types(self, data, output_path):
        """绘制消息类型分布图"""
        try:
            types = np.array(list(data['msg_types'].keys()))
            counts = np.array(list(data['msg_types'].values()))
            
            plt.figure(figsize=(10, 6))
            plt.pie(counts, labels=types, autopct='%1.1f%%')
            plt.title('消息类型分布')
            plt.axis('equal')
            plt.savefig(f"{output_path}/msg_types.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制消息类型分布图失败: {e}")
            raise 
    
    def analyze_word_frequency(self, chat_id=None, start_time=None, end_time=None, output_dir=None):
        """分析词频"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            
            # 构建查询条件
            conditions = ["msg_type = 1"]  # 只分析文本消息
            params = []
            if chat_id:
                conditions.append("chat_id = ?")
                params.append(chat_id)
            if start_time:
                conditions.append("send_time >= ?")
                # 确保时间格式正确
                if isinstance(start_time, datetime):
                    params.append(start_time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    params.append(start_time)
            if end_time:
                conditions.append("send_time <= ?")
                if isinstance(end_time, datetime):
                    params.append(end_time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    params.append(end_time)
            
            where_clause = " AND ".join(conditions)
            
            # 获取文本消息
            query = f"""
            SELECT content
            FROM messages
            WHERE {where_clause}
            """
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                raise ValueError("未找到符合条件的文本消息")
            
            # 创建输出目录
            if output_dir is None:
                output_dir = "analysis_results"
            os.makedirs(output_dir, exist_ok=True)
            
            # 加载自定义词典
            dict_manager = DictManager()
            jieba.load_userdict(dict_manager.dict_path)
            
            # 分词统计
            word_freq = defaultdict(int)
            for text in df['content']:
                if isinstance(text, str):
                    words = jieba.cut(text)
                    for word in words:
                        if len(word.strip()) > 1:  # 过滤单字词
                            word_freq[word] += 1
            
            # 生成词频报告
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            report = "词频统计报告\n" + "="*20 + "\n\n"
            report += "Top 50 高频词：\n\n"
            for word, freq in sorted_words[:50]:
                report += f"{word}: {freq}次\n"
            
            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(output_dir, f"word_frequency_{timestamp}.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # 生成词云图
            if sorted_words:
                wordcloud = WordCloud(
                    font_path='simhei.ttf',
                    width=1200,
                    height=800,
                    background_color='white'
                ).generate_from_frequencies(dict(sorted_words))
                
                plt.figure(figsize=(15, 10))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                plt.title('词频分布词云图')
                plt.savefig(os.path.join(output_dir, f"wordcloud_{timestamp}.png"))
                plt.close()
            
            # 生成词频分布柱状图
            if len(sorted_words) > 20:
                top_words = sorted_words[:20]
                words, freqs = zip(*top_words)
                
                plt.figure(figsize=(15, 8))
                plt.bar(words, freqs)
                plt.xticks(rotation=45, ha='right')
                plt.title('Top 20 高频词')
                plt.xlabel('词语')
                plt.ylabel('出现次数')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, f"word_freq_bar_{timestamp}.png"))
                plt.close()
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"词频分析失败: {str(e)}")
            raise 