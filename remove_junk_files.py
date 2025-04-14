#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
import fnmatch
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import signal
from datetime import datetime
import platform
from collections import defaultdict

JUNK_FILES = [
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
    '.AppleDouble', '.LSOverride', '.Trash-*',
    '.fseventsd', '.Spotlight-V100', '.DocumentRevisions-V100',
    '.TemporaryItems', 'lost+found', '.directory'
]
JUNK_PATTERNS = [
    '._*', '*.swp', '*.swo', '*.tmp', '*.bak', '*~', '.nfs*'
]

interrupted = False
MAX_ENTRIES_PER_CSV = 1000
DEFAULT_MAX_CSV_SIZE = 1024 * 1024

def remove_xattr_mac(file_path, attr_name):
    try:
        result = subprocess.run(['xattr', '-p', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            subprocess.run(['xattr', '-d', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False

def remove_attr_linux(file_path, attr_name):
    try:
        result = subprocess.run(['getfattr', '--only-values', '-n', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            subprocess.run(['setfattr', '-x', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False

IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def handle_interrupt(signum, frame):
    global interrupted
    interrupted = True
    print("\n[INFO] Interrupted. Output the results of the process so far.\n")

signal.signal(signal.SIGINT, handle_interrupt)

def remove_attr(file_path, attr_name, dry_run):
    if not os.path.isfile(file_path):
        return False
    if dry_run:
        return True
    if IS_MAC:
        return remove_xattr_mac(file_path, attr_name)
    elif IS_LINUX:
        return remove_attr_linux(file_path, attr_name)
    return False

def remove_file(file_path, dry_run):
    if not os.path.isfile(file_path):
        return False
    try:
        if not dry_run:
            os.remove(file_path)
        return True
    except Exception:
        return False

def process_file(file_path, args):
    deleted = {'file': False, 'attrs': [], 'junk': False}
    basename = os.path.basename(file_path)

    if basename in JUNK_FILES or any(fnmatch.fnmatch(basename, pattern) for pattern in JUNK_PATTERNS):
        if remove_file(file_path, args.dry_run):
            deleted['junk'] = True

    if ":Zone.Identifier" in file_path:
        if remove_file(file_path, args.dry_run):
            deleted['file'] = True

    for attr in ["user.Zone.Identifier"] + args.attr:
        if remove_attr(file_path, attr, args.dry_run):
            deleted['attrs'].append(attr)

    return (file_path, deleted)

def collect_files(path, exclude_git, recursive):
    files = []
    if recursive:
        for root, dirs, filenames in os.walk(path):
            if exclude_git and '.git' in dirs:
                dirs.remove('.git')
            for name in filenames:
                files.append(os.path.join(root, name))
    else:
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path):
                files.append(full_path)
    return files

def main():
    parser = argparse.ArgumentParser(description="Remove Junk Files")
    parser.add_argument('--path', '-p', default='.', help='Target directory')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run mode')
    parser.add_argument('--attr', '-a', action='append', default=[], help='Extended attributes to delete')
    parser.add_argument('--exclude-git', '-g', action='store_true', help='Exclude .git directories')
    parser.add_argument('--logfile', '-l')
    parser.add_argument('--csv-dir', '-d')
    parser.add_argument('--max-csv-size', type=int, default=DEFAULT_MAX_CSV_SIZE)
    parser.add_argument('--grouped-log', action='store_true')
    parser.add_argument('--summary', '-s', action='store_true')
    parser.add_argument('--recursive', '-R', action='store_true')
    parser.add_argument('--no-color', '-C', action='store_true')
    parser.add_argument('--csv-only', '-c', action='store_true')
    parser.add_argument('--max-workers', '-j', type=int)
    args = parser.parse_args()

    target_files = collect_files(args.path, args.exclude_git, args.recursive)
    results = []
    summary = []
    max_workers = args.max_workers if args.max_workers else os.cpu_count()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            for file_path, deleted in tqdm(executor.map(lambda f: process_file(f, args), target_files),
                                           total=len(target_files), desc="Processing", unit="file", disable=args.csv_only):
                if interrupted:
                    break
                results.append((file_path, deleted))
                if args.summary and (deleted['file'] or deleted['junk'] or deleted['attrs']):
                    summary.append(file_path)
        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user. Outputting partial results...\n")

    file_count = sum(1 for _, d in results if d['file'])
    attr_count = sum(len(d['attrs']) for _, d in results)
    junk_count = sum(1 for _, d in results if d['junk'])

    if not args.csv_only:
        print(f"[INFO] Files deleted: {file_count}")
        print(f"[INFO] Attributes removed: {attr_count}")
        print(f"[INFO] Junk files deleted: {junk_count}")
        if args.summary and summary:
            print("\n[SUMMARY] Deleted items:")
            for path in summary:
                print(path)

if __name__ == "__main__":
    main()
