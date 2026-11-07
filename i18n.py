# -*- coding: utf-8 -*-
"""共用的介面文字翻譯表（英文 / 繁體中文）。預設英文。

介面 chrome（標題、標籤、按鈕、訊息）走此表；指令本身的名稱/語法/參數/頁碼為手冊
資料，不在此翻譯。各儀器資料夾與啟動器各自保有一份本檔，維持專案獨立可攜。
"""
from __future__ import annotations

LANGS = ["en", "zh"]          # 預設為第一個：英文
LANG_LABELS = {"en": "English", "zh": "繁體中文"}

_STR = {
    # --- 語言選單 ---
    "language":        {"en": "Language",            "zh": "語言"},
    # --- 連線列 ---
    "conn_frame":      {"en": "Connection",          "zh": "連線"},
    "visa":            {"en": "VISA resource:",       "zh": "VISA 資源："},
    "sim":             {"en": "Simulation mode",      "zh": "模擬模式"},
    "connect":         {"en": "Connect",              "zh": "連線"},
    "disconnect":      {"en": "Disconnect",           "zh": "中斷連線"},
    "connected":       {"en": "● Connected: {idn}",   "zh": "● 已連線：{idn}"},
    "disconnected":    {"en": "● Not connected",      "zh": "● 未連線"},
    "sim_created":     {"en": "[SIM] virtual {model} created",
                        "zh": "[模擬] 建立虛擬 {model}"},
    # --- 指令區 ---
    "cmd_frame":       {"en": "Command",              "zh": "指令"},
    "group":           {"en": "Group:",               "zh": "群組："},
    "all":             {"en": "(All)",                "zh": "（全部）"},
    "command":         {"en": "Command:",             "zh": "指令："},
    "channel":         {"en": "Channel:",             "zh": "通道："},
    "seq_elem":        {"en": "Seq element n:",        "zh": "序列元素 n："},
    "index_n":         {"en": "Index n:",              "zh": "編號 n："},
    "chlist":          {"en": "Channel list (@):",     "zh": "通道清單 (@)："},
    "param":           {"en": "Parameter:",           "zh": "參數："},
    "no_param":        {"en": "(no parameter)",        "zh": "（此指令無參數）"},
    "no_param_gen":    {"en": "(no general parameter)", "zh": "（此指令無一般參數）"},
    "manual_p":        {"en": "manual p.{page}",       "zh": "手冊 p.{page}"},
    # --- 按鈕 ---
    "write":           {"en": "Write",                "zh": "Write 寫入"},
    "read":            {"en": "Read",                 "zh": "Read 讀取"},
    "clear_log":       {"en": "Clear log",            "zh": "清除紀錄"},
    # --- 輸出區 ---
    "result_frame":    {"en": "Read result",          "zh": "讀取結果"},
    "log_frame":       {"en": "Log / SCPI traffic",   "zh": "紀錄 / SCPI 流量"},
    "read_error":      {"en": "read error",           "zh": "讀取錯誤"},
    # --- 訊息框 ---
    "conn_fail":       {"en": "Connection failed",     "zh": "連線失敗"},
    "missing_title":   {"en": "Missing parameter",     "zh": "缺少參數"},
    "missing_msg":     {"en": "Please select or enter a parameter value",
                        "zh": "請先選擇或輸入參數值"},
    "write_fail":      {"en": "Write failed",          "zh": "寫入失敗"},
    "read_fail":       {"en": "Read failed",           "zh": "讀取失敗"},
    "unsupported":     {"en": "Unsupported",           "zh": "不支援"},
    "no_write":        {"en": "This command does not support write",
                        "zh": "此指令不支援寫入"},
    "no_read":         {"en": "This command does not support read",
                        "zh": "此指令不支援讀取"},
    "raw_hint":        {"en": "multi-arg: enter the full argument string",
                        "zh": "多參數：請輸入完整引數字串"},
    # --- 面板標題 ---
    "panel_title":     {"en": "{model} Control Panel (full command set)",
                        "zh": "{model} 控制面板（完整指令集）"},
    # --- 啟動器 ---
    "launcher_title":  {"en": "SCPI Instrument Control — Launcher",
                        "zh": "SCPI 儀器控制 — 共用啟動器"},
    "launcher_choose": {"en": "Choose an instrument panel to open",
                        "zh": "選擇要開啟的儀器控制面板"},
    "launcher_summary":{"en": "{n} instruments · {total} SCPI commands (source: each instrument's manual)",
                        "zh": "共 {n} 台儀器、{total} 條 SCPI 指令（資料來源：各台手冊）"},
    "open_panel":      {"en": "Open panel ▶",          "zh": "開啟面板 ▶"},
    "ready":           {"en": "Ready",                 "zh": "就緒"},
    "launched":        {"en": "Launched {name} panel (PID {pid})",
                        "zh": "已啟動 {name} 控制面板（PID {pid}）"},
    "launch_fail":     {"en": "Launch failed",         "zh": "啟動失敗"},
    "card_meta":       {"en": "commands: {count} · folder: {folder}/",
                        "zh": "指令數：{count}　·　資料夾：{folder}/"},
    "file_missing":    {"en": "File not found",        "zh": "找不到檔案"},
}

_current = "en"


def set_lang(code: str) -> None:
    global _current
    if code in LANGS:
        _current = code


def get_lang() -> str:
    return _current


def t(key: str, **kw) -> str:
    entry = _STR.get(key)
    if not entry:
        return key
    s = entry.get(_current) or entry.get("en") or key
    return s.format(**kw) if kw else s
