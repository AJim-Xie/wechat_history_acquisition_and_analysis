from src.wx_monitor import WeChatMonitor
from src.db_handler import DatabaseHandler
import uiautomation as auto
import time

def main():
    try:
        monitor = WeChatMonitor(
            log_path="logs",
            media_path="data/media"
        )
        db = DatabaseHandler()
        
        # 查找微信窗口
        if not monitor.find_wechat():
            monitor.logger.error("未找到微信窗口，请确保微信已登录")
            return
            
        monitor.logger.info("开始监控微信消息...")
        
        error_count = 0
        last_chat_id = None
        last_message_time = None
        
        while True:
            try:
                # 获取当前聊天信息
                chat_info = monitor.get_current_chat()
                if not chat_info:
                    monitor.logger.info("等待切换到有效的聊天窗口...")
                    time.sleep(2)
                    continue
                
                # 获取或创建chat_id
                chat_id = db.get_chat_id(chat_info['chat_name'], chat_info['chat_type'])
                
                # 如果切换了聊天窗口，重置最后消息时间
                if chat_id != last_chat_id:
                    last_message_time = db.get_last_message_time(chat_id)
                    last_chat_id = chat_id
                    monitor.logger.info(f"切换到新的聊天窗口，最后消息时间: {last_message_time}")
                
                # 获取并保存消息
                messages = monitor.get_messages(last_message_time)
                if messages:
                    monitor.logger.info(f"获取到 {len(messages)} 条新消息")
                    for msg in messages:
                        if msg:
                            db.save_message(chat_id, msg)
                            # 更新最后消息时间
                            if not last_message_time or msg['send_time'] > last_message_time:
                                last_message_time = msg['send_time']
                
                error_count = 0  # 重置错误计数
                time.sleep(1)  # 避免过于频繁的检查
                
            except KeyboardInterrupt:
                monitor.logger.info("\n程序已停止")
                break
            except Exception as e:
                error_count += 1
                monitor.logger.error(f"发生错误 ({error_count}): {e}")
                if error_count > 5:
                    monitor.logger.error("错误次数过多，程序退出")
                    break
                time.sleep(5)  # 发生错误时等待较长时间
        
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"程序出错: {e}")
    finally:
        # 清理资源
        if 'monitor' in locals():
            monitor.logger.info("正在清理资源...")
        auto.SetGlobalSearchTimeout(2.0)

if __name__ == "__main__":
    main() 