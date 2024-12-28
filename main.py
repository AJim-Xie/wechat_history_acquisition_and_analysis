from src.wx_monitor import WeChatMonitor
from src.db_handler import DatabaseHandler
from src.data_analyzer import DataAnalyzer
from src.dict_manager import DictManager
import uiautomation as auto
import time
import sys
from datetime import datetime, timedelta
import os

def select_or_create_chat(db):
    """选择或创建聊天对象"""
    while True:
        print("\n=== 选择聊天对象 ===")
        print("1. 选择已有聊天对象")
        print("2. 新增聊天对象")
        print("3. 修改聊天对象名称")
        print("0. 返回上级菜单")
        
        choice = input("\n请输入选项(0-3): ")
        
        if choice == '0':
            return None
            
        elif choice == '1':
            # 显示已有聊天对象列表
            chats = db.get_all_chats()
            if not chats:
                print("\n当前没有已记录的聊天对象")
                input("\n按回车键返回上级菜单...")
                continue
                
            print("\n历史聊天对象列表：")
            for i, chat in enumerate(chats, 1):
                msg_count = chat['msg_count'] or 0
                last_active = chat['last_active'] or '从未活跃'
                if last_active != '从未活跃':
                    try:
                        last_active = datetime.strptime(last_active, '%Y-%m-%d %H:%M:%S.%f')
                        last_active = last_active.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                print(f"{i}. {chat['chat_name']} ({msg_count}条消息, 最后活跃: {last_active})")
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
            
            # 创建新的聊天对象，返回值包含可能经过冲突处理的实际名称
            chat_id, actual_name = db.create_chat(chat_name)
            if actual_name != chat_name:
                print(f"\n由于名称冲突，实际创建的名称为: {actual_name}")
            
            return {
                'chat_id': chat_id,
                'chat_name': actual_name,
                'chat_type': 1  # 默认为私聊
            }
            
        elif choice == '3':
            # 修改聊天对象名称
            chats = db.get_all_chats()
            if not chats:
                print("\n当前没有已记录的聊天对象")
                input("\n按回车键返回���级菜单...")
                continue
            
            print("\n当前聊天对象列表：")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. {chat['chat_name']}")
            
            chat_choice = input("\n请选择要修改的聊天序号: ")
            if not chat_choice.isdigit() or not (0 < int(chat_choice) <= len(chats)):
                print("无效的选择")
                continue
            
            selected_chat = chats[int(chat_choice)-1]
            new_name = input(f"\n请输入新的名称 (当前: {selected_chat['chat_name']}): ")
            if not new_name:
                print("名称不能为空")
                continue
            
            # 更新名称，返回值是可能经过冲突处理的实际名称
            actual_name = db.update_chat_name(selected_chat['chat_id'], new_name)
            if actual_name != new_name:
                print(f"\n由于名称冲突，实际更新的名称为: {actual_name}")
            else:
                print("\n名称更新成功")
            
            continue

def show_main_menu():
    """显示主菜单"""
    print("\n=== 微信聊天记录工具 ===")
    print("1. 数据采集")
    print("2. 数据分析")
    print("3. 数据导出")
    print("4. 数据清理")
    print("5. 词典管理")
    print("6. 聊天记录搜索")
    print("0. 退出程序")
    return input("\n请选择功能(0-6): ")

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
    print("3. 导出分析报告")
    print("4. 词频分析")
    print("5. 情感分析")
    print("6. 搜索聊天记录")
    print("0. 返回上级菜单")
    return input("\n请选择功能(0-6): ")

def show_export_menu():
    """显示数据导出菜单"""
    print("\n=== 数据导出 ===")
    print("1. 导出全部数据")
    print("2. 按时间范围导出")
    print("3. 按聊天对象导出")
    print("0. 返回主菜单")
    return input("\n请选择操作(0-3): ")

def show_dict_menu():
    """显示词典管理菜单"""
    print("\n=== 词典管理 ===")
    print("1. 查看词典内容")
    print("2. 添加新词")
    print("3. 删除词条")
    print("4. 更新词频")
    print("5. 备份词典")
    print("6. 恢复备份")
    print("7. 合并词典")
    print("8. 词典可视化")
    print("0. 返回主菜单")
    return input("\n请选择操作(0-8): ")

