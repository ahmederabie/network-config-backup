# Network Config Backup & Change Audit Tool

A Python tool that connects to network devices over SSH (via [Netmiko](https://github.com/ktbyers/netmiko)), pulls the running configuration, saves a timestamped backup, and diffs it against the previous backup to flag any changes.

Includes a `--demo` mode that simulates two devices so the tool can be run and reviewed without needing real hardware.

## Demo (no hardware required)

```bash
pip install pyyaml
python config_backup.py --demo
```

Example output:

```
Running in DEMO mode (simulated devices, no real hardware required)

--- First run (initial backup) ---
[core-switch-01] Backup saved: backups/core-switch-01_20260914_221809.cfg
[core-switch-01] No previous backup to compare against (first run).
[edge-router-01] Backup saved: backups/edge-router-01_20260914_221809.cfg
[edge-router-01] No previous backup to compare against (first run).

--- Second run (simulated config change on edge-router-01) ---
[core-switch-01] Backup saved: backups/core-switch-01_20260914_221815.cfg
[core-switch-01] No changes since last backup.
[edge-router-01] Backup saved: backups/edge-router-01_20260914_221815.cfg
[edge-router-01] CHANGE DETECTED since edge-router-01_20260914_221809.cfg:
--- previous
+++ current
@@ -6,6 +6,7 @@
 no shutdown
 !
 interface GigabitEthernet0/1
+ description UPLINK-TO-CORE
 ip address 10.0.1.1 255.255.255.0
 no shutdown
```

## Real usage (against actual devices)

```bash
pip install netmiko pyyaml
cp devices.example.yaml devices.yaml   # fill in your real device details
python config_backup.py --inventory devices.yaml
```

`devices.yaml` is a plain YAML list of devices (host, credentials, device type). It's gitignored on purpose — never commit real device credentials.

## What it does

- Connects to each device in the inventory over SSH and pulls `show running-config`.
- Saves a timestamped backup file per device.
- Diffs the new backup against the most recent previous one for that device and prints a unified diff if anything changed, or confirms "no changes" if not.
- Skips devices that fail to authenticate or time out, rather than crashing the whole run.

## Requirements

Python 3.9+, `netmiko`, `pyyaml`. The demo mode only needs `pyyaml`.

## About

Built as a portfolio piece for network automation and Python scripting work. I'm CCNA-certified and write tools like this for freelance network engineering clients — see also [vlsm-subnet-calculator](https://github.com/ahmederabie/vlsm-subnet-calculator) for a subnet planning tool.
