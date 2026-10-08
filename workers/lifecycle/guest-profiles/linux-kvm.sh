#!/bin/sh
# Runs inside libguestfs on a private copy. Requires approved packages already in
# the guest or staged in the sealed appliance; never downloads software.
set -eu
[ -f /etc/os-release ]
[ -d /lib/modules ]
for kernel in /lib/modules/*; do
    [ -d "$kernel" ] || exit 1
    version=${kernel##*/}
    for module in virtio_pci virtio_blk virtio_scsi virtio_net; do
        modinfo -k "$version" "$module" >/dev/null
    done
    if command -v dracut >/dev/null; then
        dracut --force --add-drivers 'virtio_pci virtio_blk virtio_scsi virtio_net' "/boot/initramfs-$version.img" "$version"
    elif command -v update-initramfs >/dev/null; then
        for module in virtio_pci virtio_blk virtio_scsi virtio_net; do
            grep -qxF "$module" /etc/initramfs-tools/modules || echo "$module" >> /etc/initramfs-tools/modules
        done
        update-initramfs -u -k "$version"
    else
        exit 1
    fi
done
# Device-name fstab entries need an explicit workload mapping; never guess.
if grep -E '^/dev/(sd|hd|vd|xvd)[a-z]' /etc/fstab; then exit 1; fi
if [ -f /etc/udev/rules.d/70-persistent-net.rules ]; then
    mv /etc/udev/rules.d/70-persistent-net.rules /etc/udev/rules.d/70-persistent-net.rules.migration-disabled
fi
if command -v systemctl >/dev/null; then
    for unit in vmtoolsd.service vgauthd.service; do
        if [ -e "/usr/lib/systemd/system/$unit" ] || [ -e "/lib/systemd/system/$unit" ]; then
            systemctl disable "$unit"
        fi
    done
fi
