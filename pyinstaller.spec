# -*- mode: python -*-
#
#	Compiles the .py files into .exe using PyInstaller.
#	Run with: pyinstaller --clean --noconfirm pyinstaller.spec
#

import platform
from os import system

files = ['get-source', 'get-prebuilt', 'install', 'switch']

for file in files:
	binaries = None

	if file == 'install':
		binaries = [('ntfsea_%s.dll' % ('x64' if platform.architecture()[0] == '64bit' else 'x86'), '.')]

	a = Analysis([file + '.py'], pathex=['.'], binaries=binaries, datas=None, hiddenimports=[], hookspath=[], runtime_hooks=[], excludes=[], win_no_prefer_redirects=False, win_private_assemblies=False, cipher=None)
	pyz = PYZ(a.pure, a.zipped_data, cipher=None)
	exe = EXE(pyz, a.scripts, exclude_binaries=True, name=file, debug=False, strip=False, upx=False, icon=None, console=True)
	col = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, icon=None, name=file)

for file in files:
	if file == 'switch':
		continue

	system('xcopy dist\\' + file + '\\* dist\\switch /e /d /y /h /r /c')
	system('rmdir /s /q dist\\' + file)

system('rmdir /s /q dist\\WSL-Distribution-Switcher')
system('move dist\\switch dist\\WSL-Distribution-Switcher')
