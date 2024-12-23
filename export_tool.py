from src.db_handler import DatabaseHandler
from src.data_analyzer import DataAnalyzer
from datetime import datetime

def main():
    db = DatabaseHandler()
    analyzer = DataAnalyzer()
    
    print("=== 微信聊天记录导出工具 ===")
    
    # 显示可用的聊天列表
    print("\n可用的聊天列表：")
    chats = db.get_all_chats()
    for i, chat in enumerate(chats, 1):
        print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
    
    # 获取用户选择
    choice = input("\n请选择要导出的聊天序号（直接回车导出所有）：")
    chat_id = None
    if choice.isdigit() and 0 < int(choice) <= len(chats):
        chat_id = chats[int(choice)-1]['chat_id']
    
    # 选择导出格式
    format_type = input("请选择导出格式(1:CSV 2:JSON)：")
    format_type = 'csv' if format_type == '1' else 'json'
    
    # 输入时间范围
    print("\n请输入时间范围（直接回车表示不限制）：")
    start_date = input("开始日期(YYYY-MM-DD)：")
    end_date = input("结束日期(YYYY-MM-DD)：")
    
    # 处理日期
    start_time = None
    end_time = None
    try:
        if start_date:
            start_time = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_time = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print("日期格式错误，请使用YYYY-MM-DD格式")
        return
    
    # 导出文件
    try:
        export_file = analyzer.export_chat(
            chat_id=chat_id,
            start_time=start_time,
            end_time=end_time,
            format=format_type
        )
        print(f"\n导出成功！文件保存在：{export_file}")
    except Exception as e:
        print(f"导出失败：{e}")

if __name__ == "__main__":
    main() 