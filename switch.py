#!/usr/bin/env python3
# coding=utf-8
import sys
import os.path
import subprocess

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

if len(sys.argv) < 2:
	print('usage: ./switch.py image[:tag]\n\nTo switch back to the default distribution, specify %subuntu%s:%strusty%s as the argument.' % (Fore.YELLOW, Fore.RESET, Fore.YELLOW, Fore.RESET))
	exit(-1)

# handle arguments

image = sys.argv[1]
tag   = 'latest'

if ':' in image:
	idx   = image.find(':')
	tag   = image[idx + 1:]
	image = image[:idx]

label = '%s_%s' % (image, tag)

# sanity checks

print('%s[*]%s Probing the Linux subsystem...' % (Fore.GREEN, Fore.RESET))

basedir = os.path.join(os.getenv('LocalAppData'), 'lxss')

if not os.path.isdir(basedir):
	print('%s[!]%s The Linux subsystem is not installed. Please go through the standard installation procedure first.' % (Fore.RED, Fore.RESET))
	exit(-1)

if os.path.exists(os.path.join(basedir, 'temp')):
	print('%s[!]%s The Linux subsystem is currently running. Please kill all instances before continuing.' % (Fore.RED, Fore.RESET))
	exit(-1)

# read label of current distribution

clabel = ''

try:
	with open(os.path.join(basedir, 'rootfs', '.switch_label')) as f:
		clabel = f.readline().strip()

except OSError as err:
	clabel = 'ubuntu_trusty'

	if label == clabel:
		print('%s[!]%s No %s/.switch_label%s found, and the target rootfs is %subuntu%s:%strusty%s. Cannot continue.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.YELLOW, Fore.RESET))
		print('%s[!]%s To fix this, run %secho some_tag > /.switch_label%s (replacing %ssome_tag%s with something like %sdebian_sid%s) from the current Bash terminal.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))
		exit(-1)
	else:
		print('%s[!]%s No %s/.switch_label%s found, assuming current rootfs is %subuntu%s:%strusty%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, Fore.YELLOW, Fore.RESET, Fore.YELLOW, Fore.RESET))

# sanity checks, take two

if clabel == label:
	print('%s[!]%s The %s%s%s:%s%s%s rootfs is the current installation.' % (Fore.YELLOW, Fore.RESET, Fore.YELLOW, image, Fore.RESET, Fore.YELLOW, tag, Fore.RESET))
	exit(-1)

if not os.path.isdir(os.path.join(basedir, 'rootfs_' + label)):
	print('%s[!]%s The %s%s%s:%s%s%s rootfs is not installed.' % (Fore.RED, Fore.RESET, Fore.YELLOW, image, Fore.RESET, Fore.YELLOW, tag, Fore.RESET))
	exit(-1)

# do the switch

print('%s[*]%s Backing up current %srootfs%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs'), os.path.join(basedir, 'rootfs_' + clabel)])

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to backup current %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	exit(-1)

print('%s[*]%s Switching to new %srootfs%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, Fore.RESET))

try:
	subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs_' + label), os.path.join(basedir, 'rootfs')])

except subprocess.CalledProcessError as err:
	print('%s[!]%s Failed to switch to new %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
	print('%s[*]%s Rolling back to old %srootfs%s...' % (Fore.YELLOW, Fore.RESET, Fore.BLUE, Fore.RESET))

	try:
		subprocess.check_call(['cmd', '/C', 'move', os.path.join(basedir, 'rootfs_' + clabel), os.path.join(basedir, 'rootfs')])

	except subprocess.CalledProcessError as err:
		print('%s[!]%s Failed to roll back to old %srootfs%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, Fore.RESET, err))
		print('%s[!]%s You are now the proud owner of one broken Linux subsystem! To fix it, run %slxrun /uninstall%s and %slxrun /install%s from the command prompt.' % (Fore.RED, Fore.RESET, Fore.GREEN, Fore.RESET, Fore.GREEN, Fore.RESET))

	exit(-1)
