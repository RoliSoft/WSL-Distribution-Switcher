# -*- mode: python -*-
#
#	Compiles the .py files into .exe using PyInstaller.
#	Run with: pyinstaller --noconfirm --clean pyinstaller.spec
#

from os import system

files = ['get-source', 'get-prebuilt', 'install', 'switch']

for file in files:
	binaries = None

	if file == 'install':
		binaries = [('ntfsea_x86.dll', '.'),('ntfsea_x64.dll', '.')]

	a = Analysis([file + '.py'], pathex=['.'], binaries=binaries, datas=None, hiddenimports=[], hookspath=[], runtime_hooks=[], excludes=[], win_no_prefer_redirects=False, win_private_assemblies=False, cipher=None)
	pyz = PYZ(a.pure, a.zipped_data, cipher=None)
	exe = EXE(pyz, a.scripts, exclude_binaries=True, name=file, debug=False, strip=False, upx=True, icon=None, console=True)
	col = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, icon=None, name=file)

for file in files:
	if file == 'switch':
		continue

	system('xcopy dist\\' + file + '\\* dist\\switch /e /d /y /h /r /c')
	system('rmdir /s /q dist\\' + file)

system('xcopy C:\\Windows\\System32\\vcruntime140.dll dist\\switch\\vcruntime140.dll /y')
system('move dist\\switch dist\\wsl-distrib-switcher')
