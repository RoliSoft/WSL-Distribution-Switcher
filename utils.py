#!/usr/bin/env python3
# coding=utf-8
import io
import os
import re
import sys
import ssl
import glob
import time
import shlex
import signal
import subprocess


has_filter   = False
has_progress = False
has_winreg   = False
has_certifi  = False

is_cygwin = sys.platform == 'cygwin'
is_win32  = sys.platform == 'win32'
is_conemu = False

last_progress = 0


# try importing the optional dependencies

try:
	import winreg
	has_winreg = True
except ImportError:
	pass

try:
	import certifi
	has_certifi = True
except ImportError:
	pass

if is_win32:
	try:
		from colorama import init
		init()
		has_filter = True
	except ImportError:
		pass

	import ctypes

	class ConsoleCursorInfo(ctypes.Structure):
		_fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]

if not is_win32 or has_filter:
	class Fore:
		RED    = '\x1B[91m'
		GREEN  = '\x1B[92m'
		BLUE   = '\x1B[94m'
		YELLOW = '\x1B[93m'
		RESET  = '\x1B[39m'
else:
	class Fore:
		RED    = ''
		GREEN  = ''
		BLUE   = ''
		YELLOW = ''
		RESET  = ''


# registers for the interrupt signal in order to gracefully exit when Ctrl-C is hit

def handle_sigint():
	def signal_handler(signal, frame):
		clear_progress()
		show_cursor()
		print('%s[!]%s Terminating early due to interruption.' % (Fore.RED, Fore.RESET))
		sys.exit(-1)

	signal.signal(signal.SIGINT, signal_handler)


# check if any CA bundles were loaded or fallback to certifi otherwise