def collect_data(monitor, db):
    """收集聊天数据"""
    # 获取聊天对象
    chat = select_or_create_chat(db)
    if not chat:
        return
        
    print(f"\n准备监控聊天: {chat['chat_name']}")
    
    # 确保微信窗口在前台
    if not monitor.activate_window():
        print("无法激活微信窗口，请确保微信已正常运行")
        return
    
    # 自动打开聊天窗口
    if not monitor.open_chat_by_name(chat['chat_name']):
        print("无法自动打开聊天窗口，请手动打开后重试")
        return
    
    print(f"\n开始监控聊天: {chat['chat_name']}")
    
    # 获取最后一条消息的时间
    last_time = db.get_last_message_time(chat['chat_id'])
    if last_time:
        print(f"将从 {last_time} 开始获取新消息")
    
    try:
        while True:
            # 获取当前聊天窗口标题
            chat_title = monitor.get_chat_title()
            if not chat_title:
                print("未检测到聊天窗口，请确保正确的聊天窗口处于活动状态")
                time.sleep(2)
                continue
            
            # 获取新消息
            messages = monitor.get_messages(last_time)
            if messages:
                # 使用用户输入的名称或自动获取的名称
                chat_id = db.get_chat_id(chat_title, chat['chat_type'], chat['chat_name'])
                
                # 保存息，过滤未知发送者
                saved_count = 0
                for msg in messages:
                    if msg['sender_name'] and msg['sender_name'].strip():
                        db.save_message(chat_id, msg)
                        last_time = msg['send_time']
                        saved_count += 1
                print(f"已保存 {saved_count} 条新消息")
                if saved_count < len(messages):
                    print(f"已过滤 {len(messages) - saved_count} 条未知发送者的消息")
            else:
                print("本次扫描未发现新消息")
            
            time.sleep(1)  # 等待1秒
            
            # 每次扫描后询问用户是否继续
            choice = input("\n是否继续获取消息？(y/n): ")
            if choice.lower() != 'y':
                print("\n停止获取消息")
                return
            
    except KeyboardInterrupt:
        print("\n停止监控")

def analyze_data(analyzer, db, dict_manager):
    """数据分析功能"""
    while True:
        choice = show_analysis_menu()
        
        if choice == '0':
            return
            
        elif choice == '1':
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
            chats = analyzer.db.get_all_chats()
            if not chats:
                print("没有可用的聊天记录")
                continue
                
            print("\n可用的聊天列表：")
            print("0. 分析所有聊天")
            for i, chat in enumerate(chats, 1):
                chat_type = '群聊' if chat['chat_type'] == 2 else '私聊'
                msg_count = chat['msg_count']
                chat_name = chat['chat_name'].replace('聊天信息', '') if chat['chat_name'].endswith('聊天信息') else chat['chat_name']
                print(f"{i}. {chat_name} ({chat_type}, {msg_count}条消息)")
            
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
            print("1. 时间维度（信息趋势、活跃时段）")
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
            
        elif choice == '4':
            # 生成思维导图
            print("\n=== 生成思维导图 ===")
            
            # 选择聊天对象
            chats = analyzer.db.get_all_chats()
            if not chats:
                print("没有可用的聊天记录")
                continue
                
            print("\n可用的聊天列表：")
            for i, chat in enumerate(chats, 1):
                chat_type = '群聊' if chat['chat_type'] == 2 else '私聊'
                chat_name = chat['chat_name'].replace('聊天信息', '') if chat['chat_name'].endswith('聊天信息') else chat['chat_name']
                print(f"{i}. {chat_name} ({chat_type})")
            
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
            output_dir = input("\n请输入分析结果保存路径（直接回车使用默���路径）: ").strip()
            if not output_dir:
                output_dir = "analysis_results"
            
            try:
                # 生成思维导图
                output_path = analyzer.generate_mind_map(
                    chat_id=chat_id,
                    start_time=start_time,
                    end_time=end_time,
                    output_dir=output_dir
                )
                print(f"\n思维导图已生成：{output_path}")
                
            except Exception as e:
                print(f"生成失败: {e}")
            
            input("\n按回车键继续...")
        
        elif choice == '5':
            if 'dict_manager' in locals() and 'db' in locals():
                manage_dict(dict_manager, db)
            else:
                print("词典管理器或数据库未初始化")
        
        elif choice == '6':
            search_messages(analyzer)
        
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

