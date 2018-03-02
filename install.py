#!/usr/bin/env python3
# coding=utf-8
import re
import sys
import stat
import time
import atexit
import shutil
import tarfile
import os.path
import subprocess

from collections import OrderedDict
from ntfsea import ntfsea, lxattrb, stmode
from utils import *

try:
	import PySquashfsImage
	havesquashfs = True
except ImportError:
	havesquashfs = False

# handle arguments

handle_sigint()

imgarg   = ''
runhooks = True

if len(sys.argv) > 1:
	for arg in sys.argv[1:]:
		if arg.lower() == '--no-hooks':
			runhooks = False
		elif not imgarg:
			imgarg = arg

if not imgarg:
	print('usage: ./install.py [--no-hooks] image[:tag] | tarball | squashfs')
	print('\noptions:\n  --no-hooks    Omits running the hook scripts.')
	sys.exit(-1)

image, tag, fname, label = parse_image_arg(imgarg, True)

# sanity checks

print('%s[*]%s Probing the Linux subsystem...' % (Fore.GREEN, Fore.RESET))

basedir, lxpath, bashpath = probe_wsl()
#fix basedir to add LocalState\rootfs
basedir = os.path.join(basedir, 'LocalState')
rootFsDir = os.path.join(basedir, 'rootfs')
rootFsTempDir = os.path.join(basedir, 'rootfs-temp')

print('%s[*]%s Linux subsystem OK.' % (Fore.GREEN, Fore.RESET))



uid      = 0
gid      = 0
user     = ''
isroot   = False
homedir  = ''
homedirFQDN = ''

try:
	uid, gid, user = get_lxss_user()
	if user == 'root':
		isroot = True
		homedir = '/root'
	else:
		homedir = '/home/' + user

	homedirFQDN = os.path.join(rootFsDir, homedir.lstrip('/'))

	if len(homedir) == 0 or not os.path.isdir(homedirFQDN):
		print('%s[!]%s Failed to get home directory of default user in WSL: Returned path %s%s%s is not valid.' % (Fore.RED, Fore.RESET, Fore.BLUE, homedirFQDN, Fore.RESET))
		sys.exit(-1)

	print('%s[*]%s Default user is %s%s%s at %s%s%s.' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, user, Fore.RESET, Fore.BLUE, homedir, Fore.RESET))

except BaseException as err:
	print('%s[!]%s Failed to get home directory of default user in WSL: %s' % (Fore.RED, Fore.RESET, err))
	sys.exit(-1)

# check squashfs prerequisites
fext = os.path.splitext(fname)[-1].lower()

