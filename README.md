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

## 功能说明

### 1. 采集数据
- 选择已有聊天对象或新增聊天对象
- 自动监控微信消息
- 实时保存聊天记录
- 支持手动停止采集

### 2. 数据分析
- 基础统计分析
- 可视化分析
- 词频分析
- 生成思维导图
- 生成聊天故事
- 支持按时间范围分析：
  * 当天
  * 最近三天
  * 最近一周
  * 最近一月
  * 全部时间
  * 自定义时间范围

### 3. 数据导出
- 导出选项：
  * 导出全部数据
  * 按时间范围导出
  * 按聊天对象导出
- 支持格式：
  * CSV 格式
  * JSON 格式
- 可配置默认导出路径

### 4. 数据清理
- 清理方式：
  * 清空所有数据
  * 按时间范围清理
  * 按聊天对象清理
- 清理前确认机制
- 支持撤销操作

### 5. 词典管理
- 查看词典内容
- 添加/删除词条
- 更新词频
- 备份/恢复词典
- 合并词典
- 词典可视化

### 6. 搜索消息
- 搜索条件：
  * 关键词搜索
  * 时间范围筛选
  * 聊天对象筛选
- 支持多条件组合
- 结果实时预览

### 7. 配置选项
- 最大滚动次数设置
- 导出文件默认路径设置
- 配置实时生效
- 自动保存配置

## 打包说明

### 方法1：使用打包脚本
```bash
# 直接运行打包脚本
build.bat
```

### 方法2：手动打包
```bash
# 安装打包工具
pip install pyinstaller==5.13.2

# 执行打包命令
pyinstaller --clean --onefile ^
    --name "微信聊天记录分析工具" ^
    --add-data "data;data" ^
    --add-data "src;src" ^
    --add-data "README.md;." ^
    --add-data "requirements.txt;." ^
    --hidden-import uiautomation ^
    --hidden-import pandas ^
    --hidden-import numpy ^
    --hidden-import matplotlib ^
    --hidden-import seaborn ^
    --hidden-import jieba ^
    --hidden-import wordcloud ^
    --hidden-import networkx ^
    --hidden-import sklearn.feature_extraction.text ^
    --hidden-import sklearn.decomposition ^
    --exclude-module paddle ^
    --exclude-module paddlepaddle ^
    --icon=app.ico ^
    main.py
```

## 目录结构
```
├── main.py              # 主程序
├── requirements.txt     # 依赖包列表
├── src/                # 源代码目录
│   ├── wx_monitor.py   # 微信监控模块
│   ├── db_handler.py   # 数据库处理模块
│   └── data_analyzer.py # 数据分析模块
├── data/               # 数据存储目录
│   ├── wx_chat.db      # 数据库文件
│   └── custom_dict.txt # 自定义词典
├── exports/           # 导出文件目录
└── logs/              # 日志目录
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

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

## 许可证

[MIT License](LICENSE)