#!/usr/bin/env python3
# coding=utf-8
import sys
import glob
import time
import shutil
import os.path
import subprocess

if len(sys.argv) < 2:
	print('usage: ./install.py image[:tag] | archive')
	exit(-1)

# try to get colors, but don't make it a nuisance by requiring dependencies

hasfilter = False

if sys.platform == 'win32':
	try:
		from colorama import init
		init()
		hasfilter = True
	except ImportError:
		pass

if not sys.platform == 'win32' or hasfilter:
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

# handle arguments

fname = ''

if '.tar' not in sys.argv[1]:

	# handle image:tag

	image = sys.argv[1]
	tag   = 'latest'

	if ':' in image:
		idx   = image.find(':')
		tag   = image[idx + 1:]
		image = image[:idx]

	fname = 'rootfs_%s_%s.tar*' % (image, tag)
	names = glob.glob(fname)

	if len(names) > 0:
		fname = names[0]
	else:
		print('%s[!]%s No files found matching %s%s%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET))
		exit(-1)

else:

	# handle file name

	fname = sys.argv[1]

	if not os.path.isfile(fname):
		print('%s[!]%s %s%s%s is not an existing file.' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET))
		exit(-1)

# sanity checks

print('%s[*]%s Probing the Linux subsystem...' % (Fore.GREEN, Fore.RESET))

basedir = os.path.join(os.getenv('LocalAppData'), 'lxss')

if not os.path.isdir(basedir):
	print('%s[!]%s The Linux subsystem is not installed. Please go through the standard installation procedure first.' % (Fore.RED, Fore.RESET))
	exit(-1)

if os.path.exists(os.path.join(basedir, 'temp')):
	print('%s[!]%s The Linux subsystem is currently running. Please kill all instances before continuing.' % (Fore.RED, Fore.RESET))
	exit(-1)

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

# get /etc/{passwd,shadow} entries

print('%s[*]%s Fetching %s/etc/{passwd,shadow}%s entries for user %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, user, Fore.RESET))

etcpasswd = ''
etcshadow = ''

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'passwd')) as f:
		for line in f.readlines():
			if line.startswith(user + ':'):
				etcpasswd = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/passwd%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'shadow')) as f:
		for line in f.readlines():
			if line.startswith(user + ':'):
				etcshadow = line.strip()

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/shadow%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

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
except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to copy archive to WSL: %s' % (Fore.RED, Fore.RESET, err))
	exit(-1)

print('%s[*]%s Beginning extraction...' % (Fore.GREEN, Fore.RESET))

try:
	subprocess.check_call(['cmd', '/C', 'C:\\Windows\\sysnative\\bash.exe', '-c', 'cd ~/rootfs-temp && tar xfp %s' % fname])
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
	time.sleep(1)

	if not os.path.exists(os.path.join(basedir, 'temp')):
		break

# do the switch

print('%s[*]%s Backing up current %srootfs%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs'), os.path.join(basedir, 'rootfs-old')])
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
		subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs-old'), os.path.join(basedir, 'rootfs')])
	except subprocess.CalledProcessError as err:
		print('%s[!]%s Failed to roll back to old %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		print('%s[!]%s You are now the proud owner of one broken Linux subsystem! To fix it, run %slxrun /uninstall%s and %slxrun /install%s from the command prompt.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))

	exit(-1)

# append user entries to /etc/{passwd,shadow}

print('%s[*]%s Writing entries of user %s%s%s to %s/etc/{passwd,shadow}%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, user, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'passwd'), 'a') as f:
		f.write(etcpasswd + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/passwd%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

try:
	with open(os.path.join(basedir, 'rootfs', 'etc', 'shadow'), 'a') as f:
		f.write(etcshadow + '\n')

except OSError as err:
	print('%s[!]%s Failed to open file %s/etc/shadow%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)
