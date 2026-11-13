# -*- coding: utf-8 -*-
"""
Chroma 63600 控制引擎（資料表驅動的通用 SCPI 介面）
================================================

與 ``daq973a_commands.COMMANDS`` 搭配，涵蓋 Chroma 63600 程式設計手冊的完整指令集。
每條指令以 :meth:`set_command` / :meth:`query_command` 送出，無需為每條手刻方法。

Chroma 63600 的通道以「通道清單」參數表示（例如 ``(@101:120)``），而非指令標頭索引；
因此這些方法額外接受 ``ch_list`` 參數（傳入如 ``"101"``、``"101:105"``、``"101,103,110"``），
會自動組成 ``(@...)`` 附加於指令之後；查詢形式同樣可帶參數與通道清單。

需求：pip install pyvisa（以及一個 VISA backend，如 NI-VISA 或 pyvisa-py）
"""
from __future__ import annotations

from typing import Optional, Union

import pyvisa

from commands_chroma63600 import COMMANDS, COMMAND_BY_KEY

_SPECIAL = {"MIN", "MINIMUM", "MAX", "MAXIMUM", "INF", "INFINITY",
            "DEF", "DEFAULT", "AUTO", "ONCE"}


class Chroma63600:
    """Keysight Chroma 63600 資料擷取/開關量測系統控制介面。"""

    def __init__(
        self,
        resource: str,
        timeout_ms: int = 5000,
        resource_manager: Optional[pyvisa.ResourceManager] = None,
        visa_library: str = "",
    ) -> None:
        self._owns_rm = resource_manager is None
        self._rm = resource_manager or pyvisa.ResourceManager(visa_library)
        self._inst: pyvisa.resources.MessageBasedResource = (
            self._rm.open_resource(resource)
        )  # type: ignore[assignment]
        self._inst.timeout = timeout_ms
        self._inst.write_termination = "\n"
        self._inst.read_termination = "\n"

    def __enter__(self) -> "Chroma63600":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        try:
            self._inst.close()
        finally:
            if self._owns_rm:
                self._rm.close()

    # ------------------------------------------------------------------ #
    # 低階傳輸
    # ------------------------------------------------------------------ #
    def write(self, command: str) -> None:
        self._inst.write(command)

    def query(self, command: str) -> str:
        return self._inst.query(command).strip()

    def query_float(self, command: str) -> float:
        return float(self.query(command))

    # ------------------------------------------------------------------ #
    # IEEE-488.2 常用
    # ------------------------------------------------------------------ #
    def idn(self) -> str:
        return self.query("*IDN?")

    def reset(self) -> None:
        self.write("*RST")

    def clear_status(self) -> None:
        self.write("*CLS")

    def wait(self) -> None:
        self.query("*OPC?")

    def error(self) -> str:
        return self.query("SYSTem:ERRor?")

    # ------------------------------------------------------------------ #
    # 內部工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _value_token(value: Union[float, int, str]) -> str:
        if isinstance(value, str):
            if value.strip().upper() in _SPECIAL:
                return value.strip().upper()
            return value
        if isinstance(value, bool):
            return "ON" if value else "OFF"
        return repr(float(value)) if isinstance(value, float) else str(value)

    @staticmethod
    def _bool_token(state: Union[bool, int, str]) -> str:
        if isinstance(state, str):
            s = state.strip().upper()
            if s in ("ON", "OFF", "1", "0"):
                return s
            raise ValueError(f"無效的開關值: {state!r}")
        if isinstance(state, bool):
            return "ON" if state else "OFF"
        return "ON" if int(state) != 0 else "OFF"

    @staticmethod
    def _ch_token(ch_list) -> str:
        """將 '101'、'101:105'、'101,103' 或 '(@101:105)' 正規化為 '(@101:105)'。"""
        s = str(ch_list).strip()
        if not s:
            return ""
        if s.startswith("(@"):
            return s
        s = s.lstrip("@")
        return f"(@{s})"

    # ================================================================== #
    # 通用指令引擎（由資料表驅動）
    # ================================================================== #
    @staticmethod
    def list_commands():
        return COMMANDS

    @staticmethod
    def command_info(key: str) -> dict:
        try:
            return COMMAND_BY_KEY[key]
        except KeyError:
            raise KeyError(f"未知的指令 key: {key!r}") from None

    def _param_str(self, entry: dict, value, ch_list) -> str:
        """依指令型態組出參數字串（值在前、通道清單在後，以逗號相接）。"""
        parts = []
        kind = entry["kind"]
        if kind != "none" and value not in (None, ""):
            if kind == "bool":
                parts.append(self._bool_token(value))
            elif kind == "numeric":
                parts.append(self._value_token(value))
            else:  # enum / string / raw
                parts.append(str(value))
        if entry.get("chlist") and ch_list not in (None, ""):
            parts.append(self._ch_token(ch_list))
        return ",".join(parts)

    @staticmethod
    def _query_value(entry: dict, value):
        """查詢時要帶的值：只在查詢語法接受參數時才帶（避免把寫入值送成 OUTP? ON）。

        - qarg=False：查詢不帶值（通道清單照帶）。
        - 僅查詢指令（如 MEASure:...? <range>）：值照原樣帶。
        - 讀寫兩用：qsel 指定多參數寫入值中要帶的欄位（如 SLOT:LABel? <slot>）；
          否則只在值為 qopts 關鍵字（如 MIN/MAX/DEF，可長/短寫）時才帶。
        """
        if value in (None, "") or not entry.get("qarg"):
            return None
        if not entry["set"]:
            return value
        if entry.get("qsel"):
            parts = [p.strip() for p in str(value).split(",")]
            if len(parts) <= max(entry["qsel"]):
                return str(value).strip()          # 只填了查詢參數本身
            return ",".join(parts[i] for i in entry["qsel"])
        v = str(value).strip().upper()
        for opt in entry.get("qopts") or ():
            if v in (opt.upper(), "".join(ch for ch in opt if ch.isupper() or ch.isdigit())):
                return v
        return None

    def set_command(self, key: str, value=None, ch_list=None) -> None:
        """送出任一條可寫入指令。value 依型態解讀；ch_list 為通道清單（如 '101:105'）。"""
        entry = self.command_info(key)
        if not entry["set"]:
            raise ValueError(f"指令 {entry['name']} 不支援寫入（query-only）")
        param = self._param_str(entry, value, ch_list)
        self.write(f"{entry['scpi']} {param}".rstrip())

    def query_command(self, key: str, value=None, ch_list=None) -> str:
        """送出任一條查詢（部分查詢可帶參數/通道清單），回傳字串回應。"""
        entry = self.command_info(key)
        if not entry["get"]:
            raise ValueError(f"指令 {entry['name']} 不支援讀取（set-only）")
        param = self._param_str(entry, self._query_value(entry, value), ch_list)
        stem = f"{entry['scpi']}?"
        return self.query(f"{stem} {param}".rstrip())


__all__ = ["Chroma63600"]
