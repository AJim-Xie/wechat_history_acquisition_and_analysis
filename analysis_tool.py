from src.data_analyzer import DataAnalyzer
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import os
from matplotlib.font_manager import FontProperties
import matplotlib as mpl
import re

def set_global_font():
    """设置全局字体"""
    # 设置中文字体路径
    font_paths = [
        r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
        r"C:\Windows\Fonts\simhei.ttf", # 黑体
        r"C:\Windows\Fonts\simsun.ttc", # 宋体
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # Linux 文泉驿微米黑
    ]
    
    # 设置字体回退顺序
    fallback_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'WenQuanYi Micro Hei', 'DejaVu Sans']
    
    # 设置字体回退机制
    mpl.rcParams['font.family'] = ['sans-serif']
    mpl.rcParams['font.sans-serif'] = fallback_fonts
    mpl.rcParams['axes.unicode_minus'] = False
    
    # 尝试设置字体
    font_found = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            font_found = True
            # 直接返回字体路径
            return font_path
    
    if not font_found:
        # 如果找不到字体文件，尝试使用系统字体
        for font in fallback_fonts:
            try:
                font_prop = FontProperties(family=font)
                if font_prop.get_file():
                    return font_prop.get_file()
            except:
                continue
    
    raise Exception("未找到合适的中文字体，请安装所需字体")

def parse_time(time_str):
    """解析时间字符串"""
    try:
        now = datetime.now()
        
        # 如果只有时间 (HH:mm)
        if re.match(r'^\d{2}:\d{2}$', time_str):
            time_parts = time_str.split(':')
            return now.replace(
                hour=int(time_parts[0]),
                minute=int(time_parts[1]),
                second=0,
                microsecond=0
            )
        
        # 如果是"昨天 HH:mm"格式
        if time_str.startswith('昨天'):
            time_parts = time_str.split(' ')[1].split(':')
            yesterday = now - timedelta(days=1)
            return yesterday.replace(
                hour=int(time_parts[0]),
                minute=int(time_parts[1]),
                second=0,
                microsecond=0
            )
            
        # 如果是完整日期格式 (YYYY年MM月DD日 HH:mm)
        if re.match(r'^\d{4}年\d{1,2}月\d{1,2}日 \d{2}:\d{2}$', time_str):
            return datetime.strptime(time_str, '%Y年%m月%d日 %H:%M')
            
        raise ValueError(f"无法解析的时间格式: {time_str}")
        
    except Exception as e:
        raise Exception(f"时间解析失败: {time_str}, 错误: {str(e)}")

def plot_time_distribution(time_dist):
    """绘制时间分布图"""
    plt.figure(figsize=(12, 6))
    
    hours = range(24)
    counts = [time_dist.get(str(h).zfill(2), 0) for h in hours]
    plt.bar(hours, counts)
    plt.title('消息时间分布')
    plt.xlabel('小时')
    plt.ylabel('消息数量')
    plt.xticks(hours)
    return plt

def plot_message_types(type_stats):
    """绘制消息类型分布图"""
    plt.figure(figsize=(8, 8))
    
    # 处理中文标签
    labels = list(type_stats.keys())
    values = list(type_stats.values())
    
    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title('消息类型分布')
    return plt

def plot_word_cloud(keywords):
    """绘制词云图"""
    from wordcloud import WordCloud
    plt.figure(figsize=(10, 10))
    
    try:
        # 获取字体路径
        font_path = set_global_font()
        
        wc = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            font_path=font_path,
            max_words=100
        )
        wc.generate_from_frequencies(keywords)
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title('关键词词云')
    except Exception as e:
        print(f"生成词云图失败: {e}")
    return plt

def plot_daily_trend(daily_trend):
    """绘制每日消息趋势图"""
    plt.figure(figsize=(15, 6))
    dates = list(daily_trend.keys())
    counts = list(daily_trend.values())
    plt.plot(dates, counts, marker='o')
    plt.title('每日消息趋势')
    plt.xlabel('日期')
    plt.ylabel('消息数量')
    plt.xticks(rotation=45)
    plt.grid(True)
    return plt