if (fext == '.sfs' or fext == '.squashfs') and not havesquashfs:
	print('%s[!]%s Module %sPySquashfsImage%s is not available. Install it with %spip3 install PySquashfsImage%s for SquashFS support.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))
	sys.exit(-1)

# get /etc/{passwd,shadow,group,gshadow} entries

print('%s[*]%s Reading %s/etc/{passwd,shadow,group,gshadow}%s entries for %sroot%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, Fore.RESET, (' and %s%s%s' % (Fore.YELLOW, user, Fore.RESET) if not isroot else '')))

etcpasswduser  = ''
etcshadowroot  = ''
etcshadowuser  = ''
etcgroupuser   = ''
etcgshadowuser = ''

if not isroot:
	try:
		with open(os.path.join(rootFsDir, 'etc', 'passwd'), newline='\n') as f:
			for line in f.readlines():
				if line.startswith(user + ':'):
					etcpasswduser = line.strip()

	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/passwd%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		sys.exit(-1)

try:
	with open(os.path.join(rootFsDir, 'etc', 'shadow'), newline='\n') as f:
		for line in f.readlines():
			if line.startswith('root:'):
				etcshadowroot = line.strip()
			if not isroot and line.startswith(user + ':'):
				etcshadowuser = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/shadow%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	sys.exit(-1)

if not isroot:
	try:
		with open(os.path.join(rootFsDir, 'etc', 'group'), newline='\n') as f:
			for line in f.readlines():
				if line.startswith(user + ':'):
					etcgroupuser = line.strip()

	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/group%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		sys.exit(-1)

	try:
		with open(os.path.join(rootFsDir, 'etc', 'gshadow'), newline='\n') as f:
			for line in f.readlines():
				if line.startswith(user + ':'):
					etcgshadowuser = line.strip()

	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/gshadow%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		sys.exit(-1)

if etcshadowroot:
	parts = etcshadowroot.split(':')
	if parts[1] == '*' or parts[1].startswith('!'):
		#etcshadowroot = ''
		#set user password as root pw
		print('%s[*]%s Copying password of user %s to root since most images have no sudoers' % (Fore.GREEN, Fore.RESET, user))
		if not isroot:
			etcshadowroot = etcshadowuser
	else:
		etcshadowroot = parts[1]

# remove old remnants
if os.path.exists(rootFsTempDir):
	print('%s[*]%s Removing leftover %srootfs-temp%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

	try:
		def retry_rw(operation, name, exc):
			os.chmod(name, stat.S_IWRITE)
			operation(name)

		shutil.rmtree(rootFsTempDir, onerror = retry_rw)

	except Exception:
		pass

	# ensure it's removed
	if os.path.exists(rootFsTempDir):
		print('%s[*]%s Failed to remove leftover %srootfs-temp%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET))
		sys.exit(-1)
# extract archive

print('%s[*]%s Beginning extraction...' % (Fore.GREEN, Fore.RESET))

if fext == '.sfs' or fext == '.squashfs':

	# extract rootfs from SquashFS

	try:
		img  = PySquashfsImage.SquashFsImage(fname)
		path = rootFsTempDir

		hide_cursor()
		ntfsea.init()

		i = 0
		for file in img.root.findAll():
			name = file.getPath().lstrip('./')
			winpath = path + '/' + escape_ntfs_invalid(name)

			draw_progress(i, img.total_inodes, name)
			i += 1

			try:

				# create directory or extract file

				if file.isFolder():
					os.makedirs(winpath, exist_ok = True)

				else:
					with open(winpath, 'wb') as f:
						f.write(file.getContent())

				# apply lxattrb

				os.chmod(winpath, 0o777)

				attrb = lxattrb.fromsfs(file).generate()
				ntfsea.writeattr(path_trans(winpath), 'lxattrb', attrb)

			except Exception as err:
				clear_progress()
				print('%s[!]%s Failed to extract %s: %s' % (Fore.YELLOW, Fore.RESET, name, err))
				pass

	finally:
		img.close()
		clear_progress()
		show_cursor()

else:

	# the TarFile class has a list of supported compression methods, but this is stored
	# in a dictionary, which somehow becomes randomized during each run. since the 'tar'
	# option accepts anything, if during randomization it gets in front of the actual
	# compression method the archive is using, the archive won't be opened properly anymore.
	#
	# this resulted in a very annoying heisenbug during the installation when ignore_zeros was
	# set to True. thanks to @yyjdelete for tracking it down: https://bugs.python.org/issue28449
	#
	# since ignore_zeros is pretty useful due to the use of multiple layers in the prebuilt images,
	# the workaround here is to monkeypatch the TarFile.OPEN_METH dictionary and replace it with
	# a dictionary whose order is preserved.

	tarfile.TarFile.OPEN_METH = OrderedDict()
	tarfile.TarFile.OPEN_METH['gz']  = 'gzopen'
	tarfile.TarFile.OPEN_METH['bz2'] = 'bz2open'
	tarfile.TarFile.OPEN_METH['xz']  = 'xzopen'
	tarfile.TarFile.OPEN_METH['tar'] = 'taropen'

	# extract rootfs from tarball

	fileobj = ProgressFileObject(fname)
	fileobj.current_extraction = 'Scanning archive...'

	try:
		ntfsea.init()
		path = rootFsTempDir
		with tarfile.open(fileobj = fileobj, mode = 'r:*', dereference = True, ignore_zeros = True, errorlevel = 2) as tar:

			file = tar.next()

			if file is None:
				clear_progress()
				print('%s[!]%s Failed to extract archive: unable to determine archive type.' % (Fore.RED, Fore.RESET))
				sys.exit(-1)

			while file is not None:
				try:

					# extract file

					file.name = file.name.lstrip('./')
					fileobj.current_extraction = file.name
					file.name = path + '/' + escape_ntfs_invalid(file.name)

					if file.issym() or file.islnk():

						# create symlink manually

						dirname = os.path.dirname(file.name)
						if not os.path.exists(dirname):
							os.makedirs(dirname, exist_ok=True)

						# if a hardlink's linkname begins with a leading dot, the dot must be omitted,
						# or else the symlink will be broken because it will be interpreted as relative
						with open(file.name, 'w', encoding='utf-8') as link:
							link.write(file.linkname.lstrip('.') if file.islnk() else file.linkname)

					elif file.isdev():

						# skip device files, such as /dev/*
						continue

					else:

						# extract file
						tar.extract(file, path)

					# apply lxattrb

					os.chmod(file.name, 0o777)

					attrb = lxattrb.fromtar(file).generate()
					ntfsea.writeattr(path_trans(file.name), 'lxattrb', attrb)

				except Exception as err:
					clear_progress()
					print('%s[!]%s Failed to extract %s: %s' % (Fore.YELLOW, Fore.RESET, fileobj.current_extraction, err))
					pass

				finally:
					file = tar.next()

		# some archives don't seem to have the directories themselves as separate
		# entries, and this results in lxattrb not being applied to them, which will
		# lead to bash.exe returning Error: 0x80070002 or 0x8007001f

		dattrb = lxattrb(stmode.FDIR | 0o755).generate()
		fattrb = lxattrb(stmode.FREG | 0o755).generate()

		for root, subFolders, files in os.walk(path):

			# apply generic root:root 0755 to those without an attribute

			for folder in subFolders:
				folder = path_trans(os.path.join(root, folder))

				if ntfsea.getattr(folder, 'lxattrb') is None:
					ntfsea.writeattr(folder, 'lxattrb', dattrb)

			for file in files:
				file = path_trans(os.path.join(root, file))

				if ntfsea.getattr(file, 'lxattrb') is None:
					ntfsea.writeattr(file, 'lxattrb', fattrb)

	except Exception as err:
		clear_progress()
		print('%s[!]%s Failed to extract archive: %s' % (Fore.RED, Fore.RESET, err))
		sys.exit(-1)

	finally:
		clear_progress()
		show_cursor()

# read label of current distribution

clabel = get_label(rootFsDir)

if not clabel:
	clabel = 'ubuntu_trusty'
	print('%s[!]%s No %s/.switch_label%s found, assuming current rootfs is %subuntu%s:%strusty%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.YELLOW, Fore.RESET))

# do the switch

print('%s[*]%s Backing up current %srootfs%s to %srootfs_%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.BLUE, clabel, Fore.RESET))

try:
	subprocess.check_output(['cmd', '/C', 'move', path_trans(rootFsDir), path_trans(os.path.join(basedir, 'rootfs_' + clabel))])

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to backup current %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	sys.exit(-1)

print('%s[*]%s Switching to new %srootfs%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

time.sleep(4)

try:
	subprocess.check_output(['cmd', '/C', 'move', path_trans(rootFsTempDir), path_trans(rootFsDir)])

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to switch to new %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	print('%s[*]%s Rolling back to old %srootfs%s...' % (Fore.YELLOW, Fore.RESET, Fore.BLUE, Fore.RESET))

	try:
		subprocess.check_output(['cmd', '/C', 'move', path_trans(os.path.join(basedir, 'rootfs_' + clabel)), path_trans(rootFsDir)])

	except subprocess.CalledProcessError as err:
		print('%s[!]%s Failed to roll back to old %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		print('%s[!]%s You are now the proud owner of one broken Linux subsystem! To fix it, run %slxrun /uninstall%s and %slxrun /install%s from the command prompt.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))

	sys.exit(-1)

# save label

try:
	with open(os.path.join(rootFsDir, '.switch_label'), 'w') as f:
		f.write(label + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/.switch_label%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
# append user entries to /etc/{passwd,shadow,group,gshadow}

print('%s[*]%s Writing entries of %sroot%s%s to %s/etc/{passwd,shadow,group,gshadow,}%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, Fore.RESET, (' and %s%s%s' % (Fore.YELLOW, user, Fore.RESET) if not isroot else ''), Fore.BLUE, Fore.RESET))

if not isroot:
	try:
		with open(os.path.join(rootFsDir, 'etc', 'passwd'), 'a', newline='\n') as f:
			f.write(etcpasswduser + '\n')
		#sudo not installed via image
		#with open(os.path.join(rootFsDir, 'etc', 'sudoers'), 'a', newline='\n') as f:
		#	f.write(u + ' ALL=(ALL) ALL' + '\n')
	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/passwd%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))

if not isroot or etcshadowroot:
	try:
		shadows = []

		with open(os.path.join(rootFsDir, 'etc', 'shadow'), 'r+', newline='\n') as f:
			shadows = f.readlines()

			if etcshadowroot:
				for i in range(len(shadows)):
					if shadows[i].startswith('root:'):
						parts = shadows[i].split(':')
						#parts[1] = etcshadowroot
						#jpst
						rootpw_parts = etcshadowroot.split(':')
						rootpw = rootpw_parts[1]
						parts[1] = rootpw
						shadows[i] = ':'.join(parts)

			f.seek(0)
			f.writelines(shadows)

			if etcshadowuser:
				f.write(etcshadowuser + '\n')

	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/shadow%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))

if not isroot:
	try:
		with open(os.path.join(rootFsDir, 'etc', 'group'), 'a', newline='\n') as f:
			f.write(etcgroupuser + '\n')

	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/group%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))

	try:
		with open(os.path.join(rootFsDir, 'etc', 'gshadow'), 'a', newline='\n') as f:
			f.write(etcgshadowuser + '\n')

	except OSError as err:
		print('%s[!]%s Failed to open file %s/etc/gshadow%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))

# check if post-install hooks exist

havehooks = False

if runhooks:
	hooks = ['all', image, image + '_' + tag]

	for hook in hooks:
		hookfile = 'hook_postinstall_%s.sh' % hook

		if os.path.isfile(hookfile):
			havehooks = True
			break

# switch to root, if regular user and have hooks

if not isroot and havehooks:

	print('%s[*]%s Switching default user to %sroot%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, Fore.RESET))

	try:
		set_default_user('root')

	except BaseException as err:
		print('%s[!]%s Failed to switch default user in WSL: %s' % (Fore.RED, Fore.RESET, err))
		sys.exit(-1)

	homedir  = '/root'
	homedirFQDN = os.path.join(rootFsDir, homedir.lstrip('/'))

	if not os.path.isdir(homedirFQDN):
		print('%s[!]%s Failed to get home directory of default user in WSL: Returned path %s%s%s is not valid.' % (Fore.RED, Fore.RESET, Fore.BLUE, homedirFQDN, Fore.RESET))
		sys.exit(-1)

	# since we switched to root, switch back to regular user on exit

	def switch_user_back(uid, gid, user):
		print('%s[*]%s Switching default user back to %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, user, Fore.RESET))

		try:
			set_default_user(user)

		except BaseException as err:
			print('%s[!]%s Failed to switch default user in WSL: %s' % (Fore.RED, Fore.RESET, err))
			sys.exit(-1)

	atexit.register(switch_user_back, uid, gid, user)


# run post-install hooks, if any

if havehooks:

	if not is_cygwin:
		winver = sys.getwindowsversion().build

	else:
		wmic  = subprocess.check_output(['cmd', '/c', 'wmic.exe os get buildnumber'], universal_newlines = True)
		match = re.match('BuildNumber[\s\r\n]+(\d+)', wmic)

		if match is not None:
			winver = int(match.group(1))
		else:
			winver = 0

	hooks = ['all', image, image + '_' + tag]

	for hook in hooks:
		print("DEBUG: hook="+hook)
		hookfile = 'hook_postinstall_%s.sh' % hook

		if os.path.isfile(hookfile):
			print('%s[*]%s Running post-install hook %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.GREEN, hook, Fore.RESET))

			hookpath = os.path.join(homedirFQDN, hookfile)
			print("DEBUG: hookpath="+hookpath)
			try:
				subprocess.check_call(['cmd', '/C', path_trans(bashpath) + '\\bash.exe', '-c', 'echo -n > /root/%s && chmod +x /root/%s' % (hookfile, hookfile)])

				if not os.path.isfile(hookpath):
					print('%s[!]%s Failed to copy hook to WSL: File %s%s%s not present.' % (Fore.RED, Fore.RESET, Fore.BLUE, hookpath, Fore.RESET))
					continue

			except subprocess.CalledProcessError as err:
				print('%s[!]%s Failed to run hook in WSL: %s' % (Fore.RED, Fore.RESET, err))
				continue

			try:
				with open(hookfile) as s, open(hookpath, 'a', newline='\n') as d:
					d.write(s.read().replace('\r', ''))

			except OSError as err:
				print('%s[!]%s Failed to open hook: %s' % (Fore.RED, Fore.RESET, err))
				continue

			try:
				subprocess.check_call(['cmd', '/C', path_trans(bashpath) + '\\bash.exe', '-c', 'REGULARUSER="%s" WINVER="%d" /root/%s' % (user if not isroot else '', winver, hookfile)])

			except subprocess.CalledProcessError as err:
				print('%s[!]%s Failed to run hook in WSL: %s' % (Fore.RED, Fore.RESET, err))
				continue

			os.unlink(hookpath)

print('%s[*]%s Finished install.' % (Fore.GREEN, Fore.RESET))