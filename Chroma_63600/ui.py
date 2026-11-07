# -*- coding: utf-8 -*-
"""
Chroma 63600 控制面板 (Tkinter GUI) — 支援英文 / 繁體中文（預設英文）
================================================================

以下拉式選單選擇 SCPI command（涵蓋手冊完整指令集，依功能群組分類），
面板依指令型態自動彈出參數欄位；右上角「Language」可即時切換英文/繁中介面。

執行：
    python ui.py

無實體儀器時，勾選「Simulation mode」即可離線操作測試整個介面。
整個 UI 由資料表（commands 模組）驅動；介面文字由 i18n 模組翻譯。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import i18n
from i18n import t
from instrument import Chroma63600 as Instrument
from commands_chroma63600 import COMMANDS, GROUP_ORDER

# 以下兩個常數供各儀器專案沿用（複製本檔後只需改這兩行與匯入列）
MODEL = "Chroma 63600"
SIM_IDN = "Chroma,63600,SIM0000,1.00"

_order = {g: i for i, g in enumerate(GROUP_ORDER)}
_SORTED = sorted(COMMANDS, key=lambda c: (_order.get(c["group"], 999), c["page"], c["scpi"]))


def _label(entry) -> str:
    return f"[{entry['group']}] {entry['name']}"


CMD_BY_LABEL = {_label(c): c for c in _SORTED}
LABELS = list(CMD_BY_LABEL.keys())


class _FakeResource:
    def __init__(self):
        self.timeout = 0
        self.write_termination = "\n"
        self.read_termination = "\n"
        self.state = {"*IDN?": SIM_IDN + " (SIM)"}

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


def _make_sim() -> Instrument:
    d = Instrument.__new__(Instrument)
    d._owns_rm = False
    d._rm = None            # type: ignore[assignment]
    d._inst = _FakeResource()  # type: ignore[assignment]
    return d


class InstrumentPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("880x670")
        self.minsize(780, 600)

        self.daq = None
        self.param_var = tk.StringVar()
        self.chlist_var = tk.StringVar()
        self._idn = ""
        self._connected = False

        self._build_connection_bar()
        self._build_command_area()
        self._build_action_buttons()
        self._build_output_area()

        self._retranslate()
        self._on_command_change()
        self._set_controls_enabled(False)

    # ---------------- 連線列 ---------------- #
    def _build_connection_bar(self):
        frm = ttk.LabelFrame(self)
        frm.pack(fill="x", padx=10, pady=(10, 4))
        self.conn_frame = frm

        self.visa_label = ttk.Label(frm)
        self.visa_label.grid(row=0, column=0, padx=4, pady=6, sticky="w")
        self.resource_var = tk.StringVar(value="TCPIP0::192.168.0.10::inst0::INSTR")
        ttk.Entry(frm, textvariable=self.resource_var, width=40).grid(
            row=0, column=1, padx=4, pady=6, sticky="we")
        self.sim_var = tk.BooleanVar(value=True)
        self.sim_chk = ttk.Checkbutton(frm, variable=self.sim_var)
        self.sim_chk.grid(row=0, column=2, padx=4)
        self.connect_btn = ttk.Button(frm, command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=4)

        # 語言選單
        self.lang_label = ttk.Label(frm)
        self.lang_label.grid(row=0, column=4, padx=(12, 2))
        self.lang_var = tk.StringVar(value=i18n.LANG_LABELS[i18n.get_lang()])
        self.lang_combo = ttk.Combobox(
            frm, textvariable=self.lang_var, state="readonly", width=10,
            values=[i18n.LANG_LABELS[c] for c in i18n.LANGS])
        self.lang_combo.grid(row=0, column=5, padx=(0, 4))
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_lang_change())

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(frm, textvariable=self.status_var, foreground="#b00")
        self.status_label.grid(row=1, column=0, columnspan=6, padx=6, pady=(0, 6), sticky="w")
        frm.columnconfigure(1, weight=1)

    # ---------------- Command 區 ---------------- #
    def _build_command_area(self):
        frm = ttk.LabelFrame(self)
        frm.pack(fill="x", padx=10, pady=4)
        self.cmd_frame = frm

        self.group_label = ttk.Label(frm)
        self.group_label.grid(row=0, column=0, padx=4, pady=6, sticky="w")
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(frm, textvariable=self.group_var, state="readonly", width=22)
        self.group_combo.grid(row=0, column=1, padx=4, pady=6, sticky="w")
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self._on_group_change())

        self.command_label = ttk.Label(frm)
        self.command_label.grid(row=1, column=0, padx=4, pady=6, sticky="w")
        self.cmd_var = tk.StringVar(value=LABELS[0])
        self.cmd_combo = ttk.Combobox(frm, textvariable=self.cmd_var, state="readonly",
                                      values=LABELS, width=68)
        self.cmd_combo.grid(row=1, column=1, columnspan=3, padx=4, pady=6, sticky="we")
        self.cmd_combo.bind("<<ComboboxSelected>>", lambda e: self._on_command_change())

        self.syntax_var = tk.StringVar(value="")
        ttk.Label(frm, textvariable=self.syntax_var, foreground="#357",
                  font=("Consolas", 9), wraplength=840, justify="left").grid(
                      row=2, column=1, columnspan=3, padx=4, sticky="w")

        self.param_label = ttk.Label(frm)
        self.param_container = ttk.Frame(frm)
        self.hint_var = tk.StringVar(value="")
        self.hint_label = ttk.Label(frm, textvariable=self.hint_var, foreground="#666")
        self.chlist_label = ttk.Label(frm)
        self.chlist_entry = ttk.Entry(frm, textvariable=self.chlist_var, width=24)

        self.param_label.grid(row=3, column=0, padx=4, pady=6, sticky="w")
        self.param_container.grid(row=3, column=1, columnspan=3, padx=4, pady=6, sticky="we")
        self.chlist_label.grid(row=4, column=0, padx=4, pady=6, sticky="w")
        self.chlist_entry.grid(row=4, column=1, padx=4, pady=6, sticky="w")
        self.hint_label.grid(row=5, column=1, columnspan=3, padx=4, pady=(0, 6), sticky="w")
        frm.columnconfigure(1, weight=1)

    def _group_values(self):
        return [t("all")] + [g for g in GROUP_ORDER if any(c["group"] == g for c in COMMANDS)]

    def _on_group_change(self):
        g = self.group_var.get()
        labels = LABELS if g == t("all") else [_label(c) for c in _SORTED if c["group"] == g]
        self.cmd_combo.config(values=labels)
        if labels:
            self.cmd_var.set(labels[0])
        self._on_command_change()

    def _current_command(self) -> dict:
        return CMD_BY_LABEL[self.cmd_var.get()]

    def _on_command_change(self):
        cmd = self._current_command()
        rw = "RW" if cmd["set"] and cmd["get"] else ("R" if cmd["get"] else "W")
        self.syntax_var.set(f"{cmd['syntax']}   —  [{rw}] {t('manual_p', page=cmd['page'])}")

        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_var.set("")
        self.hint_var.set(cmd.get("hint", ""))

        kind = cmd["kind"]
        if kind == "none":
            self.param_label.config(text=t("no_param_gen"))
            self._param_widget = None
        else:
            self.param_label.config(text=t("param"))
            if kind == "bool":
                self.param_var.set("ON")
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 state="readonly", values=["ON", "OFF"], width=22)
            elif kind == "enum" and cmd["opts"]:
                self.param_var.set(cmd["opts"][0])
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 values=cmd["opts"], width=28)
            elif kind == "numeric":
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 values=cmd.get("suggest") or [], width=28)
            else:
                w = ttk.Entry(self.param_container, textvariable=self.param_var, width=44)
                if not self.hint_var.get():
                    self.hint_var.set(t("raw_hint"))
            w.pack(side="left")
            self._param_widget = w

        if cmd["chlist"]:
            self.chlist_label.grid()
            self.chlist_entry.grid()
        else:
            self.chlist_label.grid_remove()
            self.chlist_entry.grid_remove()
        self._refresh_action_state()

    # ---------------- 按鈕 ---------------- #
    def _build_action_buttons(self):
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=10, pady=4)
        self.write_btn = ttk.Button(frm, command=self._do_write, width=16)
        self.read_btn = ttk.Button(frm, command=self._do_read, width=16)
        self.write_btn.pack(side="left", padx=4)
        self.read_btn.pack(side="left", padx=4)
        self.clear_btn = ttk.Button(frm, command=self._clear_log)
        self.clear_btn.pack(side="right", padx=4)

    # ---------------- 輸出區 ---------------- #
    def _build_output_area(self):
        frm = ttk.LabelFrame(self)
        frm.pack(fill="x", padx=10, pady=4)
        self.result_frame = frm
        self.result_var = tk.StringVar(value="—")
        ttk.Label(frm, textvariable=self.result_var, font=("Consolas", 15, "bold"),
                  foreground="#06c", wraplength=840, justify="left").pack(anchor="w", padx=8, pady=8)
        logfrm = ttk.LabelFrame(self)
        logfrm.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log_frame = logfrm
        self.log = tk.Text(logfrm, height=8, wrap="none", font=("Consolas", 9))
        yscroll = ttk.Scrollbar(logfrm, command=self.log.yview)
        self.log.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

    # ---------------- 語言 ---------------- #
    def _on_lang_change(self):
        for code, label in i18n.LANG_LABELS.items():
            if label == self.lang_var.get():
                i18n.set_lang(code)
                break
        self._retranslate()

    def _retranslate(self):
        self.title(t("panel_title", model=MODEL))
        self.conn_frame.config(text=t("conn_frame"))
        self.visa_label.config(text=t("visa"))
        self.sim_chk.config(text=t("sim"))
        self.connect_btn.config(text=t("disconnect") if self._connected else t("connect"))
        self.lang_label.config(text=t("language"))
        self.cmd_frame.config(text=t("cmd_frame"))
        self.group_label.config(text=t("group"))
        self.command_label.config(text=t("command"))
        self.chlist_label.config(text=t("chlist"))
        self.write_btn.config(text=t("write"))
        self.read_btn.config(text=t("read"))
        self.clear_btn.config(text=t("clear_log"))
        self.result_frame.config(text=t("result_frame"))
        self.log_frame.config(text=t("log_frame"))
        # 群組下拉（保留目前選擇；全部→新的 all 標籤）
        cur = self.group_var.get()
        vals = self._group_values()
        was_all = (cur == "" or cur in (t("all"), "(All)", "（全部）"))
        self.group_combo.config(values=vals)
        self.group_var.set(t("all") if was_all else cur)
        # 狀態列
        if self._connected:
            self.status_var.set(t("connected", idn=self._idn))
            self.status_label.config(foreground="#080")
        else:
            self.status_var.set(t("disconnected"))
            self.status_label.config(foreground="#b00")
        self._on_command_change()

    # ---------------- 連線 ---------------- #
    def _toggle_connection(self):
        if self.daq is not None:
            self._disconnect()
            return
        try:
            self.daq = _make_sim() if self.sim_var.get() else Instrument(self.resource_var.get())
            if self.sim_var.get():
                self._log(t("sim_created", model=MODEL))
            self._idn = self.daq.idn()
            self._connected = True
            self.status_var.set(t("connected", idn=self._idn))
            self.status_label.config(foreground="#080")
            self.connect_btn.config(text=t("disconnect"))
            self._set_controls_enabled(True)
            self._log(f"CONNECT -> {self._idn}")
        except Exception as e:  # noqa: BLE001
            self.daq = None
            messagebox.showerror(t("conn_fail"), str(e))
            self._log(f"CONNECT ERROR: {e}")

    def _disconnect(self):
        try:
            if self.daq:
                self.daq.close()
        finally:
            self.daq = None
            self._connected = False
            self._idn = ""
            self.status_var.set(t("disconnected"))
            self.status_label.config(foreground="#b00")
            self.connect_btn.config(text=t("connect"))
            self._set_controls_enabled(False)
            self._log("DISCONNECT")

    def _set_controls_enabled(self, enabled: bool):
        self._connected = enabled if self.daq is not None else False
        self._refresh_action_state()

    def _refresh_action_state(self):
        enabled = self.daq is not None
        cmd = self._current_command()
        self.write_btn.config(state="normal" if enabled and cmd["set"] else "disabled")
        self.read_btn.config(state="normal" if enabled and cmd["get"] else "disabled")

    # ---------------- Write / Read ---------------- #
    def _coerce_numeric(self, text: str):
        try:
            return float(text)
        except ValueError:
            return text

    def _collect_value(self, cmd):
        if cmd["kind"] == "none":
            return None
        raw = self.param_var.get().strip()
        if raw == "":
            return None
        return self._coerce_numeric(raw) if cmd["kind"] == "numeric" else raw

    def _do_write(self):
        if not self.daq:
            return
        cmd = self._current_command()
        try:
            value = self._collect_value(cmd)
            ch = (self.chlist_var.get().strip() or None) if cmd["chlist"] else None
            if cmd["kind"] != "none" and value is None and not (cmd["chlist"] and ch):
                messagebox.showwarning(t("missing_title"), t("missing_msg"))
                return
            self.daq.set_command(cmd["key"], value, ch_list=ch)
            tag = f" {ch}" if ch else ""
            self._log(f"WRITE {cmd['scpi']}{tag} <- {value if value is not None else ''}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("write_fail"), str(e))
            self._log(f"WRITE ERROR: {e}")

    def _do_read(self):
        if not self.daq:
            return
        cmd = self._current_command()
        try:
            value = self._collect_value(cmd)
            ch = (self.chlist_var.get().strip() or None) if cmd["chlist"] else None
            result = self.daq.query_command(cmd["key"], value, ch_list=ch)
            self.result_var.set(str(result))
            self._log(f"READ  {cmd['scpi']}? -> {result}")
        except Exception as e:  # noqa: BLE001
            self.result_var.set(t("read_error"))
            messagebox.showerror(t("read_fail"), str(e))
            self._log(f"READ ERROR: {e}")

    # ---------------- 紀錄 ---------------- #
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n")
        self.log.see("end")

    def _clear_log(self):
        self.log.delete("1.0", "end")

    def destroy(self):
        if self.daq:
            try:
                self.daq.close()
            except Exception:  # noqa: BLE001
                pass
        super().destroy()


if __name__ == "__main__":
    InstrumentPanel().mainloop()