def clean_data(analyzer):
    """数据清理功能"""
    while True:
        print("\n=== 数据清理 ===")
        print("1. 按时间范围清理")
        print("2. 按聊天对象清理")
        print("0. 返回主菜单")
        
        clean_choice = input("\n请选择(0-2): ")
        
        if clean_choice == '0':
            return
            
        elif clean_choice == '1':
            # 按时间范围清理
            print("\n请输入要清理的时间范围")
            print("注意：该时间之前的消息将被删除！")
            date_str = input("请输入日期(YYYY-MM-DD): ")
            
            try:
                before_date = datetime.strptime(date_str, '%Y-%m-%d')
                # 预览将要清理的数据
                preview = analyzer.preview_clean_data(before_date=before_date)
                
                print("\n=== 清理预览 ===")
                print(f"将删除 {date_str} 之前的所有消息：")
                print(f"- 消息总数：{preview['msg_count']}条")
                print(f"- 时间范围：{preview['earliest_time']} 至 {preview['latest_time']}")
                print(f"- 涉及聊天数：{preview['chat_count']}")
                print(f"- 涉及用户数：{preview['user_count']}")
                print("\n涉及的聊天对象：")
                for chat in preview['chats']:
                    print(f"- {chat['name']}: {chat['count']}条消息")
                
                confirm = input("\n确定要删除这些消息吗？(y/n): ")
                if confirm.lower() == 'y':
                    count = analyzer.clean_data(before_date=before_date)
                    print(f"\n已清理 {count} 条消息")
                else:
                    print("\n已取消清理")
            except ValueError:
                print("日期格式错误")
                
        elif clean_choice == '2':
            # 按聊天对象清理
            chats = analyzer.db.get_all_chats()
            if not chats:
                print("\n没有可用的聊天记录")
                continue
                
            print("\n可用的聊天列表：")
            for i, chat in enumerate(chats, 1):
                msg_count = chat.get('msg_count', 0)
                print(f"{i}. {chat['chat_name']} ({msg_count}条消息)")
            
            chat_choice = input("\n请选择要清理的聊天序号: ")
            if not chat_choice.isdigit() or not (0 < int(chat_choice) <= len(chats)):
                print("无效的选择")
                continue
            
            selected_chat = chats[int(chat_choice)-1]
            # 预览将要清理的数据
            preview = analyzer.preview_clean_data(chat_id=selected_chat['chat_id'])
            
            print("\n=== 清理预览 ===")
            print(f"将删除与 {selected_chat['chat_name']} 的所有聊天记录：")
            print(f"- 消息总数：{preview['msg_count']}条")
            print(f"- 时间范围：{preview['earliest_time']} 至 {preview['latest_time']}")
            print(f"- 涉及用户数：{preview['user_count']}")
            
            confirm = input("\n确定要删除这些消息吗？(y/n): ")
            if confirm.lower() == 'y':
                count = analyzer.clean_data(chat_id=selected_chat['chat_id'])
                print(f"\n已清理 {count} 条消息")
            else:
                print("\n已取消清理")
        
        else:
            print("无效的选择")
        
        input("\n按回车键继续...")

def manage_dict(dict_manager, db):
    """词典管理功能"""
    while True:
        choice = show_dict_menu()
        
        if choice == '0':
            return
            
        elif choice == '1':
            # 查看词典内容
            words = dict_manager.list_words()
            print("\n当前词典内容：")
            print("词语\t词频\t词性")
            print("-" * 30)
            for word in words:
                print("\t".join(word))
            
        elif choice == '2':
            # 添加新词
            word = input("请输入词语: ")
            freq = input("请输入词频(100-1000): ")
            pos = input("请输入词性(可选): ")
            
            if not word or not freq.isdigit():
                print("输入无效")
                continue
                
            success, msg = dict_manager.add_word(word, freq, pos if pos else None)
            print(msg)
            
        elif choice == '3':
            # 删除词条
            word = input("请输入要删除的词语: ")
            success, msg = dict_manager.remove_word(word)
            print(msg)
            
        elif choice == '4':
            # 更新词频
            print("正在从聊天记录计算词频...")
            success, msg = dict_manager.update_frequencies(db)
            print(msg)
            
        elif choice == '5':
            # 备份词典
            name = input("请输入备份名称(直接回车使用时间戳): ")
            success, msg = dict_manager.backup_dict(name if name else None)
            if success:
                print(f"备份成功: {msg}")
            else:
                print(f"备份失败: {msg}")
            
        elif choice == '6':
            # 恢复备份
            backups = os.listdir(dict_manager.backup_dir)
            if not backups:
                print("没有可用的备份")
                continue
                
            print("\n可用的备份：")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup}")
            
            choice = input("\n请选择要恢复的备份编号: ")
            if choice.isdigit() and 0 < int(choice) <= len(backups):
                success, msg = dict_manager.restore_backup(backups[int(choice)-1])
                print(msg)
            else:
                print("选择无效")
        
        elif choice == '7':
            # 合并词典
            other_dict = input("请输入要合并的词典文件路径: ")
            print("\n请选择合并策略：")
            print("1. 取最大词频")
            print("2. 取最小词频")
            print("3. 取平均词频")
            strategy_choice = input("请选择(1-3): ")
            
            strategy_map = {'1': 'max', '2': 'min', '3': 'avg'}
            if strategy_choice in strategy_map:
                success, msg = dict_manager.merge_dict(
                    other_dict,
                    merge_strategy=strategy_map[strategy_choice]
                )
                print(msg)
            else:
                print("无效的选择")
        
        elif choice == '8':
            # 词典可视化
            success, msg = dict_manager.visualize_dict()
            print(msg)
            if success:
                print("1. 词分布图")
                print("2. 词云图")
                print("3. 统计信息")
                print("以上文件已保存到 analysis_results 目录")
        
        input("\n按回车键继续...")

