# Remove Junk Files

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.6%2B-blue) ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20WSL-lightgrey)

A fast, cross-platform command-line tool to clean up unwanted system files, metadata, and alternate data streams. Logs deletions to CSV files.  
100% made by ChatGPT.

## Features

- Removes common junk files: `.DS_Store`, `Thumbs.db`, `.AppleDouble`, `*.swp`, `*~`, etc.
- Deletes `:Zone.Identifier` files (Windows ADS)
- Clears extended attributes like `user.Zone.Identifier`
- Works on Linux, macOS, and WSL
- Multithreaded with progress bar
- Supports CSV output with splitting/grouping

## Installation

```bash
git clone https://github.com/NadjaSenpai/remove-junk-files.git
cd remove-junk-files
chmod +x remove_junk_files.py
```

## Usage

```bash
./remove_junk_files.py -R -l logs.csv -d logs/
```

Use `--help` to see full options.

## License

MIT License.
