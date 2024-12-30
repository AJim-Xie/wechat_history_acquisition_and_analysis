from datetime import datetime
import time

def get_chat_messages(self, chat_window, max_scroll=None):
    """获取聊天窗口中的消息
    Args:
        chat_window: 聊天窗口对象
        max_scroll: 最大滚动次数,None表示使用默认值5
    """
    messages = []
    last_position = 0
    scroll_count = 0
    max_scroll = max_scroll or 5  # 默认滚动5次
    
    while True:
        # 获取当前可见的消息元素
        message_elements = chat_window.GetChildren()
        current_position = len(message_elements)
        
        # 如果没有新消息了，就退出循环
        if current_position == last_position:
            break
            
        # 处理新出现的消息
        for element in message_elements[last_position:]:
            message = self._parse_message_element(element)
            if message:
                messages.append(message)
        
        # 更新位置
        last_position = current_position
        
        # 向上滚动
        chat_window.WheelUp(wheelTimes=3)
        time.sleep(0.5)  # 等待加载
        
        scroll_count += 1
        if scroll_count >= max_scroll:  # 达到最大滚动次数
            break
    
    # 按时间排序
    messages.sort(key=lambda x: x['send_time'])
    return messages 

def _parse_message_element(self, element):
    """解析消息元素"""
    try:
        # 获取基本信息
        msg_info = element.GetChildren()
        if not msg_info:
            return None
            
        # 解析时间
        time_str = msg_info[0].Name
        send_time = None
        
        try:
            # 处理时间格式
            if '/' in time_str:
                # 处理 2024/12/18 9:09 格式
                date_parts = time_str.split(' ')
                if len(date_parts) == 2:
                    date_str, time_str = date_parts
                    year, month, day = map(int, date_str.split('/'))
                    hour, minute = map(int, time_str.split(':'))
                    send_time = datetime(year, month, day, hour, minute)
            else:
                # 尝试其他格式
                time_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y/%m/%d %H:%M:%S',
                    '%Y/%m/%d %H:%M'
                ]
                for fmt in time_formats:
                    try:
                        send_time = datetime.strptime(time_str, fmt)
                        break
                    except ValueError:
                        continue
                        
            if not send_time:
                raise ValueError(f"无法解析时间: {time_str}")
                
        except Exception as e:
            self.logger.error(f"时间解析失败: {time_str}, 错误: {str(e)}")
            return None
            
        # 构建消息对象
        return {
            'sender_name': msg_info[1].Name if len(msg_info) > 1 else '',
            'content': msg_info[2].Name if len(msg_info) > 2 else '',
            'send_time': send_time,
            'msg_type': self._get_message_type(msg_info)
        }
        
    except Exception as e:
        self.logger.error(f"消息解析失败: {str(e)}")
        return None 