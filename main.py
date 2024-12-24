from src.wx_monitor import WeChatMonitor
from src.db_handler import DatabaseHandler
from src.data_analyzer import DataAnalyzer
import uiautomation as auto
import time
import sys
from datetime import datetime

def select_or_create_chat(db):
    """选择或创建聊天对象"""
    while True:
        print("\n=== 选择聊天对象 ===")
        print("1. 选择已有聊天对象")
        print("2. 新增聊天对象")
        print("0. 退出程序")
        
        choice = input("\n请输入选项(0-2): ")
        
        if choice == '0':
            return None
            
        if choice == '1':
            # 显示已有聊天对象列表
            chats = db.get_all_chats()
            if not chats:
                print("当前没有已记录的聊天对象")
                continue
                
            print("\n可用的聊天列表：")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
            
            chat_choice = input("\n请选择聊天序号: ")
            if chat_choice.isdigit() and 0 < int(chat_choice) <= len(chats):
                return chats[int(chat_choice)-1]
            print("无效的选择")
            
        elif choice == '2':
            # 新增聊天对象
            chat_name = input("\n请输入聊天对象名称: ")
            if not chat_name:
                print("名称不能为空")
                continue
                
            # 检查是否已存在
            existing_chat = db.get_chat_by_name(chat_name)
            if existing_chat:
                print(f"该聊天对象已存在: {chat_name}")
                continue
                
            # 创建新的聊天对象
            chat_id = db.create_chat(chat_name)
            return {
                'chat_id': chat_id,
                'chat_name': chat_name,
                'chat_type': 1  # 默认为私聊
            }

def main():
    monitor = WeChatMonitor()
    db = DatabaseHandler()
    
    # 查找微信窗口
    if not monitor.find_wechat():
        monitor.logger.error("未找到微信窗口，请确保微信已登录")
        return
        
    while True:
        # 选择或创建聊天对象
        chat = select_or_create_chat(db)
        if not chat:
            break
            
        monitor.logger.info(f"已选择聊天对象: {chat['chat_name']}")
        
        while True:
            # 获取当前聊天标题
            chat_title = monitor.get_chat_title()
            if chat_title and chat_title != chat['chat_name']:
                # 更新chat_name
                db.update_chat_name(chat['chat_id'], chat_title)
                chat['chat_name'] = chat_title
                monitor.logger.info(f"更新聊天名称为: {chat_title}")
            
            # 获取并保存消息
            messages = monitor.get_messages(db.get_last_message_time(chat['chat_id']))
            if messages:
                monitor.logger.info(f"获取到 {len(messages)} 条新消息")
                for msg in messages:
                    if msg:
                        db.save_message(chat['chat_id'], msg)
            
            # 询问是否继续
            choice = input("\n是否继续获取消息？(y/n): ")
            if choice.lower() != 'y':
                break
        
        # 询问是否选择其他聊天对象
        choice = input("\n是否选择其他聊天对象？(y/n): ")
        if choice.lower() != 'y':
            break
    
    monitor.logger.info("程序已退出")

if __name__ == "__main__":
    main() 