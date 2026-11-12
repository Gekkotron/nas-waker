#!/bin/bash
# Raspberry Pi NAS: NTFS USB disk + MiniDLNA (films) + vsftpd (nightly backups)
# + nightly auto-shutdown + the GPIO17 shutdown pin driven by the ESP32 waker.
#
# Idempotent: safe to run again after a reinstall or a config change.
# Run on the Pi, from this folder:
#   sudo FTP_PASS='choose-one' ./setup-nas.sh            # first install (FTP + Samba password)
#   sudo ./setup-nas.sh                                  # re-run, keeps the FTP password
#   sudo ./setup-nas.sh --rescan                         # also rebuild the DLNA index
#   sudo DISK_PASS='…' ./setup-nas.sh                     # Samba password of the whole-disk share
set -euo pipefail
cd "$(dirname "$0")"

# ---- settings -------------------------------------------------------------
DISK_UUID="${DISK_UUID:-A20A1C0F0A1BDF5B}"        # blkid of the NTFS partition
MNT="${MNT:-/mnt/films}"
NAS_UID=1000                                      # the login user (nas)
NAS_GID=1000
MEDIA_DIRS=("Films" "Dessin animée" "Séries" "News")   # folders on the disk shared over DLNA
DLNA_NAME="${DLNA_NAME:-NAS Films}"
FTP_USER="${FTP_USER:-ftpbackup}"
DISK_USER="${DISK_USER:-nas}"                     # SMB account for the whole-disk share
BACKUP_DIR="$MNT/Backups"
SHUTDOWN_GPIO=17                                  # ESP32 pulls it low = clean shutdown
# ---------------------------------------------------------------------------

RESCAN=0
[ "${1:-}" = "--rescan" ] && RESCAN=1
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }

echo "== packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq minidlna vsftpd ntfs-3g >/dev/null

echo "== disk: $MNT (ntfs3 kernel driver)"
mkdir -p "$MNT"
FSTAB_LINE="UUID=$DISK_UUID $MNT ntfs3 rw,uid=$NAS_UID,gid=$NAS_GID,umask=002,iocharset=utf8,windows_names,nofail,x-systemd.device-timeout=30s 0 0"
if ! grep -qxF "$FSTAB_LINE" /etc/fstab; then
  sed -i "\| $MNT |d" /etc/fstab
  echo "$FSTAB_LINE" >> /etc/fstab
  systemctl daemon-reload
  umount "$MNT" 2>/dev/null || true
fi
findmnt -n "$MNT" >/dev/null || mount "$MNT"
findmnt -n -o SOURCE,FSTYPE,OPTIONS "$MNT"
mkdir -p "$BACKUP_DIR"
# ntfs3 keeps the Linux owner of files created by Linux in on-disk attributes
# (a folder made by root stays root:755 despite uid=), so set it explicitly.
chown "$NAS_UID:$NAS_GID" "$BACKUP_DIR"
chmod 775 "$BACKUP_DIR"

echo "== FTP user $FTP_USER (jailed in $BACKUP_DIR)"
if ! id "$FTP_USER" >/dev/null 2>&1; then
  : "${FTP_PASS:?first install: set FTP_PASS}"
  useradd --no-create-home --home-dir "$BACKUP_DIR" --shell /usr/sbin/nologin --gid "$NAS_GID" "$FTP_USER"
fi
usermod --home "$BACKUP_DIR" --gid "$NAS_GID" "$FTP_USER" 2>/dev/null || true
[ -n "${FTP_PASS:-}" ] && echo "$FTP_USER:$FTP_PASS" | chpasswd
grep -qx /usr/sbin/nologin /etc/shells || echo /usr/sbin/nologin >> /etc/shells   # for pam_shells
echo "$FTP_USER" > /etc/vsftpd.userlist

echo "== vsftpd (plain FTP, LAN only)"
[ -f /etc/vsftpd.conf.orig ] || cp /etc/vsftpd.conf /etc/vsftpd.conf.orig
cat > /etc/vsftpd.conf <<EOF
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=002
# only the backup account may log in, jailed in $BACKUP_DIR
userlist_enable=YES
userlist_deny=NO
userlist_file=/etc/vsftpd.userlist
chroot_local_user=YES
allow_writeable_chroot=YES
local_root=$BACKUP_DIR
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=40100
utf8_filesystem=YES
use_localtime=YES
xferlog_enable=YES
xferlog_std_format=NO
dirmessage_enable=NO
idle_session_timeout=600
data_connection_timeout=300
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
ssl_enable=NO
EOF

echo "== minidlna \"$DLNA_NAME\""
[ -f /etc/minidlna.conf.orig ] || cp /etc/minidlna.conf /etc/minidlna.conf.orig
{
  for d in "${MEDIA_DIRS[@]}"; do echo "media_dir=V,$MNT/$d"; done
  cat <<EOF
friendly_name=$DLNA_NAME
db_dir=/var/cache/minidlna
log_dir=/var/log/minidlna
port=8200
inotify=yes
notify_interval=300
root_container=B
album_art_names=Cover.jpg/cover.jpg/AlbumArtSmall.jpg/albumartsmall.jpg/AlbumArt.jpg/albumart.jpg/Album.jpg/album.jpg/Folder.jpg/folder.jpg/Thumb.jpg/thumb.jpg/poster.jpg
EOF
} > /etc/minidlna.conf
echo "fs.inotify.max_user_watches=100000" > /etc/sysctl.d/90-minidlna.conf
sysctl -q -p /etc/sysctl.d/90-minidlna.conf

