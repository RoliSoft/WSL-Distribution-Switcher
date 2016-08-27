#!/bin/bash
#
#   Sample global post-install hook for the WSL distribution switcher.
#   Supports APT (Debian, Ubuntu..) and RPM-based (Fedora, CentOS..) distributions.
#   Remove ".sample" from file name for install.py to run it automatically after installation.
#
#   Accepts the following environmental variables:
#       REGULARUSER -- name of your regular user; sent by install.py automatically.
#       ROOTPASSWD  -- root password to set; password is not reset if nothing is set.
#
#   Installs the following packages:
#       locale, apt-utils, dialog -- Debian only, to fix apt/dpkg warnings
#       passwd, sudo -- Both, changes root password and adds regular user to sudoers
#       tar, gzip, bzip2, xz, squashfs-tools, vim, git, tmux -- Both, but not crucial per-se
#

logerr () { echo -e "\e[91m[!]\e[39m $@" 1>&2; }
logwrn () { echo -e "\e[93m[!]\e[39m $@"; }
log ()    { echo -e "\e[92m[*]\e[39m $@"; }

# detect package manager

log "Detecting operating system..."

DEB=$(test -f /usr/bin/dpkg && /usr/bin/dpkg --search /usr/bin/dpkg >> /dev/null 2>&1; test "$?" != "0"; echo "$?")
RPM=$(test -f /usr/bin/rpm && /usr/bin/rpm -q -f /usr/bin/rpm >> /dev/null 2>&1; test "$?" != "0"; echo "$?")

if [[ "${DEB}" == 1 ]]; then
	export DEBIAN_FRONTEND=noninteractive
	mgr="apt-get -y"
elif [[ "${RPM}" == 1 ]]; then
	if [[ -f /usr/bin/dnf ]]; then
		mgr="dnf -y"
		#if ! grep -q "fastestmirror=true" /etc/dnf/dnf.conf; then
		#	echo -e "\nfastestmirror=true" >> /etc/dnf/dnf.conf
		#fi
	else
		mgr="yum -y"
	fi
else
	echo "Unsupported operating system." 1>&2; exit 1
fi

# update to prevent installation failures later on

log "Initiating system upgrade..."

if [[ "${DEB}" == 1 ]]; then
	${mgr} update && ${mgr} dist-upgrade && ${mgr} install apt-utils dialog locales
elif [[ "${RPM}" == 1 ]]; then
	${mgr} upgrade
fi

# fix perl locale warnings with apt/dpkg

if [[ "${DEB}" == 1 ]]; then
	if [[ ! -f /etc/locale.gen ]] || ! grep -q -E "^\s*en_US\.UTF-8" /etc/locale.gen; then
		log "Fixing locale warnings with apt/dpkg..."

		if [[ -f /usr/share/i18n/charmaps/UTF-8.gz ]]; then
			if [[ ! -f /bin/gzip ]]; then
				${mgr} install gzip
			fi

			gzip -d /usr/share/i18n/charmaps/UTF-8.gz
		fi

		echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
		locale-gen
	fi
fi

# fix root login by resetting the password
# this works on most distributions I tried, on others it might require --stdin or chpasswd

if [[ ! -z "${ROOTPASSWD}" ]]; then
	log "Resetting root password..."

	if [[ ! -f /usr/bin/passwd ]]; then
		${mgr} install passwd
	fi

	echo -e "$ROOTPASSWD\n$ROOTPASSWD" | passwd
fi

# install sudo and edit sudoers

log "Setting up sudo..."

if [[ ! -f /usr/bin/sudo ]]; then
	${mgr} install sudo
fi

if [[ ! -z "${REGULARUSER}" ]] && ! grep -q -E "${REGULARUSER}.*?ALL.*?NOPASSWD.*?ALL" /etc/sudoers; then
	echo -e "\n${REGULARUSER}   ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
fi

# fix sudo hostname resolution warning

if ! grep -q "${HOSTNAME}" /etc/hosts; then
	log "Fixing hostname resolution warnings with sudo..."
	echo -e "\n127.0.1.1   ${HOSTNAME}.localdomain ${HOSTNAME}" >> /etc/hosts
fi

# install some basics

log "Installing tools..."

if [[ "${DEB}" == 1 ]]; then
	distspec="xz-utils"
elif [[ "${RPM}" == 1 ]]; then
	distspec="xz"
fi

${mgr} install vim tmux git tar gzip bzip2 squashfs-tools ${distspec}
