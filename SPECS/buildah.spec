%global with_debug 1

%if 0%{?with_debug}
%global _find_debuginfo_dwz_opts %{nil}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

%global gomodulesmode GO111MODULE=on

%global import_path github.com/containers/buildah
%global branch release-1.43
%global commit0 9fe6fe4c0348e3f95875624f33522b4aae67f06e
%global shortcommit0 %(c=%{commit0}; echo ${c:0:7})

%if %{defined fedora}
%define build_with_btrfs 1
%endif

%if %{defined rhel}
%define fips 1
%define sequoia 1
%endif

%global git0 https://github.com/containers/%{name}

Name: buildah
# Set different Epoch for copr
%if %{defined copr_username}
Epoch: 102
%else
Epoch: 2
%endif
# DO NOT TOUCH the Version string!
# The TRUE source of this specfile is:
# https://github.com/containers/skopeo/blob/main/rpm/skopeo.spec
# If that's what you're reading, Version must be 0, and will be updated by Packit for
# copr and koji builds.
# If you're reading this on dist-git, the version is automatically filled in by Packit.
Version: 1.43.1
# The `AND` needs to be uppercase in the License for SPDX compatibility
License: Apache-2.0 AND BSD-2-Clause AND BSD-3-Clause AND ISC AND MIT AND MPL-2.0
Release: 3%{?dist}
%if %{defined golang_arches_future}
ExclusiveArch: %{golang_arches_future}
%else
ExclusiveArch: aarch64 ppc64le s390x x86_64
%endif
Summary: A command line tool used for creating OCI Images
URL: https://%{name}.io
%if 0%{?branch:1}
Source0: https://gitlab.cee.redhat.com/sustaining-engineering/container-tools/src-git/%{name}/-/archive/%{commit0}/%{branch}-%{shortcommit0}.tar.gz
%else
Source0: https://%{import_path}/archive/%{commit0}/%{name}-%{version}-%{shortcommit0}.tar.gz
%endif
BuildRequires: device-mapper-devel
BuildRequires: git-core
BuildRequires: golang >= 1.16.6
BuildRequires: glib2-devel
BuildRequires: glibc-static
%if !%{defined gobuild}
BuildRequires: go-rpm-macros
%endif
BuildRequires: gpgme-devel
BuildRequires: libassuan-devel
BuildRequires: make
%if %{defined build_with_btrfs}
BuildRequires: btrfs-progs-devel
%endif
BuildRequires: shadow-utils-subid-devel
BuildRequires: sqlite-devel
Requires: containers-common-extra
%if %{defined fedora}
BuildRequires: libseccomp-static
%else
BuildRequires: libseccomp-devel
%endif
Requires: libseccomp >= 2.4.1-0
Suggests: cpp
%if %{defined sequoia}
Requires: podman-sequoia
%endif

%description
The %{name} package provides a command line tool which can be used to
* create a working container from scratch
or
* create a working container from an image as a starting point
* mount/umount a working container's root file system for manipulation
* save container's root file system layer to create a new image
* delete a working container or an image

# This subpackage is only intended for CI testing.
# Not meant for end user/customer usage.
%package tests
Summary: Tests for %{name}

Requires: %{name} = %{epoch}:%{version}-%{release}
%if %{defined bats_epel}
Requires: bats
%else
Recommends: bats
%endif
Requires: bzip2
Requires: podman
Requires: golang
Requires: jq
Requires: httpd-tools
Requires: openssl
Requires: nmap-ncat
Requires: git-daemon

%description tests
%{summary}

This package contains system tests for %{name}

%prep
%if 0%{?branch:1}
%autosetup -Sgit -n %{name}-%{commit0}
%else
%autosetup -Sgit -n %{name}-%{commit0}
%endif

%build
%set_build_flags
export CGO_CFLAGS=$CFLAGS

# These extra flags present in $CFLAGS have been skipped for now as they break the build
CGO_CFLAGS=$(echo $CGO_CFLAGS | sed 's/-flto=auto//g')
CGO_CFLAGS=$(echo $CGO_CFLAGS | sed 's/-Wp,D_GLIBCXX_ASSERTIONS//g')
CGO_CFLAGS=$(echo $CGO_CFLAGS | sed 's/-specs=\/usr\/lib\/rpm\/redhat\/redhat-annobin-cc1//g')

%ifarch x86_64
export CGO_CFLAGS+=" -m64 -mtune=generic -fcf-protection=full"
%endif

export CNI_VERSION=`grep '^# github.com/containernetworking/cni ' src/modules.txt | sed 's,.* ,,'`
export LDFLAGS="-X main.buildInfo=`date +%s` -X main.cniVersion=${CNI_VERSION}"

export BUILDTAGS="seccomp $(hack/systemd_tag.sh) $(hack/libsubid_tag.sh) libsqlite3"
%if !%{defined build_with_btrfs}
export BUILDTAGS+=" exclude_graphdriver_btrfs"
%endif

%if %{defined fips}
export BUILDTAGS+=" libtrust_openssl"
%endif

%if %{defined sequoia}
export BUILDTAGS+=" containers_image_sequoia"
%endif

%gobuild -o bin/%{name} ./cmd/%{name}
%gobuild -o bin/imgtype ./tests/imgtype
%gobuild -o bin/copy ./tests/copy
%gobuild -o bin/tutorial ./tests/tutorial
%gobuild -o bin/inet ./tests/inet
%gobuild -o bin/dumpspec ./tests/dumpspec
%gobuild -o bin/passwd ./tests/passwd
%gobuild -o bin/crash ./tests/crash
%gobuild -o bin/wait ./tests/wait
%{__make} docs