def plot_weekly_activity(weekly_activity):
    """绘制每周活跃度分布图"""
    plt.figure(figsize=(10, 6))
    days = list(weekly_activity.keys())
    counts = list(weekly_activity.values())
    plt.bar(days, counts)
    plt.title('每周活跃度分布')
    plt.xlabel('星期')
    plt.ylabel('消息数量')
    return plt

def plot_length_distribution(length_dist):
    """绘制消息长度分布图"""
    plt.figure(figsize=(10, 6))
    categories = list(length_dist.keys())
    counts = list(length_dist.values())
    plt.bar(categories, counts)
    plt.title('消息长度分布')
    plt.xlabel('长度类别')
    plt.ylabel('消息数量')
    plt.xticks(rotation=15)
    return plt

def plot_interaction_network(interactions):
    """绘制互动关系网络图"""
    try:
        import networkx as nx
        plt.figure(figsize=(12, 12))
        G = nx.DiGraph()
        
        # 添加边和权重
        for interaction in interactions:
            # 处理特殊字符
            from_user = interaction['from_user']
            to_user = interaction['to_user']
            
            # 使用更安全的字符处理方式
            def sanitize_name(name):
                # 保留中文和基本ASCII字符
                import re
                cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', name)
                if not cleaned:
                    return f"用户{hash(name) % 1000}"
                return cleaned
            
            from_user = sanitize_name(from_user)
            to_user = sanitize_name(to_user)
            
            G.add_edge(from_user, to_user, weight=interaction['count'])
        
        # 设置节点位置
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # 计算节点大小和边的宽度
        node_size = [G.degree(node) * 100 for node in G.nodes()]
        edge_width = [G[u][v]['weight'] / 10 for u, v in G.edges()]
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, 
                             node_color='lightblue',
                             node_size=node_size,
                             alpha=0.7)
        
        # 绘制边
        nx.draw_networkx_edges(G, pos,
                             width=edge_width,
                             alpha=0.5,
                             edge_color='gray',
                             arrows=True,
                             arrowsize=10)
        
        # 添加标签
        labels = {node: node for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels,
                              font_size=8,
                              font_family='sans-serif')
        
        plt.title('用户互动关系网络')
        plt.axis('off')
        
    except Exception as e:
        print(f"生成互动关系网络图失败: {e}")
    return plt

def print_usage():
    """打印使用说明"""
    print("\n=== 微信聊天记录分析工具使用说明 ===")
    print("\n运行方式：")
    
    print("\n1. 启动监控（首次使用必须先运行此项）")
    print("   > python main.py")
    print("   - 开始监控并记录微信消息")
    print("   - 保持程序运行以持续采集数据")
    
    print("\n2. 分析聊天记录")
    print("   > python analysis_tool.py")
    print("   功能：")
    print("   - 查看聊天统计信息")
    print("   - 生成数据可视化图表")
    print("   - 分析用户互动关系")
    print("   - 查看关键词词云")
    
    print("\n3. 导出聊天记录")
    print("   > python export_tool.py")
    print("   - 导出格式：CSV或JSON")
    print("   - 可按时间和对象筛选")
    
    print("\n使用步骤：")
    print("1. 确保已安装依赖：")
    print("   pip install -r requirements.txt")
    
    print("\n2. 启动数据采集：")
    print("   - 运行 python main.py")
    print("   - 保持微信登录状态")
    
    print("\n3. 数据分析与导出：")
    print("   - 运行 python analysis_tool.py 进行数据分析")
    print("   - 或运行 python export_tool.py 导出数据")
    
    print("\n注意事项：")
    print("- 首次使用需要先运行 main.py 采集数据")
    print("- 分析工具支持多种时间范围的数据分析")
    print("- 可以随时查看和导出已采集的数据")
    print("- 清理数据前建议先导出备份")
    print("- 图表结果保存在 analysis_results 目录")
    
    print("\n文件说明：")
    print("- main.py: 消息监控与采集")
    print("- analysis_tool.py: 数据分析与可视化")
    print("- export_tool.py: 数据导出工具")
    print("- data/wx_chat.db: 数据库文件")
    print("- analysis_results/: 分析结果保存目录")

