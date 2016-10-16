#!/bin/bash
#
#   Sample global post-install hook for the WSL distribution switcher.
#   Supports Arch Linux, APT (Debian, Ubuntu..) and RPM-based (Fedora, CentOS..) distributions.
#   Remove ".sample" from file name for install.py to run it automatically after installation.
#
#   Accepts the following environmental variables:
#       REGULARUSER   -- name of your regular user; sent by install.py automatically.
#       WINVER        -- build version of your Windows; sent by install.py automatically.
#       ROOTPASSWD    -- root password to set; password is not reset if nothing is set.
#       SUDONOPASSWD  -- if set to "1", regular user will be added to sudoers with NOPASSWD.
#       WITHOUTPACAUR -- if set to "1", AUR helper pacaur will not be installed under Arch.
#
#   Installs the following packages:
#       locale, apt-utils, dialog -- Debian only, to fix apt/dpkg warnings
#       passwd, sudo -- Both, changes root password and adds regular user to sudoers
#       fakeroot, pacaur, base-devel -- Arch Linux only, patched fakeroot to use TCP instead of Unix sockets
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

	echo -e 'Dpkg::Progress-Fancy "1";\nAPT::Color "1";' >> /etc/apt/apt.conf.d/99progressbar
elif [[ "${RPM}" == 1 ]]; then
	if type -P dnf >/dev/null; then
		mgr="dnf -y"

		echo -e "\ncolor=always" >> /etc/dnf/dnf.conf
		#echo -e "\nfastestmirror=true" >> /etc/dnf/dnf.conf
	else
		mgr="yum -y"

		echo -e "\ncolor=always" >> /etc/yum.conf
		#echo -e "\nfastestmirror=true" >> /etc/yum.conf
	fi
	mgrinst="${mgr} install"
elif [[ "${PAC}" == 1 ]]; then
	mgr="pacman --noconfirm"
	mgrinst="${mgr} --needed -S"

	sed -i 's/^#Color$/Color/' /etc/pacman.conf

	if [[ "${WINVER}" -lt 14936 ]]; then
		# fake chroot() for pacman in order to prevent installation failures during initial update
		echo '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' | base64 -d | xz -d > /lib64/libmockchroot.so
		echo '/lib64/libmockchroot.so' > /etc/ld.so.preload

		# it's shipped as a binary blob, since otherwise it would require gcc to compile,
		# which is not available before pacman is set up. to recreate blob above, run:
		#   wget https://gist.githubusercontent.com/RoliSoft/84813cc353caec614dee8bf74c1b09ef/raw/409978e320084e645b60d86dff7775dc06e9bc1e/libmockchroot.c -O libmockchroot.c
		#   gcc libmockchroot.c -shared -fPIC -ldl -o libmockchroot.so
		#   strip -s libmockchroot.so
		#   cat libmockchroot.so | xz | base64
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
elif [[ "${PAC}" == 1 ]]; then
	# update db and install super-essentials

	${mgr} -Sy
	${mgrinst} archlinux-keyring

	if [[ "${WINVER}" -lt 14936 ]]; then
		# switch primitive chroot mocker which always returns true,
		# to fakechroot which actually rewrites the paths

		${mgrinst} fakechroot
		echo '/usr/lib/libfakeroot/fakechroot/libfakechroot.so' > /etc/ld.so.preload
	fi

	# continue with system upgrade

	${mgr} -Su
	pacman-db-upgrade
	${mgr} -S ca-certificates-mozilla gawk
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

	${mgrinst} base-devel git po4a

	# overwrite standard fakeroot with a temporary pass-through script
	# since we are root at this point, the bypass script has no side-effect

	echo -e '#!/bin/bash\nif [[ "$1" == "-v" ]]; then\n\techo 1.0; exit\nfi\nexport FAKEROOTKEY=1\nexec "$@"\nunset FAKEROOTKEY' > /usr/bin/fakeroot
	chmod +x /usr/bin/fakeroot
	export PATH="/usr/bin/core_perl:/usr/bin/vendor_perl:$PATH"

	# download and patch the fakeroot package from ABS

	pushd $(mktemp -d)
	git clone git://git.archlinux.org/svntogit/packages.git --depth=1 --branch=packages/fakeroot && cd packages/trunk
	sed -i 's/--with-ipc=sysv$/--with-ipc=tcp/' PKGBUILD

	# patch mkpkg to run as root temporarily and build package

	sed -i 's/EUID\s*==\s*0/EUID == 99999/' /usr/bin/makepkg
	makepkg -si --noconfirm
	sed -i 's/EUID\s*==\s*99999/EUID == 0/' /usr/bin/makepkg

	# update pacman config to ignore fakeroot updates, as those use --with-ipc=sysv

	sed -i -e 's/IgnorePkg\s*=/IgnorePkg = fakeroot /' -e 's/^\s*#\s*IgnorePkg/IgnorePkg/' /etc/pacman.conf

	# cleanup

	cd ../.. && rm -rf packages
	popd
fi

# install pacaur for Arch

if [[ "${PAC}" == 1 && "${WITHOUTPACAUR}" != "1" ]]; then
	log "Installing pacaur..."

	# preinstall pacaur dependencies

	${mgrinst} yajl expac

	gpg --keyserver hkp://pool.sks-keyservers.net --recv-keys 487EACC08557AD082088DABA1EB2638FF56C0C53
	pushd $(mktemp -d)

	sed -i 's/EUID\s*==\s*0/EUID == 99999/' /usr/bin/makepkg

	# download and compile cower

	git clone https://aur.archlinux.org/cower.git --depth=1 && cd cower
	makepkg -si --noconfirm
	cd .. && rm -rf cower

	# download and compile pacaur

	git clone https://aur.archlinux.org/pacaur.git --depth=1 && cd pacaur
	makepkg -si --noconfirm
	cd .. && rm -rf pacaur

	sed -i 's/EUID\s*==\s*99999/EUID == 0/' /usr/bin/makepkg

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
