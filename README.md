# Bridgiron

A Windows tool that minimizes copy-paste effort between ChatGPT and Claude Code.

[日本語版 README](README_ja.md)

## Overview

Bridgiron is a Windows GUI tool that streamlines the workflow when using ChatGPT (for design) and Claude Code (for implementation) together. It eliminates tedious manual copy-paste operations between the two AI assistants.

## Features

- **Prompt Extraction Bookmarklet**: Extract prompts from ChatGPT responses with one click (SOP/EOP marker detection)
- **CC Report Copy**: Extract the latest report from Claude Code session logs (Alt+C shortcut)
- **Copy History**: Stores up to 50 entries each for GPT→CC and CC→GPT, with Win+V style UI
- **Mini Window**: Auto-switches to a compact window when CLI is active, stays out of your way

## System Requirements

- Windows 10 / 11
- Web browser (for ChatGPT bookmarklet)

## Installation

1. Download the latest `Bridgiron_Setup_vX.XX.exe` from [Releases](../../releases)
2. Run the installer
3. Set your project path (Claude Code working directory) during installation

## Usage

1. Launch Bridgiron
2. Click "Copy Code" to generate a bookmarklet and add it to your browser bookmarks
3. On ChatGPT, click the bookmarklet → The prompt is copied
4. Paste into Claude Code and run
5. After completion, click "Copy CC Report" or press Alt+C → The report is copied
6. Paste into ChatGPT

For detailed instructions, see `Readme.html` after installation.

## License

MIT License
