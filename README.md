# Windows Subsystem for Linux Distribution Switcher

The purpose of this project is to let you easily download and install new Linux distributions under Windows Subsystem for Linux and seamlessly switch between them.

The rootfs archives are currently downloaded from Docker Hub's official images' repositories ("source") or published image layers ("prebuilt").

If you want to read about some of the challenges I faced while implementing the scripts, you can check out [this blog post](https://lab.rolisoft.net/blog/switching-the-distribution-behind-the-windows-subsystem-for-linux.html). This readme only contains usage information and some troubleshooting.

## Usage

The scripts provided here are written in Python 3, and they need to be run from Windows, __NOT__ from WSL. You can download a Python 3 installer from their [official website](https://www.python.org/downloads/), or you can use the one bundled with Cygwin. Since WSL is stored in `%LocalAppData%` for each user, you don't need admin rights in order to use any of the scripts.

To begin, clone the repository or [download a copy](https://github.com/RoliSoft/WSL-Distribution-Switcher/archive/master.zip).

### Obtaining tarballs

#### get-source.py

This script can download the tarballs for the official images in Docker Hub.

The first argument of the script is the name of the image, optionally followed by a colon and the desired tag: `get-source.py image[:tag]`. For example, to get the rootfs tarball for Debian Sid, just run `get-source.py debian:sid`. If you don't specify a tag, `latest` will be used, which is generally the _stable_ edition of the distribution.

```
$ python get-source.py debian:sid
[*] Fetching official-images info for debian:sid...
[*] Fetching Dockerfile from repo tianon/docker-brew-debian/.../sid...
[*] Downloading archive https://raw.githubusercontent.com/.../sid/rootfs.tar.xz...
[*] Rootfs archive for debian:sid saved to rootfs_debian_sid.tar.xz.
```

For presentation purposes, the following images and tags are available as of August 18th:

* [debian](https://hub.docker.com/_/debian/) &ndash; 8.5, 8, jessie, latest __|__ jessie-backports __|__ oldstable __|__ oldstable-backports __|__ sid __|__ stable __|__ stable-backports __|__ stretch __|__ testing __|__ unstable __|__ 7.11, 7, wheezy __|__ wheezy-backports __|__ rc-buggy __|__ experimental
* [ubuntu](https://hub.docker.com/_/ubuntu/) &ndash; 12.04.5, 12.04, precise-20160707, precise __|__ 14.04.5, 14.04, trusty-20160802, trusty __|__ 16.04, xenial-20160809, xenial, latest __|__ 16.10, yakkety-20160806.1, yakkety, devel
* [fedora](https://hub.docker.com/_/fedora/) &ndash; latest, 24 __|__ 23 __|__ 22 __|__ 21 __|__ rawhide __|__ 20, heisenbug
* [centos](https://hub.docker.com/_/centos/) &ndash; latest, centos7, 7 __|__ centos6, 6 __|__ centos5, 5 __|__ centos7.2.1511, 7.2.1511 __|__ centos7.1.1503, 7.1.1503 __|__ centos7.0.1406, 7.0.1406 __|__ centos6.8, 6.8 __|__ centos6.7, 6.7 __|__ centos6.6, 6.6 __|__ centos5.11, 5.11
* [opensuse](https://hub.docker.com/_/opensuse/) &ndash; 42.1, leap, latest __|__ 13.2, harlequin __|__ tumbleweed
* [mageia](https://hub.docker.com/_/mageia/) &ndash; latest, 5
* [oraclelinux](https://hub.docker.com/_/oraclelinux/) &ndash; latest, 7, 7.2 __|__ 7.1 __|__ 7.0 __|__ 6, 6.8 __|__ 6.7 __|__ 6.6 __|__ 5, 5.11
* [alpine](https://hub.docker.com/_/alpine/) &ndash; 3.1 __|__ 3.2 __|__ 3.3 __|__ 3.4, latest __|__ edge
* [crux](https://hub.docker.com/_/crux/) &ndash; latest, 3.1
* [clearlinux](https://hub.docker.com/_/clearlinux/) &ndash; latest, base

#### get-prebuilt.py

This script can download the layers of the prebuilt images published on Docker Hub. This is what Docker downloads when you run `docker pull`.

The first argument of the script is the name of the image, optionally followed by a colon and the desired tag: `get-prebuilt.py image[:tag]`. For example, to get the rootfs tarball for Debian Sid, just run `get-prebuilt.py debian:sid`. If you don't specify a tag, `latest` will be used, which is generally the _stable_ edition of the distribution.

```
$ python get-prebuilt.py kalilinux/kali-linux-docker
[*] Requesting authorization token...
[*] Fetching manifest info for kalilinux/kali-linux-docker:latest...
[*] Downloading layer sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4...
[*] Downloading layer sha256:6e61dde25369335dcf17965aa372c086db53c8021e885df0e09f9c4536d3231e...
[*] Downloading layer sha256:45f74187929d366242688b3d32ccb5e86c205214071b99e94c0214e7ff2bc836...
[*] Downloading layer sha256:e5b4b71338633a415ad948734490e368e69605ba508a5fa8ad64775433798fb2...
[*] Downloading layer sha256:3f96326089c0580ebbcbb68d2f49dce1d7b6fe5cd79d211e4c887b0c9cdbeb02...
[*] Downloading layer sha256:d4ecedcfaa73285da5657fd51173fa9955468bf693332c03dce58ded73615c62...
[*] Downloading layer sha256:340395ad18dbbbd79d902342eef997fbd3ecb6679ad5005e5e714e8b0bc11e77...
[*] Downloading layer sha256:b2860afd831e842446489d37f8933c71dbd4f5d5f4b13d35185c4341fcca9a84...
[*] Rootfs archive for kalilinux/kali-linux-docker:latest saved to rootfs_kali....tar.gz.
```

### Installing new rootfs

The `install.py` script is responsible for installing the tarballs as new rootfs.

The first argument of the script is either the _a)_ name of the file or the _b)_ same image:tag notation used in the `get.py` script: `install.py image[:tag] | tarball | squashfs`. You can install tarballs from sources other than the Docker Hub, however, they're not guaranteed to work.

The specified file can be a `.tar*` archive, or a SquashFS image with `.sfs` or `.squashfs` extension. In order to process SquashFS images, the `unsquashfs` application needs to be installed inside WSL. You can do this with `apt-get install squashfs-tools` on the default distribution.

To install the freshly downloaded `rootfs_debian_sid.tar.xz` archive, run `install.py debian:sid` or `install.py rootfs_debian_sid.tar.xz`.

```
$ python install.py debian:sid
[*] Probing the Linux subsystem...
[*] Home directory is at /home/RoliSoft for user RoliSoft.
[*] Reading /etc/{passwd,shadow,group,gshadow} entries for users root and RoliSoft...
[*] Copying rootfs_debian_sid.tar.xz to /home/RoliSoft/rootfs-temp...
[*] Beginning extraction...
[*] Waiting for the Linux subsystem to exit...
[*] Backing up current rootfs...
        1 dir(s) moved.
[*] Switching to new rootfs...
        1 dir(s) moved.
[*] Writing entries of users root and RoliSoft to /etc/{passwd,shadow,group,gshadow}...
```

This operation extracts the tarball into your home directory from within WSL, then quits WSL and replaces the current rootfs with the new one.

Running `bash` should now launch the new distribution:

```
$ bash
RoliSoft@ROLISOFT-PC ≈/wsl-distrib $ cat /etc/debian_version
stretch/sid
```

### Switching between distributions

The `switch.py` script is responsible for switching between the installed distributions.

All installed distributions are labelled through a `.switch-label` file in the root directory. This is created from Windows, so it is not visible from within WSL and is only used by the switcher script.

When switching between distributions, the `rootfs` folder is renamed: the old one will get the value from the `.switch-label` file appended to it, e.g. `rootfs_debian_sid`, while the new one will be renamed from its `rootfs_ubuntu_trusty` name to `rootfs` in order to become the active one.

The `/home`, `/root` and similar directories are stored separately, and as such switching between distributions can be seamless, as your personal and dotfiles will persist and will never be touched during any operation.

The default installation is Ubuntu Trusty. Any rootfs directory with no switch label inside will automatically be labelled `ubuntu:trusty`, so this is the argument you'll have to specify if you want to go back to the original installation.

When the script is run without any arguments, the list of installed distributions will be returned:

```
$ python switch.py
usage: ./switch.py image[:tag]

The following distributions are currently installed:

  - debian:sid*
  - fedora:rawhide
  - ubuntu:trusty

To switch back to the default distribution, specify ubuntu:trusty as the argument.
```

To switch between the distributions, just run the script with the image:tag you want to switch to:

```
$ python switch.py fedora:rawhide
[*] Probing the Linux subsystem...
[*] Backing up current rootfs...
        1 dir(s) moved.
[*] Switching to new rootfs...
        1 dir(s) moved.

$ bash -c 'dnf --version'
1.1.9
  Installed: dnf-0:1.1.9-6.fc26.noarch at 2016-08-12 08:30
  Built    : Fedora Project at 2016-08-09 16:53
	...

$ python switch.py debian:sid
[*] Probing the Linux subsystem...
[*] Backing up current rootfs...
        1 dir(s) moved.
[*] Switching to new rootfs...
        1 dir(s) moved.

$ bash -c 'apt-get -v'
apt 1.3~pre2 (amd64)
Supported modules:
*Ver: Standard .deb
	...
```

As mentioned before, switching is just 2 directory rename operations. However, WSL cannot be running while this is happening.

## To-do list

* ~~Figure out pulling and merging the layers from Docker Hub directly, in order to support all published prebuilt images. The procedure is thoroughly documented on the [Docker Registry HTTP API V2](https://docs.docker.com/registry/spec/api/) page, however, merging the downloaded layers might present an issue.~~ Done, see `get-prebuilt.py`.

* ~~Check whether extracting the SquashFS files from within ISO images to a rootfs works as well as Docker's rootfs tarballs. If so, implement new installer to automate it.~~ Done, installer now supports SquashFS images as the first argument.

* Figure out if it's possible to attach the Linux-specific metadata from outside of WSL, so then tarballs can be extracted and processed without invoking WSL.

* Implement hooks, so patches can be applied to fix WSL issues on a per-image basis, or just user-specific ones, such as preinstalling a few packages.

## Troubleshooting

* __get-source.py returns "Failed to find a suitable rootfs specification in Dockerfile."__

The `Dockerfile` has no `ADD archive.tar /` directive. All suitable Linux distributions are packaged similarly and added into root with this directive. Its absence may mean you are trying to download an application based on an OS instead, or the `Dockerfile` for the operating system is a bit more complex than just "add these files".

`FROM` directives are not currently processed. Try downloading the image with `get-prebuilt.py`.

* __install.py returns an error after "Beginning extraction..."__

This depends on the error, which should be printed on the console. The Python script has no access to the error message due to `stdout`/`stderr` redirection limits within WSL. (See [issue #2](https://github.com/Microsoft/BashOnWindows/issues/2).)

Generally, you should switch back to the default installation (`./switch.py ubuntu:trusty`) and try again, since the extraction part has to be done from within WSL due to Linux-specific metadata being attached to the files.

In case of not found errors, make sure you have all dependencies installed from within WSL: `sudo apt-get install tar gzip bzip2 xz-utils`

In case of permission errors, make sure you have write access to your home directory at `/home/$USER` and `/tmp`. Also make sure you have no leftover `rootfs-temp` directory in your home. While the script removes such leftover artifacts, if these files were touched from outside of WSL, it's possible it can't remove it.

Also, I've noticed, if you create a directory or file outside of WSL, you will __not__ see it from within WSL, and if you try to write to a file with the same name, you'll just get a generic I/O error. In this case, open `%LocalAppData%\lxss` from Windows Explorer, and check if `home/rootfs-temp` exists.

## Screenshots

![installation](https://lab.rolisoft.net/images/wslswitcher/install.png)

![switching](https://lab.rolisoft.net/images/wslswitcher/switch.png?2)