import os
import re
import logging
from pathlib import Path
import sqlite3
import jieba
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
from wordcloud import WordCloud

class DictManager:
    def __init__(self, dict_path="data/custom_dict.txt", backup_dir="data/dict_backups"):
        self.dict_path = dict_path
        self.backup_dir = backup_dir
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(dict_path), exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        
        # 如果词典文件不存在，创建示例文件
        if not os.path.exists(dict_path):
            self._create_example_dict()
    
    def _create_example_dict(self):
        """创建示例词典文件"""
        example_content = '''# 自定义词典格式说明：
# 每行一个词条，格式为：词语 词频 词性(可选)
# 示例：
微信 1000 n
朋友圈 800 n
表情包 500 n
红包 1000 n
群聊 900 n
私聊 800 n
语音消息 600 n
视频通话 500 n
截图 400 n
撤回 300 v
置顶 200 v
# 自定义词条：
'''
        try:
            with open(self.dict_path, 'w', encoding='utf-8') as f:
                f.write(example_content)
            self.logger.info(f"已创建示例词典文件: {self.dict_path}")
        except Exception as e:
            self.logger.error(f"创建示例词典文件失败: {e}")
    
    def validate_dict(self):
        """验证词典格式"""
        if not os.path.exists(self.dict_path):
            return False, "词典文件不存在"
            
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                parts = line.split()
                if len(parts) < 2:
                    return False, f"第{i}行格式错误: {line}"
                    
                if not parts[1].isdigit():
                    return False, f"第{i}行词频必须为数字: {line}"
                    
                if len(parts) > 2 and not re.match(r'^[a-zA-Z]+$', parts[2]):
                    return False, f"第{i}行词性格式错误: {line}"
                    
            return True, "词典格式正确"
            
        except Exception as e:
            return False, f"验证词典时出错: {e}"
    
    def add_word(self, word, freq=500, pos=None):
        """添加新词到词典"""
        try:
            if self.has_word(word):
                return False, "词语已存在"
                
            # 构建词条
            entry = f"{word} {freq}"
            if pos:
                entry += f" {pos}"
                
            # 添加到词典
            with open(self.dict_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{entry}")
                
            return True, "添加成功"
            
        except Exception as e:
            self.logger.error(f"添加词语失败: {e}")
            return False, f"添加失败: {e}"
    
    def remove_word(self, word):
        """删除词条"""
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            with open(self.dict_path, 'w', encoding='utf-8') as f:
                removed = False
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        if line.split()[0] != word:
                            f.write(line)
                        else:
                            removed = True
                    else:
                        f.write(line)
                        
            return removed, "删除成功" if removed else "词条不存在"
            
        except Exception as e:
            return False, f"删除词条失败: {e}"
    
    def list_words(self):
        """列出所有词条"""
        try:
            words = []
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        words.append(line.split())
            return words
        except Exception as e:
            self.logger.error(f"列出词条失败: {e}")
            return [] 
    
    def backup_dict(self, backup_name=None):
        """备份词典文件
        
        Args:
            backup_name: 备份文件名，默认使用时间戳
        """
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"custom_dict_{timestamp}.txt"
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            with open(self.dict_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            self.logger.info(f"词典已备份到: {backup_path}")
            return True, backup_path
        except Exception as e:
            self.logger.error(f"备份词典失败: {e}")
            return False, str(e)
    
    def restore_backup(self, backup_name):
        """从备份恢复词典
        
        Args:
            backup_name: 备份文件名
        """
        backup_path = os.path.join(self.backup_dir, backup_name)
        try:
            if not os.path.exists(backup_path):
                return False, "备份文件不存在"
            
            # 先备份当前词典
            self.backup_dict(f"auto_backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
            # 恢复备份
            with open(backup_path, 'r', encoding='utf-8') as src, \
                 open(self.dict_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            return True, "恢复成功"
        except Exception as e:
            return False, f"恢复失败: {e}"
    
    def calculate_word_frequencies(self, db_handler, min_freq=100, max_freq=1000):
        """从聊天记录计算词频
        
        Args:
            db_handler: DatabaseHandler实例
            min_freq: 最小词频
            max_freq: 最大词频
        """
        try:
            # 获取所有消息内容
            conn = sqlite3.connect(db_handler.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM messages WHERE content IS NOT NULL")
            contents = cursor.fetchall()
            
            # 分词统计
            word_freq = defaultdict(int)
            for content, in contents:
                words = jieba.cut(content)
                for word in words:
                    if len(word) > 1:  # 忽略单字
                        word_freq[word] += 1
            
            # 归一化词频
            if word_freq:
                max_count = max(word_freq.values())
                normalized_freq = {
                    word: int(min_freq + (max_freq - min_freq) * count / max_count)
                    for word, count in word_freq.items()
                }
                return normalized_freq
            return {}
            
        except Exception as e:
            self.logger.error(f"计算词频失败: {e}")
            return {}
        finally:
            conn.close()
    
    def update_frequencies(self, db_handler):
        """更新词典中的词频"""
        try:
            # 获取当前词典内容
            current_words = self.list_words()
            current_dict = {word[0]: (word[1], word[2] if len(word) > 2 else None) 
                          for word in current_words}
            
            # 计算新词频
            new_frequencies = self.calculate_word_frequencies(db_handler)
            
            # 更新词典文件
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with open(self.dict_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        word = line.split()[0]
                        if word in new_frequencies:
                            pos = current_dict.get(word, (None, None))[1]
                            new_line = f"{word} {new_frequencies[word]}"
                            if pos:
                                new_line += f" {pos}"
                            f.write(new_line + '\n')
                        else:
                            f.write(line)
                    else:
                        f.write(line)
            
            return True, "词频更新成功"
        except Exception as e:
            return False, f"更新词频失败: {e}"
    
    def merge_dict(self, other_dict_path, merge_strategy='max'):
        """合并另一个词典文件
        
        Args:
            other_dict_path: 要合并的词典文件路径
            merge_strategy: 合并策略，可选 'max'/'min'/'avg'
        """
        try:
            if not os.path.exists(other_dict_path):
                return False, "要合并的词典文件不存在"
            
            # 读取当前词典
            current_dict = {}
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        word = parts[0]
                        freq = int(parts[1])
                        pos = parts[2] if len(parts) > 2 else None
                        current_dict[word] = (freq, pos)
            
            # 读取要合并的词典
            other_dict = {}
            with open(other_dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        word = parts[0]
                        freq = int(parts[1])
                        pos = parts[2] if len(parts) > 2 else None
                        other_dict[word] = (freq, pos)
            
            # 合并词典
            merged_dict = {}
            all_words = set(current_dict.keys()) | set(other_dict.keys())
            
            for word in all_words:
                curr_freq, curr_pos = current_dict.get(word, (0, None))
                other_freq, other_pos = other_dict.get(word, (0, None))
                
                # 根据策略合并词频
                if merge_strategy == 'max':
                    merged_freq = max(curr_freq, other_freq)
                elif merge_strategy == 'min':
                    merged_freq = min(curr_freq, other_freq) if curr_freq and other_freq else (curr_freq or other_freq)
                else:  # 'avg'
                    merged_freq = int((curr_freq + other_freq) / (2 if curr_freq and other_freq else 1))
                
                # 保留任一词性标注
                merged_pos = curr_pos or other_pos
                merged_dict[word] = (merged_freq, merged_pos)
            
            # 备份当前词典
            self.backup_dict()
            
            # 写入合并后的词典
            with open(self.dict_path, 'w', encoding='utf-8') as f:
                f.write("# 自定义词典格式说明：\n")
                f.write("# 每行一个词条，格式为：词语 词频 词性(可选)\n")
                f.write("# 示例：\n")
                
                # 按词频降序排序
                sorted_words = sorted(merged_dict.items(), key=lambda x: x[1][0], reverse=True)
                
                for word, (freq, pos) in sorted_words:
                    line = f"{word} {freq}"
                    if pos:
                        line += f" {pos}"
                    f.write(line + '\n')
            
            return True, f"成功合并词典，共 {len(merged_dict)} 个词条"
            
        except Exception as e:
            return False, f"合并词典失败: {e}"
    
    def visualize_dict(self, output_dir="analysis_results"):
        """可视化词典数据"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 读取词典数据
            words = self.list_words()
            if not words:
                return False, "词典为空"
            
            # 提取词频数据
            word_freqs = [(word[0], int(word[1])) for word in words]
            words, freqs = zip(*word_freqs)
            
            # 1. 词频分布图
            plt.figure(figsize=(12, 6))
            plt.bar(words[:20], freqs[:20])  # 显示前20个高频词
            plt.xticks(rotation=45, ha='right')
            plt.title('词频分布（前20个高频词）')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'word_frequency.png'))
            plt.close()
            
            # 2. 词云图
            text = ' '.join([f"{word} " * freq for word, freq in word_freqs])
            wordcloud = WordCloud(
                font_path='simhei.ttf',  # 使用系统字体
                width=1200,
                height=800,
                background_color='white'
            ).generate(text)
            
            plt.figure(figsize=(15, 10))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.savefig(os.path.join(output_dir, 'wordcloud.png'))
            plt.close()
            
            # 3. 词频统计信息
            total_words = len(words)
            avg_freq = sum(freqs) / total_words
            max_freq = max(freqs)
            min_freq = min(freqs)
            
            stats = f"""词典统计信息：
总词条数：{total_words}
平均词频：{avg_freq:.2f}
最高词频：{max_freq}
最低词频：{min_freq}
"""
            with open(os.path.join(output_dir, 'dict_stats.txt'), 'w', encoding='utf-8') as f:
                f.write(stats)
            
            return True, f"可视化结果已保存到 {output_dir} 目录"
            
        except Exception as e:
            return False, f"生成可视化失败: {e}"
    
    def has_word(self, word):
        """检查词典中是否存在指定词语"""
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if parts[0] == word:
                            return True
            return False
            
        except Exception as e:
            self.logger.error(f"检查词语是否存在失败: {e}")
            return False
            
    def add_word(self, word, freq=500, pos=None):
        """添加新词到词典"""
        try:
            if self.has_word(word):
                return False, "词语已存在"
                
            # 构建词条
            entry = f"{word} {freq}"
            if pos:
                entry += f" {pos}"
                
            # 添加到词典
            with open(self.dict_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{entry}")
                
            return True, "添加成功"
            
        except Exception as e:
            self.logger.error(f"添加词语失败: {e}")
            return False, f"添加失败: {e}" 