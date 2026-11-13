# -*- coding: utf-8 -*-
"""
AFG31000 控制面板 (Tkinter GUI) — 支援英文 / 繁體中文（預設英文）
================================================================

以下拉式選單選擇 SCPI command（涵蓋手冊完整 187 條指令，依功能群組分類），
面板依指令型態自動彈出參數欄位；右上角「Language」可即時切換英文/繁中介面。

連線列的「Scan」會列出電腦上所有 VISA 資源（GPIB 優先，並附 *IDN? 識別），
由下拉選單選擇後連線；也可直接手動輸入資源字串。
指令區的「Search」可用關鍵字（名稱/SCPI/語法/說明，空白分隔為 AND）篩選指令。

執行：
    python ui.py
    python ui.py --sim      # 開發測試用：模擬模式（介面上不顯示此選項）
"""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import i18n
from i18n import t
from afg31000 import AFG31000
from afg31000_commands import COMMANDS, GROUP_ORDER

MODEL = "AFG31000"
SIM_IDN = "TEKTRONIX,AFG31052,SIM0000,SCPI:99.0 FV:1.0"

_order = {g: i for i, g in enumerate(GROUP_ORDER)}
_SORTED = sorted(COMMANDS, key=lambda c: (_order.get(c["group"], 999), c["page"]))


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


def _make_simulated_afg() -> AFG31000:
    afg = AFG31000.__new__(AFG31000)
    afg._owns_rm = False
    afg._rm = None            # type: ignore[assignment]
    afg._inst = _FakeResource()  # type: ignore[assignment]
    return afg


_make_sim = _make_simulated_afg   # 別名


class InstrumentPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("820x660")
        self.minsize(720, 580)

        self.afg = None
        self.param_var = tk.StringVar()
        self.channel_var = tk.StringVar(value="1")
        self.element_var = tk.StringVar(value="1")
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
        # 資源下拉：Scan 後列出找到的資源，也可手動輸入
        self.resource_var = tk.StringVar(value="GPIB0::9::INSTR")
        self.resource_combo = ttk.Combobox(frm, textvariable=self.resource_var, width=52)
        self.resource_combo.grid(row=0, column=1, padx=4, pady=6, sticky="we")
        self.scan_btn = ttk.Button(frm, command=self._scan_resources)
        self.scan_btn.grid(row=0, column=2, padx=4)
        # 模擬模式：介面上隱藏，僅供開發測試（python ui.py --sim）
        self.sim_var = tk.BooleanVar(value="--sim" in sys.argv)
        self.connect_btn = ttk.Button(frm, command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=4)
        self.lang_label = ttk.Label(frm)
        self.lang_label.grid(row=0, column=4, padx=(12, 2))
        self.lang_var = tk.StringVar(value=i18n.LANG_LABELS[i18n.get_lang()])
        self.lang_combo = ttk.Combobox(frm, textvariable=self.lang_var, state="readonly",
                                       width=10, values=[i18n.LANG_LABELS[c] for c in i18n.LANGS])
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
        self.group_combo = ttk.Combobox(frm, textvariable=self.group_var, state="readonly", width=24)
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
        self.cmd_var = tk.StringVar(value=LABELS[0])
        self.cmd_combo = ttk.Combobox(frm, textvariable=self.cmd_var, state="readonly",
                                      values=LABELS, width=60)
        self.cmd_combo.grid(row=1, column=1, columnspan=3, padx=4, pady=6, sticky="we")
        self.cmd_combo.bind("<<ComboboxSelected>>", lambda e: self._on_command_change())

        self.syntax_var = tk.StringVar(value="")
        ttk.Label(frm, textvariable=self.syntax_var, foreground="#357",
                  font=("Consolas", 9), wraplength=780, justify="left").grid(
                      row=2, column=1, columnspan=3, padx=4, sticky="w")

        self.channel_label = ttk.Label(frm)
        self.channel_combo = ttk.Combobox(frm, textvariable=self.channel_var, state="readonly",
                                          values=["1", "2"], width=5)
        self.element_label = ttk.Label(frm)
        self.element_spin = ttk.Spinbox(frm, from_=1, to=256, width=6, textvariable=self.element_var)

        self.param_label = ttk.Label(frm)
        self.param_container = ttk.Frame(frm)
        self.hint_var = tk.StringVar(value="")
        self.hint_label = ttk.Label(frm, textvariable=self.hint_var, foreground="#666")

        self.channel_label.grid(row=3, column=0, padx=4, pady=6, sticky="w")
        self.channel_combo.grid(row=3, column=1, padx=4, pady=6, sticky="w")
        self.element_label.grid(row=3, column=2, padx=4, pady=6, sticky="e")
        self.element_spin.grid(row=3, column=3, padx=4, pady=6, sticky="w")
        self.param_label.grid(row=4, column=0, padx=4, pady=6, sticky="w")
        self.param_container.grid(row=4, column=1, columnspan=3, padx=4, pady=6, sticky="we")
        self.hint_label.grid(row=5, column=1, columnspan=3, padx=4, pady=(0, 6), sticky="w")
        frm.columnconfigure(1, weight=1)

    def _group_values(self):
        return [t("all")] + [g for g in GROUP_ORDER if any(c["group"] == g for c in COMMANDS)]

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
        cmds = [c for c in _SORTED
                if (g in ("", t("all")) or c["group"] == g) and self._matches(c, words)]
        labels = [_label(c) for c in cmds]
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
        return CMD_BY_LABEL[self.cmd_var.get()]

    def _on_command_change(self):
        cmd = self._current_command()
        rw = "RW" if cmd["set"] and cmd["get"] else ("R" if cmd["get"] else "W")
        self.syntax_var.set(f"{cmd['syntax']}   —  [{rw}] {t('manual_p', page=cmd['page'])}")

        if cmd["chan"]:
            self.channel_label.grid()
            self.channel_combo.grid()
            self.channel_combo.config(values=[str(x) for x in cmd["channels"]])
            if self.channel_var.get() not in [str(x) for x in cmd["channels"]]:
                self.channel_var.set(str(cmd["channels"][0]))
        else:
            self.channel_label.grid_remove()
            self.channel_combo.grid_remove()

        if cmd["elem"]:
            self.element_label.grid()
            self.element_spin.grid()
        else:
            self.element_label.grid_remove()
            self.element_spin.grid_remove()

        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_var.set("")
        self.hint_var.set("")

        kind = cmd["kind"]
        if kind == "none":
            self.param_label.config(text=t("no_param"))
            self._param_widget = None
        else:
            self.param_label.config(text=t("param"))
            if kind == "bool":
                self.param_var.set("ON")
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 state="readonly", values=["ON", "OFF"], width=20)
            elif kind == "enum":
                opts = cmd["opts"] or []
                if opts:
                    self.param_var.set(opts[0])
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 state="readonly", values=opts, width=24)
            elif kind == "numeric":
                w = ttk.Combobox(self.param_container, textvariable=self.param_var,
                                 values=cmd.get("suggest") or [], width=24)
                self.hint_var.set(cmd.get("hint", ""))
            else:
                w = ttk.Entry(self.param_container, textvariable=self.param_var, width=40)
                self.hint_var.set(cmd.get("hint", "") or t("raw_hint"))
            w.pack(side="left")
            self._param_widget = w
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
        ttk.Label(frm, textvariable=self.result_var, font=("Consolas", 16, "bold"),
                  foreground="#06c", wraplength=780, justify="left").pack(anchor="w", padx=8, pady=8)
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
        self.scan_btn.config(text=t("scan"))
        self.connect_btn.config(text=t("disconnect") if self._connected else t("connect"))
        self.lang_label.config(text=t("language"))
        self.cmd_frame.config(text=t("cmd_frame"))
        self.group_label.config(text=t("group"))
        self.search_label.config(text=t("search"))
        self.command_label.config(text=t("command"))
        self.channel_label.config(text=t("channel"))
        self.element_label.config(text=t("seq_elem"))
        self.write_btn.config(text=t("write"))
        self.read_btn.config(text=t("read"))
        self.clear_btn.config(text=t("clear_log"))
        self.result_frame.config(text=t("result_frame"))
        self.log_frame.config(text=t("log_frame"))
        cur = self.group_var.get()
        was_all = (cur == "" or cur in (t("all"), "(All)", "（全部）"))
        self.group_combo.config(values=self._group_values())
        self.group_var.set(t("all") if was_all else cur)
        if self._connected:
            self.status_var.set(t("connected", idn=self._idn))
            self.status_label.config(foreground="#080")
        else:
            self.status_var.set(t("disconnected"))
            self.status_label.config(foreground="#b00")
        self._apply_filter()
        self._on_command_change()

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
        if error is not None:
            self._restore_status()
            messagebox.showerror(t("scan_fail"), str(error))
            self._log(f"SCAN ERROR: {error}")
            return
        self.resource_combo.config(values=items)
        self._restore_status()          # 狀態列恢復顯示連線狀態，不顯示掃描結果提示
        if items:
            self.resource_var.set(items[0])
            self.resource_combo.event_generate("<Button-1>")   # 自動展開下拉
        self._log("SCAN -> " + (", ".join(items) if items else "(none)"))

    def _restore_status(self):
        if self._connected:
            self.status_var.set(t("connected", idn=self._idn))
            self.status_label.config(foreground="#080")
        else:
            self.status_var.set(t("disconnected"))
            self.status_label.config(foreground="#b00")

    def _resource_name(self) -> str:
        """下拉項目為「資源字串 + IDN」，連線時只取資源字串。"""
        return self.resource_var.get().strip().split()[0] if self.resource_var.get().strip() else ""

    # ---------------- 連線 ---------------- #
    def _toggle_connection(self):
        if self.afg is not None:
            self._disconnect()
            return
        try:
            self.afg = _make_sim() if self.sim_var.get() else AFG31000(self._resource_name())
            if self.sim_var.get():
                self._log(t("sim_created", model=MODEL))
            self._idn = self.afg.idn()
            self._connected = True
            self.status_var.set(t("connected", idn=self._idn))
            self.status_label.config(foreground="#080")
            self.connect_btn.config(text=t("disconnect"))
            self._set_controls_enabled(True)
            self._log(f"CONNECT -> {self._idn}")
        except Exception as e:  # noqa: BLE001
            self.afg = None
            messagebox.showerror(t("conn_fail"), str(e))
            self._log(f"CONNECT ERROR: {e}")

    def _disconnect(self):
        try:
            if self.afg:
                self.afg.close()
        finally:
            self.afg = None
            self._connected = False
            self._idn = ""
            self.status_var.set(t("disconnected"))
            self.status_label.config(foreground="#b00")
            self.connect_btn.config(text=t("connect"))
            self._set_controls_enabled(False)
            self._log("DISCONNECT")

    def _set_controls_enabled(self, enabled: bool):
        self._refresh_action_state()

    def _refresh_action_state(self):
        enabled = self.afg is not None
        cmd = self._current_command()
        self.write_btn.config(state="normal" if enabled and cmd["set"] else "disabled")
        self.read_btn.config(state="normal" if enabled and cmd["get"] else "disabled")

    # ---------------- Write / Read ---------------- #
    def _pos_kwargs(self, cmd):
        kw = {}
        if cmd["chan"]:
            kw["channel"] = int(self.channel_var.get())
        if cmd["elem"]:
            kw["element"] = int(self.element_var.get())
        return kw

    def _pos_tag(self, cmd, kw):
        bits = []
        if cmd["chan"]:
            bits.append(f"CH{kw['channel']}")
        if cmd["elem"]:
            bits.append(f"ELEM{kw['element']}")
        return (" " + " ".join(bits)) if bits else ""

    def _coerce_numeric(self, text: str):
        try:
            return float(text)
        except ValueError:
            return text

    def _do_write(self):
        if not self.afg:
            return
        cmd = self._current_command()
        try:
            kw = self._pos_kwargs(cmd)
            if cmd["kind"] == "none":
                self.afg.set_command(cmd["key"], **kw)
                shown = ""
            else:
                raw = self.param_var.get().strip()
                if raw == "":
                    messagebox.showwarning(t("missing_title"), t("missing_msg"))
                    return
                value = self._coerce_numeric(raw) if cmd["kind"] == "numeric" else raw
                self.afg.set_command(cmd["key"], value, **kw)
                shown = raw
            self._log(f"WRITE {cmd['name']}{self._pos_tag(cmd, kw)} <- {shown}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("write_fail"), str(e))
            self._log(f"WRITE ERROR: {e}")

    def _do_read(self):
        if not self.afg:
            return
        cmd = self._current_command()
        try:
            kw = self._pos_kwargs(cmd)
            if cmd.get("qarg"):
                arg = self.param_var.get().strip() or None
                result = self.afg.query_command(cmd["key"], arg=arg, **kw)
            else:
                result = self.afg.query_command(cmd["key"], **kw)
            self.result_var.set(str(result))
            self._log(f"READ  {cmd['name']}{self._pos_tag(cmd, kw)} -> {result}")
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
        if self.afg:
            try:
                self.afg.close()
            except Exception:  # noqa: BLE001
                pass
        super().destroy()


if __name__ == "__main__":
    InstrumentPanel().mainloop()
