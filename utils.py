#!/usr/bin/env python3
# coding=utf-8
import os
import sys
import glob

# try to get colors, but don't make it a nuisance by requiring dependencies

has_filter = False

if sys.platform == 'win32':
	try:
		from colorama import init
		init()
		has_filter = True
	except ImportError:
		pass

if not sys.platform == 'win32' or has_filter:
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

	image = argv
	tag   = 'latest'
	fname = ''
	label = ''

	if not can_be_file or '.tar' not in argv:

		# handle image:tag

		if ':' in image:
			idx   = image.find(':')
			tag   = image[idx + 1:]
			image = image[:idx]

		if can_be_file:
			fname = 'rootfs_%s_%s.tar*' % (image, tag)
			names = glob.glob(fname)

			if len(names) > 0:
				fname = names[0]
			else:
				print('%s[!]%s No files found matching %s%s%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET))
				exit(-1)

		else:
			fname = 'rootfs_%s_%s' % (image, tag)

		label = '%s_%s' % (image, tag)

	else:

		# handle file name

		fname = argv

		if not os.path.isfile(fname):
			print('%s[!]%s %s%s%s is not an existing file.' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET))
			exit(-1)

		label = fname[:fname.find('.tar')]

		if label.startswith('rootfs_'):
			label = label[len('rootfs_'):]

	return image, tag, fname, label


# sanity check WSL installation

def probe_wsl(silent = False):
	"""
	Checks whether the WSL is installed and not running.

	:type silent: Whether to print an error message or just return an empty string on failure.

	:return: Path to the WSL directory.
	"""

	basedir = os.path.join(os.getenv('LocalAppData'), 'lxss')

	if not os.path.isdir(basedir):
		if silent:
			return None

		print('%s[!]%s The Linux subsystem is not installed. Please go through the standard installation procedure first.' % (Fore.RED, Fore.RESET))
		exit(-1)

	if os.path.exists(os.path.join(basedir, 'temp')):
		if silent:
			return None

		print('%s[!]%s The Linux subsystem is currently running. Please kill all instances before continuing.' % (Fore.RED, Fore.RESET))
		exit(-1)

	return basedir
