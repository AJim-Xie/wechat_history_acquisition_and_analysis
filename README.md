# 微信聊天记录分析工具

一个用于采集、分析和导出微信聊天记录的工具集。

## 功能特点

- 自动采集微信聊天记录
- 支持文本、图片、视频等多媒体内容
- 提供丰富的数据分析功能
- 支持多种格式导出
- 可视化分析结果

## 安装说明

### 1. 环境要求
- Python 3.7+
- Windows 操作系统（因使用 uiautomation）
- 微信 PC 版本

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 数据采集
```bash
python main.py
```
- 运行后会自动监控微信消息
- 请保持微信处于登录状态
- 需要采集哪个聊天记录就切换到对应窗口
- 按 Ctrl+C 可停止采集

### 2. 数据分析
```bash
python analysis_tool.py
```
功能选项：
1. 分析聊天记录
   - 基础统计信息
   - 活跃用户排名
   - 消息类型分布
   - 热门关键词
   - 互动关系网络
2. 清空聊天记录
3. 查询聊天记录
4. 显示使用说明

### 3. 数据导出
```bash
python export_tool.py
```
- 支持导出格式：CSV/JSON
- 可按时间范围导出
- 可按聊天对象导出

## 目录结构
```
├── main.py              # 主程序（数据采集）
├── analysis_tool.py     # 数据分析工具
├── export_tool.py       # 数据导出工具
├── requirements.txt     # 依赖包列表
├── src/                 # 源代码目录
│   ├── wx_monitor.py    # 微信监控模块
│   ├── db_handler.py    # 数据库处理模块
│   └── data_analyzer.py # 数据分析模块
├── data/               # 数据存储目录
│   ├── wx_chat.db      # 数据库文件
│   └── media/          # 媒体文件目录
├── exports/            # 导出文件目录
├── logs/               # 日志目录
└── analysis_results/   # 分析结果目录
```

## 注意事项

1. 首次使用：
   - 确保已安装所有依赖
   - 需要先采集数据才能进行分析
   - 检查中文字体是否正确安装

2. 数据安全：
   - 定期备份数据库文件
   - 清空数据前先导出备份
   - 注意保护隐私信息

3. 使用建议：
   - 建议定期清理无用数据
   - 导出大量数据时可能需要较长时间
   - 分析大量数据时注意内存占用

## 常见问题

1. 无法采集消息？
   - 检查微信是否正常登录
   - 确认是否有正确的窗口焦点
   - 检查程序运行权限

2. 分析图表无法显示中文？
   - 检查是否安装了中文字体
   - Windows 需要微软雅黑等中文字体
   - Linux 需要文泉驿等中文字体

3. 导出失败？
   - 检查存储空间是否充足
   - 确认导出路径是否有写入权限
   - 检查文件是否被其他程序占用

## 更新日志

### v1.0.0
- 基础功能实现
- 支持数据采集和分析
- 添加导出功能
- 实现可视化分析

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

## 许可证

[MIT License](LICENSE)

## 自定义词典

### 1. 词典格式
- 位置：data/custom_dict.txt
- 每行一个词条
- 格式：词语 词频 词性(可选)
- 示例：微信 1000 n

### 2. 词性说明
- n：名词
- v：动词
- a：形容词
- d：副词
- ...更多词性见jieba文档

### 3. 使用方法
1. 直接编辑词典文件
2. 使用词典管理功能：
   ```python
   from src.dict_manager import DictManager
   dm = DictManager()
   
   # 基本操作
   dm.add_word("新词", 1000, "n")
   dm.remove_word("旧词")
   words = dm.list_words()
   
   # 合并词典
   dm.merge_dict("other_dict.txt", merge_strategy='max')
   
   # 可视化
   dm.visualize_dict()
   ```

### 4. 词典合并
- 支持多个词典文件合并
- 提供三种合并策略：
  * 最大词频：取两个词典中的最大词频
  * 最小词频：取两个词典中的最小词频
  * 平均词频：取两个词典的平均词频
- 自动处理词性冲突
- 合并前自动备份

### 5. 可视化功能
- 词频分布图：显示高频词分布
- 词云图：直观展示词频
- 统计信息：包含词条数量、平均词频等

### 6. 注意事项
- 词频越大，分词时优先级越高
- 建议词频设置在100-1000之间
- 添加新词前先检查是否已存在
- 定期备份词典文件
- 合并前检查词典格式

## 功能说明

### 1. 采集数据
- 自动监控微信消息
- 需要采集哪个聊天记录就切换到对应窗口
- 按 Ctrl+C 可停止采集

### 2. 数据分析
- 基础统计信息
- 活跃用户排名
- 消息类型分布
- 热门关键词
- 互动关系网络
- 支持按时间范围分析：
  * 当天
  * 最近3天
  * 最近7天
  * 最近30天
  * 全部时间
  * 自定义时间范围

### 3. 数据导出
- 支持导出格式：CSV/JSON
- 导出选项：
  * 导出全部数据
  * 按时间范围导出
  * 按聊天对象导出
- 可配置默认导出路径

### 4. 数据清理
- 清空方式：
  * 清空所有数据
  * 按时间范围清空
  * 按聊天对象清空
- 清空前会要求确认

### 5. 词典管理
- 添加/删除自定义词语
- 设置词频和词性
- 导入/导出词典
- 词典可视化
- 支持词典合并

### 6. 搜索消息
- 搜索条件：
  * 关键词搜索
  * 时间范围筛选
  * 聊天对象筛选
- 支持多条件组合搜索

### 7. 配置选项
- 最大滚动次数设置
- 导出文件默认路径设置
- 配置实时生效
- 自动保存配置

## 打包EXE文件方法
方法1：直接运行打包脚本
build.bat
方法2：手动执行打包命令
pyinstaller --clean --onefile 
--name "微信聊天记录分析工具" 
--add-data "data;data" 
--add-data "src;src" 
--add-data "README.md;." 
--add-data "requirements.txt;." 
--hidden-import uiautomation 
--hidden-import pandas 
--hidden-import numpy 
--hidden-import matplotlib 
--hidden-import seaborn 
--hidden-import jieba 
--hidden-import wordcloud 
--hidden-import networkx 
--hidden-import sklearn.feature_extraction.text 
--hidden-import sklearn.decomposition 
--exclude-module paddle 
--exclude-module paddlepaddle 
main.py