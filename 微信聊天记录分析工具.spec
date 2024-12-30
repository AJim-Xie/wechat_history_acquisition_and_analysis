# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('src', 'src'), ('README.md', '.'), ('requirements.txt', '.')],
    hiddenimports=['uiautomation', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'jieba', 'wordcloud', 'networkx', 'sklearn.feature_extraction.text', 'sklearn.decomposition'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['paddle', 'paddlepaddle'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='微信聊天记录分析工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