def search_messages(analyzer):
    """聊天记录搜索功能"""
    print("\n=== 聊天记录搜索 ===")
    print("请输入搜索条件（直接回车跳过）：")
    
    conditions = {}
    
    # 显示所有发送者列表
    senders = analyzer.get_all_senders()
    if senders:
        print("\n可选的发送者：")
        for i, sender in enumerate(senders, 1):
            print(f"{i}. {sender}")
        
        sender_choice = input("\n请选择发送者序号（直接回车跳过）: ").strip()
        if sender_choice.isdigit() and 1 <= int(sender_choice) <= len(senders):
            conditions['sender'] = senders[int(sender_choice) - 1]
    
    keyword = input("关键词: ").strip()
    if keyword:
        conditions['keyword'] = keyword
    
    # 显示所有@提及用户列表
    mentions = analyzer.get_all_mentions()
    if mentions:
        print("\n可选的@提及用户：")
        for i, mention in enumerate(mentions, 1):
            print(f"{i}. {mention}")
        
        mention_choice = input("\n请选择@提及用户序号（直接回车跳过）: ").strip()
        if mention_choice.isdigit() and 1 <= int(mention_choice) <= len(mentions):
            conditions['mention'] = mentions[int(mention_choice) - 1]
    
    # 显示所有聊天对象列表
    chats = analyzer.get_all_chats()
    if chats:
        print("\n可选的聊天对象：")
        for i, chat in enumerate(chats, 1):
            print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
        
        chat_choice = input("\n请选择聊天对象序号（直接回车跳过）: ").strip()
        if chat_choice.isdigit() and 1 <= int(chat_choice) <= len(chats):
            conditions['chat_name'] = chats[int(chat_choice)-1]['chat_name']
    
    print("\n时间范围：")
    print("1. 最近一天")
    print("2. 最近一周")
    print("3. 最近一月")
    print("4. 自定义时间范围")
    print("0. 不限时间")
    
    time_choice = input("请选择(0-4): ")
    if time_choice in ['1', '2', '3']:
        days = {'1': 1, '2': 7, '3': 30}[time_choice]
        conditions['start_time'] = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    elif time_choice == '4':
        start_date = input("开始日期(YYYY-MM-DD): ")
        end_date = input("结束日期(YYYY-MM-DD): ")
        try:
            conditions['start_time'] = f"{start_date} 00:00:00"
            conditions['end_time'] = f"{end_date} 23:59:59"
        except ValueError:
            print("日期格式错误")
            return
    
    # 执行搜索
    results = analyzer.search_messages(conditions)
    
    if not results:
        print("\n未找到匹配的聊天记录")
        return
        
    print(f"\n找到 {len(results)} 条匹配记录：")
    print("-" * 60)
    
    for msg in results:
        time_str = msg['time'].split('.')[0]  # 移除毫秒部分
        print(f"[{time_str}] {msg['chat_name']} - {msg['sender']}:")
        print(f"    {msg['content']}")
        print("-" * 60)

def main():
    """���函数"""
    # 初始化组件
    db = DatabaseHandler()
    monitor = WeChatMonitor()
    analyzer = DataAnalyzer(db)
    dict_manager = DictManager()
    
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
            analyze_data(analyzer, db, dict_manager)
        elif choice == '3':
            export_data(analyzer)
        elif choice == '4':
            clean_data(analyzer)
        elif choice == '5':
            manage_dict(dict_manager, db)
        elif choice == '6':
            search_messages(analyzer)
        else:
            print("无效的选择")
    
    print("\n程序已退出")

if __name__ == "__main__":
    main() 