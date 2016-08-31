#!/bin/bash
#
#   Sample global post-install hook for the WSL distribution switcher.
#   Supports Arch Linux, APT (Debian, Ubuntu..) and RPM-based (Fedora, CentOS..) distributions.
#   Remove ".sample" from file name for install.py to run it automatically after installation.
#
#   Accepts the following environmental variables:
#       REGULARUSER  -- name of your regular user; sent by install.py automatically.
#       ROOTPASSWD   -- root password to set; password is not reset if nothing is set.
#       SUDONOPASSWD -- if set to "1", regular user will be added to sudoers with NOPASSWD.
#
#   Installs the following packages:
#       locale, apt-utils, dialog -- Debian only, to fix apt/dpkg warnings
#       passwd, sudo -- Both, changes root password and adds regular user to sudoers
#       fakeroot, base-devel -- Arch Linux only, patched fakeroot to use TCP instead of Unix sockets
#       tar, gzip, bzip2, xz, squashfs-tools, vim, git, tmux, curl, wget -- Both, but not crucial per-se
#

logerr () { echo -e "\e[91m[!]\e[39m $@" 1>&2; }
logwrn () { echo -e "\e[93m[!]\e[39m $@"; }
log ()    { echo -e "\e[92m[*]\e[39m $@"; }

# detect package manager

log "Detecting operating system..."

DEB=$(test -f /usr/bin/dpkg && /usr/bin/dpkg --search /usr/bin/dpkg >> /dev/null 2>&1; test "$?" != "0"; echo "$?")
RPM=$(test -f /usr/bin/rpm && /usr/bin/rpm -q -f /usr/bin/rpm >> /dev/null 2>&1; test "$?" != "0"; echo "$?")
PAC=$(test -f /usr/bin/pacman && /usr/bin/pacman -Qo /usr/bin/pacman >> /dev/null 2>&1; test "$?" != "0"; echo "$?")

if [[ "${DEB}" == 1 ]]; then
	export DEBIAN_FRONTEND=noninteractive
	mgr="apt-get -y"
	mgrinst="${mgr} install"
elif [[ "${RPM}" == 1 ]]; then
	if ! type -P dnf >/dev/null; then
		mgr="dnf -y"
		#if ! grep -q "fastestmirror=true" /etc/dnf/dnf.conf; then
		#	echo -e "\nfastestmirror=true" >> /etc/dnf/dnf.conf
		#fi
	else
		mgr="yum -y"
	fi
	mgrinst="${mgr} install"
