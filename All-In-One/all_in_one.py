# -*- coding: utf-8 -*-
"""
SCPI 儀器控制 — All-In-One 整合程式（支援英文 / 繁體中文，預設英文）
=====================================================================

單一視窗整合所有儀器的控制面板。左上角下拉式選單先選「分類」再選「儀器」：

    Power Supply        : 2231A-30-3 / E3633A / E36300
    DAQ                 : DAQ973A
    E-Load              : Chroma 63600
    Oscilloscope        : DPO 7 Series / MSO 5 Series / R&S RTE
    Function Generator  : AFG3000 / AFG31000
    Meter / SMU         : Series 2400

各儀器的指令資料表與驅動程式直接沿用其原資料夾（../<folder>/），不複製、不分叉；
本程式只負責「動態載入 + 通用面板」。切換儀器時面板會保留（連線、紀錄、選擇
皆不會遺失），因此可同時連線並輪流操作多台儀器。

執行：
    python all_in_one.py

各儀器面板的連線列有「Scan」（列出 VISA 資源，GPIB 優先並附 *IDN?）；指令區有「Search」關鍵字篩選。
模擬模式已自介面隱藏，僅供開發測試：python all_in_one.py --sim
"""
from __future__ import annotations

import importlib
import os
import queue
import sys
import threading
import types
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 本資料夾的 i18n 必須優先於各儀器資料夾內的同名 i18n
sys.path.insert(0, HERE)
import i18n  # noqa: E402
from i18n import t  # noqa: E402

DEFAULT_RESOURCE = "GPIB0::9::INSTR"

# --------------------------------------------------------------------------- #
# 儀器登錄表
#   style = "chlist" : set_command(key, value, ch_list=...)       （通道清單 / 無通道型）
#   style = "index"  : set_command(key, value, channel=, element=) （標頭編號型）
# --------------------------------------------------------------------------- #
CATEGORIES = [
    ("cat_psu", ["2231A-30-3", "E3633A", "E36300", "Chroma 62000P"]),
    ("cat_daq", ["DAQ973A"]),
    ("cat_eload", ["Chroma 63600"]),
    ("cat_scope", ["DPO 7 Series", "MSO 5 Series", "R&S RTE"]),
    ("cat_fgen", ["AFG3000", "AFG31000"]),
    ("cat_meter", ["Series 2400"]),
]

