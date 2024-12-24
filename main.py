from src.wx_monitor import WeChatMonitor
from src.db_handler import DatabaseHandler
from src.data_analyzer import DataAnalyzer
import uiautomation as auto
import time
import sys
from datetime import datetime, timedelta

def select_or_create_chat(db):
    """选择或创建聊天对象"""
    while True:
        print("\n=== 选择聊天对象 ===")
        print("1. 选择已有聊天对象")
        print("2. 新增聊天对象")
        print("0. 返回上级菜单")
        
        choice = input("\n请输入选项(0-2): ")
        
        if choice == '0':
            return None
            
        if choice == '1':
            # 显示已有聊天对象列表
            chats = db.get_all_chats()
            if not chats:
                print("\n当前没有已记录的聊天对象")
                input("\n按回车键返回上级菜单...")
                continue
                
            print("\n历史聊天对象列表：")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
            print("0. 返回上级菜单")
            
            chat_choice = input("\n请选择聊天序号: ")
            if chat_choice == '0':
                continue
                
            if chat_choice.isdigit() and 0 < int(chat_choice) <= len(chats):
                selected_chat = chats[int(chat_choice)-1]
                print(f"\n已选择: {selected_chat['chat_name']}")
                
                # 展示所有已存储的聊天记录
                print("\n该聊天对象的所有记录：")
                messages = db.get_chat_messages(selected_chat['chat_id'])
                if not messages:
                    print("暂无聊天记录")
                else:
                    for msg in messages:
                        time_str = msg['send_time'].strftime('%Y-%m-%d %H:%M:%S')
                        print(f"[{time_str}] {msg['sender_name']}: {msg['content'][:50]}...")
                
                confirm = input("\n确认选择该聊天对象？(y/n): ")
                if confirm.lower() == 'y':
                    return selected_chat
                continue
            
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

def show_main_menu():
    """显示主菜单"""
    print("\n=== 微信聊天记录工具 ===")
    print("1. 数据采集")
    print("2. 数据分析")
    print("3. 数据导出")
    print("0. 退出程序")
    return input("\n请选择功能(0-3): ")

def show_collection_menu():
    """显示数据采集菜单"""
    print("\n=== 数据采集 ===")
    print("1. 选择已有聊天对象")
    print("2. 新增聊天对象")
    print("0. 返回主菜单")
    return input("\n请选择操作(0-2): ")

def show_analysis_menu():
    """显示数据分析菜单"""
    print("\n=== 数据分析 ===")
    print("1. 基础统计信息")
    print("2. 可视化分析")
    print("3. 自定义分析")
    print("0. 返回主菜单")
    return input("\n请选择操作(0-3): ")

def show_export_menu():
    """显示数据导出菜单"""
    print("\n=== 数据导出 ===")
    print("1. 导出全部数据")
    print("2. 按时间范围导出")
    print("3. 按聊天对象导出")
    print("0. 返回主菜单")
    return input("\n请选择操作(0-3): ")

def collect_data(monitor, db):
    """数据采集功能"""
    while True:
        choice = show_collection_menu()
        
        if choice == '0':
            return
            
        if choice not in ['1', '2']:
            print("无效的选择")
            continue
            
        # 选择或创建聊天对象
        chat = select_or_create_chat(db)
        if not chat:
            continue
            
        monitor.logger.info(f"已选择聊天对象: {chat['chat_name']}")
        
        # 消息采集循环
        while True:
            # 获取当前聊天标题
            chat_title = monitor.get_chat_title()
            if chat_title and chat_title != chat['chat_name']:
                db.update_chat_name(chat['chat_id'], chat_title)
                chat['chat_name'] = chat_title
                monitor.logger.info(f"更新聊天名称为: {chat_title}")
            
            # 获��并保存消息
            messages = monitor.get_messages(db.get_last_message_time(chat['chat_id']))
            if messages:
                monitor.logger.info(f"获取到 {len(messages)} 条新消息")
                for msg in messages:
                    if msg:
                        db.save_message(chat['chat_id'], msg)
            
            # 询问是否继续
            if input("\n是否继续获取消息？(y/n): ").lower() != 'y':
                break

