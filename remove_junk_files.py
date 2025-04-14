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

# 対象の不要ファイル
JUNK_FILES = [
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
    '.AppleDouble', '.LSOverride', '.Trash-*',
    '.fseventsd', '.Spotlight-V100', '.DocumentRevisions-V100',
    '.TemporaryItems', 'lost+found', '.directory'
]
JUNK_PATTERNS = [
    '._*', '*.swp', '*.swo', '*.tmp', '*.bak', '*~', '.nfs*'
]

# 中断フラグ
interrupted = False

MAX_ENTRIES_PER_CSV = 1000  # CSV分割の件数しきい値（将来の拡張用）
DEFAULT_MAX_CSV_SIZE = 1024 * 1024  # 1MB

# macOS: 拡張属性削除
def remove_xattr_mac(file_path, attr_name):
    try:
        result = subprocess.run(['xattr', '-p', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            subprocess.run(['xattr', '-d', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False

# Linux: 拡張属性削除
def remove_attr_linux(file_path, attr_name):
    try:
        result = subprocess.run(['getfattr', '--only-values', '-n', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            subprocess.run(['setfattr', '-x', attr_name, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False

# OS判定
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Ctrl+C対応
def handle_interrupt(signum, frame):
    global interrupted
    interrupted = True
    print("\n[INFO] 中断されました。これまでの処理結果を出力します。\n")

signal.signal(signal.SIGINT, handle_interrupt)

# 拡張属性削除（OS別）
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

# ファイル削除
def remove_file(file_path, dry_run):
    if not os.path.isfile(file_path):
        return False
    try:
        if not dry_run:
            os.remove(file_path)
        return True
    except Exception:
        return False

# 単一ファイル処理
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

# 再帰的にファイル収集
# ...（以下変更なし）


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
    args = parser.parse_args()

    target_files = collect_files(args.path, args.exclude_git, recursive=True)
    with ThreadPoolExecutor() as executor:
        for file_path, deleted in tqdm(executor.map(lambda f: process_file(f, args), target_files), total=len(target_files)):
            pass

if __name__ == "__main__":
    main()
