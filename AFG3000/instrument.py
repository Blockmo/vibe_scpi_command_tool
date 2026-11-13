# -*- coding: utf-8 -*-
"""
AFG3000 控制引擎（資料表驅動的通用 SCPI 介面）
=============================================

與 ``commands_afg3000.COMMANDS`` 搭配。Tektronix AFG3000 系列把通道放在指令標頭
（如 ``SOURce[1|2]:FREQuency``、``OUTPut[1|2]:STATe``、內部雜訊 ``SOURce<3|4>``）；
資料表以 ``{ch}`` 代表通道，呼叫時以 ``channel=`` 傳入（預設 1）。

需求：pip install pyvisa（以及一個 VISA backend，如 NI-VISA 或 pyvisa-py）
"""
from __future__ import annotations

from typing import Optional, Union

import pyvisa

from commands_afg3000 import COMMANDS, COMMAND_BY_KEY

_SPECIAL = {"MIN", "MINIMUM", "MAX", "MAXIMUM", "INF", "INFINITY",
            "DEF", "DEFAULT", "AUTO", "ONCE"}


class AFG3000:
    """Tektronix AFG3000 系列任意波形／函數信號產生器控制介面。"""

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

    def __enter__(self) -> "AFG3000":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        try:
            self._inst.close()
        finally:
            if self._owns_rm:
                self._rm.close()

    # 低階傳輸
    def write(self, command: str) -> None:
        self._inst.write(command)

    def query(self, command: str) -> str:
        return self._inst.query(command).strip()

    def query_float(self, command: str) -> float:
        return float(self.query(command))

    # IEEE-488.2 常用
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

    # 內部工具
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
    def _parse_bool(resp: str) -> bool:
        return resp.strip() not in ("0", "OFF", "off")

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

    @staticmethod
    def _check_channel(channel: int, allowed) -> int:
        ch = int(channel)
        if ch not in allowed:
            raise ValueError(f"通道 {ch} 不適用，允許：{tuple(allowed)}")
        return ch

    def _command_header(self, entry: dict, channel: int, element: int) -> str:
        """將指令模板的 {ch}/{n} 代入，產生實際 SCPI 標頭。"""
        ch = (self._check_channel(channel, entry["channels"])
              if entry["chan"] else channel)
        return entry["scpi"].format(ch=ch, n=int(element))

    def set_command(self, key: str, value=None, channel: int = 1,
                    element: int = 1) -> None:
        """送出任一條可寫入指令。value 依型態解讀；channel 代入標頭通道 {ch}。"""
        entry = self.command_info(key)
        if not entry["set"]:
            raise ValueError(f"指令 {entry['name']} 不支援寫入（query-only）")
        header = self._command_header(entry, channel, element)
        kind = entry["kind"]
        if kind == "none":
            self.write(header)
        elif value is None:
            raise ValueError(f"指令 {entry['name']} 需要參數值")
        elif kind == "bool":
            self.write(f"{header} {self._bool_token(value)}")
        elif kind == "numeric":
            self.write(f"{header} {self._value_token(value)}")
        else:  # enum / string / raw
            self.write(f"{header} {value}")

    def query_command(self, key: str, channel: int = 1, element: int = 1,
                      arg=None) -> str:
        """送出任一條查詢，回傳字串回應。"""
        entry = self.command_info(key)
        if not entry["get"]:
            raise ValueError(f"指令 {entry['name']} 不支援讀取（set-only）")
        header = self._command_header(entry, channel, element)
        if entry.get("qarg") and arg is not None:
            token = (
                self._value_token(arg) if entry["kind"] == "numeric" else str(arg)
            )
            return self.query(f"{header}? {token}")
        return self.query(f"{header}?")


__all__ = ["AFG3000"]