elif [[ "${PAC}" == 1 ]]; then
	mgr="pacman --noconfirm"
	mgrinst="${mgr} --needed -S"

	# fake chroot() in order to prevent installation failures:
	echo '/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4BdPBNddAD+RRYRoPYmm2orhgzJO2QSUh1Ilea0Hqf4n5/VkVmV4LG9rbFIVZpKGk2uZnYmbqXh7ZxJIWnXoP3BDp42H8DNvYVufvmBKsWmh9DYoUb9e4yV7fskyJhMGXTrtwYfF3acVqBdX6to3Tn+ZBb//X/Snr/gbjaKubb33c8qSowjVJEioaMGkhowfrcFylqKEtGIZQDVn1ZpG2jy6/F3TsS0eds2NdbAkyVyHLdZBpwFnNV/BUVA+ZJOPWzM9kmuM+FS6Y9aib+RKcxIc2pZgGpLPSbniyak50Z46gOgcWaOVaymRpq4dzPsa5zexFlyn7GPWz+K1h2JMYknLyAvuYiebgH1HAEBtjGRotTTtC8RxrVe/Z8GlfJrEyRaNKpJOmi2yDwONNPkXmTFN2dOtcaEiEB5TNOugCOCoxwhSjeJ5HVWyaG4578iPCx1gTveQMfXvGwvd4+W51PxJPLAy0VKN/5IHcupZbXhRV3h99Jf85jjM363cqeyvXIrscU/w0wfWuGY9wjHGcDnNlFk9v+oIyqxQzvHW0x2FhNnBfhogz4fvk2mPgvuG8PfNV4sVZZm00krY+RPHvvU2qmbUDHLccdfrGGAGrnYBkV+E9I0YBmukB7iQnPwcBwmegz0O7mfAb2ati5jbAzJsJiaaw7ikfc5lXX/cZLPxftKkK3rTPQf4CHpYJtYjvaboB3Vg7qMTTU6BprhCrr7xBbWWHTfCdEFOFsU7zGnl3q1/qCoeVT5+Rr9QUn2UGbbeibBMl9oIVjemlTWDZ5O+16Kz0C3mAbN7lP3CZadHQhdQAOAtjOdgDPOlBHD/7DunFncMU6kyUQ5qg6WlLdq5W/0BXbRBsIBxq4GhFBjaN5JrmsXUN1GQfWgMYrw63lm1AkrSTVfH/mJm+rUWrMHRxIMWAZw+AJXx1uvn5PbJ2HMA7KTJsdl/6kcbAc7BCGmNNliOllyiTM5rspozU2EphDT+qCGItgQQp0Md1nq9h5UnVp6lggH8Ikh9GFpkiiQNb+vwqTmEzLI386MCA2NDGjijnh0zxOVh/vqosfceSk/ADeQJ4KjmcrzIOZ/F6L+5gl482NyXt0SVOnNrwxtXcBPjwyNq1NLbX8d8+h/IGJeAfJlct7k/h9tuBFB/F4b9ucdZ4SlYLMcDnJmyZaUWPqa2bmRPBsOzjwjenLM1f0WMqGn6yqcaklwyaXBNkJjBdLHn1jG9eUAEWWh4nzsPFkp9Jf3OxqukJnYCzQ/eTJPTSwks3YmrMDGvkRfaZjAsRMPOt1KNCPdqC+j9dpYatjxRN95NvMgt09EWrWNt4HDjXcgx7QwvwtlCdbgAUoP5Odo3XNCFbXZzuqQkTJHyVA8pLPIZ0nN9xF+wasWaZ+m8HqhBZAMj1NV9Qgm2c6p8x5pNFZY4gJrDnO5MmlMSW+cR6IVS9X5Iowr4FO9HIIXH25sbO0EuGw2dILfF30JzIJIs6m5W7vxD8Nqb9oYfCiUbz40ETsq/x9vXgJ4yTO64CPg5J26GuFxAZJsxyO2kuupjPcpVoVUOF6nBPqIVRj1MUOgktZxT1ZKtIz3K1AR4HzKDn1bjKyiNx5Pc2osQzdtf8usfgQgIp3UCLvqcCEVIrNWS+hTc1r0J6eliP5R3a8T1c49loq5PJQAA5OFQ5XQD0PQAAfMJ0C4AAGgPxEmxxGf7AgAAAAAEWVo=' | base64 -d | xz -d > /root/libmockchroot.so
	export LD_PRELOAD=/root/libmockchroot.so

	# temporary workaround by @goreliu at
	#   https://github.com/Microsoft/BashOnWindows/issues/8#issuecomment-240026910
	# it's shipped as a binary blob, since otherwise it would require gcc to compile,
	# which is not available before pacman is set up. to recreate blob above, run:
	#   echo 'int chroot(const char *path){return 0;}' > chroot.c
	#   gcc chroot.c -shared -fPIC -o libmockchroot.so
	#   strip -s libmockchroot.so
	#   cat libmockchroot.so | xz | base64
else
	echo "Unsupported operating system." 1>&2; exit 1
fi

# update to prevent installation failures later on

log "Initiating system upgrade..."

if [[ "${DEB}" == 1 ]]; then
	${mgr} update && ${mgr} dist-upgrade && ${mgr} install apt-utils dialog locales
elif [[ "${RPM}" == 1 ]]; then
	${mgr} upgrade
elif [[ "${PAC}" == 1 ]]; then
	${mgr} -Sy
	${mgrinst} archlinux-keyring
	${mgr} -Su
	pacman-db-upgrade
	${mgr} -S ca-certificates-mozilla
