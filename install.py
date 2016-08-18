#!/usr/bin/env python3
# coding=utf-8
import sys
import time
import shutil
import os.path
import subprocess
from utils import Fore, parse_image_arg, probe_wsl

# handle arguments

if len(sys.argv) < 2:
	print('usage: ./install.py image[:tag] | tarball | squashfs')
	exit(-1)

image, tag, fname, label = parse_image_arg(sys.argv[1], True)

# sanity checks

print('%s[*]%s Probing the Linux subsystem...' % (Fore.GREEN, Fore.RESET))

basedir = probe_wsl()

user     = ''
homedir  = ''
homedirw = ''

# somewhat a major issue, stdout and stderr can't be redirected, so this script can't monitor the output
# of any of the launched commands. it can, however, receive the exit status, so that's something, I guess.
# ref: https://github.com/Microsoft/BashOnWindows/issues/2

try:
	subprocess.check_call(['cmd', '/C', 'C:\\Windows\\sysnative\\bash.exe', '-c', 'echo $HOME > /tmp/.wsl_usr.txt; echo $USER >> /tmp/.wsl_usr.txt'])
	out = os.path.join(basedir, 'rootfs/tmp/.wsl_usr.txt')

	if not os.path.isfile(out):
		print('%s[!]%s Failed to get home directory of default user in WSL: Output file %s%s%s not present.' % (Fore.RED, Fore.RESET, Fore.BLUE, out, Fore.RESET))
		exit(-1)

	with open(out) as f:
		homedir  = f.readline().strip()
		homedirw = os.path.join(basedir, homedir.lstrip('/'))

		if len(homedir) == 0 or not os.path.isdir(homedirw):
			print('%s[!]%s Failed to get home directory of default user in WSL: Returned path %s%s%s is not valid.' % (Fore.RED, Fore.RESET, Fore.BLUE, homedirw, Fore.RESET))
			exit(-1)

		user = f.readline().strip()

	print('%s[*]%s Home directory is at %s%s%s for user %s%s%s.' % (Fore.GREEN, Fore.RESET, Fore.BLUE, homedir, Fore.RESET, Fore.YELLOW, user, Fore.RESET))

	os.unlink(out)

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to get home directory of default user in WSL: %s' % (Fore.RED, Fore.RESET, err))
	exit(-1)

# check squashfs prerequisites

fext = os.path.splitext(fname)[-1].lower()

if fext == '.sfs' or fext == '.squashfs':
	paths = ['usr/local/sbin', 'usr/local/bin', 'usr/sbin', 'usr/bin', 'sbin', 'bin']
	found = False

	for path in paths:
		if os.path.isfile(os.path.join(basedir, 'rootfs', path, 'unsquashfs')):
			found = True
			break

	if not found:
		print('%s[!]%s Failed to find %sunsquashfs%s in the current WSL distribution. Install it with %sapt-get install squashfs-tools%s for SquashFS support.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))
		exit(-1)

# get /etc/{passwd,shadow,group,gshadow} entries

print('%s[*]%s Reading %s/etc/{passwd,shadow,group,gshadow}%s entries for users %sroot%s and %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.YELLOW, user, Fore.RESET))

etcpasswduser  = ''
etcshadowroot  = ''
etcshadowuser  = ''
etcgroupuser   = ''
etcgshadowuser = ''

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'passwd')) as f:
		for line in f.readlines():
			if line.startswith(user + ':'):
				etcpasswduser = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/passwd%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'shadow')) as f:
		for line in f.readlines():
			if line.startswith('root:'):
				etcshadowroot = line.strip()
			if line.startswith(user + ':'):
				etcshadowuser = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/shadow%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'group')) as f:
		for line in f.readlines():
			if line.startswith(user + ':'):
				etcgroupuser = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/group%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'gshadow')) as f:
		for line in f.readlines():
			if line.startswith(user + ':'):
				etcgshadowuser = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/gshadow%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

if etcshadowroot:
	parts = etcshadowroot.split(':')

	if parts[1] == '*' or parts[1].startswith('!'):
		etcshadowroot = ''
		print('%s[!]%s Your %sroot%s account has no password set, which means you cannot use %ssu%s. Since most distributions do not come with %ssudo%s preinstalled, you might end up powerless.' % (Fore.RED, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))

	else:
		etcshadowroot = parts[1]

