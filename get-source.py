#!/usr/bin/env python3
# coding=utf-8
import sys
import urllib.request
from utils import Fore, parse_image_arg, chunked_copy, clear_progress

# handle arguments

if len(sys.argv) < 2:
	print('usage: ./get-source.py image[:tag]')
	exit(-1)

image, tag, fname, label = parse_image_arg(sys.argv[1], False)

dfurl = ''
tgurl = ''

# find the Dockerfile for the specified image and tag

print('%s[*]%s Fetching official-images info for %s%s%s:%s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, image, Fore.RESET, Fore.YELLOW, tag, Fore.RESET))

try:
	with urllib.request.urlopen('https://raw.githubusercontent.com/docker-library/official-images/master/library/' + image) as f:

		data = f.read().decode('utf-8').splitlines() + ['']

		# there seems to be two versions for this file:
		#  a) simplistic one-line per tag:
		#       latest: git://github.com/oracle/docker-images.git@a44844fe085a561ded44865eafb63f742e4250c1 OracleLinux/7.2
		#  b) key-values spanning over multiple lines:
		#       GitRepo: https://github.com/CentOS/sig-cloud-instance-images.git
		#       Directory: docker
		#       Tags: latest, centos7, 7
		#       GitFetch: refs/heads/CentOS-7
		#       GitCommit: f5b919346432acc728078aa32ffb6dcf84d303a0

		# try a) first

		for line in data:
			if line.startswith(tag + ': '):

				# extract the parts

				line   = line.split(': ', 1)
				line   = line[1].split(' ', 1)
				path   = line[1]
				line   = line[0].split('@', 1)
				repo   = line[0]
				commit = line[1]
				repo   = repo[repo.find('github.com/') + len('github.com/'):]

				if repo.find('.git') != -1:
					repo = repo[:repo.find('.git')]

				if len(path) != 0:
					path = '/' + path

				# build direct URL to Dockerfile

				dfurl = 'https://raw.githubusercontent.com/%s/%s%s/Dockerfile' % (repo, commit, path)
				break

		# try b) second

		if not dfurl:
			repo   = ''
			path   = ''
			commit = ''
			isTag  = False

			for line in data:
				if line == '':

					# tags are separated by double new lines and we need to wait for all values
					# before building the direct URL

					if isTag and repo and commit:

						dfurl = 'https://raw.githubusercontent.com/%s/%s%s/Dockerfile' % (repo, commit, path)
						break

					else:
						continue

				line = line.split(': ', 1)

				# collect key-values

				if line[0] == 'GitRepo':
					repo = line[1]
					repo = repo[repo.find('github.com/') + len('github.com/') : repo.find('.git')]

				elif line[0] == 'Tags':
					tags  = line[1].split(', ')
					isTag = tag in tags

				elif line[0] == 'GitCommit':
					commit = line[1]

				elif line[0] == 'Directory':
					path = '/' + line[1]

		# otherwise, fail miserably

		if not dfurl:
			print('%s[!]%s Failed to find tag %s%s%s for image %s%s%s.' % (Fore.RED, Fore.RESET, Fore.BLUE, tag, Fore.RESET, Fore.BLUE, image, Fore.RESET))
			exit(-1)

except urllib.error.HTTPError as err:
	print('%s[!]%s Failed to fetch official-images info for %s%s%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, image, Fore.RESET, err))
	print('%s[!]%s If this is not an official image, try getting it with %sget-prebuilt.py %s%s.' % (Fore.RED, Fore.RESET, Fore.GREEN, sys.argv[1].strip(), Fore.RESET))
	exit(-1)

# process Dockerfile

print('%s[*]%s Fetching Dockerfile from repo %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, dfurl[dfurl.find('.com/') + len('.com/') : dfurl.find('/Dockerfile')], Fore.RESET))

try:
	with urllib.request.urlopen(dfurl) as f:

		data = f.read().decode('utf-8').splitlines()

		for line in data:
			line = line.split(' ')

			# we are only interested in rootfs archives, generally specified like so:
			#   ADD oraclelinux-7.2-rootfs.tar.xz /

			if line[0].lower() == 'add' and line[2] == '/':
				tgurl  = dfurl[:dfurl.rfind('/Dockerfile') + 1] + line[1]
				fname += line[1][line[1].find('.tar'):]

		# otherwise, fail miserably

		if not tgurl:
			print('%s[!]%s Failed to find a suitable rootfs specification in Dockerfile.' % (Fore.RED, Fore.RESET))
			exit(-1)

except urllib.error.HTTPError as err:
	print('%s[!]%s Failed to fetch Dockerfile from %s%s%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, dfurl, Fore.RESET, err))
	exit(-1)

# download rootfs archive

print('%s[*]%s Downloading archive %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, tgurl, Fore.RESET))

try:
	with urllib.request.urlopen(tgurl) as u, open(fname, 'wb') as f:
		chunked_copy(fname, u, f)

except urllib.error.HTTPError as err:
	clear_progress()
	print('%s[!]%s Failed to download archive from %s%s%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, tgurl, Fore.RESET, err))
	exit(-1)

except OSError as err:
	clear_progress()
	print('%s[!]%s Failed to open file %s%s%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET, err))
	exit(-1)

print('%s[*]%s Rootfs archive for %s%s%s:%s%s%s saved to %s%s%s.' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, image, Fore.RESET, Fore.YELLOW, tag, Fore.RESET, Fore.GREEN, fname, Fore.RESET))
