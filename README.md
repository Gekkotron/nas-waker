# nas-waker

A Raspberry Pi 4 home NAS that is only on when it is needed, woken by an ESP32.

- **Films over DLNA**: MiniDLNA shares an NTFS USB disk (TVs, Freebox, VLC).
- **Nightly backups over FTP**: vsftpd, one jailed account, plain FTP on the LAN.
- **Power schedule**: the ESP32 wakes the Pi at 23:00. The Pi powers itself off 30 minutes after that nightly boot, and waits first while an FTP upload or a DLNA stream is still running.
- **Nidoo integration**: the ESP32 publishes Home Assistant MQTT discovery, so [Nidoo](https://github.com/Gekkotron/Nidoo) shows *NAS online*, *Wake NAS* and *Shut down NAS* with no Nidoo change.

```
           Wi-Fi / MQTT (Nidoo)
                  │
   ┌──────────────┴───────┐   GPIO25 ──► pin 5  (GPIO3)   wake from halt
   │  ESP32 DevKit        │   GPIO26 ──► pin 11 (GPIO17)  clean shutdown
   │  ESPHome 2026.10.2   │   VIN    ◄── pin 2  (5V)      stays live while the Pi is halted
   └──────────────────────┘   GND    ─── pin 6  (GND)
                                         Raspberry Pi 4 ── USB ── NTFS disk
```

## Layout

| Path | What |
|---|---|
| `esp32/nas-waker.yaml` | ESPHome firmware for the waker |
| `esp32/secrets.example.yaml` | Template for `esp32/secrets.yaml` (git-ignored) |
| `pi/setup-nas.sh` | Idempotent installer for everything on the Pi |
| `pi/nightly-autoshutdown` | Powers the Pi off after the nightly window |
| `pi/systemd/` | Its service and timer (30 min after boot) |

## Wiring

Both boards use 3.3 V logic, so the wires go straight across with no extra parts. The ESP32 outputs are open-drain: they only ever pull a Pi pin to ground and the Pi's pull-ups do the rest.

| Raspberry Pi 4 | ESP32 DevKit | Role |
|---|---|---|
| pin 2 (5V) | VIN | powers the ESP32 |
| pin 6 (GND) | GND | common ground |
| pin 5 (GPIO3) | D25 | pulse low: wake from halt |
| pin 11 (GPIO17) | D26 | pulse low: clean shutdown |

Pin 1 is the corner pin nearest the SD card; pin 2 is beside it on the outer edge.

> [!WARNING]
> Disconnect the 5V wire while the ESP32 is plugged into a computer over USB, or USB power feeds into the Pi.
> Also power the ESP32 before connecting D26: an unpowered ESP32 drags its pins to ground, which the Pi reads as a shutdown request.

## Pi setup

Raspberry Pi OS (Debian 13 trixie), user `nas` (uid 1000), the bootloader at its default `WAKE_ON_GPIO=1`.

Edit the settings block at the top of `pi/setup-nas.sh` (the disk UUID from `blkid`, and the folders to share), then:

```sh
scp -r pi nas@192.168.1.131:
ssh nas@192.168.1.131
sudo FTP_PASS='choose-a-password' ./pi/setup-nas.sh   # first install
sudo ./pi/setup-nas.sh                               # later runs keep the FTP password
sudo ./pi/setup-nas.sh --rescan                      # also rebuild the DLNA index
```

The script:

- mounts the disk at `/mnt/films` with the in-kernel `ntfs3` driver (`nofail`, so the Pi still boots without it);
- installs MiniDLNA ("NAS Films", status page on port 8200) and vsftpd (account `ftpbackup`, jailed in `/mnt/films/Backups`, passive ports 40000–40100);
- installs the nightly auto-shutdown;
- adds `dtoverlay=gpio-shutdown,gpio_pin=17` to `/boot/firmware/config.txt`.

It keeps `.orig` copies of the config files it replaces.

### Nightly auto-shutdown

`nightly-autoshutdown.timer` runs the script 30 minutes after every boot. The script:

1. Waits until the clock is set from the network (a Pi 4 has no RTC).
2. Stays on if the Pi booted outside the nightly window (22:45–23:30). A Pi started by hand to watch a film is never switched off.
3. Otherwise powers off, re-checking every 5 minutes while connections are open on FTP (21, 40000–40100) or DLNA (8200), with a hard limit of 3 hours.

Override the settings in `/etc/default/nightly-autoshutdown`. To test without powering off:

```sh
sudo nightly-autoshutdown --dry-run --window 00:00-23:59
journalctl -t nightly-autoshutdown
```

## ESP32 firmware

```sh
cd esp32
cp secrets.example.yaml secrets.yaml      # then fill it in
uvx esphome==2026.10.2 run nas-waker.yaml --device /dev/cu.usbserial-0001   # first flash, over USB
uvx esphome==2026.10.2 run nas-waker.yaml --device nas-waker.local          # every later update, over Wi-Fi
uvx esphome==2026.10.2 logs nas-waker.yaml --device nas-waker.local         # logs only
uvx esphome==2026.10.2 dashboard .                                          # web UI on http://localhost:6052
```

Keep `ota_password` in `secrets.yaml`: without it the next update has to go over USB. Keep ESPHome at the same pinned version as the Nidoo satellites.

What the firmware does:

- **23:00**: pulses the wake line; at **23:05** it pulses again if the NAS is still offline.
- **NAS online**: polls `http://192.168.1.131:8200/` every 30 s (offline after 90 s without an answer).
- **Wake NAS / Shut down NAS** buttons pulse the wake / shutdown lines.

### In Nidoo

The ESP32 publishes discovery under `homeassistant/` on the broker Nidoo reads, so these appear under the device **NAS waker**:

| Entity | Kind |
|---|---|
| `ESPbinary_sensornas_online` | binary_sensor (connectivity) |
| `ESPbuttonwake_nas` | button |
| `ESPbuttonshut_down_nas` | button |
| `ESPsensorwifi_signal` | sensor (dBm) |

## Notes

- **Shut down before unplugging the disk.** An NTFS volume removed while mounted comes back read-only; repair it with `sudo ntfsfix /dev/sda1` or `chkdsk` on Windows.
- **ntfs3 stores Linux owners on the disk.** A folder created by root stays `root:755` despite the `uid=` mount option, so `setup-nas.sh` runs `chown` on `Backups/`.
- **ESPHome 2026.10.2**: a template binary sensor needs `trigger_on_initial_state: true`, or its first state is never sent to MQTT.
- **Plain FTP is unencrypted.** Never forward port 21 on the router.
