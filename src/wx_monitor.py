import uiautomation as auto
import time
from datetime import datetime, timedelta
import re
import logging
import os
import sys

class WeChatMonitor:
    def __init__(self, log_path="logs", media_path="data/media"):
        self.wx_window = None
        self.chat_window = None
        self.last_time = None
        auto.SetGlobalSearchTimeout(2)
        
        # 获取程序运行路径
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境路径
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 使用绝对路径
        self.log_path = os.path.join(base_path, log_path)
        self.media_path = os.path.join(base_path, media_path)
        
        # 设置日志
        os.makedirs(self.log_path, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(f"{self.log_path}/wx_monitor.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 设置媒体文件存储路径
        os.makedirs(self.media_path, exist_ok=True)
        for folder in ['images', 'videos', 'files']:
            os.makedirs(f"{self.media_path}/{folder}", exist_ok=True)
        
    def find_wechat(self):
        """查找微信主窗口"""
        try:
            # 设置较短的超时时间
            auto.SetGlobalSearchTimeout(1.0)
            
            # 先尝试通过类名查找
            try:
                self.wx_window = auto.WindowControl(
                    searchDepth=1, 
                    ClassName='WeChatMainWndForPC',
                    searchInterval=0.5  # 减少搜索间隔
                )
                if self.wx_window.Exists(maxSearchSeconds=1):
                    self.logger.info("通过类名找到微信窗口")
                    return True
            except Exception as e:
                self.logger.debug(f"通过类名查找失败: {e}")
            
            # 如果通过类名找不到，再尝试通过窗口名查找
            try:
                self.wx_window = auto.WindowControl(
                    searchDepth=1, 
                    Name="微信",
                    searchInterval=0.5  # 减少搜索间隔
                )
                if self.wx_window.Exists(maxSearchSeconds=1):
                    self.logger.info("通过窗口名找到微信窗口")
                    return True
            except Exception as e:
                self.logger.debug(f"通过窗口名查找失败: {e}")
            
            self.logger.warning("未找到微信窗口")
            return False
            
        except KeyboardInterrupt:
            self.logger.info("用户中断操作")
            return False
        except Exception as e:
            self.logger.error(f"查找微信窗口时出错: {e}")
            return False
        finally:
            # 恢复默认超时时间
            auto.SetGlobalSearchTimeout(2.0)
    
    def get_current_chat(self):
        """获取当前聊天窗口信息"""
        if not self.wx_window:
            return None
        
        try:
            # 设置较短的超时时间
            auto.SetGlobalSearchTimeout(1.0)
            
            # 获取聊天信息按钮
            chat_name_control = self.wx_window.ButtonControl(
                Name="聊天信息",
                searchInterval=0.5
            )
            if not chat_name_control.Exists(maxSearchSeconds=1):
                self.logger.warning("未找到聊天信息按钮")
                return None
            
            title = chat_name_control.Name
            self.logger.info(f"原始聊天标题: {title}")
            
            # 点击聊天信息按钮
            try:
                chat_name_control.Click(simulateMove=False)
                time.sleep(0.8)  # 等待管理页面打开
                
                # 查找群聊特征控件
                group_features = [
                    ("ButtonControl", "查看全部群成员"),
                    ("ButtonControl", "群聊名称"),
                    ("TextControl", "群公告"),
                    ("ButtonControl", "群管理"),
                    ("ButtonControl", "全部群成员"),
                    ("ButtonControl", "保存到通讯录"),  # 群聊特有
                    ("TextControl", "群聊成员"),  # 群聊特有
                    ("ButtonControl", "删除退出"),  # 群聊特有
                ]
                
                is_group = False
                found_features = []  # 用于记录找到的群聊特征
                
                # 遍历所有群聊特征
                for control_type, name in group_features:
                    try:
                        control = getattr(self.wx_window, control_type)(Name=name)
                        if control.Exists(maxSearchSeconds=0.2):
                            found_features.append(name)
                            is_group = True  # 只要找到任一特征就判定为群聊
                            self.logger.info(f"找到群聊特征: {name}")
                    except Exception as e:
                        self.logger.debug(f"查找特征 {name} 时出错: {e}")
                        continue
                
                # 再次点击聊天信息按钮关闭管理页面
                chat_name_control.Click(simulateMove=False)
                time.sleep(0.3)  # 等待管理页面关闭
                
                chat_type = 2 if is_group else 1
                self.logger.info(f"聊天类型判定为: {'群聊' if chat_type == 2 else '私聊'}")
                if found_features:
                    self.logger.info(f"找到的群聊特征: {', '.join(found_features)}")
                else:
                    self.logger.info("未找到任何群聊特征，判定为私聊")
                
                return {
                    "chat_name": title,
                    "chat_type": chat_type
                }
                
            except Exception as e:
                self.logger.error(f"检查群聊特征时出错: {e}")
                # 尝试关闭管理页面
                try:
                    chat_name_control.Click(simulateMove=False)
                    time.sleep(0.3)
                except:
                    pass
                return None
                
        except Exception as e:
            self.logger.error(f"获取聊天信息失败: {e}")
            return None
        finally:
            auto.SetGlobalSearchTimeout(2.0)
    
    def _get_media_path(self, msg_type, file_id):
        """获取媒体文件保存路径"""
        type_folder = {
            2: 'images',
            3: 'videos',
            4: 'files',
            5: 'voices',
            6: 'emoticons'
        }.get(msg_type, 'others')
        
        folder_path = os.path.join(self.media_path, type_folder)
        os.makedirs(folder_path, exist_ok=True)
        return os.path.join(folder_path, file_id)
    
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
                    if name == "查看更多消息":
                        # 记录"查看更多消息"，但发送者和发送时间置空
                        result = {
                            "sender_name": None,
                            "send_time": None,
                            "content": "查看更多消息",
                            "msg_type": 1  # 使用默认文本类型
                        }
                        self.logger.debug("记录'查看更多消息'控件")
                        return result
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
                        re.match(r'^\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}$', name) or
                        re.match(r'^昨天 \d{2}:\d{2}$', name)
                    ):
                        time_str = name
                        original_time = self._parse_time(time_str)
                        if original_time:
                            self.last_time = original_time
                        continue
                    
                    # 将所有非时间的文本添加到唯一名称集合
                    unique_names.add(name)
                    
                except Exception as e:
                    self.logger.error(f"解析控件出错: {e}")
                    continue
            
            # 从唯一名称集合中移除sender_name
            if sender_name:
                unique_names.discard(sender_name)
            
            # 获取content（排序sender后的最长文本）
            content = max(unique_names, key=len) if unique_names else None
            
            # 如果content未知，根据控件类型识别消息类型
            if content == "未知内容" or not content:
                for control_type, name in all_controls:
                    try:
                        if not name:
                            continue
                            
                        # 根据控件类型识别特殊消息类型
                        if control_type == 50001:  # 图片控件类型
                            msg_type = 2
                            file_id = f"img_{int(time.time())}.jpg"
                            file_path = self._get_media_path(msg_type, file_id)
                            content = f"[图片]"
                            self.logger.info(f"图片将保存至: {file_path}")
                            break
                        elif control_type == 50002:  # 视频控件类型
                            msg_type = 3
                            file_id = f"video_{int(time.time())}.mp4"
                            file_path = self._get_media_path(msg_type, file_id)
                            content = f"[视频]"
                            self.logger.info(f"视频将保存至: {file_path}")
                            break
                        elif control_type == 50003:  # 文件控件类型
                            msg_type = 4
                            file_id = f"file_{int(time.time())}"
                            content = f"[文件]"
                            file_path = self._get_media_path(msg_type, file_id)
                            self.logger.info(f"文件将保存至: {file_path}")
                            break
                        elif control_type == 50004:  # 语音控件类型
                            msg_type = 5
                            file_id = f"voice_{int(time.time())}.mp3"
                            file_path = self._get_media_path(msg_type, file_id)
                            content = f"[语音]"
                            self.logger.info(f"语音将保存至: {file_path}")
                            break
                        elif control_type == 50005:  # 表情控件类型
                            msg_type = 6
                            content = "[表情]"
                            self.logger.info(f"检测到表情消息")
                            break
                        elif control_type == 50006:  # 转发消息控件类型
                            msg_type = 7
                            content = "[转发的聊天记录]"
                            self.logger.info(f"检测到转发消息")
                            break
                    except Exception as e:
                        self.logger.error(f"解析控件出错: {e}")
                        continue
            
            # 检查是否为时间消息
            is_time_message = content and (
                re.match(r'^\d{1,2}:\d{2}$', content) or  # 修改正则以支持单位数小时
                re.match(r'^星期[一二三四五六日] \d{1,2}:\d{2}$', content) or
                re.match(r'^\d{4}年\d{2}月\d{2}日 \d{1,2}:\d{2}$', content) or
                re.match(r'^昨天 \d{1,2}:\d{2}$', content)
            )
            
            if sender or content:  # 放宽条件，允许部分信息缺失
                # 如果找到未知发送者且内容是时间格式，则更新发送时间
                if (sender == "未知发送者" or not sender) and is_time_message:
                    # 获取当前日期
                    current_date = datetime.now().date()
                    
                    # 解析时间字符串
                    if re.match(r'^\d{1,2}:\d{2}$', content):
                        # 处理纯时间格式 (H:MM 或 HH:MM)
                        hour, minute = map(int, content.split(':'))
                        send_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                    else:
                        # 其他时间格式使用现有的解析方法
                        parsed_time = self._parse_time(content)
                        if parsed_time:
                            send_time = parsed_time
                        else:
                            send_time = original_time or self.last_time or datetime.now()
                    
                    self.last_time = send_time
                else:
                    send_time = original_time or self.last_time or datetime.now()
                
                result = {
                    "sender_name": sender or "未知发送者",
                    "send_time": send_time,
                    "content": content or "[未知类型消息]",
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
        try:
            now = datetime.now()
            
            # 如果是"昨天 HH:MM"格式
            if re.match(r'^昨天 \d{2}:\d{2}$', time_str):
                hour, minute = map(int, time_str.split(' ')[1].split(':'))
                yesterday = now - timedelta(days=1)
                return datetime(yesterday.year, yesterday.month, yesterday.day, hour, minute)
            
            # 如果只有时分格式 (HH:MM)，使用当天日期
            if re.match(r'^\d{2}:\d{2}$', time_str):
                hour, minute = map(int, time_str.split(':'))
                return datetime(now.year, now.month, now.day, hour, minute)
            
            # 如果是星期+时分格式 (星期X HH:MM)
            if re.match(r'^星期[一二三四五六日] \d{2}:\d{2}$', time_str):
                weekday_map = {'一':0, '二':1, '三':2, '四':3, '五':4, '六':5, '日':6}
                weekday = weekday_map[time_str[2]]
                hour, minute = map(int, time_str.split(' ')[1].split(':'))
                
                # 计算目标日期
                days_diff = (weekday - now.weekday()) % 7
                target_date = now - timedelta(days=days_diff)
                return datetime(target_date.year, target_date.month, target_date.day, hour, minute)
            
            # 如果是完整日期格式 (YYYY年MM月DD日 HH:MM)
            if re.match(r'^\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}$', time_str):
                return datetime.strptime(time_str, '%Y年%m月%d日 %H:%M')
            
            self.logger.warning(f"未知的时间格式: {time_str}")
            return None
            
        except Exception as e:
            self.logger.error(f"解析时间失败: {time_str}, 错误: {e}")
            return None

    def get_messages(self, last_time=None):
        """获取聊天消息"""
        if not self.wx_window:
            self.logger.warning("未找到微信窗口")
            return []
        
        messages = []
        message_hash_set = set()  # 用消息去重
        
        try:
            # 获取消息列表区域
            message_list = self.wx_window.ListControl(Name="消息")
            if not message_list.Exists(maxSearchSeconds=2):
                self.logger.warning("未找到消息列表")
                return []
            
            # 遍历消息
            for msg in message_list.GetChildren():
                try:
                    content = self._parse_message(msg)
                    if content and content['send_time']:
                        # 生成消息唯一标识
                        msg_hash = f"{content['sender_name']}_{content['send_time']}_{content['content'][:50]}"
                        
                        # 检查是否重复消息
                        if msg_hash in message_hash_set:
                            self.logger.debug(f"跳过重复消息: {msg_hash}")
                            continue
                            
                        # 检查时间
                        if last_time and content['send_time'] <= last_time:
                            self.logger.debug(f"跳过旧消息: {content['send_time']}")
                            continue
                            
                        message_hash_set.add(msg_hash)
                        messages.append(content)
                except Exception as e:
                    self.logger.error(f"解析单条消息时出错: {e}")
                    continue
            
            if messages:
                self.logger.info(f"获取到 {len(messages)} 条新消息")
            return messages
        except Exception as e:
            self.logger.error(f"获取消息列表时出错: {e}")
            return []
    
    def get_chat_title(self):
        """获取当前聊天窗口标题"""
        if not self.wx_window:
            return None
            
        try:
            chat_name_control = self.wx_window.ButtonControl(
                Name="聊天信息",
                searchInterval=0.5
            )
            if chat_name_control.Exists(maxSearchSeconds=1):
                title = chat_name_control.Name
                self.logger.info(f"获取到聊天标题: {title}")
                return title
            return None
        except Exception as e:
            self.logger.error(f"获取聊天标题失败: {e}")
            return None

    def activate_window(self):
        """检查微信窗口是否在前台，如果不在则激活"""
        try:
            if not self.wx_window:
                self.find_wechat()
                if not self.wx_window:
                    self.logger.error("未找到微信窗口")
                    return False
            
            # 检查窗口是否最小化
            pattern = self.wx_window.GetWindowPattern()
            if pattern and pattern.WindowVisualState == 2:  # 2表示最小化
                self.logger.info("微信窗口已最小化，正在还原...")
                self.wx_window.ShowWindow(1)  # 1表示正常显示
                time.sleep(0.5)
            
            # 激活窗口
            try:
                # 尝试直接激活窗口
                self.wx_window.SetActive()
                time.sleep(0.5)
                
                # 确保窗口可见
                if not self.wx_window.Exists():
                    self.logger.error("窗口不可见")
                    return False
                    
                # 移动鼠标到窗口中心以确保焦点
                rect = self.wx_window.BoundingRectangle
                center_x = (rect.left + rect.right) // 2
                center_y = (rect.top + rect.bottom) // 2
                auto.MoveTo(center_x, center_y)
                time.sleep(0.2)
                
                return True
                
            except Exception as e:
                self.logger.error(f"激活窗口时出错: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"激活窗口失败: {e}")
            return False

    def open_chat_by_name(self, chat_name):
        """通过名称打开指定的聊天窗口"""
        try:
            # 首先确保窗口在前台
            if not self.activate_window():
                return False
            
            # 1. 点击通讯录按钮
            contact_btn = self.wx_window.ButtonControl(Name="通讯录")
            if not contact_btn.Exists(maxSearchSeconds=2):
                self.logger.error("未找到通讯录按钮")
                return False
            contact_btn.Click()
            time.sleep(1)  # 等待通讯录加载
            
            # 2. 找到搜索框并输入聊天对象名称
            search_box = self.wx_window.EditControl(Name="搜索")
            if not search_box.Exists(maxSearchSeconds=2):
                self.logger.error("未找到搜索框")
                return False
            
            search_box.Click()
            time.sleep(0.5)
            auto.SendKeys(chat_name)
            time.sleep(0.5)
            auto.SendKeys('{Enter}')
            time.sleep(1)  # 等待索结果
            
            # 3. 验证是否进入聊天界面
            chat_name_control = self.wx_window.ButtonControl(Name="聊天信息")
            if not chat_name_control.Exists(maxSearchSeconds=2):
                self.logger.error("未能进入聊天界面")
                return False
            
            # 4. 向上滚动8次
            message_list = self.wx_window.ListControl(Name="消息")
            if message_list.Exists(maxSearchSeconds=2):
                for _ in range(8):
                    message_list.WheelUp(wheelTimes=3)  # 每次滚动3个单位
                    time.sleep(0.4)  # 等待消息加载
            
            self.logger.info(f"成功打开并滚动聊天窗口: {chat_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"打开聊天窗口失败: {e}")
            return False