@echo off
chcp 65001
echo 正在清理旧的构建文件...
rmdir /s /q build dist
del /f /q *.spec

echo 正在安装打包工具...
python -m pip install --upgrade pip
pip install pyinstaller

echo 正在安装依赖...
pip install -r requirements.txt --disable-pip-version-check

echo 正在打包应用...
pyinstaller --clean ^
    --onefile ^
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
    --icon=app.ico ^
    main.py

echo 打包完成！
pause 