INSTRUMENTS: dict[str, dict[str, Any]] = {
    "2231A-30-3": dict(
        folder="2231A-30-3", cmd_mod="commands_2231a", drv_mod="instrument", cls="K2231A",
        style="chlist", sim_idn="Keithley instruments,2231A-30-3,SIM0000,1.0.0",
        kind={"en": "Triple-channel DC Power Supply (Keithley)", "zh": "三通道直流電源供應器 (Keithley)"}),
    "E3633A": dict(
        folder="E3633A", cmd_mod="commands_e3633a", drv_mod="instrument", cls="E3633A",
        style="chlist", sim_idn="Agilent Technologies,E3633A,SIM0000,1.0",
        kind={"en": "Single-output DC Power Supply (Agilent/Keysight)",
              "zh": "單輸出直流電源供應器 (Agilent/Keysight)"}),
    "E36300": dict(
        folder="E36300", cmd_mod="commands_e36300", drv_mod="instrument", cls="E36300",
        style="chlist", sim_idn="Keysight Technologies,E36313A,SIM0000,1.0.0",
        kind={"en": "Triple-output DC Power Supply (Keysight)", "zh": "三輸出直流電源供應器 (Keysight)"}),
    "Chroma 62000P": dict(
        folder="Chroma_62000P", cmd_mod="commands_chroma62000p", drv_mod="instrument",
        cls="Chroma62000P", style="chlist", sim_idn="Chroma ATE,62012P-80-60,SIM0000,1.00",
        kind={"en": "Programmable DC Power Supply (Chroma)", "zh": "可程式直流電源供應器 (Chroma)"}),
    "DAQ973A": dict(
        folder="DAQ973A", cmd_mod="daq973a_commands", drv_mod="instrument", cls="DAQ973A",
        style="chlist", sim_idn="Keysight Technologies,DAQ973A,SIM0000,A.01.00",
        kind={"en": "Data Acquisition / Switch System (Keysight)",
              "zh": "資料擷取 / 開關量測系統 (Keysight)"}),
    "Chroma 63600": dict(
        folder="Chroma_63600", cmd_mod="commands_chroma63600", drv_mod="instrument",
        cls="Chroma63600", style="chlist", sim_idn="Chroma,63600,SIM0000,1.00",
        kind={"en": "DC Electronic Load (Chroma)", "zh": "直流電子負載 (Chroma)"}),
    "DPO 7 Series": dict(
        folder="DPO_7SERIES", cmd_mod="commands_dpo7", drv_mod="instrument", cls="DPO7",
        style="index", elem_label="index_n", sim_idn="TEKTRONIX,DPO7254,SIM0000,CF:91.1CT FV:1.0",
        kind={"en": "Digital Phosphor Oscilloscope (Tektronix)", "zh": "數位螢光示波器 (Tektronix)"}),
    "MSO 5 Series": dict(
        folder="MSO_5SERIES", cmd_mod="commands_mso5", drv_mod="instrument", cls="MSO5",
        style="index", elem_label="index_n", sim_idn="TEKTRONIX,MSO54,SIM0000,CF:91.1CT FV:1.0",
        kind={"en": "Mixed-Signal Oscilloscope (Tektronix)", "zh": "混合訊號示波器 (Tektronix)"}),
    "R&S RTE": dict(
        folder="RS_RTE", cmd_mod="commands_rte", drv_mod="instrument", cls="RTE",
        style="index", elem_label="index_n",
        sim_idn="Rohde&Schwarz,RTE1104,1326.0003K04/SIM0000,4.70.1.0",
        kind={"en": "Digital Oscilloscope (Rohde & Schwarz)", "zh": "數位示波器 (Rohde & Schwarz)"}),
    "AFG3000": dict(
        folder="AFG3000", cmd_mod="commands_afg3000", drv_mod="instrument", cls="AFG3000",
        style="index", elem_label="index_n", sim_idn="TEKTRONIX,AFG3252,SIM0000,SCPI:99.0 FV:3.1.1",
        kind={"en": "Arbitrary/Function Generator (Tektronix)",
              "zh": "任意波形／函數信號產生器 (Tektronix)"}),
    "AFG31000": dict(
        folder="AFG31000", cmd_mod="afg31000_commands", drv_mod="afg31000", cls="AFG31000",
        style="index", elem_label="seq_elem", sim_idn="TEKTRONIX,AFG31052,SIM0000,SCPI:99.0 FV:1.0",
        kind={"en": "Arbitrary Function Generator (Tektronix)",
              "zh": "任意函數信號產生器 (Tektronix)"}),
    "Series 2400": dict(
        folder="Series2400", cmd_mod="commands_2400", drv_mod="instrument", cls="K2400",
        style="index", elem_label="index_n",
        sim_idn="KEITHLEY INSTRUMENTS INC.,MODEL 2400,SIM0000,C32   Oct  4 2010 14:20:11/A02  /S/K",
        kind={"en": "SourceMeter / SMU (Keithley)", "zh": "電源量測單元 SMU (Keithley)"}),
}


# --------------------------------------------------------------------------- #
# 動態載入：各資料夾的驅動模組多半同名（instrument.py），故逐台隔離載入
# --------------------------------------------------------------------------- #
def _ensure_pyvisa():
    """未安裝 pyvisa 時放入替身模組，讓模擬模式仍可運作；實際連線時才報錯。"""
    try:
        import pyvisa  # noqa: F401
    except ImportError:
        stub = types.ModuleType("pyvisa")

        def _missing(*_a, **_k):
            raise RuntimeError("pyvisa is not installed:  pip install pyvisa pyvisa-py")

        setattr(stub, "ResourceManager", _missing)
        sys.modules["pyvisa"] = stub


_BACKENDS: dict[str, dict] = {}


def load_backend(name: str) -> dict:
    """載入（並快取）某台儀器的指令資料表與驅動類別。"""
    if name in _BACKENDS:
        return _BACKENDS[name]
    spec = INSTRUMENTS[name]
    _ensure_pyvisa()
    folder = os.path.join(ROOT, spec["folder"])
    names = (spec["cmd_mod"], spec["drv_mod"])
    for n in names:                       # 清掉他台留下的同名模組
        sys.modules.pop(n, None)
    sys.path.insert(1, folder)            # index 0 保留給本資料夾（i18n）
    try:
        cmds = importlib.import_module(spec["cmd_mod"])
        drv = importlib.import_module(spec["drv_mod"])
    finally:
        sys.path.remove(folder)
        for n in names:                   # 模組物件已被引用，移出 sys.modules 避免撞名
            sys.modules.pop(n, None)
    backend = {
        "commands": cmds.COMMANDS,
        "group_order": cmds.GROUP_ORDER,
        "cls": getattr(drv, spec["cls"]),
    }
    _BACKENDS[name] = backend
    return backend


