# -*- coding: utf-8 -*-
"""
SCPI 儀器控制 — 共用啟動器（支援英文 / 繁體中文，預設英文）
=============================================================

一個視窗整合四台儀器的控制面板。點選任一台即以子行程啟動該台的 GUI
（各台專案自成資料夾、獨立執行，互不干擾）。右上角可切換英文/繁中介面。

執行：
    python launcher.py
"""
from __future__ import annotations

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

import i18n
from i18n import t

HERE = os.path.dirname(os.path.abspath(__file__))

INSTRUMENTS = [
    {
        "name": "AFG31000", "folder": "AFG31000", "entry": "ui.py", "count": 187,
        "kind": {"en": "Arbitrary Function Generator (Tektronix)",
                 "zh": "任意函數信號產生器 (Tektronix)"},
        "note": {"en": "SOURce{1|2} dual channel; waveform/modulation/sweep/burst/sequence",
                 "zh": "SOURce{1|2} 雙通道；波形/調變/掃頻/突波/序列"},
    },
    {
        "name": "DAQ973A", "folder": "DAQ973A", "entry": "ui.py", "count": 421,
        "kind": {"en": "Data Acquisition / Switch System (Keysight)",
                 "zh": "資料擷取 / 開關量測系統 (Keysight)"},
        "note": {"en": "(@channel-list) model; incl. DAQM909A digitizer module",
                 "zh": "(@通道清單) 模型；含 DAQM909A 數位化模組"},
    },
    {
        "name": "34970 / 34972A", "folder": "34970", "entry": "ui.py", "count": 179,
        "kind": {"en": "Data Acquisition / Switch Unit (Keysight/Agilent)",
                 "zh": "資料擷取 / 開關單元 (Keysight/Agilent)"},
        "note": {"en": "(@channel-list) model",
                 "zh": "(@通道清單) 模型"},
    },
    {
        "name": "Chroma 63600", "folder": "Chroma_63600", "entry": "ui.py", "count": 212,
        "kind": {"en": "DC Electronic Load (Chroma)",
                 "zh": "直流電子負載 (Chroma)"},
        "note": {"en": "CHANnel <n> active-channel model; CC/CR/CV/CP…",
                 "zh": "CHANnel <n> 作用中通道模型；CC/CR/CV/CP…"},
    },
    {
        "name": "E36300", "folder": "E36300", "entry": "ui.py", "count": 101,
        "kind": {"en": "Triple-output DC Power Supply (Keysight)",
                 "zh": "三輸出直流電源供應器 (Keysight)"},
        "note": {"en": "(@1:3) channel-list model; output/list/data-logger",
                 "zh": "(@1:3) 通道清單模型；輸出/LIST 序列/資料記錄器"},
    },
    {
        "name": "2231A-30-3", "folder": "2231A-30-3", "entry": "ui.py", "count": 76,
        "kind": {"en": "Triple-channel DC Power Supply (Keithley)",
                 "zh": "三通道直流電源供應器 (Keithley)"},
        "note": {"en": "INSTrument:SELect CH1/CH2/CH3 active-channel model",
                 "zh": "INSTrument:SELect CH1/CH2/CH3 作用中通道模型"},
    },
    {
        "name": "E3633A", "folder": "E3633A", "entry": "ui.py", "count": 59,
        "kind": {"en": "Single-output DC Power Supply (Agilent/Keysight)",
                 "zh": "單輸出直流電源供應器 (Agilent/Keysight)"},
        "note": {"en": "single output, no channel; VOLTage:RANGe P8V/P20V range switching",
                 "zh": "單輸出、無通道；VOLTage:RANGe P8V/P20V 檔位切換"},
    },
]


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("580x560")
        self.minsize(540, 520)
        self._procs = []

        top = ttk.Frame(self)
        top.pack(fill="x", padx=16, pady=(12, 0))
        self.lang_label = ttk.Label(top)
        self.lang_label.pack(side="left")
        self.lang_var = tk.StringVar(value=i18n.LANG_LABELS[i18n.get_lang()])
        self.lang_combo = ttk.Combobox(top, textvariable=self.lang_var, state="readonly",
                                       width=10, values=[i18n.LANG_LABELS[c] for c in i18n.LANGS])
        self.lang_combo.pack(side="left", padx=6)
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_lang_change())

        self.title_label = ttk.Label(self, font=("Microsoft JhengHei", 14, "bold"))
        self.title_label.pack(pady=(10, 4))
        self.summary_label = ttk.Label(self, foreground="#666")
        self.summary_label.pack(pady=(0, 10))

        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True, padx=16, pady=4)
        self._cards = []
        self._build_cards()

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, foreground="#357",
                  anchor="w").pack(fill="x", side="bottom", padx=16, pady=8)

        self._retranslate()

    def _build_cards(self):
        for inst in INSTRUMENTS:
            card = ttk.LabelFrame(self.body, text=f"  {inst['name']}  ")
            card.pack(fill="x", pady=6)
            left = ttk.Frame(card)
            left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
            kind_lbl = ttk.Label(left, font=("Microsoft JhengHei", 11, "bold"))
            kind_lbl.pack(anchor="w")
            note_lbl = ttk.Label(left, foreground="#555")
            note_lbl.pack(anchor="w")
            meta_lbl = ttk.Label(left, foreground="#888")
            meta_lbl.pack(anchor="w", pady=(2, 0))
            btn = ttk.Button(card, command=lambda i=inst: self._launch(i), width=14)
            btn.pack(side="right", padx=10)
            self._cards.append((inst, kind_lbl, note_lbl, meta_lbl, btn))

    # ---------------- 語言 ---------------- #
    def _on_lang_change(self):
        for code, label in i18n.LANG_LABELS.items():
            if label == self.lang_var.get():
                i18n.set_lang(code)
                break
        self._retranslate()

    def _retranslate(self):
        lang = i18n.get_lang()
        self.title(t("launcher_title"))
        self.lang_label.config(text=t("language"))
        self.title_label.config(text=t("launcher_choose"))
        total = sum(i["count"] for i in INSTRUMENTS)
        self.summary_label.config(text=t("launcher_summary", n=len(INSTRUMENTS), total=total))
        for inst, kind_lbl, note_lbl, meta_lbl, btn in self._cards:
            kind_lbl.config(text=inst["kind"][lang])
            note_lbl.config(text=inst["note"][lang])
            meta_lbl.config(text=t("card_meta", count=inst["count"], folder=inst["folder"]))
            btn.config(text=t("open_panel"))
        if not self.status_var.get() or self.status_var.get() in (
                i18n._STR["ready"]["en"], i18n._STR["ready"]["zh"]):
            self.status_var.set(t("ready"))

    def _launch(self, inst):
        folder = os.path.join(HERE, inst["folder"])
        entry = os.path.join(folder, inst["entry"])
        if not os.path.isfile(entry):
            messagebox.showerror(t("file_missing"), entry)
            return
        try:
            proc = subprocess.Popen([sys.executable, inst["entry"]], cwd=folder)
            self._procs.append(proc)
            self.status_var.set(t("launched", name=inst["name"], pid=proc.pid))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("launch_fail"), str(e))
            self.status_var.set(f"{t('launch_fail')}: {e}")


if __name__ == "__main__":
    Launcher().mainloop()