def ensure_ca_load():
	if ssl.create_default_context().cert_store_stats()['x509_ca'] == 0:
		if has_certifi:
			def create_certifi_context(purpose = ssl.Purpose.SERVER_AUTH, *, cafile = None, capath = None, cadata = None):
				return ssl.create_default_context(purpose, cafile = certifi.where())

			ssl._create_default_https_context = create_certifi_context

		else:
			print('%s[!]%s Python was unable to load any CA bundles. Additionally, the fallback %scertifi%s module is not available. Install it with %spip3 install certifi%s for TLS connection support.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))
			sys.exit(-1)


# parse image[:tag] | archive argument

def parse_image_arg(argv, can_be_file = False):
	"""
	Parses the image[:tag] argument passed to the script. When can_be_file is True,
	the argument can also be a filename, _and_ if it is not, the generated image:tag
	should have a corresponding rootfs archive available.

	:param argv: Passed argument.
	:param can_be_file: Whether argument can be a file and image:tag should also resolve to a file.

	:return: Name of the image, tag, name of the file, label.
	"""

	exts  = ['.tar', '.sfs', '.squashfs']
	argvl = argv.lower()
	image = argv
	tag   = 'latest'
	fname = ''
	label = ''

	if not can_be_file or all(ext not in argvl for ext in exts):

		# handle image:tag

		if ':' in image:
			idx   = image.find(':')
			tag   = image[idx + 1:]
			image = image[:idx]

		if can_be_file:
			fname = 'rootfs_%s_%s.tar*' % (image.replace('/', '_'), tag)
			names = glob.glob(fname)

			if len(names) > 0:
				fname = names[0]
			else:
				print('%s[!]%s No files found matching %s%s%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET))
				sys.exit(-1)

		else:
			fname = 'rootfs_%s_%s' % (image.replace('/', '_'), tag)

		label = '%s_%s' % (image.replace('/', '_'), tag)

	else:

		# handle file name

		fname = argv

		if not os.path.isfile(fname):
			print('%s[!]%s %s%s%s is not an existing file.' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET))
			sys.exit(-1)

		idx = -1

		for ext in exts:
			idx = argvl.find(ext)

			if idx != -1:
				break

		label = os.path.basename(argvl[:idx])

		if label.startswith('rootfs_'):
			label = label[len('rootfs_'):]

		if label.find('_') == -1:
			label += '_' + tag

	return image, tag, fname, label


# sanity check WSL installation

def probe_wsl(silent = False):
	"""
	Checks whether the WSL is installed and not running.

	:type silent: Whether to print an error message or just return an empty string on failure.

	:return: Paths to the WSL directory and lxrun/bash executables.
	"""

	global is_cygwin

	if not is_cygwin:
		packagesSubFolder = os.path.join(os.getenv('LocalAppData'), 'Packages')
		basedir = os.path.join(packagesSubFolder, 'CanonicalGroupLimited.UbuntuonWindows_79rhkp1fndgsc')
		localStateDir = os.path.join(basedir, 'LocalState')
	else:
		print('JPST: not yet fixed when running this process via cygwin, sorry!')
		sys.exit(-1)
		basedir = subprocess.check_output('/usr/bin/cygpath -F 0x001c', shell = True, universal_newlines = True)
		basedir = os.path.join(basedir.strip(), 'lxss')

	if not os.path.isdir(basedir):
		if silent:
			return None, None

		print('%s[!]%s The Linux subsystem is not installed. Please go through the standard installation procedure first.' % (Fore.RED, Fore.RESET))
		sys.exit(-1)

	# new temp is in basedir/LocalState/temp
	if os.path.exists(os.path.join(localStateDir, 'temp')) and os.listdir(os.path.join(localStateDir, 'temp')):
		if silent:
			return None, None

		print('%s[!]%s The Linux subsystem is currently running. Please kill all instances before continuing.' % (Fore.RED, Fore.RESET))
		sys.exit(-1)

	if not is_cygwin:
		syspath = os.getenv('SystemRoot')
	else:
		syspath = subprocess.check_output('/usr/bin/cygpath -W', shell = True, universal_newlines = True).strip()

	lxpath  = ''
	#methinks location in System32 is from legacy installer
	lxpaths = [os.path.join(syspath, 'WinSxS\\amd64_microsoft-windows-lxss-installer_31bf3856ad364e35_10.0.16299.15_none_26fe0303c009a799'), os.path.join(syspath, 'System32')]

	for path in lxpaths:
		if os.path.exists(os.path.join(path, 'LxRun.exe')):
			lxpath = path
			break

	if not lxpath and not silent:
		print('%s[!]%s Unable to find %slxrun.exe%s in the expected locations.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET))
		sys.exit(-1)
		
	bashpath = ''
	#new iteration of WSL splitted all linux related resources in seperate folders inside C:\Windows\WinSxS\*
	bashpaths = [os.path.join(syspath, 'WinSxS', 'amd64_microsoft-windows-lxss-bash_31bf3856ad364e35_10.0.16299.15_none_62878a822db68b25')]
	
	for path in bashpaths:
		if os.path.exists(os.path.join(path, 'bash.exe')):
			bashpath = path
			break
	
	if not bashpath and not slient:
		print('%s[!]%s Unable to find %bash.exe%s in the expected locations.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET))
		sys.exit(-1)

	return basedir, lxpath, bashpath


# translate the path between Windows and Cygwin

def path_trans(path):
	"""
	Translate the path, if required.
	Under the native Windows installation of Python, this function does nothing.
	Under the Cygwin version, the provided path is translated to a Windows-native path.

	:param path: Path to be translated.
	:return: Translated path.
	"""

	global is_cygwin

	if not is_cygwin or not path.startswith('/cygdrive/'):
		return path

	# too slow:
	# subprocess.check_output('/usr/bin/cygpath -w ' + shlex.quote(path), shell = True, universal_newlines = True).strip()

	path = path[10] + ':\\' + path[12:].replace('/', '\\')
	return path


# get label of rootfs

def get_label(path):
	"""
	Gets the label for the specified rootfs. If the .switch_label file is not present,
	but the OS was identified, the file will be created for future use.

	:param path: Path to the rootfs.

	:return: Label of the rootfs.
	"""

	# see if .switch_label exists

	if os.path.isfile(os.path.join(path, '.switch_label')):
		try:
			with open(os.path.join(path, '.switch_label')) as f:
				label = f.readline().strip()

				if len(label) > 0:
					return label

		except OSError:
			pass

	# check if the directory name has any stuff appended to it

	dirname = os.path.basename(path)

	if dirname.startswith('rootfs_'):
		label = dirname[len('rootfs_'):]

		if len(label) > 0:

			# save label for next occasion

			try:
				with open(os.path.join(path, '.switch_label'), 'w') as f:
					f.write(label + '\n')
			except OSError:
				pass

			return label

	# see if any *release files exist in /etc/

	rlsfiles = glob.glob(os.path.join(path, 'etc', '*release')) + glob.glob(os.path.join(path, 'usr', 'lib', 'os-release*'))

	if len(rlsfiles) > 0:
		rlslines = []

		for file in rlsfiles:
			try:
				with open(file) as f:
					rlslines += f.readlines()
			except OSError:
				pass

		name = ['', '', '']  # ID || DISTRIB_ID || NAME
		vers = ['', '', '']  # DISTRIB_CODENAME || DISTRIB_RELEASE || VERSION_ID

		for line in rlslines:
			kv = line.split('=', 1)

			if len(kv) < 2:
				continue

			key = kv[0].strip().strip('"\'').lower()
			val = kv[1].strip().strip('"\'').lower()

			if len(val) == 0:
				continue

			if key == 'id':
				name[0] = val
			elif key == 'distrib_id':
				name[1] = val
			elif key == 'name':
				name[2] = val

			if key == 'distrib_codename':
				vers[0] = val
			elif key == 'distrib_release':
				vers[1] = val
			elif key == 'version_id':
				vers[2] = val

		name = list(filter(None, name))
		vers = list(filter(None, vers))

		if len(name) > 0:
			label = name[0] + ('_' + vers[0] if len(vers) > 0 else '')

			# save label for next occasion

			try:
				with open(os.path.join(path, '.switch_label'), 'w') as f:
					f.write(label + '\n')
			except OSError:
				pass

			return label

	# oh well

	return ''


# toggle cursor visibility in the terminal

def show_cursor():
	"""
	Turns the cursor back on in the terminal.
	"""

	if not sys.platform == 'win32':
		sys.stdout.write('\033[?25h')

	else:
		ci = ConsoleCursorInfo()
		handle = ctypes.windll.kernel32.GetStdHandle(-11)
		ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
		ci.visible = True
		ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))


def hide_cursor():
	"""
	Turns the cursor off in the terminal.
	"""

	global is_conemu

	if not sys.platform == 'win32':
		sys.stdout.write('\033[?25l')
		is_conemu = False

	else:
		ci = ConsoleCursorInfo()
		handle = ctypes.windll.kernel32.GetStdHandle(-11)
		ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
		ci.visible = False
		ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
		is_conemu = os.environ.get('ConEmuANSI') == 'ON'


# some characters are forbidden in NTFS, but are not in ext4. the most popular of these characters
# seems to be the colon character. LXSS solves this issue by escaping the character on NTFS.
# while this seems like a dumb implementation, it will be called a lot of times inside the
# decompression loop, so it has to be fast: http://stackoverflow.com/a/27086669/156626

def escape_ntfs_invalid(name):
	"""
	Escapes characters which are forbidden in NTFS, but are not in ext4.

	:param name: Path potentially containing forbidden NTFS characters.

	:return: Path with forbidden NTFS characters escaped.
	"""
	return name.replace('*', '#002A').replace('|', '#007C').replace(':', '#003A').replace('>', '#003E').replace('<', '#003C').replace('?', '#003F').replace('"', '#0022')


# stream copier with progress bar

def chunked_copy(name, source, dest):
	"""
	Copies one stream into another, with progress bar.

	:param name: Name of the file to display.
	:param source: Source stream.
	:param dest: Destination stream.

	:return: Number of bytes copied.
	"""

	global is_conemu

	size = int(source.info()['Content-Length'].strip())
	recv = 0

	if len(name) > 23:
		name = name[0:20] + '...'

	hide_cursor()

	while True:
		chunk = source.read(8192)
		recv += len(chunk)

		if not chunk:
			break

		dest.write(chunk)

		draw_progress(recv, size, name)

	show_cursor()

	return recv


# FileIO wrapper with progress bar

class ProgressFileObject(io.FileIO):
	def __init__(self, path, *args, **kwargs):
		self._total_size = os.path.getsize(path)
		self.current_extraction = ''
		io.FileIO.__init__(self, path, *args, **kwargs)

		hide_cursor()

	def read(self, length):
		"""
		Read at most size bytes, returned as bytes.

		Only makes one system call, so less data may be returned than requested.
		In non-blocking mode, returns None if no data is available.
		Return an empty bytes object at EOF.
		"""

		draw_progress(self.tell(), self._total_size, self.current_extraction)

		return io.FileIO.read(self, length)

	def __del__(self):
		show_cursor()


# standalone function to draw an interactive progressbar

def draw_progress(recv, size, name):
	"""
	Draws an interactive progressbar based on the specified information.

	:param recv: Number of bytes received.
	:param size: Total size of the file.
	:param name: Name of the file to display.
	"""

	global is_conemu, has_progress, last_progress

	if recv > size:
		recv = size

	if recv == size:
		clear_progress()
		return

	if time.time() - last_progress < 0.05:
		return

	has_progress  = True
	last_progress = time.time()

	if len(name) > 23:
		name = name[0:20] + '...'
	else:
		name = name.ljust(23, ' ')

	pct = round(recv / size * 100, 2)
	bar = int(50 * recv / size)
	sys.stdout.write('\r    %s [%s>%s] %0.2f%%' % (name, '=' * bar, ' ' * (50 - bar), pct))

	if is_conemu:
		sys.stdout.write('\033]9;4;1;%0.0f\033\\\033[39m' % pct)

	sys.stdout.flush()


def clear_progress():
	"""
	Clears the progress bar.
	"""

	global is_conemu, has_progress

	if not has_progress:
		return

	has_progress = False

	sys.stdout.write('\r%s\r' % (' ' * (66 + 23)))

	if is_conemu:
		sys.stdout.write('\033]9;4;0\033\\\033[39m')

	sys.stdout.flush()


# functions to interact with the registry

def get_lxss_user():
	"""
	Gets the active user inside WSL.

	:return: Tuple of UID, GID and the name of the user.
	"""
	
	#gets
	user = subprocess.check_output(['cmd', '/c', 'ubuntu.exe run whoami'], universal_newlines = True).strip()
	default_user_output = subprocess.check_output(['cmd', '/c', 'ubuntu.exe run id'], universal_newlines = True).strip()
	
	#splits
	default_user_output = default_user_output.split(' ')
	uidoutput = default_user_output[0]
	gidoutput = default_user_output[1]
	groupsoutput = default_user_output[2]
	
	#uid
	uidoutput = uidoutput.split('=')
	uidoutput = uidoutput[1]
	uid = uidoutput.replace('('+user+')','')
	
	#gid
	gidoutput = gidoutput.split('=')
	gidoutput = gidoutput[1]
	gid = gidoutput.replace('('+user+')','')
	
	return uid, gid, user


def set_default_user(user):
	"""
	Switches the active user inside WSL to the requested one.

	:param user: Name of the new user.
	"""

	try:
		subprocess.check_call(['cmd', '/C', 'ubuntu.exe config --default-user %s' % (user)])

	except subprocess.CalledProcessError as err:
		print('%s[!]%s Failed to roll back to old %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		print('%s[!]%s You are now the proud owner of one broken Linux subsystem! To fix it, run %slxrun /uninstall%s and %slxrun /install%s from the command prompt.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))
		sys.exit(-1)