# --------------------------------------------------------------------------- #
# 模擬資源
# --------------------------------------------------------------------------- #
class _FakeResource:
    def __init__(self, idn: str):
        self.timeout = 0
        self.write_termination = "\n"
        self.read_termination = "\n"
        self.state = {"*IDN?": idn + " (SIM)"}

    def write(self, cmd: str):
        if " " in cmd:
            head, val = cmd.split(" ", 1)
            self.state[head] = val.strip()

    def query(self, cmd: str) -> str:
        cmd = cmd.strip()
        if cmd in self.state:
            return self.state[cmd]
        head = cmd.split("?", 1)[0].strip()
        return self.state.get(head, "0")

    def close(self):
        pass


def _make_sim(cls, idn: str):
    d = cls.__new__(cls)
    d._owns_rm = False
    d._rm = None
    d._inst = _FakeResource(idn)
    return d


class _CaptureResource:
    """只記錄驅動程式要送出的字串、不實際傳送 — 供「Copy Command」組出完整 SCPI。"""
    def __init__(self):
        self.last = ""

    def write(self, cmd: str):
        self.last = cmd

    def query(self, cmd: str) -> str:
        self.last = cmd
        return ""

    def close(self):
        pass


def _make_capture(cls):
    d = cls.__new__(cls)
    d._owns_rm = False
    d._rm = None
    d._inst = _CaptureResource()
    return d


