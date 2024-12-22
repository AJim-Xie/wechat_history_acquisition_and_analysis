import uiautomation as auto
import time
from datetime import datetime
import re

class WeChatMonitor:
    def __init__(self):
        self.wx_window = None
        self.chat_window = None
        # 设置全局超时时间
        auto.SetGlobalSearchTimeout(2)
        
    def find_wechat(self):
        """查找微信主窗口"""
        try:
            self.wx_window = auto.WindowControl(Name="微信")
            if self.wx_window.Exists(maxSearchSeconds=3):
                print("找到微信窗口")
                return True
            else:
                print("未找到微信窗口")
                return False
        except Exception as e:
            print(f"查找微信窗口时出错: {e}")
            return False
    
    def get_current_chat(self):
        """获取当前聊天窗口信息"""
        if not self.wx_window:
            return None
            
        try:
            # 尝试获取聊天窗口的标题
            chat_name_control = self.wx_window.ButtonControl(Name="聊天信息")
            if not chat_name_control.Exists(maxSearchSeconds=2):
                print("未找到聊天信息按钮")
                return None
                
            title = chat_name_control.Name
            print(f"当前聊天: {title}")
            
            # 判断是群聊还是私聊
            is_group = "[群聊]" in title
            
            return {
                "chat_name": title,
                "chat_type": 2 if is_group else 1
            }
        except Exception as e:
            print(f"获取聊天信息时出错: {e}")
            return None
    
    def get_messages(self):
        """获取聊天消息"""
        if not self.wx_window:
            return []
            
        messages = []
        try:
            # 获取消息列表区域
            message_list = self.wx_window.ListControl(Name="消息")
            if not message_list.Exists(maxSearchSeconds=2):
                print("未找到消息列表")
                return []
                
            # 打印调试信息
            print(f"找到消息列表，子元素数量: {len(message_list.GetChildren())}")
            
            # 遍历消息
            for msg in message_list.GetChildren():
                try:
                    content = self._parse_message(msg)
                    if content:
                        messages.append(content)
                except Exception as e:
                    print(f"解析单条消息时出错: {e}")
                    continue
                    
            return messages
        except Exception as e:
            print(f"获取消息列表时出错: {e}")
            return []
    
    def _parse_message(self, msg_control):
        """解析单条消息"""
        try:
            # 打印控件信息用于调试
            print(f"正在解析消息控件: {msg_control.Name}")
            
            # 获取所有子控件
            children = msg_control.GetChildren()
            print(f"消息控件子元素数量: {len(children)}")
            
            # 遍历查找所需信息
            sender = None
            time_str = None
            content = None
            
            for child in children:
                try:
                    if "发送者" in child.Name:
                        sender = child.Name
                    elif re.match(r'^\d{2}:\d{2}$', child.Name) or \
                         re.match(r'^星期[一二三四五六日] \d{2}:\d{2}$', child.Name) or \
                         re.match(r'^\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}$', child.Name):
                        time_str = child.Name
                    else:
                        content = child.Name
                except Exception:
                    continue
            
            if sender and time_str and content:
                send_time = self._parse_time(time_str)
                return {
                    "sender_name": sender,
                    "send_time": send_time,
                    "content": content,
                    "msg_type": 1
                }
            else:
                print(f"消息信息不完整: sender={sender}, time={time_str}, content={content}")
                return None
                
        except Exception as e:
            print(f"解析消息失败: {e}")
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