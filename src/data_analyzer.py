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
        """获取所有会话列表"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT chat_id, chat_name, chat_type 
            FROM chats 
            ORDER BY chat_name
            ''')
            
            return [
                {
                    'chat_id': row[0],
                    'chat_name': row[1],
                    'chat_type': row[2]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            self.logger.error(f"获取会话列表失败: {e}")
            return []
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
        """按时间范围查询消息"""
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
                    # 设置为当天的开始时刻
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
                    # 如果时间格式不匹配，尝试其他常见格式
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
            self.logger.error(f"导出全部数据失败: {e}")
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
            self.logger.error(f"按时���范围导出数据失败: {e}")
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
        """分析并可视化聊天数据"""
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
            
            # 4. 群组维度分析（如果是群聊）
            if chat_id and messages.iloc[0]['chat_type'] == 2:
                self._analyze_group_patterns(messages, output_dir)
            
            plt.close('all')
            return output_dir
            
        except Exception as e:
            self.logger.error(f"分析可视化失败: {str(e)}")
            raise ValueError(f"分析失败: {str(e)}")
    
    def _analyze_time_patterns(self, messages, output_dir):
        """分析时间维度模式"""
        # 1. 消息数量趋势
        plt.figure(figsize=(15, 6))
        daily_counts = messages.groupby(messages['send_time'].dt.date).size()
        plt.plot(daily_counts.index, daily_counts.values)
        plt.title('每日消息数量趋势')
        plt.xlabel('日期')
        plt.ylabel('消息数量')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'daily_message_trend.png'))
        plt.close()
        
        # 2. 每小时活跃度分布
        plt.figure(figsize=(12, 6))
        hourly_counts = messages.groupby(messages['send_time'].dt.hour).size()
        plt.bar(hourly_counts.index, hourly_counts.values)
        plt.title('消息发送时段分布')
        plt.xlabel('小时')
        plt.ylabel('消息数量')
        plt.savefig(os.path.join(output_dir, 'hourly_distribution.png'))
        plt.close()
    
    def _analyze_user_patterns(self, messages, output_dir):
        """分析用户维度模式"""
        # 1. 用户发言排名
        plt.figure(figsize=(12, 6))
        user_counts = messages.groupby('sender_name').size().sort_values(ascending=True)
        plt.barh(user_counts.index, user_counts.values)
        plt.title('用户发言数量排名')
        plt.xlabel('消息数量')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'user_ranking.png'))
        plt.close()
        
        # 2. 用户活跃度热力图
        user_hour_counts = messages.groupby([messages['send_time'].dt.hour, 'sender_name']).size().unstack(fill_value=0)
        plt.figure(figsize=(15, 8))
        sns.heatmap(user_hour_counts, cmap='YlOrRd')
        plt.title('用户活跃时段分布')
        plt.xlabel('用户')
        plt.ylabel('小时')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'user_activity_heatmap.png'))
        plt.close()
    
    def _analyze_content_patterns(self, messages, output_dir):
        """分析内容维度模式"""
        # 1. 消息类型分布
        plt.figure(figsize=(8, 8))
        type_counts = messages['msg_type'].value_counts()
        plt.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%')
        plt.title('消息类型分布')
        plt.savefig(os.path.join(output_dir, 'message_types.png'))
        plt.close()
        
        # 2. 词云图
        text = ' '.join(messages[messages['msg_type'] == 1]['content'].astype(str))
        words = ' '.join(jieba.analyse.extract_tags(text, topK=100, withWeight=False))
        wordcloud = WordCloud(width=800, height=400, background_color='white', font_path='simhei.ttf')
        wordcloud.generate(words)
        plt.figure(figsize=(15, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.savefig(os.path.join(output_dir, 'wordcloud.png'))
        plt.close()
    
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
                        if pair[0] != pair[1]:  # 排除自己和自己的互动
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