# --------------------------------------------------------------------------- #
# 通用儀器面板（嵌入主視窗的 Frame）
# --------------------------------------------------------------------------- #
class InstrumentPanel(ttk.Frame):
    def __init__(self, master, name: str, on_state_change=None):
        super().__init__(master)
        self.name = name
        self.spec = INSTRUMENTS[name]
        self.style = self.spec["style"]
        be = load_backend(name)
        self.Instrument = be["cls"]
        self.commands = be["commands"]
        self.group_order = be["group_order"]
        self._on_state_change = on_state_change

        order = {g: i for i, g in enumerate(self.group_order)}
        self._sorted = sorted(self.commands,
                              key=lambda c: (order.get(c["group"], 999), str(c["page"]), c["scpi"]))
        self.cmd_by_label = {self._label(c): c for c in self._sorted}
        self.labels = list(self.cmd_by_label)

        self.dev: Any = None
        self._idn = ""
        self.param_var = tk.StringVar()
        self.chlist_var = tk.StringVar()
        self.channel_var = tk.StringVar(value="1")
        self.element_var = tk.StringVar(value="1")

        self._build_connection_bar()
        self._build_command_area()
        self._build_action_buttons()
        self._build_output_area()
        self.retranslate()

    @staticmethod
    def _label(c) -> str:
        return f"[{c['group']}] {c['name']}"

    @property
    def connected(self) -> bool:
        return self.dev is not None

    # ---------------- 連線列 ---------------- #
    def _build_connection_bar(self):
        frm = ttk.LabelFrame(self)
        frm.pack(fill="x", padx=10, pady=(6, 4))
        self.conn_frame = frm
        self.visa_label = ttk.Label(frm)
        self.visa_label.grid(row=0, column=0, padx=4, pady=6, sticky="w")
        # 資源下拉：Scan 後列出找到的資源，也可手動輸入
        self.resource_var = tk.StringVar(value=DEFAULT_RESOURCE)
        self.resource_combo = ttk.Combobox(frm, textvariable=self.resource_var, width=56)
        self.resource_combo.grid(row=0, column=1, padx=4, pady=6, sticky="we")
        self.scan_btn = ttk.Button(frm, command=self._scan_resources)
        self.scan_btn.grid(row=0, column=2, padx=4)
        # 模擬模式：介面上隱藏，僅供開發測試（python all_in_one.py --sim）
        self.sim_var = tk.BooleanVar(value="--sim" in sys.argv)
        self.connect_btn = ttk.Button(frm, command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=4)
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(frm, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, columnspan=4, padx=6, pady=(0, 6), sticky="w")
        frm.columnconfigure(1, weight=1)

    # ---------------- Command 區 ---------------- #
    def _build_command_area(self):
        frm = ttk.LabelFrame(self)
        frm.pack(fill="x", padx=10, pady=4)
        self.cmd_frame = frm

        self.group_label = ttk.Label(frm)
        self.group_label.grid(row=0, column=0, padx=4, pady=6, sticky="w")
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(frm, textvariable=self.group_var, state="readonly", width=26)
        self.group_combo.grid(row=0, column=1, padx=4, pady=6, sticky="w")
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self._on_group_change())

        # 關鍵字搜尋（與群組篩選並用）
        search_box = ttk.Frame(frm)
        search_box.grid(row=0, column=2, columnspan=2, padx=4, pady=6, sticky="e")
        self.search_label = ttk.Label(search_box)
        self.search_label.pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_box, textvariable=self.search_var, width=28)
        self.search_entry.pack(side="left", padx=4)
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.search_entry.bind("<Escape>", lambda e: self.search_var.set(""))
        self.search_count_var = tk.StringVar()
        ttk.Label(search_box, textvariable=self.search_count_var, foreground="#666",
                  width=14).pack(side="left")

        self.command_label = ttk.Label(frm)
        self.command_label.grid(row=1, column=0, padx=4, pady=6, sticky="w")
        self.cmd_var = tk.StringVar(value=self.labels[0])
        self.cmd_combo = ttk.Combobox(frm, textvariable=self.cmd_var, state="readonly",
                                      values=self.labels, width=70)
        self.cmd_combo.grid(row=1, column=1, columnspan=3, padx=4, pady=6, sticky="we")
        self.cmd_combo.bind("<<ComboboxSelected>>", lambda e: self._on_command_change())

        self.syntax_var = tk.StringVar()
        ttk.Label(frm, textvariable=self.syntax_var, foreground="#357",
                  font=("Consolas", 9), wraplength=860, justify="left").grid(
                      row=2, column=1, columnspan=3, padx=4, sticky="w")

        # 標頭編號型：通道 / 編號
        self.channel_label = ttk.Label(frm)
        self.channel_combo = ttk.Combobox(frm, textvariable=self.channel_var, state="readonly",
                                          values=["1", "2"], width=5)
        self.element_label = ttk.Label(frm)
        self.element_spin = ttk.Spinbox(frm, from_=1, to=256, width=6, textvariable=self.element_var)
        self.channel_label.grid(row=3, column=0, padx=4, pady=6, sticky="w")
        self.channel_combo.grid(row=3, column=1, padx=4, pady=6, sticky="w")
        self.element_label.grid(row=3, column=2, padx=4, pady=6, sticky="e")
        self.element_spin.grid(row=3, column=3, padx=4, pady=6, sticky="w")

        # 參數
        self.param_label = ttk.Label(frm)
        self.param_container = ttk.Frame(frm)
        self.param_label.grid(row=4, column=0, padx=4, pady=6, sticky="w")
        self.param_container.grid(row=4, column=1, columnspan=3, padx=4, pady=6, sticky="we")

        # 通道清單型：(@...)
        self.chlist_label = ttk.Label(frm)
        self.chlist_entry = ttk.Entry(frm, textvariable=self.chlist_var, width=24)
        self.chlist_label.grid(row=5, column=0, padx=4, pady=6, sticky="w")
        self.chlist_entry.grid(row=5, column=1, padx=4, pady=6, sticky="w")

        self.hint_var = tk.StringVar()
        ttk.Label(frm, textvariable=self.hint_var, foreground="#666").grid(
            row=6, column=1, columnspan=3, padx=4, pady=(0, 6), sticky="w")
        frm.columnconfigure(1, weight=1)

    def _group_values(self):
        return [t("all")] + [g for g in self.group_order
                             if any(c["group"] == g for c in self.commands)]

    def _on_group_change(self):
        self._apply_filter(force_first=True)

    @staticmethod
    def _matches(c, words) -> bool:
        hay = " ".join(str(c.get(k, "")) for k in
                       ("name", "scpi", "syntax", "desc", "params", "group")).lower()
        return all(w in hay for w in words)

    def _apply_filter(self, force_first: bool = False):
        """依群組 + 搜尋關鍵字（空白分隔、全部須符合、不分大小寫）更新指令下拉。"""
        g = self.group_var.get()
        words = self.search_var.get().lower().split()
        labels = [self._label(c) for c in self._sorted
                  if (g in ("", t("all")) or c["group"] == g) and self._matches(c, words)]
        if words:
            self.search_count_var.set(
                t("search_count", n=len(labels)) if labels else t("search_none"))
        else:
            self.search_count_var.set("")
        if not labels:                      # 無符合：保留目前指令，不清空
            self.cmd_combo.config(values=[])
            return
        self.cmd_combo.config(values=labels)
        if force_first or self.cmd_var.get() not in labels:
            self.cmd_var.set(labels[0])
            self._on_command_change()

    def _current_command(self) -> dict:
        return self.cmd_by_label[self.cmd_var.get()]

    @staticmethod
    def _show(widgets, visible: bool):
        for w in widgets:
            w.grid() if visible else w.grid_remove()

    def _on_command_change(self):
        cmd = self._current_command()
        rw = "RW" if cmd["set"] and cmd["get"] else ("R" if cmd["get"] else "W")
        self.syntax_var.set(f"{cmd['syntax']}   —  [{rw}] {t('manual_p', page=cmd['page'])}")

        # 位置欄位（依型態顯示）
        has_chan = self.style == "index" and bool(cmd.get("chan"))
        has_elem = self.style == "index" and bool(cmd.get("elem"))
        has_chlist = self.style == "chlist" and bool(cmd.get("chlist"))
        self._show((self.channel_label, self.channel_combo), has_chan)
        self._show((self.element_label, self.element_spin), has_elem)
        self._show((self.chlist_label, self.chlist_entry), has_chlist)
        if has_chan:
            chs = [str(x) for x in cmd.get("channels") or [1, 2]]
            self.channel_combo.config(values=chs)
            if self.channel_var.get() not in chs:
                self.channel_var.set(chs[0])

        # 參數欄位
        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_var.set("")
        self.hint_var.set(cmd.get("hint", "") or "")
        kind = cmd["kind"]
        if kind == "none":
            self.param_label.config(text=t("no_param_gen" if self.style == "chlist" else "no_param"))
        else:
            self.param_label.config(text=t("param"))
            if kind == "bool":
                self.param_var.set("ON")
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 state="readonly", values=["ON", "OFF"], width=22)
            elif kind == "enum" and cmd.get("opts"):
                self.param_var.set(cmd["opts"][0])
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 values=cmd["opts"], width=28)
            elif kind == "numeric":
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 values=cmd.get("suggest") or [], width=28)
            else:
                w = ttk.Entry(self.param_container, textvariable=self.param_var, width=46)
                if not self.hint_var.get():
                    self.hint_var.set(t("raw_hint"))
            w.pack(side="left")
        self._refresh_action_state()

    # ---------------- 按鈕 ---------------- #
    def _build_action_buttons(self):
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=10, pady=4)
        self.write_btn = ttk.Button(frm, command=self._do_write, width=16)
        self.read_btn = ttk.Button(frm, command=self._do_read, width=16)
        self.write_btn.pack(side="left", padx=4)
        self.read_btn.pack(side="left", padx=4)
        self.copy_btn = ttk.Button(frm, command=self._do_copy, width=16)
        self.copy_btn.pack(side="left", padx=(16, 4))
        self.clear_btn = ttk.Button(frm, command=self._clear_log)
        self.clear_btn.pack(side="right", padx=4)

    # ---------------- 輸出區 ---------------- #
    def _build_output_area(self):
        frm = ttk.LabelFrame(self)
        frm.pack(fill="x", padx=10, pady=4)
        self.result_frame = frm
        self.result_var = tk.StringVar(value="—")
        ttk.Label(frm, textvariable=self.result_var, font=("Consolas", 15, "bold"),
                  foreground="#06c", wraplength=860, justify="left").pack(anchor="w", padx=8, pady=8)
        logfrm = ttk.LabelFrame(self)
        logfrm.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log_frame = logfrm
        self.log = tk.Text(logfrm, height=8, wrap="none", font=("Consolas", 9))
        ys = ttk.Scrollbar(logfrm, command=self.log.yview)
        self.log.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

    # ---------------- 語言 ---------------- #
    def retranslate(self):
        self.conn_frame.config(text=f"{t('conn_frame')} — {self.name}")
        self.visa_label.config(text=t("visa"))
        self.scan_btn.config(text=t("scan"))
        self.connect_btn.config(text=t("disconnect") if self.connected else t("connect"))
        self.cmd_frame.config(text=t("cmd_frame"))
        self.group_label.config(text=t("group"))
        self.search_label.config(text=t("search"))
        self.command_label.config(text=t("command"))
        self.channel_label.config(text=t("channel"))
        self.element_label.config(text=t(self.spec.get("elem_label", "index_n")))
        self.chlist_label.config(text=t("chlist"))
        self.write_btn.config(text=t("write"))
        self.read_btn.config(text=t("read"))
        self.copy_btn.config(text=t("copy_cmd"))
        self.clear_btn.config(text=t("clear_log"))
        self.result_frame.config(text=t("result_frame"))
        self.log_frame.config(text=t("log_frame"))
        cur = self.group_var.get()
        was_all = cur == "" or cur in ("(All)", "（全部）")
        self.group_combo.config(values=self._group_values())
        if was_all:
            self.group_var.set(t("all"))
        self._update_status()
        self._apply_filter()
        self._on_command_change()

    def _update_status(self):
        if self.connected:
            self.status_var.set(t("connected", idn=self._idn))
            self.status_label.config(foreground="#080")
        else:
            self.status_var.set(t("disconnected"))
            self.status_label.config(foreground="#b00")

    # ---------------- 掃描 VISA 資源 ---------------- #
    def _scan_resources(self):
        """背景執行緒列出 VISA 資源並查詢 *IDN?，完成後填入資源下拉選單。"""
        self.scan_btn.config(state="disabled")
        self.status_var.set(t("scanning"))
        self.status_label.config(foreground="#357")
        self._scan_q: queue.Queue = queue.Queue()
        threading.Thread(target=self._scan_worker, args=(self._scan_q,), daemon=True).start()
        self.after(100, self._poll_scan)

    def _poll_scan(self):
        """主執行緒輪詢掃描結果（Tk 物件只能在主執行緒操作）。"""
        try:
            items, error = self._scan_q.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_scan)
            return
        self._scan_done(items, error)

    @staticmethod
    def _scan_worker(q: "queue.Queue"):
        try:
            _ensure_pyvisa()
            import pyvisa
            rm = pyvisa.ResourceManager()
            found = list(rm.list_resources("?*::INSTR"))
            # GPIB 排最前面，其次 USB / TCPIP，序列埠 (ASRL) 最後
            rank = {"GPIB": 0, "USB": 1, "TCPI": 2, "VXI": 3, "ASRL": 9}
            found.sort(key=lambda r: (rank.get(r[:4].upper(), 5), r))
            items = []
            for res in found:
                idn = ""
                if not res.upper().startswith("ASRL"):   # 序列埠不查詢，避免卡住
                    try:
                        inst = rm.open_resource(res, open_timeout=1000)
                        inst.timeout = 1500
                        idn = inst.query("*IDN?").strip()  # type: ignore[attr-defined]
                        inst.close()
                    except Exception:  # noqa: BLE001
                        idn = ""
                items.append(f"{res}    {idn}".rstrip())
            q.put((items, None))
        except Exception as e:  # noqa: BLE001
            q.put(([], e))

    def _scan_done(self, items, error):
        self.scan_btn.config(state="normal")
        self._update_status()           # 狀態列恢復顯示連線狀態，不顯示掃描結果提示
        if error is not None:
            messagebox.showerror(t("scan_fail"), str(error))
            self._log(f"SCAN ERROR: {error}")
            return
        self.resource_combo.config(values=items)
        if items:
            self.resource_var.set(items[0])
            self.resource_combo.event_generate("<Button-1>")   # 自動展開下拉
        self._log("SCAN -> " + (", ".join(items) if items else "(none)"))

    def _resource_name(self) -> str:
        """下拉項目為「資源字串 + IDN」，連線時只取資源字串。"""
        v = self.resource_var.get().strip()
        return v.split()[0] if v else ""

    # ---------------- 連線 ---------------- #
    def _toggle_connection(self):
        if self.connected:
            self.disconnect()
            return
        try:
            if self.sim_var.get():
                self.dev = _make_sim(self.Instrument, self.spec["sim_idn"])
                self._log(t("sim_created", model=self.name))
            else:
                self.dev = self.Instrument(self._resource_name())
            self._idn = self.dev.idn()
            self._log(f"CONNECT -> {self._idn}")
        except Exception as e:  # noqa: BLE001
            self.dev = None
            messagebox.showerror(t("conn_fail"), str(e))
            self._log(f"CONNECT ERROR: {e}")
        self._after_conn_change()

    def disconnect(self):
        if self.dev is None:
            return
        try:
            self.dev.close()
        except Exception:  # noqa: BLE001
            pass
        self.dev = None
        self._idn = ""
        self._log("DISCONNECT")
        self._after_conn_change()

    def _after_conn_change(self):
        self.connect_btn.config(text=t("disconnect") if self.connected else t("connect"))
        self._update_status()
        self._refresh_action_state()
        if self._on_state_change:
            self._on_state_change()

    def _refresh_action_state(self):
        cmd = self._current_command()
        on = self.connected
        self.write_btn.config(state="normal" if on and cmd["set"] else "disabled")
        self.read_btn.config(state="normal" if on and cmd["get"] else "disabled")

    # ---------------- Write / Read ---------------- #
    def _value(self, cmd):
        if cmd["kind"] == "none":
            return None
        raw = self.param_var.get().strip()
        # 數值也原樣傳入（驅動程式對字串不做轉換），避免 32 被送成 32.0
        return raw or None

    def _pos_kwargs(self, cmd) -> dict:
        if self.style == "chlist":
            if cmd.get("chlist"):
                return {"ch_list": self.chlist_var.get().strip() or None}
            return {}
        kw = {}
        if cmd.get("chan"):
            kw["channel"] = int(self.channel_var.get())
        if cmd.get("elem"):
            kw["element"] = int(self.element_var.get())
        return kw

    @staticmethod
    def _pos_tag(kw) -> str:
        bits = []
        if kw.get("ch_list"):
            bits.append(f"(@{kw['ch_list']})")
        if "channel" in kw:
            bits.append(f"CH{kw['channel']}")
        if "element" in kw:
            bits.append(f"#{kw['element']}")
        return (" " + " ".join(bits)) if bits else ""

    def _do_write(self):
        if not self.connected:
            return
        cmd = self._current_command()
        try:
            value = self._value(cmd)
            kw = self._pos_kwargs(cmd)
            if cmd["kind"] != "none" and value is None and not kw.get("ch_list"):
                messagebox.showwarning(t("missing_title"), t("missing_msg"))
                return
            self.dev.set_command(cmd["key"], value, **kw)
            self._log(f"WRITE {cmd['scpi']}{self._pos_tag(kw)} <- "
                      f"{value if value is not None else ''}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("write_fail"), str(e))
            self._log(f"WRITE ERROR: {e}")

    def _do_read(self):
        if not self.connected:
            return
        cmd = self._current_command()
        try:
            kw = self._pos_kwargs(cmd)
            if self.style == "chlist":
                result = self.dev.query_command(cmd["key"], self._value(cmd), **kw)
            elif cmd.get("qarg"):
                arg = self.param_var.get().strip() or None
                result = self.dev.query_command(cmd["key"], arg=arg, **kw)
            else:
                result = self.dev.query_command(cmd["key"], **kw)
            self.result_var.set(str(result))
            self._log(f"READ  {cmd['scpi']}?{self._pos_tag(kw)} -> {result}")
        except Exception as e:  # noqa: BLE001
            self.result_var.set(t("read_error"))
            messagebox.showerror(t("read_fail"), str(e))
            self._log(f"READ ERROR: {e}")

    # ---------------- Copy Command ---------------- #
    def build_scpi(self, cmd) -> str:
        """組出目前選擇（含參數/通道）實際會送出的 SCPI 字串。

        可寫入且已填參數（或無參數）→ 寫入字串；否則若可查詢 → 查詢字串。
        """
        cap = _make_capture(self.Instrument)
        value = self._value(cmd)
        kw = self._pos_kwargs(cmd)
        if cmd["set"] and (cmd["kind"] == "none" or value is not None or kw.get("ch_list")):
            cap.set_command(cmd["key"], value, **kw)
        elif cmd["get"]:
            if self.style == "chlist":
                cap.query_command(cmd["key"], value, **kw)
            elif cmd.get("qarg"):
                cap.query_command(cmd["key"], arg=self.param_var.get().strip() or None, **kw)
            else:
                cap.query_command(cmd["key"], **kw)
        else:
            return cmd["syntax"]
        return cap._inst.last

    def _do_copy(self):
        try:
            text = self.build_scpi(self._current_command())
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("copy_fail"), str(e))
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()           # 確保視窗關閉後剪貼簿內容仍保留
        self._log(t("copied", cmd=text))

    # ---------------- 紀錄 ---------------- #
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n")
        self.log.see("end")

    def _clear_log(self):
        self.log.delete("1.0", "end")


