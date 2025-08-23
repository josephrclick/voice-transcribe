#!/usr/bin/env python3

import os
import sys

DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "sudo rm",
    ":(){:|:&};:",  # Fork bomb
    "dd if=/dev/zero",
    "chmod -R 777",
    "> /dev/sda",  # Disk wipe
    "mkfs.",  # Format filesystem
    "DROP DATABASE",  # SQL destruction
    "DELETE FROM",  # Bulk deletions without WHERE
]

DANGEROUS_PATHS = [
    "/etc/",
    "/boot/",
    "/sys/",
    "/proc/",
    "~/.ssh/",
    "~/.aws/",
    ".git/objects/",
]


def check_safety():
    # Get command from environment
    command = os.environ.get("TOOL_COMMAND", "")
    tool_name = os.environ.get("TOOL_NAME", "")
    file_path = os.environ.get("TOOL_FILE_PATH", "")

    # Check dangerous command patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in command.lower():
            print(f"🛑 BLOCKED: Dangerous command pattern detected: {pattern}")
            print(f"Command attempted: {command}")
            sys.exit(1)

    # Check for mass deletions
    if "rm" in command and command.count("*") > 2:
        print("⚠️ BLOCKED: Multiple wildcards in deletion command")
        sys.exit(1)

    # Check protected paths
    if file_path:
        for protected in DANGEROUS_PATHS:
            if protected in file_path:
                print(f"🛑 BLOCKED: Attempting to modify protected path: {protected}")
                sys.exit(1)

    # Check for force flags without confirmation
    if any(flag in command for flag in ["-f", "--force", "-y", "--yes"]) and any(cmd in command for cmd in ["rm", "del", "format", "mkfs"]):
            print("⚠️ BLOCKED: Force flag used with destructive command")
            sys.exit(1)

    # Log allowed commands for audit
    if os.environ.get("LOG_COMMANDS", "false").lower() == "true":
        with open(".claude/command_log.txt", "a") as f:
            f.write(f"{tool_name}: {command}\n")


if __name__ == "__main__":
    check_safety()
