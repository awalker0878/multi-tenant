#!/bin/sh
set -eu
[ -f /etc/os-release ]
[ -d /lib/modules ]
for kernel in /lib/modules/*; do
    [ -d "$kernel" ] || exit 1
    version=${kernel##*/}
    for module in mptspi vmxnet3; do modinfo -k "$version" "$module" >/dev/null; done
    if command -v dracut >/dev/null; then
        dracut --force --add-drivers 'mptspi vmxnet3' "/boot/initramfs-$version.img" "$version"
    elif command -v update-initramfs >/dev/null; then
        for module in mptspi vmxnet3; do
            grep -qxF "$module" /etc/initramfs-tools/modules || echo "$module" >> /etc/initramfs-tools/modules
        done
        update-initramfs -u -k "$version"
    else exit 1; fi
done
if grep -E '^/dev/(sd|hd|vd|xvd)[a-z]' /etc/fstab; then exit 1; fi
if [ -f /etc/udev/rules.d/70-persistent-net.rules ]; then
    mv /etc/udev/rules.d/70-persistent-net.rules /etc/udev/rules.d/70-persistent-net.rules.migration-disabled
fi
command -v vmtoolsd >/dev/null
systemctl enable vmtoolsd.service
