from src.data_analyzer import DataAnalyzer
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import os
from matplotlib.font_manager import FontProperties
import matplotlib as mpl

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

def main():
    try:
        # 设置全局字体
        set_global_font()
        
        analyzer = DataAnalyzer()
        
        print("=== 微信聊天记录分析工具 ===")
        
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
                return
        
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
        
    except Exception as e:
        print(f"分析失败：{e}")

if __name__ == "__main__":
    main() 