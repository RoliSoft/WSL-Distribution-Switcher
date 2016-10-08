#!/usr/bin/env python3
# coding=utf-8
import sys
import tarfile
import struct
import ctypes


class stmode:
	# File types

	IFMT = 0o170000
	SOCK = 0o140000
	FLNK = 0o120000
	FREG = 0o100000
	BLCK = 0o60000
	FDIR = 0o40000
	FCHR = 0o20000
	FIFO = 0o10000

	# Protection bits

	SUID = 0o4000
	SGID = 0o2000
	SVTX = 0o1000

	# Permissions

	# owner
	RWXU = 0o700
	RUSR = 0o400
	WUSR = 0o200
	XUSR = 0o100
	# group
	RWXG = 0o70
	RGRP = 0o40
	WGRP = 0o20
	XGRP = 0o10
	# others
	RWXO = 0o7
	ROTH = 0o4
	WOTH = 0o2
	XOTH = 0o1

	# Methods follow the same naming convention as TarInfo

	@staticmethod
	def issock(mode):
		return mode & stmode.IFMT == stmode.SOCK

	@staticmethod
	def issym(mode):
		return mode & stmode.IFMT == stmode.FLNK

	@staticmethod
	def isblk(mode):
		return mode & stmode.IFMT == stmode.BLCK

	@staticmethod
	def isdir(mode):
		return mode & stmode.IFMT == stmode.FDIR

	@staticmethod
	def isfile(mode):
		return mode & stmode.IFMT == stmode.FREG

	@staticmethod
	def ischr(mode):
		return mode & stmode.IFMT == stmode.FCHR

	@staticmethod
	def isfifo(mode):
		return mode & stmode.IFMT == stmode.FIFO

	@staticmethod
	def isdev(mode):
		return stmode.ischr(mode) or stmode.isblk(mode) or stmode.isfifo(mode)

	@staticmethod
	def getperms(mode):
		return mode & ~stmode.IFMT


class lxattrb:
	structure = 'HHIIIIIIIQQQ'

	def __init__(self, mode = 0, uid = 0, gid = 0, drive = 0, atime = 0, mtime = 0, ctime = 0):
		self.flags   = 0
		self.version = 1
		self.mode    = mode  # 33206
		self.uid     = uid
		self.gid     = gid
		self.drive   = drive
		self.atime   = atime
		self.mtime   = mtime
		self.ctime   = ctime

	def generate(self):
		return struct.pack(lxattrb.structure, self.flags, self.version, self.mode, self.uid, self.gid, self.drive, 0, 0, 0, self.atime, self.mtime, self.ctime)

	@staticmethod
	def parse(value):
		ret = lxattrb()
		ret.flags, ret.version, ret.mode, ret.uid, ret.gid, ret.drive, _, _, _, ret.atime, ret.mtime, ret.ctime = struct.unpack(lxattrb.structure, value)
		return ret

	@staticmethod
	def fromtar(tar):
		ret = lxattrb()

		ret.uid   = tar.uid
		ret.gid   = tar.gid
		ret.drive = 0
		ret.atime = tar.mtime
		ret.mtime = tar.mtime
		ret.ctime = tar.mtime

		# set file type

		if tar.isfile():
			ret.mode |= stmode.FREG
		elif tar.isdir():
			ret.mode |= stmode.FDIR
		elif tar.issym() or tar.islnk():
			ret.mode |= stmode.FLNK
		elif tar.ischr():
			ret.mode |= stmode.FCHR
		elif tar.isblk():
			ret.mode |= stmode.BLCK
		elif tar.isfifo():
			ret.mode |= stmode.FIFO

		# apply permissions

		ret.mode |= tar.mode

		return ret


# with tarfile.open('rootfs_alpine_latest.tar.gz', 'r:*') as tar:
# 	for f in tar.getmembers():
# 		print(oct(lxattrb.fromtar(f).mode))

# asd = ctypes.create_string_buffer(250)
#
# print(ctypes.windll.ntdll.RtlDosPathNameToNtPathName_U_WithStatus('C:\\Usrs\\RoliSoft\\AppData\\Local\\lxss\\rootfs\\etc\\apt\\test1.txt', ctypes.byref(asd), None, None))
# print(ctypes.windll.ntdll.get_last_error())
# print(repr(asd.raw)) #.encode(sys.stdout.encoding, errors='replace'))

NULL = ctypes.POINTER(ctypes.c_uint)()
asd = ctypes.create_unicode_buffer(250)

retcode = ctypes.windll.Ntdll.RtlDosPathNameToNtPathName_U_WithStatus(ctypes.c_wchar_p('C:\\Users\\RoliSoft\\AppData\\Local\\lxss\\rootfs\\etc\\apt\\test1.txt'), ctypes.byref(asd), NULL, NULL)
retcode = ctypes.windll.Ntdll.RtlDosPathNameToNtPathName_U_WithStatus(ctypes.c_wchar_p('C:\\Users\\RoliSoft\\AppData\\Local\\lxss\\rootfs\\etc\\apt\\test1.txt'), ctypes.byref(asd), NULL, NULL)


# a = lxattrb.parse(b'\x00\x00\x01\x00\xb6\x81\x00\x00\xe8\x03\x00\x00\xe8\x03\x00\x00\x00\x00\x00\x00\xf0\xb4\xcb\x2a\x70\x46\x23\x0d\x44\xd5\x34\x1b\x8d\x92\xf6\x57\x00\x00\x00\x00\xab\x92\xf6\x57\x00\x00\x00\x00\x60\xf3\xf7\x57\x00\x00\x00\x00')
# print(oct(stmode.getperms(a.mode)))
# print(stmode.FREG | 0o666)
