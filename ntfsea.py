#!/usr/bin/env python3
# coding=utf-8
import sys
import struct
import ctypes
import tarfile
import platform


# class for manipulating mode bits stored in lxattrb

class stmode:
	# file types

	IFMT = 0o170000
	SOCK = 0o140000
	FLNK = 0o120000
	FREG = 0o100000
	BLCK = 0o60000
	FDIR = 0o40000
	FCHR = 0o20000
	FIFO = 0o10000

	# protection bits

	SUID = 0o4000
	SGID = 0o2000
	SVTX = 0o1000

	# permissions

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

	# methods follow the same naming convention as TarInfo

	@staticmethod
	def issock(mode):
		"""
		Determine whether mode bits indicate a socket.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.SOCK

	@staticmethod
	def issym(mode):
		"""
		Determine whether mode bits indicate a symbolic link.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.FLNK

	@staticmethod
	def isblk(mode):
		"""
		Determine whether mode bits indicate a block device.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.BLCK

	@staticmethod
	def isdir(mode):
		"""
		Determine whether mode bits indicate a directory.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.FDIR

	@staticmethod
	def isfile(mode):
		"""
		Determine whether mode bits indicate a regular file.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.FREG

	@staticmethod
	def ischr(mode):
		"""
		Determine whether mode bits indicate a character device.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.FCHR

	@staticmethod
	def isfifo(mode):
		"""
		Determine whether mode bits indicate a FIFO device.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return mode & stmode.IFMT == stmode.FIFO

	@staticmethod
	def isdev(mode):
		"""
		Determine whether mode bits indicate a character, block or FIFO device.
		:param mode: Mode bits.
		:return: Evaluation result.
		"""
		return stmode.ischr(mode) or stmode.isblk(mode) or stmode.isfifo(mode)

	@staticmethod
	def getperms(mode):
		"""
		Extract the permission bits from the full bitset.
		:param mode: Mode bits.
		:return: Permission bits.
		"""
		return mode & ~stmode.IFMT


# class for parsing and generating lxattrb entries

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
		"""
		Generate an lxattrb entry using the currently set values.
		:return: Entry bytes.
		"""

		return struct.pack(lxattrb.structure, self.flags, self.version, self.mode, self.uid, self.gid, self.drive, 0, 0, 0, self.atime, self.mtime, self.ctime)

	@staticmethod
	def parse(value):
		"""
		Parse an existing lxattrb entry byte array.
		:param value: Entry bytes.
		:return: An instance of this class with the data members filled accordingly.
		"""

		ret = lxattrb()
		ret.flags, ret.version, ret.mode, ret.uid, ret.gid, ret.drive, _, _, _, ret.atime, ret.mtime, ret.ctime = struct.unpack(lxattrb.structure, value)
		return ret

	@staticmethod
	def fromtar(tar):
		"""
		Converts a TarInfo instance to its equivalent Lxattrb instance.
		:param tar: TarInfo instance.
		:return: An instance of this class with the data members filled accordingly.
		"""

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

	@staticmethod
	def fromsfs(sfs):
		"""
		Converts a SquashedFile instance to its equivalent Lxattrb instance.
		:param sfs: SquashedFile instance.
		:return: An instance of this class with the data members filled accordingly.
		"""

		ret = lxattrb()

		ret.uid   = sfs.inode.uid
		ret.gid   = sfs.inode.gid
		ret.drive = 0
		ret.atime = sfs.inode.time
		ret.mtime = sfs.inode.time
		ret.ctime = sfs.inode.time
		ret.mode  = sfs.inode.mode

		return ret


# internal structures of the ntfsea.dll for ctypes

class ntfsea_Ea(ctypes.Structure):
	_fields_ = [('Name',        ctypes.c_char * 256),
	            ('ValueLength', ctypes.c_uint),
	            ('Value',       ctypes.c_ubyte * 256)]


class ntfsea_EaList(ctypes.Structure):
	_fields_ = [('ListSize', ctypes.c_uint),
	            ('List',     ntfsea_Ea * 4096)]


# class for interfacing with the ntfsea.dll library

class ntfsea:
	lib    = None
	pwstr  = ctypes.c_wchar_p
	pstr   = lambda str: ctypes.c_char_p(str.encode('utf-8'))
	pbytes = lambda str: ctypes.create_string_buffer(str, len(str))

	@staticmethod
	def init():
		"""
		Initializes the ntfsea library.
		"""

		if ntfsea.lib is None:
			if hasattr(ctypes, 'WinDLL'):
				loader = ctypes.WinDLL
			else:
				loader = ctypes.CDLL

			ntfsea.lib = loader('ntfsea_%s.dll' % ('x64' if platform.architecture()[0] == '64bit' else 'x86'))
			ntfsea.lib.GetEaList.restype = ctypes.POINTER(ntfsea_EaList)
			ntfsea.lib.GetEa.restype     = ctypes.POINTER(ntfsea_Ea)
			ntfsea.lib.WriteEa.restype   = ctypes.c_int

	@staticmethod
	def getattrlist(file):
		"""
		Fetches the list of extended attributes available on the requested file.
		:param file: Path to the file.
		:return: List of extended attributes or None.
		"""

		ret = ntfsea.lib.GetEaList(ntfsea.pwstr(file))

		if ret.contents.ListSize > 0:
			eas = []

			for i in range(0, ret.contents.ListSize):
				try:
					eas += [(ret.contents.List[i].Name.decode('utf-8'),
					        bytes(ret.contents.List[i].Value[:ret.contents.List[i].ValueLength]))]
				except Exception:
					pass

			return eas
		else:
			return None

	@staticmethod
	def getattr(file, name):
		"""
		Fetches the specified extended attribute and its value from the requested file.
		:param file: Path to the file.
		:param name: Name of the extended attribute.
		:return: Extended attribute information or None.
		"""

		ret = ntfsea.lib.GetEa(ntfsea.pwstr(file), ntfsea.pstr(name))

		if 0 < ret.contents.ValueLength <= 256:
			try:
				return bytes(ret.contents.Value[:ret.contents.ValueLength])
			except Exception:
				return None
		else:
			return None

	@staticmethod
	def writeattr(file, name, value):
		"""
		Writes the specified extended attribute and its value to the requested file.
		:param file: Path to the file.
		:param name: Name of the extended attribute.
		:param value: Value of the extended attribute.
		:return: Number of bytes written (should match EaValueLength) or -1 on failure.
		"""

		ret = ntfsea.lib.WriteEa(ntfsea.pwstr(file), ntfsea.pstr(name), ntfsea.pbytes(value), len(value))
		return ret