%install
make DESTDIR=%{buildroot} PREFIX=%{_prefix} install install.completions

install -d -p %{buildroot}/%{_datadir}/%{name}/test/system
cp -pav tests/. %{buildroot}/%{_datadir}/%{name}/test/system
cp bin/imgtype %{buildroot}/%{_bindir}/%{name}-imgtype
cp bin/copy    %{buildroot}/%{_bindir}/%{name}-copy
cp bin/tutorial %{buildroot}/%{_bindir}/%{name}-tutorial
cp bin/inet     %{buildroot}/%{_bindir}/%{name}-inet
cp bin/dumpspec %{buildroot}/%{_bindir}/%{name}-dumpspec
cp bin/passwd %{buildroot}/%{_bindir}/%{name}-passwd
cp bin/crash %{buildroot}/%{_bindir}/%{name}-crash
cp bin/wait %{buildroot}/%{_bindir}/%{name}-wait

rm %{buildroot}%{_datadir}/%{name}/test/system/tools/build/*

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

# Include check to silence rpmlint.
%check

%files
%license LICENSE vendor/modules.txt
%doc README.md
%{_bindir}/%{name}
%{_mandir}/man1/%{name}*
%dir %{_datadir}/bash-completion
%dir %{_datadir}/bash-completion/completions
%{_datadir}/bash-completion/completions/%{name}

%files tests
%license LICENSE
%{_bindir}/%{name}-imgtype
%{_bindir}/%{name}-copy
%{_bindir}/%{name}-tutorial
%{_bindir}/%{name}-inet
%{_bindir}/%{name}-dumpspec
%{_bindir}/%{name}-passwd
%{_bindir}/%{name}-crash
%{_bindir}/%{name}-wait
%{_datadir}/%{name}/test

%changelog
* Tue Jun 30 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.43.1-3
- bump golang.org/x/crypto to v0.52.0 to fix CVE-2026-39830
- Resolves: RHEL-186266

* Mon May 04 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.43.1-2
- Rebuild for CVE-2026-25679
- Resolves: RHEL-158476

* Fri Apr 10 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.43.1-1
- update to the latest content of https://github.com/containers/buildah/tree/release-1.43
  (https://github.com/containers/buildah/commit/c6eb14c)
- fixes "Buildah concurrent bearer token requests [RHEL 10.2] [0day]"
- Resolves: RHEL-164030

* Tue Apr 07 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.43.0-3
- Switch from GnuPG to Sequoia for container image signature verification
- Enable containers_image_sequoia build tag and add podman-sequoia dependency
- Resolves: RHEL-56366

* Mon Feb 23 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.43.0-2
- Rebuild for new golang to address CVE-2025-68121
- Resolves: RHEL-149240

* Mon Feb 09 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.43.0-1
- update to https://github.com/containers/buildah/releases/tag/v1.43.0
- Related: RHEL-122178

* Tue Feb 03 2026 Jindrich Novy <jnovy@redhat.com> - 2:1.41.8-1
- update to https://github.com/containers/buildah/releases/tag/v1.41.8
- Related: RHEL-122178

* Fri Sep 12 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.41.4-1
- update to https://github.com/containers/buildah/releases/tag/v1.41.4
- Related: RHEL-114411

* Fri Aug 15 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.41.3-1
- update to https://github.com/containers/buildah/releases/tag/v1.41.3
- Related: RHEL-80817

* Thu Aug 14 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.41.2-1
- update to https://github.com/containers/buildah/releases/tag/v1.41.2
- Related: RHEL-80817

* Mon Aug 11 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.41.1-1
- update to https://github.com/containers/buildah/releases/tag/v1.41.1
- Related: RHEL-80817

* Tue Jul 22 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.41.0-1
- update to https://github.com/containers/buildah/releases/tag/v1.41.0
- Related: RHEL-80817

* Tue Jun 10 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.40.1-1
- update to https://github.com/containers/buildah/releases/tag/v1.40.1
- Related: RHEL-80817

* Fri Mar 28 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.39.4-1
- update to https://github.com/containers/buildah/releases/tag/v1.39.4
- Related: RHEL-80817

* Tue Mar 18 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.39.3-1
- update to https://github.com/containers/buildah/releases/tag/v1.39.3
- Related: RHEL-80817

* Wed Mar 05 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.39.2-1
- update to https://github.com/containers/buildah/releases/tag/v1.39.2
- Related: RHEL-80817

* Thu Feb 27 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.39.1-1
- update to https://github.com/containers/buildah/releases/tag/v1.39.1
- Resolves: RHEL-81133

* Tue Feb 04 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.39.0-1
- update to https://github.com/containers/buildah/releases/tag/v1.39.0
- Related: RHEL-58990

* Tue Jan 21 2025 Jindrich Novy <jnovy@redhat.com> - 2:1.38.1-1
- update to https://github.com/containers/buildah/releases/tag/v1.38.1
- Related: RHEL-58990

* Mon Nov 25 2024 Jindrich Novy <jnovy@redhat.com> - 2:1.38.0-1
- update to https://github.com/containers/buildah/releases/tag/v1.38.0
- Related: RHEL-58990

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 2:1.37.4-2
- Bump release for October 2024 mass rebuild:
  Resolves: RHEL-64018

* Tue Oct 08 2024 Jindrich Novy <jnovy@redhat.com> - 2:1.37.4-1
- update to https://github.com/containers/buildah/releases/tag/v1.37.4
- Resolves: RHEL-61720