# start the services only once the disk is mounted
for s in minidlna vsftpd; do
  mkdir -p "/etc/systemd/system/$s.service.d"
  printf '[Unit]\nRequiresMountsFor=%s\n' "$MNT" > "/etc/systemd/system/$s.service.d/mount.conf"
done

echo "== Samba: \\\\$(hostname)\\Backups (FTP account) and \\\\$(hostname)\\Disque (whole disk, $DISK_USER)"
apt-get install -y -qq samba avahi-daemon >/dev/null
[ -f /etc/samba/smb.conf.orig ] || cp /etc/samba/smb.conf /etc/samba/smb.conf.orig
cat > /etc/samba/smb.conf <<EOF
[global]
   server string = NAS
   server role = standalone server
   workgroup = WORKGROUP
   server min protocol = SMB2_10
   disable netbios = yes
   smb ports = 445
   map to guest = never
   restrict anonymous = 2
   load printers = no
   printing = bsd
   printcap name = /dev/null
   disable spoolss = yes
   log file = /var/log/samba/log.%m
   max log size = 1000
   logging = file
   multicast dns register = yes

[Backups]
   path = $BACKUP_DIR
   comment = Nightly backups
   valid users = $FTP_USER
   read only = no
   browseable = yes
   # files written from the Mac look exactly like FTP uploads
   force user = $FTP_USER
   force group = nas
   create mask = 0664
   directory mask = 0775
   # keep macOS clutter off the NTFS disk
   veto files = /.DS_Store/._*/.Trashes/.Spotlight-V100/.fseventsd/
   delete veto files = yes

# the whole disk, to sort and clean up files; not for the backup account
[Disque]
   path = $MNT
   comment = Whole disk
   valid users = $DISK_USER
   read only = no
   browseable = yes
   force user = $DISK_USER
   force group = nas
   create mask = 0664
   directory mask = 0775
   veto files = /.DS_Store/._*/.Trashes/.Spotlight-V100/.fseventsd/
   delete veto files = yes
EOF
testparm -s /etc/samba/smb.conf >/dev/null 2>&1 || { echo "smb.conf invalid" >&2; exit 1; }
if [ -n "${SMB_PASS:-${FTP_PASS:-}}" ]; then
  P="${SMB_PASS:-$FTP_PASS}"
  printf '%s\n%s\n' "$P" "$P" | smbpasswd -s -a "$FTP_USER" >/dev/null
elif ! pdbedit -L 2>/dev/null | grep -q "^$FTP_USER:"; then
  echo "   WARNING: no Samba password for $FTP_USER yet; re-run with SMB_PASS=… (or FTP_PASS=…)"
fi
if [ -n "${DISK_PASS:-}" ]; then
  printf '%s\n%s\n' "$DISK_PASS" "$DISK_PASS" | smbpasswd -s -a "$DISK_USER" >/dev/null
elif ! pdbedit -L 2>/dev/null | grep -q "^$DISK_USER:"; then
  echo "   WARNING: no Samba password for $DISK_USER yet; re-run with DISK_PASS=…"
fi
mkdir -p /etc/systemd/system/smbd.service.d
printf '[Unit]\nRequiresMountsFor=%s\n' "$MNT" > /etc/systemd/system/smbd.service.d/mount.conf

echo "== remove the old nightly auto-shutdown (the Nidoo flow now shuts the NAS down)"
if [ -e /etc/systemd/system/nightly-autoshutdown.timer ]; then
  systemctl disable -q --now nightly-autoshutdown.timer 2>/dev/null || true
  rm -f /etc/systemd/system/nightly-autoshutdown.service /etc/systemd/system/nightly-autoshutdown.timer \
        /usr/local/sbin/nightly-autoshutdown /etc/default/nightly-autoshutdown
fi

echo "== GPIO$SHUTDOWN_GPIO shutdown pin (ESP32 waker)"
CFG=/boot/firmware/config.txt
OVERLAY="dtoverlay=gpio-shutdown,gpio_pin=$SHUTDOWN_GPIO,active_low=1,gpio_pull=up"
[ -f "$CFG.orig" ] || cp "$CFG" "$CFG.orig"
if ! grep -qxF "$OVERLAY" "$CFG"; then
  printf '\n# NAS waker (ESP32): pulse GPIO%s low = clean shutdown; GPIO3 (pin 5) low = wake\n%s\n' \
    "$SHUTDOWN_GPIO" "$OVERLAY" >> "$CFG"
  echo "   added to $CFG (active after next boot)"
fi
grep -q '^WAKE_ON_GPIO=1' <(rpi-eeprom-config 2>/dev/null) \
  || echo "   WARNING: bootloader WAKE_ON_GPIO is not 1; the ESP32 cannot wake the Pi (sudo rpi-eeprom-config --edit)"

echo "== services"
systemctl daemon-reload
systemctl enable -q minidlna vsftpd smbd avahi-daemon
if [ "$RESCAN" = 1 ]; then
  systemctl stop minidlna
  rm -f /var/cache/minidlna/files.db
fi
systemctl restart vsftpd minidlna smbd
sleep 2
systemctl is-active minidlna vsftpd smbd
echo "== done"