fi

# fix locale warnings

if [[ "${DEB}" == 1 || "${PAC}" == 1 ]]; then
	log "Fixing locale warnings..."

	if [[ -f /usr/share/i18n/charmaps/UTF-8.gz ]]; then
		if ! type -P gzip >/dev/null; then
			${mgrinst} gzip
		fi

		gzip -d /usr/share/i18n/charmaps/UTF-8.gz
	fi

	if ! grep -q -E "^\s*en_US\.UTF-8" /etc/locale.gen; then
		echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
	fi

	locale-gen
fi

# fix root login by resetting the password
# this works on most distributions I tried, on others it might require --stdin or chpasswd

if [[ ! -z "${ROOTPASSWD}" ]]; then
	log "Resetting root password..."

	if ! type -P passwd >/dev/null; then
		${mgrinst} passwd
	fi

	echo -e "$ROOTPASSWD\n$ROOTPASSWD" | passwd
fi

# install sudo and edit sudoers

log "Setting up sudo..."

if ! type -P sudo >/dev/null; then
	${mgrinst} sudo
fi

if [[ ! -z "${REGULARUSER}" ]]; then
	if [[ "${SUDONOPASSWD}" == "1" ]]; then
		if ! grep -q -E "${REGULARUSER}.*?ALL.*?NOPASSWD.*?ALL" /etc/sudoers; then
			echo -e "\n${REGULARUSER}   ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
		fi
	else
		group="sudo"
		umpkg="passwd"

		if [[ "${DEB}" != 1 ]]; then
			group="wheel"
			umpkg="shadow-utils"

			if ! grep -q -E "^\s*%wheel" /etc/sudoers && grep -q -E "^\s*#\s*%wheel" /etc/sudoers; then
				sed -i '0,/%wheel/{s/^\s*#\s*//}' /etc/sudoers
			fi
		fi

		if ! type -P usermod >/dev/null; then
			${mgrinst} ${umpkg}
		fi

		usermod -aG "${group}" "${REGULARUSER}"
	fi
fi

# fix sudo hostname resolution warning

if ! grep -q "${HOSTNAME}" /etc/hosts; then
	log "Fixing hostname resolution warnings with sudo..."
	echo -e "\n127.0.1.1   ${HOSTNAME}.localdomain ${HOSTNAME}" >> /etc/hosts
fi

# install TCP version of fakeroot for Arch

if [[ "${PAC}" == 1 ]]; then
	log "Installing patched fakeroot..."

	# install original fakeroot and dependencies for makepkg

	${mgrinst} base-devel git

	# overwrite standard fakeroot with a temporary pass-through script
	# since we are root at this point, the bypass script has no side-effect

	echo -e '#!/bin/bash\nif [[ "$1" == "-v" ]]; then\n\techo 1.0; exit\nfi\nexport FAKEROOTKEY=1\nexec "$@"\nunset FAKEROOTKEY' > /usr/bin/fakeroot
	chmod +x /usr/bin/fakeroot

	# download and compile the fakeroot-tcp version from AUR

	pushd $(mktemp -d)
	git clone https://aur.archlinux.org/fakeroot-tcp.git && cd fakeroot-tcp

	# patch mkpkg to run as root temporarily and build package

	sed -i 's/EUID\s*==\s*0/EUID == 99999/' /usr/bin/makepkg
	makepkg -s
	sed -i 's/EUID\s*==\s*99999/EUID == 0/' /usr/bin/makepkg

	# switch fakeroot package

	${mgr} -R fakeroot
	${mgr} -U fakeroot-tcp-*.pkg.tar.xz

	# cleanup

	cd .. && rm -rf fakeroot-tcp
	popd
fi

# install some basics

log "Installing tools..."

if [[ "${DEB}" == 1 ]]; then
	distspec="xz-utils"
elif [[ "${RPM}" == 1 || "${PAC}" == 1 ]]; then
	distspec="xz"
fi

${mgrinst} vim tmux git curl wget tar gzip bzip2 squashfs-tools ${distspec}