def analyze_data(analyzer):
    """数据分析功能"""
    while True:
        choice = show_analysis_menu()
        
        if choice == '0':
            return
            
        if choice == '1':
            # 基础统计信息
            stats = analyzer.get_basic_stats()
            print("\n=== 基础统计信息 ===")
            print(f"总聊天数: {stats['chat_count']}")
            print(f"总消息数: {stats['message_count']}")
            print(f"活跃用户数: {stats['user_count']}")
            
        elif choice == '2':
            # 可视化分析
            print("\n=== 可视化分析 ===")
            
            # 选择聊天对象
            chats = analyzer.get_all_chats()
            if not chats:
                print("没有可用的聊天记录")
                continue
                
            print("\n可用的聊天列表：")
            print("0. 分析所有聊天")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
            
            chat_choice = input("\n请选择聊天序号: ")
            chat_id = None
            if chat_choice.isdigit():
                if int(chat_choice) > 0 and int(chat_choice) <= len(chats):
                    chat_id = chats[int(chat_choice)-1]['chat_id']
            
            # 选择时间范围
            print("\n请选择分析时间范围：")
            print("1. 最近一周")
            print("2. 最近一月")
            print("3. 最近三月")
            print("4. 自定义时间范围")
            
            time_choice = input("\n请选择(1-4): ")
            start_time = None
            end_time = None
            
            if time_choice in ['1', '2', '3']:
                days = {'1': 7, '2': 30, '3': 90}[time_choice]
                start_time = datetime.now() - timedelta(days=days)
            elif time_choice == '4':
                start_date = input("开始日期(YYYY-MM-DD): ")
                end_date = input("结束日期(YYYY-MM-DD): ")
                try:
                    start_time = datetime.strptime(f"{start_date} 00:00:00", '%Y-%m-%d %H:%M:%S')
                    end_time = datetime.strptime(f"{end_date} 23:59:59", '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print("日期格式错误")
                    continue
            
            # 选择输出目录
            output_dir = input("\n请输入分析结果保存路径（直接回车使用默认路径）: ").strip()
            if not output_dir:
                output_dir = "analysis_results"
            
            try:
                # 执行分析
                result_dir = analyzer.analyze_and_visualize(
                    chat_id=chat_id,
                    start_time=start_time,
                    end_time=end_time,
                    output_dir=output_dir
                )
                
                print(f"\n分析完成！结果保存在：{result_dir}")
                print("\n生成的图表包括：")
                print("1. 消息数量趋势图")
                print("2. 用户活跃度分布图")
                print("3. 消息类型分布图")
                print("4. 关键词词云图")
                print("5. 用户互动热力图")
                if chat_id and any(c['chat_id'] == chat_id and c['chat_type'] == 2 for c in chats):
                    print("6. 群组活跃度分析图")
                
            except Exception as e:
                print(f"分析失败: {e}")
            
        elif choice == '3':
            # 自定义分析
            print("\n=== 自定义分析 ===")
            print("请选择要分析的维度（多选，用逗号分隔）：")
            print("1. 时间维度（消息趋势、活跃时段）")
            print("2. 用户维度（发言排名、活跃度）")
            print("3. 内容维度（消息类型、关键词）")
            print("4. 群组维度（成员互动、话题分析）")
            
            dimensions = input("\n请输入维度编号: ").split(',')
            dimensions = [d.strip() for d in dimensions if d.strip() in ['1', '2', '3', '4']]
            
            if not dimensions:
                print("未选择有效的分析维度")
                continue
            
            # 选择聊天对象
            chats = analyzer.get_all_chats()
            if not chats:
                print("没有可用的聊天记录")
                continue
                
            print("\n可用的聊天列表：")
            print("0. 分析所有聊天")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
            
            chat_choice = input("\n请选择聊天序号: ")
            chat_id = None
            if chat_choice.isdigit():
                if int(chat_choice) > 0 and int(chat_choice) <= len(chats):
                    chat_id = chats[int(chat_choice)-1]['chat_id']
            
            # 选择时间范围
            print("\n请选择分析时间范围：")
            print("1. 最近一周")
            print("2. 最近一月")
            print("3. 最近三月")
            print("4. 自定义时间范围")
            
            time_choice = input("\n请选择(1-4): ")
            start_time = None
            end_time = None
            
            if time_choice in ['1', '2', '3']:
                days = {'1': 7, '2': 30, '3': 90}[time_choice]
                start_time = datetime.now() - timedelta(days=days)
            elif time_choice == '4':
                start_date = input("开始日期(YYYY-MM-DD): ")
                end_date = input("结束日期(YYYY-MM-DD): ")
                try:
                    start_time = datetime.strptime(f"{start_date} 00:00:00", '%Y-%m-%d %H:%M:%S')
                    end_time = datetime.strptime(f"{end_date} 23:59:59", '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print("日期格式错误")
                    continue
            
            try:
                # 执行自定义分析
                results = analyzer.custom_analyze(
                    dimensions=dimensions,
                    chat_id=chat_id,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # 显示分析结果
                print("\n=== 分析结果 ===")
                
                if '1' in dimensions:  # 时间维度
                    print("\n时间维度分析：")
                    print(f"日均消息数: {results['time']['daily_avg']:.1f}")
                    print(f"最活跃的时段: {results['time']['peak_hour']}时")
                    print(f"最不活跃的时段: {results['time']['lowest_hour']}时")
                    print(f"工作日占比: {results['time']['weekday_ratio']:.1%}")
                    print(f"周末占比: {results['time']['weekend_ratio']:.1%}")
                
                if '2' in dimensions:  # 用户维度
                    print("\n用户维度分析：")
                    print("发言最多的用户：")
                    for user in results['user']['top_users']:
                        print(f"  {user['name']}: {user['count']}条消息")
                    print(f"人均发言数: {results['user']['avg_messages']:.1f}")
                
                if '3' in dimensions:  # 内容维度
                    print("\n内容维度分析：")
                    print("消息类型分布：")
                    for msg_type, ratio in results['content']['type_ratio'].items():
                        print(f"  {msg_type}: {ratio:.1%}")
                    print("\n热门关键词：")
                    for word, weight in results['content']['keywords']:
                        print(f"  {word}: {weight:.2f}")
                
                if '4' in dimensions and chat_id:  # 群组维度
                    print("\n群组维度分析：")
                    print(f"群成员数: {results['group']['member_count']}")
                    print(f"活跃成员数: {results['group']['active_member_count']}")
                    print(f"群活跃度: {results['group']['activity_score']:.2f}")
                    print("互动最频繁的成员对：")
                    for pair in results['group']['top_interactions']:
                        print(f"  {pair['users']}: {pair['count']}次互动")
                
            except Exception as e:
                print(f"分析失败: {e}")
            
        input("\n按回车键继续...")

def export_data(analyzer):
    """数据导出功能"""
    while True:
        choice = show_export_menu()
        
        if choice == '0':
            return
            
        export_path = input("\n请输入导出文件路径: ")
        if not export_path:
            print("路径不能为空")
            continue
            
        format_choice = input("请选择导出格式(1:CSV 2:JSON): ")
        if format_choice not in ['1', '2']:
            print("无效的格式选择")
            continue
            
        try:
            if choice == '1':
                # 导出全部数据
                analyzer.export_all(export_path, format_choice == '1')
                
            elif choice == '2':
                # 按时间范围导出
                start_date = input("请输入开始日期(YYYY-MM-DD): ")
                end_date = input("请输入结束日期(YYYY-MM-DD): ")
                analyzer.export_by_time(export_path, start_date, end_date, format_choice == '1')
                
            elif choice == '3':
                # 按聊天对象导出
                chats = analyzer.get_all_chats()
                if not chats:
                    print("没有可用的聊天记录")
                    continue
                    
                print("\n可用的聊天列表：")
                for i, chat in enumerate(chats, 1):
                    print(f"{i}. {chat['chat_name']}")
                
                chat_choice = input("\n请选择聊天序号: ")
                if not chat_choice.isdigit() or not (0 < int(chat_choice) <= len(chats)):
                    print("无效的选择")
                    continue
                    
                analyzer.export_by_chat(
                    export_path, 
                    chats[int(chat_choice)-1]['chat_id'],
                    format_choice == '1'
                )
            
            print(f"\n数据已导出到: {export_path}")
            
        except Exception as e:
            print(f"导出失败: {e}")
        
        input("\n按回车键继续...")

def main():
    """主函数"""
    monitor = WeChatMonitor()
    db = DatabaseHandler()
    analyzer = DataAnalyzer(db)
    
    # 查找微信窗口
    if not monitor.find_wechat():
        print("未找到微信窗口，请确保微信已登录")
        return
    
    while True:
        choice = show_main_menu()
        
        if choice == '0':
            break
            
        elif choice == '1':
            collect_data(monitor, db)
            
        elif choice == '2':
            analyze_data(analyzer)
            
        elif choice == '3':
            export_data(analyzer)
            
        else:
            print("无效的选择")
    
    print("\n程序已退出")

if __name__ == "__main__":
    main() 