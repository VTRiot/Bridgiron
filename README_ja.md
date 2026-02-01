# Bridgiron
長時間にわたる 仕様設計 → 実装 のループを、ChatGPTとClaude Codeの間でトークン制限を意識しながら回している開発者向けに設計されたツールです。
ChatGPT と Claude Code 間のコピペ作業を最小労力化するツール

[English README](README.md)

## 概要

Bridgiron は、ChatGPT（設計担当）と Claude Code（実装担当）を連携させて開発を行う際の、手動コピペ作業を効率化するWindows向けGUIツールです。

## 機能

- **プロンプト抽出ブックマークレット**: ChatGPT の応答から SOP/EOP マーカー間のプロンプトを1クリックで抽出・コピー
- **CC報告コピー**: Claude Code のセッションログから最新の報告を抽出してコピー（Alt+C対応）
- **コピー履歴**: GPT→CC / CC→GPT 各50件を保存、Win+V 風UIで選択
- **ミニウィンドウ**: CLI操作時に自動で小窓化、邪魔にならない常駐表示

## 動作環境

- Windows 10 / 11
- ブラウザ（ChatGPT用ブックマークレット）

## インストール

1. [Releases](../../releases) から最新の `Bridgiron_Setup_vX.XX.exe` をダウンロード
2. インストーラーを実行
3. インストール時にプロジェクトパス（Claude Code の作業フォルダ）を設定

## 使い方

1. Bridgiron を起動
2. 「コードをコピー」ボタンでブックマークレットを生成し、ブラウザのブックマークに登録
3. ChatGPT の画面でブックマークレットをクリック → プロンプトがコピーされる
4. Claude Code に貼り付けて実行
5. 完了後、「CC報告をコピー」または Alt+C → 報告がコピーされる
6. ChatGPT に貼り付け

詳しい使い方は、インストール後に `Readme.html` を参照してください。

## ライセンス

MIT License
