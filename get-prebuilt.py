#!/usr/bin/env python3
# coding=utf-8
import sys
import json
import urllib.request
from utils import Fore, parse_image_arg, chunked_copy

# handle arguments

if len(sys.argv) < 2:
	print('usage: ./get-prebuilt.py image[:tag]')
	exit(-1)

image, tag, fname, label = parse_image_arg(sys.argv[1], False)

token = ''

# get auth token to Docker Hub

print('%s[*]%s Requesting authorization token...' % (Fore.GREEN, Fore.RESET))

try:
	with urllib.request.urlopen('https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s:pull' % image) as f:

		data  = json.loads(f.read().decode('utf-8'))
		token = data['token']

except urllib.error.HTTPError as err:
	print('%s[!]%s Failed to authorization token: %s' % (Fore.RED, Fore.RESET, err))
	exit(-1)

except KeyError as err:
	print('%s[!]%s Failed to authorization token: %s' % (Fore.RED, Fore.RESET, err))
	exit(-1)

# get the image manifest

print('%s[*]%s Fetching manifest info for %s%s%s:%s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, image, Fore.RESET, Fore.YELLOW, tag, Fore.RESET))

manifest = {}

try:
	r = urllib.request.Request('https://registry.hub.docker.com/v2/%s/manifests/%s' % (image, tag))
	r.add_header('Authorization', 'Bearer ' + token)

	with urllib.request.urlopen(r) as f:

		manifest = json.loads(f.read().decode('utf-8'))

		if len(manifest['fsLayers']) == 0:
			print('%s[!]%s Manifest for image %s%s%s has no layers.' % (Fore.RED, Fore.RESET, Fore.BLUE, image, Fore.RESET))
			exit(-1)

except urllib.error.HTTPError as err:
	print('%s[!]%s Failed to fetch manifest info for %s%s%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, image, Fore.RESET, err))
	exit(-1)

# download the layers

dled   = set()
fname += '.tar.gz'

for layer in manifest['fsLayers']:
	if layer['blobSum'] in dled:
		continue

	dled.add(layer['blobSum'])

	print('%s[*]%s Downloading layer %s%s%s...' % (Fore.GREEN, Fore.RESET, Fore.BLUE, layer['blobSum'], Fore.RESET))

	try:
		r = urllib.request.Request('https://registry.hub.docker.com/v2/%s/blobs/%s' % (image, layer['blobSum']))
		r.add_header('Authorization', 'Bearer ' + token)

		with urllib.request.urlopen(r) as u, open(fname, 'ab') as f:
			chunked_copy(fname, u, f)

	except urllib.error.HTTPError as err:
		print('%s[!]%s Failed to download layer %s%s%s: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, layer['blobSum'], Fore.RESET, err))
		exit(-1)

	except OSError as err:
		print('%s[!]%s Failed to open file %s%s%s for writing: %s' % (Fore.RED, Fore.RESET, Fore.BLUE, fname, Fore.RESET, err))
		exit(-1)

print('%s[*]%s Rootfs archive for %s%s%s:%s%s%s saved to %s%s.tar.gz%s.' % (Fore.GREEN, Fore.RESET, Fore.YELLOW, image, Fore.RESET, Fore.YELLOW, tag, Fore.RESET, Fore.GREEN, fname, Fore.RESET))
