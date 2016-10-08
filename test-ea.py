#!/usr/bin/env python3
# coding=utf-8
import sys
import ctypes
import platform

pwstr = ctypes.c_wchar_p
pstr = lambda str: ctypes.c_char_p(str.encode('utf-8'))
pbytes = lambda str: ctypes.create_string_buffer(str, len(str))

ntfsea = ctypes.WinDLL('C:\\Users\\RoliSoft\\Documents\\Visual Studio 2015\\Projects\\ntfsea\\ntfsea\\bin\\Release-32\\ntfsea.dll') # ctypes.WinDLL('ntfsea_%s.dll' % ('x64' if platform.architecture()[0] == '64bit' else 'x86'))

test = b'test\x11the\x22up\x33\x00\x11\x22\x33\x00\x11\x22\x33yo\x00x'

class _Ea(ctypes.Structure):
	_fields_ = [('Name', ctypes.c_char * 256), ('ValueLength', ctypes.c_uint), ('Value', ctypes.c_ubyte * 256)]

ntfsea.GetEa.restype = ctypes.POINTER(_Ea)
ntfsea.WriteEa.restype = ctypes.c_int

ntfsea.WriteEa(pwstr('C:\\Users\\RoliSoft\\AppData\\Local\\lxss\\rootfs\\etc\\apt\\asdf.txt'), pstr('asd'), pbytes(test), len(test))
asd = ntfsea.GetEa(pwstr('C:\\Users\\RoliSoft\\AppData\\Local\\lxss\\rootfs\\etc\\apt\\asdf.txt'), pstr('asd'))
ba = bytearray(asd.contents.Value[:asd.contents.ValueLength])
print(ba)