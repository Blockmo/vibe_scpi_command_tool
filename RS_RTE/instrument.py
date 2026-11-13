# -*- coding: utf-8 -*-
"""
R&S RTE 控制引擎（資料表驅動的通用 SCPI 介面）
====================================================

與 ``commands_rte.COMMANDS`` 搭配。R&S RTE 把通道/項目編號以數值後綴放在指令標頭
（如 ``CHANnel<m>:SCALe``、``MEASurement<m>:MAIN``、``CALCulate:MATH<m>``、
``TRIGger<m>:LEVel<n>``）；資料表以 ``{n}`` 代表該編號，呼叫時以 ``element=`` 傳入
（預設 1）。``TRIGger<m>:...LEVel<n>`` 類以來源通道 ``<n>`` 為編號、``TRIGger1``（A 事件）。

多參數指令（如 SEARch 系列 ``<SearchName>, <State>``）型態為 raw，值以逗號分隔整串傳入；
其查詢會自動只帶前導參數（``qn`` 欄位，例 ``SEARch:TRIGger:EDGE:STATe? MySearch``）。

需求：pip install pyvisa（以及一個 VISA backend，如 NI-VISA 或 pyvisa-py）
"""
from __future__ import annotations

from typing import Optional, Union

import pyvisa

from commands_rte import COMMANDS, COMMAND_BY_KEY

_SPECIAL = {"MIN", "MINIMUM", "MAX", "MAXIMUM", "INF", "INFINITY",
            "DEF", "DEFAULT", "AUTO", "ONCE"}


class RTE:
    """Rohde & Schwarz RTE 示波器控制介面。"""

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

    def __enter__(self) -> "RTE":
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

    def _command_header(self, entry: dict, element: int) -> str:
        """將指令模板的 {n} 代入編號（element），產生實際 SCPI 標頭。"""
        if entry.get("elem"):
            return entry["scpi"].format(n=int(element))
        return entry["scpi"]

    def set_command(self, key: str, value=None, channel: int = 1,
                    element: int = 1) -> None:
        """送出任一條可寫入指令。value 依型態解讀；element 代入標頭編號 {n}。
        （channel 參數為與其他儀器介面相容而保留，RTE 不使用。）"""
        entry = self.command_info(key)
        if not entry["set"]:
            raise ValueError(f"指令 {entry['name']} 不支援寫入（query-only）")
        header = self._command_header(entry, element)
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
        header = self._command_header(entry, element)
        if entry.get("qarg") and arg is not None:
            qn = entry.get("qn") or 0
            if qn and isinstance(arg, str):
                # 多參數指令：查詢只帶前導參數（如 SEARch:...:STATe? <SearchName>）；
                # 允許直接傳入寫入用的完整字串 "MySearch, ON"
                parts = [p.strip() for p in arg.split(",")]
                arg = ", ".join(parts[:qn]) if len(parts) > qn else arg
            token = (
                self._value_token(arg) if entry["kind"] == "numeric" else str(arg)
            )
            return self.query(f"{header}? {token}")
        return self.query(f"{header}?")


__all__ = ["RTE"]
