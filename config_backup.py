#!/usr/bin/env python3
"""
Network Config Backup & Change Audit Tool

Connects to network devices over SSH (via Netmiko), pulls the running
configuration, saves a timestamped backup, and diffs it against the previous
backup to flag any changes.

Real usage (against actual devices):
    python config_backup.py --inventory devices.yaml

Portfolio / demo mode (no real devices needed):
    python config_backup.py --demo

Portfolio piece for network automation / Python scripting services.
"""

import argparse
import difflib
import os
import sys
import yaml
from datetime import datetime

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def load_inventory(path: str) -> list[dict]:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("devices", [])


def fetch_running_config(device: dict) -> str:
    """Connect to a real device and pull its running-config."""
    if not NETMIKO_AVAILABLE:
        raise RuntimeError("netmiko is not installed. Run: pip install netmiko")

    connection = ConnectHandler(
        device_type=device.get("device_type", "cisco_ios"),
        host=device["host"],
        username=device["username"],
        password=device["password"],
        secret=device.get("secret", ""),
    )
    if device.get("secret"):
        connection.enable()
    output = connection.send_command("show running-config")
    connection.disconnect()
    return output


def fetch_demo_config(device_name: str, variant: int) -> str:
    """Simulated config output, used for demo mode so this tool can be run/reviewed
    without needing access to real network hardware."""
    base = f"""!
hostname {device_name}
!
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 10.0.1.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.0.0.0 0.0.0.255 area 0
 network 10.0.1.0 0.0.0.255 area 0
!
line vty 0 4
 login local
 transport input ssh
!
end
"""
    if variant == 2:
        # simulate a config change: an ACL added, an interface description changed
        base = base.replace(
            "interface GigabitEthernet0/1\n ip address 10.0.1.1 255.255.255.0",
            "interface GigabitEthernet0/1\n description UPLINK-TO-CORE\n ip address 10.0.1.1 255.255.255.0",
        )
        base += "!\naccess-list 101 deny ip any host 10.0.0.99\n"
    return base


def backup_filename(device_name: str, timestamp: str) -> str:
    return os.path.join(BACKUP_DIR, f"{device_name}_{timestamp}.cfg")


def latest_previous_backup(device_name: str, exclude_file: str) -> str | None:
    if not os.path.isdir(BACKUP_DIR):
        return None
    candidates = [
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith(f"{device_name}_") and f.endswith(".cfg") and f != os.path.basename(exclude_file)
    ]
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return os.path.join(BACKUP_DIR, candidates[0])


def diff_configs(old_path: str, new_content: str) -> str:
    with open(old_path, "r") as f:
        old_lines = f.readlines()
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current")
    return "".join(diff)


def run_backup_for_device(device_name: str, config_text: str) -> None:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    new_path = backup_filename(device_name, timestamp)

    with open(new_path, "w") as f:
        f.write(config_text)
    print(f"[{device_name}] Backup saved: {new_path}")

    previous = latest_previous_backup(device_name, new_path)
    if previous is None:
        print(f"[{device_name}] No previous backup to compare against (first run).")
        return

    diff = diff_configs(previous, config_text)
    if diff.strip():
        print(f"[{device_name}] CHANGE DETECTED since {os.path.basename(previous)}:")
        print(diff)
    else:
        print(f"[{device_name}] No changes since last backup.")


def run_real(inventory_path: str) -> None:
    devices = load_inventory(inventory_path)
    if not devices:
        print("No devices found in inventory file.", file=sys.stderr)
        sys.exit(1)

    for device in devices:
        name = device.get("name", device["host"])
        try:
            config_text = fetch_running_config(device)
        except NetmikoAuthenticationException:
            print(f"[{name}] Authentication failed, skipping.", file=sys.stderr)
            continue
        except NetmikoTimeoutException:
            print(f"[{name}] Connection timed out, skipping.", file=sys.stderr)
            continue
        run_backup_for_device(name, config_text)


def run_demo() -> None:
    print("Running in DEMO mode (simulated devices, no real hardware required)\n")
    demo_devices = ["core-switch-01", "edge-router-01"]

    print("--- First run (initial backup) ---")
    for name in demo_devices:
        run_backup_for_device(name, fetch_demo_config(name, variant=1))

    print("\n--- Second run (simulated config change on edge-router-01) ---")
    run_backup_for_device("core-switch-01", fetch_demo_config("core-switch-01", variant=1))
    run_backup_for_device("edge-router-01", fetch_demo_config("edge-router-01", variant=2))


def main():
    parser = argparse.ArgumentParser(description="Network Config Backup & Change Audit Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inventory", help="Path to YAML inventory file of real devices")
    group.add_argument("--demo", action="store_true", help="Run against simulated demo devices")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        run_real(args.inventory)


if __name__ == "__main__":
    main()
