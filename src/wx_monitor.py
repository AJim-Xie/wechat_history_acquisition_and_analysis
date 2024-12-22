import uiautomation as auto
import time
from datetime import datetime
import re
import logging
import os

class WeChatMonitor:
    def __init__(self, log_path="logs", media_path="data/media"):
        self.wx_window = None
        self.chat_window = None
        self.last_time = None
        auto.SetGlobalSearchTimeout(2)
        
        # 设置日志
        os.makedirs(log_path, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(f"{log_path}/wx_monitor.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 设置媒体文件存储路径
        self.media_path = media_path
        os.makedirs(media_path, exist_ok=True)
        for folder in ['images', 'videos', 'files']:
            os.makedirs(f"{media_path}/{folder}", exist_ok=True)
        
    def find_wechat(self):
        """查找微信主窗口"""
        try:
            self.wx_window = auto.WindowControl(Name="微信")
            if self.wx_window.Exists(maxSearchSeconds=3):
                self.logger.info("找到微信窗口")
                return True
            else:
                self.logger.warning("未找到微信窗口")
                return False
        except Exception as e:
            self.logger.error(f"查找微信窗口时出错: {e}")
            return False
    
    def get_current_chat(self):
        """获取当前聊天窗口信息"""
        if not self.wx_window:
            return None
        
        try:
            # 获取聊天信息
            chat_name_control = self.wx_window.ButtonControl(Name="聊天信息")
            if not chat_name_control.Exists(maxSearchSeconds=2):
                self.logger.warning("未找到聊天信息按钮")
                return None
            
            title = chat_name_control.Name
            self.logger.info(f"原始聊天标题: {title}")
            
            # 定义聊天类型
            CHAT_TYPE = {
                'GROUP': 2,    # 群聊
                'PRIVATE': 1,  # 私聊
                'PUBLIC': 3,   # 公众号
                'SYSTEM': 4,   # 系统账号
            }
            
            # 优化聊天类型判断逻辑
            def get_chat_type(title):
                # 系统账��列表 - 扩充更多系统账号
                system_accounts = [
                    "文件传输助手", "微信支付", "微信团队", "微信支付分", "腾讯新闻",
                    "QQ邮箱提醒", "微信运动", "微信小店", "支付宝", "系统通知",
                    "微信红包", "微信收藏", "看一看", "朋友圈", "游戏", "语音记事本"
                ]
                
                # 群聊特征 - 增加更多群聊特征
                group_indicators = [
                    "[群聊]", "群聊", "（", "）", "(", ")", 
                    "交流群", "群", "讨论组", "社群", "协会",
                    "班级", "团队", "家族", "联盟", "战队",
                    "俱乐部", "商会", "同学", "同事"
                ]
                
                # 公众号特征 - 增加更多公众号特征
                public_indicators = [
                    "公众号", "订阅号", "视频号", "小程序",
                    "官方", "新闻", "头条", "资讯", "助手",
                    "Bot", "机器人", "服务号"
                ]
                
                # 判断群聊人数的正则表达式
                group_member_pattern = r'.*[（\(](\d+)[\)）]$'
                
                # 判断顺序：系统账号 > 公众号 > 群聊 > 私聊
                if title in system_accounts:
                    self.logger.info(f"检测到系统账号: {title}")
                    return CHAT_TYPE['SYSTEM'], "系统账号"
                elif any(x in title for x in public_indicators):
                    self.logger.info(f"检测到公众号: {title}")
                    return CHAT_TYPE['PUBLIC'], "公众号"
                elif any(x in title for x in group_indicators):
                    self.logger.info(f"检测到群聊(关键词匹配): {title}")
                    return CHAT_TYPE['GROUP'], "群聊"
                else:
                    # 检查群成员数量
                    match = re.search(group_member_pattern, title)
                    if match:
                        member_count = int(match.group(1))
                        if member_count > 1:
                            self.logger.info(f"检测到群聊(成员数量 {member_count}): {title}")
                            return CHAT_TYPE['GROUP'], "群聊"
                    
                    self.logger.info(f"判定为私聊: {title}")
                    return CHAT_TYPE['PRIVATE'], "私聊"
            
            chat_type, type_name = get_chat_type(title)
            self.logger.info(f"当前聊天: {title} (类型: {type_name})")
            
            return {
                "chat_name": title,
                "chat_type": chat_type
            }
            
        except Exception as e:
            self.logger.error(f"获取聊天信息时出错: {e}")
            return None
            
    def _get_media_path(self, msg_type, file_id):
        """获取媒体文件存储路径"""
        type_folder = {
            2: 'images',
            3: 'videos',
            4: 'files'
        }.get(msg_type, 'others')
        
        return os.path.join(self.media_path, type_folder, file_id)
    
    def _parse_message(self, msg_control):
        """解析单条消息"""
        try:
            self.logger.debug("="*50)
            self.logger.debug(f"正在解析消息控件: {msg_control.Name}")
            
            # 打印完整的控件树结构
            def print_control_tree(control, level=0):
                self.logger.debug("  "*level + f"- {control.ControlType}: {control.Name}")
                for child in control.GetChildren():
                    print_control_tree(child, level + 1)
            
            print("\n控件树结构:")
            print_control_tree(msg_control)
            
            # 递归遍历所有子控件
            def traverse_controls(control):
                results = []
                try:
                    if control.Name:  # 如果控件有名称
                        results.append((control.ControlType, control.Name))
                except:
                    pass
                    
                # 递归遍历子控件
                for child in control.GetChildren():
                    results.extend(traverse_controls(child))
                return results
                
            # 获取所有控件信息
            all_controls = traverse_controls(msg_control)
            self.logger.debug("\n所有控件信息:")
            for control_type, name in all_controls:
                self.logger.debug(f"类型: {control_type}, 名称: {name}")
            
            # 初始化变量
            sender = None
            time_str = None
            msg_type = 1  # 默认文本类型
            file_id = None
            original_time = None  # 记录原始时间
            
            # 获取所有唯一的名称
            unique_names = set()
            sender_name = None
            
            # 第一次遍历：找到sender
            for control_type, name in all_controls:
                if control_type == 50000 and not sender:
                    sender = name
                    sender_name = name
                    break
            
            # 第二次遍历：收集所有唯一名称和处理时间
            for control_type, name in all_controls:
                try:
                    # 跳过空名称
                    if not name:
                        continue
                    
                    # 检查时间格式
                    if not time_str and (
                        re.match(r'^\d{2}:\d{2}$', name) or
                        re.match(r'^星期[一二三四五六日] \d{2}:\d{2}$', name) or
                        re.match(r'^\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}$', name)
                    ):
                        time_str = name
                        original_time = self._parse_time(time_str)
                        if original_time:
                            self.last_time = original_time
                        continue
                    
                    # 识别消息类型
                    if "图片" in name:
                        msg_type = 2
                        file_id = f"img_{int(time.time())}.jpg"
                        file_path = self._get_media_path(msg_type, file_id)
                        content = f"[图片] {file_path}"
                        self.logger.info(f"图片将保存至: {file_path}")
                    elif "视频" in name:
                        msg_type = 3
                        file_id = f"video_{int(time.time())}.mp4"
                        file_path = self._get_media_path(msg_type, file_id)
                        content = f"[视频] {file_path}"
                        self.logger.info(f"视频将保存至: {file_path}")
                    elif "文件" in name:
                        msg_type = 4
                        file_id = f"file_{int(time.time())}"
                        file_path = self._get_media_path(msg_type, file_id)
                        content = f"[文件] {file_path}"
                        self.logger.info(f"文件将保存至: {file_path}")
                    else:
                        unique_names.add(name)
                    
                except Exception as e:
                    self.logger.error(f"解析控件出错: {e}")
                    continue
            
            # 从唯一名称集合中移除sender_name
            if sender_name:
                unique_names.discard(sender_name)
            
            # 获取content（排除sender后的最长文本）
            content = max(unique_names, key=len) if unique_names else None
            
            if sender or content:  # 放宽条件，允许部分信息缺失
                # 使用最后记录的时间或当前时间
                send_time = original_time or self.last_time or datetime.now()
                
                result = {
                    "sender_name": sender or "未知发送者",
                    "send_time": send_time,
                    "content": content or "未知内容",
                    "msg_type": msg_type
                }
                if file_id:
                    result["file_id"] = file_id
                    
                self.logger.info(f"解析结果: {result}")
                return result
            else:
                self.logger.warning(f"消息信息不完整: sender={sender}, time={time_str}, content={content}")
                return None
                
        except Exception as e:
            self.logger.error(f"解析消息失败: {e}")
            return None
            
    def _parse_time(self, time_str):
        """解析时间字符串"""
        patterns = {
            r'^\d{2}:\d{2}$': '%H:%M',
            r'^星期[一二三四五六日] \d{2}:\d{2}$': '%w %H:%M',
            r'^\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}$': '%Y年%m月%d日 %H:%M'
        }
        
        for pattern, time_format in patterns.items():
            if re.match(pattern, time_str):
                try:
                    return datetime.strptime(time_str, time_format)
                except:
                    continue
        return None 

    def get_messages(self):
        """获取聊天消息"""
        if not self.wx_window:
            self.logger.warning("未找到微信窗口")
            return []
        
        messages = []
        try:
            # 获取消息列表区域
            message_list = self.wx_window.ListControl(Name="消息")
            if not message_list.Exists(maxSearchSeconds=2):
                self.logger.warning("未找到消息列表")
                return []
            
            # 打印调试信息
            self.logger.info(f"找到消息列表，子元素数量: {len(message_list.GetChildren())}")
            
            # 遍历消息
            for msg in message_list.GetChildren():
                try:
                    content = self._parse_message(msg)
                    if content:
                        messages.append(content)
                except Exception as e:
                    self.logger.error(f"解析单条消息时出错: {e}")
                    continue
                
            return messages
        except Exception as e:
            self.logger.error(f"获取消息列表时出错: {e}")
            return []