from src.wx_monitor import WeChatMonitor
from src.db_handler import DatabaseHandler
import time

def main():
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
            
            # 获取并保存消息
            messages = monitor.get_messages()
            if messages:
                monitor.logger.info(f"获取到 {len(messages)} 条消息")
                for msg in messages:
                    if msg:
                        db.save_message(chat_id, msg)
            
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

if __name__ == "__main__":
    main() 