def main():
    try:
        # 设置全局字体
        set_global_font()
        
        analyzer = DataAnalyzer()
        
        print("=== 微信聊天记录分析工具 ===")
        print_usage()  # 添加使用说明
        
        while True:  # 添加循环，让用户可以连续操作
            print("\n请选择操作：")
            print("1. 分析聊天记录")
            print("2. 清空聊天记录")
            print("3. 查询聊天记录")
            print("4. 显示使用说明")
            print("0. 退出程序")
            
            choice = input("\n请输入选项(0-4)：")
            
            if choice == '0':
                print("程序已退出")
                break
                
            if choice == '4':
                print_usage()
                continue
                
            if choice == '2':
                # 清空聊天记录
                print("\n请选择清空方式：")
                print("1. 清空所有数据")
                print("2. 按时间范围清空")
                print("3. 按聊天对象清空")
                
                clean_choice = input("\n请输入选项(1-3)：")
                
                if clean_choice == '1':
                    confirm = input("确定要清空所有数据吗？(y/n)：")
                    if confirm.lower() == 'y':
                        count = analyzer.clean_data()
                        print(f"\n已清空 {count} 条聊天记录")
                
                elif clean_choice == '2':
                    before_date = input("请输入清空该日期之前的数据(YYYY-MM-DD)：")
                    try:
                        before_time = datetime.strptime(before_date, '%Y-%m-%d')
                        count = analyzer.clean_data(before_date=before_time)
                        print(f"\n已清空 {count} 条聊天记录")
                    except ValueError:
                        print("日期格式错误")
                        continue
                
                elif clean_choice == '3':
                    # 显示可用的聊天列表
                    chats = analyzer.get_all_chats()
                    print("\n可用的聊天列表：")
                    for i, chat in enumerate(chats, 1):
                        print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
                    
                    chat_choice = input("\n请选择要清空的聊天序号：")
                    if chat_choice.isdigit() and 0 < int(chat_choice) <= len(chats):
                        chat_id = chats[int(chat_choice)-1]['chat_id']
                        confirm = input(f"确定要清空该聊天的所有记录吗？(y/n)：")
                        if confirm.lower() == 'y':
                            count = analyzer.clean_data(chat_id=chat_id)
                            print(f"\n已清空 {count} 条聊天记录")
                    else:
                        print("无效的选择")
                        continue
                
            elif choice == '3':
                # 查询聊天记录
                print("\n请选择查询方式：")
                print("1. 查看所有聊天记录")
                print("2. 按时间范围查询")
                print("3. 按聊天对象查询")
                
                query_choice = input("\n请输入选项(1-3)：")
                
                start_time = None
                end_time = None
                chat_id = None
                
                if query_choice == '2':
                    start_date = input("请输入开始日期(YYYY-MM-DD)：")
                    end_date = input("请输入结束日期(YYYY-MM-DD)：")
                    try:
                        if start_date:
                            start_time = datetime.strptime(start_date, '%Y-%m-%d')
                        if end_date:
                            end_time = datetime.strptime(end_date, '%Y-%m-%d')
                    except ValueError:
                        print("日期格式错误")
                        continue
                
                elif query_choice == '3':
                    # 显示可用的聊天列表
                    chats = analyzer.get_all_chats()
                    print("\n可用的聊天列表：")
                    for i, chat in enumerate(chats, 1):
                        print(f"{i}. {chat['chat_name']} ({'群聊' if chat['chat_type'] == 2 else '私聊'})")
                    
                    chat_choice = input("\n请选择要查询的聊天序号：")
                    if chat_choice.isdigit() and 0 < int(chat_choice) <= len(chats):
                        chat_id = chats[int(chat_choice)-1]['chat_id']
                    else:
                        print("无效的选择")
                        continue
                
                # 执行查询
                messages = analyzer.query_messages(
                    chat_id=chat_id,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # 显示查询结果
                print(f"\n共找到 {len(messages)} 条聊天记录：")
                for msg in messages:
                    time_str = msg['send_time'].strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[{time_str}] {msg['sender_name']}: {msg['content']}")
            
            elif choice == '1':
                # 分析聊天记录
                # 选择分析时间范围
                print("\n请选择分析时间范围：")
                print("1. 最近一周")
                print("2. 最近一月")
                print("3. 最近三月")
                print("4. 自定义时间范围")
                
                choice = input("\n请选择(1-4)：")
                days = {
                    '1': 7,
                    '2': 30,
                    '3': 90
                }.get(choice, None)
                
                if choice == '4':
                    start_date = input("请输入开始日期(YYYY-MM-DD)：")
                    try:
                        start_time = datetime.strptime(start_date, '%Y-%m-%d')
                        days = (datetime.now() - start_time).days
                    except ValueError:
                        print("日期格式错误")
                        continue
                
                # 获取分析结果
                result = analyzer.analyze_chat(days=days)
                
                # 1. 输出基础统计信息
                print("\n=== 基础统计信息 ===")
                print(f"总消息数：{result['basic_stats']['total_messages']}")
                print(f"活跃用户数：{result['basic_stats']['unique_senders']}")
                print(f"活跃天数：{result['basic_stats']['active_days']}")
                print(f"平均消息长度：{result['basic_stats']['avg_length']:.1f}")
                
                # 2. 输出活跃用户排名
                print("\n=== 活跃用户排名 ===")
                for user in result['active_users']:
                    print(f"{user['name']}: {user['count']}条消息")
                
                # 3. 输出消息类型分布
                print("\n=== 消息类型分布 ===")
                for type_name, count in result['message_types'].items():
                    print(f"{type_name}: {count}条")
                
                # 4. 输出热门关键词
                print("\n=== 热门关键词 ===")
                for word, count in list(result['top_keywords'].items())[:10]:
                    print(f"{word}: {count}次")
                
                # 5. 新增输出内容
                print("\n=== 消息长度分布 ===")
                for category, count in result['length_distribution'].items():
                    print(f"{category}: {count}条")
                    
                print("\n=== 每周活跃度 ===")
                for day, count in result['weekly_activity'].items():
                    print(f"{day}: {count}条消息")
                    
                print("\n=== 常用表情 ===")
                for emoji, count in list(result['emoji_stats'].items())[:10]:
                    print(f"{emoji}: {count}次")
                    
                print("\n=== 主要互动关系 ===")
                for interaction in result['interactions'][:5]:
                    print(f"{interaction['from_user']} -> {interaction['to_user']}: {interaction['count']}次互动")
                
                # 6. 生成可视化图表
                # 创建输出目录
                output_dir = "analysis_results"
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 时间分布图
                plot_time_distribution(result['time_distribution'])
                plt.savefig(f"{output_dir}/time_dist_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                # 消息类型分布图
                plot_message_types(result['message_types'])
                plt.savefig(f"{output_dir}/msg_types_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                # 词云图
                plot_word_cloud(result['top_keywords'])
                plt.savefig(f"{output_dir}/wordcloud_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                # 每日消息趋势图
                plot_daily_trend(result['daily_trend'])
                plt.savefig(f"{output_dir}/daily_trend_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                # 每周活跃度分布图
                plot_weekly_activity(result['weekly_activity'])
                plt.savefig(f"{output_dir}/weekly_activity_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                # 消息长度分布图
                plot_length_distribution(result['length_distribution'])
                plt.savefig(f"{output_dir}/length_dist_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                # 互动关系网络图
                plot_interaction_network(result['interactions'])
                plt.savefig(f"{output_dir}/interaction_network_{timestamp}.png", dpi=300, bbox_inches='tight')
                plt.close()
                
                print(f"\n分析结果已保存到 {output_dir} 目录")
            
            else:
                print("无效的选择")
                
    except Exception as e:
        print(f"操作失败：{e}")

if __name__ == "__main__":
    main() 