# remove old remnants

if os.path.exists(os.path.join(homedirw, 'rootfs-temp')):
	print('%s[*]%s Removing leftover %srootfs-temp%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

	shutil.rmtree(os.path.join(homedirw, 'rootfs-temp'), True)

# move archive and extract it

print('%s[*]%s Copying %s%s%s to %s%s/rootfs-temp%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, fname, Fore.RESET, Fore.GREEN, homedir, Fore.RESET))

lsfname = os.path.abspath(fname)
lsfname = '/mnt/' + lsfname[0].lower() + '/' + lsfname[3:].replace('\\', '/')

try:
	subprocess.check_call(['cmd', '/C', 'C:\\Windows\\sysnative\\bash.exe', '-c', 'cd ~ && mkdir -p rootfs-temp && cd rootfs-temp && cp %s .' % lsfname])
	pass

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to copy archive to WSL: %s' % (Fore.RED, Fore.RESET, err))
	exit(-1)

print('%s[*]%s Beginning extraction...' % (Fore.GREEN, Fore.RESET))

xtrcmd = 'sudo tar xfp %s --ignore-zeros --exclude=\'dev/*\'' % fname

if fext == '.sfs' or fext == '.squashfs':
	xtrcmd = 'sudo unsquashfs -f -x -d . ' + fname

try:
	subprocess.check_call(['cmd', '/C', 'C:\\Windows\\sysnative\\bash.exe', '-c', 'cd ~/rootfs-temp && ' + xtrcmd])
	pass

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to extract archive in WSL: %s' % (Fore.RED, Fore.RESET, err))
	exit(-1)

try:
	os.unlink(os.path.join(homedirw, 'rootfs-temp', fname))
except:
	pass

# wait for WSL to exit

print('%s[*]%s Waiting for the Linux subsystem to exit...' % (Fore.GREEN, Fore.RESET))

while True:
	time.sleep(5)

	if not os.path.exists(os.path.join(basedir, 'temp')):
		break

# read label of current distribution

clabel = ''

try:
	with open(os.path.join(basedir, 'rootfs', '.switch_label')) as f:
		clabel = f.readline().strip()

except OSError as err:
	clabel = 'ubuntu_trusty'
	print('%s[!]%s No %s/.switch_label%s found, assuming current rootfs is %subuntu%s:%strusty%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.YELLOW, Fore.RESET))

# do the switch

print('%s[*]%s Backing up current %srootfs%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs'), os.path.join(basedir, 'rootfs_' + clabel)])

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to backup current %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

print('%s[*]%s Switching to new %srootfs%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	subprocess.check_call(['cmd', '/C', 'move', os.path.join(homedirw, 'rootfs-temp'), os.path.join(basedir, 'rootfs')])

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to switch to new %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	print('%s[*]%s Rolling back to old %srootfs%s...' % (Fore.YELLOW, Fore.RESET, Fore.BLUE, Fore.RESET))

	try:
		subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs_' + clabel), os.path.join(basedir, 'rootfs')])

	except subprocess.CalledProcessError as err:
		print('%s[!]%s Failed to roll back to old %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		print('%s[!]%s You are now the proud owner of one broken Linux subsystem! To fix it, run %slxrun /uninstall%s and %slxrun /install%s from the command prompt.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))

	exit(-1)

# append user entries to /etc/{passwd,shadow,group,gshadow}

print('%s[*]%s Writing entries of users %sroot%s and %s%s%s to %s/etc/{passwd,shadow,group,gshadow}%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.YELLOW, user, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'passwd'), 'a') as f:
		f.write(etcpasswduser + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/passwd%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	shadows = []

	with open(os.path.join(basedir, 'rootfs', 'etc', 'shadow'), 'r+') as f:
		shadows = f.readlines()

		if etcshadowroot:
			for i in range(len(shadows)):
				if shadows[i].startswith('root:'):
					parts = shadows[i].split(':')
					parts[1] = etcshadowroot
					shadows[i] = ':'.join(parts)

		f.seek(0)
		f.writelines(shadows)
		f.write(etcshadowuser + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/shadow%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'group'), 'a') as f:
		f.write(etcgroupuser + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/group%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'gshadow'), 'a') as f:
		f.write(etcgshadowuser + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/gshadow%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', '.switch_label'), 'w') as f:
		f.write(label + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/.switch_label%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
