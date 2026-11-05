# Iridium.spec — PyInstaller build config
# Build: pyinstaller Iridium.spec
# Output: dist/Iridium.exe

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('customtkinter')
hiddenimports = collect_submodules('yt_dlp')

a = Analysis(
    ['iridium.py'],
    pathex=[],
    binaries=[('ffmpeg.exe', '.'), ('ffprobe.exe', '.')],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'IPython', 'jupyter', 'notebook',
        'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Iridium',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # no black command window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # no icon= line — uses the default PyInstaller icon
)