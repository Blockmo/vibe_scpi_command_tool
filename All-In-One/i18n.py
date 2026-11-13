# -*- coding: utf-8 -*-
"""All-In-One 整合程式的介面文字翻譯表（英文 / 繁體中文）。預設英文。

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
    # --- 掃描 VISA 資源 ---
    "scan":            {"en": "Scan",                  "zh": "掃描"},
    "scanning":        {"en": "Scanning VISA resources…", "zh": "正在掃描 VISA 資源…"},
    "scan_fail":       {"en": "Scan failed",           "zh": "掃描失敗"},
    # --- 指令搜尋 ---
    "search":          {"en": "Search:",               "zh": "搜尋："},
    "search_count":    {"en": "{n} match(es)",         "zh": "符合 {n} 條"},
    "search_none":     {"en": "no match",              "zh": "無符合指令"},
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
    # --- All-In-One 整合程式 ---
    "aio_title":       {"en": "SCPI Instrument Control — All-In-One",
                        "zh": "SCPI 儀器控制 — 整合程式"},
    "category":        {"en": "Category:",             "zh": "分類："},
    "instrument":      {"en": "Instrument:",           "zh": "儀器："},
    "cat_psu":         {"en": "Power Supply",          "zh": "電源供應器"},
    "cat_daq":         {"en": "DAQ",                   "zh": "資料擷取 DAQ"},
    "cat_eload":       {"en": "E-Load",                "zh": "電子負載"},
    "cat_scope":       {"en": "Oscilloscope",          "zh": "示波器"},
    "cat_fgen":        {"en": "Function Generator",    "zh": "函數信號產生器"},
    "cat_meter":       {"en": "Meter / SMU",           "zh": "電錶 / 電源量測單元"},
    "aio_info":        {"en": "{kind}  ·  {count} commands  ·  source: {folder}/",
                        "zh": "{kind}　·　{count} 條指令　·　來源：{folder}/"},
    "load_fail":       {"en": "Failed to load instrument module",
                        "zh": "載入儀器模組失敗"},
    "copy_cmd":        {"en": "Copy Command",          "zh": "複製指令"},
    "copied":          {"en": "Copied: {cmd}",         "zh": "已複製：{cmd}"},
    "copy_fail":       {"en": "Copy failed",           "zh": "複製失敗"},
    "conn_count":      {"en": "Connected instruments: {n}",
                        "zh": "已連線儀器：{n} 台"},
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