# --------------------------------------------------------------------------- #
# 主視窗
# --------------------------------------------------------------------------- #
class AllInOneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("960x760")
        self.minsize(860, 660)
        self._panels: dict[str, InstrumentPanel] = {}
        self._current: InstrumentPanel | None = None

        # ---- 頂列：左上角 分類 / 儀器 下拉；右上角 語言 ---- #
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 0))
        self.cat_label = ttk.Label(top, font=("Microsoft JhengHei", 10, "bold"))
        self.cat_label.pack(side="left")
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(top, textvariable=self.cat_var, state="readonly", width=20)
        self.cat_combo.pack(side="left", padx=(4, 12))
        self.cat_combo.bind("<<ComboboxSelected>>", lambda e: self._on_category_change())

        self.inst_label = ttk.Label(top, font=("Microsoft JhengHei", 10, "bold"))
        self.inst_label.pack(side="left")
        self.inst_var = tk.StringVar()
        self.inst_combo = ttk.Combobox(top, textvariable=self.inst_var, state="readonly", width=18)
        self.inst_combo.pack(side="left", padx=4)
        self.inst_combo.bind("<<ComboboxSelected>>", lambda e: self._show_instrument(self.inst_var.get()))

        self.lang_var = tk.StringVar(value=i18n.LANG_LABELS[i18n.get_lang()])
        self.lang_combo = ttk.Combobox(top, textvariable=self.lang_var, state="readonly", width=10,
                                       values=[i18n.LANG_LABELS[c] for c in i18n.LANGS])
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_lang_change())
        self.lang_label = ttk.Label(top)
        self.lang_label.pack(side="right", padx=4)

        self.info_var = tk.StringVar()
        ttk.Label(self, textvariable=self.info_var, foreground="#555").pack(
            fill="x", padx=12, pady=(6, 0))
        ttk.Separator(self).pack(fill="x", padx=10, pady=(6, 0))

        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)

        self.footer_var = tk.StringVar()
        ttk.Label(self, textvariable=self.footer_var, foreground="#357", anchor="w").pack(
            fill="x", side="bottom", padx=12, pady=(0, 6))

        self._cat_index = 0
        self._retranslate()
        self._on_category_change()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- 分類 / 儀器 ---- #
    def _on_category_change(self):
        labels = [t(k) for k, _ in CATEGORIES]
        if self.cat_var.get() in labels:
            self._cat_index = labels.index(self.cat_var.get())
        names = CATEGORIES[self._cat_index][1]
        self.inst_combo.config(values=names)
        # 分類內已有開啟中的面板就沿用，否則選第一台
        cur = self._current.name if self._current else None
        target = cur if cur in names else names[0]
        self.inst_var.set(target)
        self._show_instrument(target)

    def _show_instrument(self, name: str):
        panel = self._panels.get(name)
        if panel is None:
            try:
                panel = InstrumentPanel(self.body, name, on_state_change=self._update_footer)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror(t("load_fail"), f"{name}\n\n{e}")
                return
            self._panels[name] = panel
        if self._current is not None and self._current is not panel:
            self._current.pack_forget()
        panel.pack(fill="both", expand=True)
        self._current = panel
        self._update_info()
        self._update_footer()

    def _update_info(self):
        if not self._current:
            return
        spec = self._current.spec
        self.info_var.set(t("aio_info", kind=spec["kind"][i18n.get_lang()],
                            count=len(self._current.commands), folder=spec["folder"]))

    def _update_footer(self):
        live = [n for n, p in self._panels.items() if p.connected]
        txt = t("conn_count", n=len(live))
        if live:
            txt += "  —  " + ", ".join(live)
        self.footer_var.set(txt)

    # ---- 語言 ---- #
    def _on_lang_change(self):
        for code, label in i18n.LANG_LABELS.items():
            if label == self.lang_var.get():
                i18n.set_lang(code)
                break
        self._retranslate()
        for p in self._panels.values():
            p.retranslate()
        self._update_info()
        self._update_footer()

    def _retranslate(self):
        self.title(t("aio_title"))
        self.cat_label.config(text=t("category"))
        self.inst_label.config(text=t("instrument"))
        self.lang_label.config(text=t("language"))
        labels = [t(k) for k, _ in CATEGORIES]
        self.cat_combo.config(values=labels)
        self.cat_var.set(labels[self._cat_index])

    def _on_close(self):
        for p in self._panels.values():
            p.disconnect()
        self.destroy()


if __name__ == "__main__":
    AllInOneApp().mainloop()
