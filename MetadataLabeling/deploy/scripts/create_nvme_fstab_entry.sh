#!/usr/bin/env bash
set -euo pipefail

DEVICE="${1:-/dev/nvme0n1p1}"
MOUNT_POINT="${2:-/opt/ssd}"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo." >&2
  exit 1
fi
if [[ ! -b "${DEVICE}" ]]; then
  echo "Block device not found: ${DEVICE}" >&2
  exit 1
fi
UUID="$(blkid -s UUID -o value "${DEVICE}")"
FSTYPE="$(blkid -s TYPE -o value "${DEVICE}")"
if [[ -z "${UUID}" || -z "${FSTYPE}" ]]; then
  echo "The partition must already be formatted. This script will not format it." >&2
  exit 1
fi
mkdir -p "${MOUNT_POINT}"
LINE="UUID=${UUID} ${MOUNT_POINT} ${FSTYPE} defaults,noatime,nofail,x-systemd.device-timeout=10 0 2"
if ! grep -q "UUID=${UUID}" /etc/fstab; then
  printf '%s\n' "${LINE}" >> /etc/fstab
fi
mount "${MOUNT_POINT}"
echo "Mounted ${DEVICE} at ${MOUNT_POINT}."
