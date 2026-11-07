# -*- coding: utf-8 -*-
"""
AFG31000 控制 API
=================

以 PyVISA 封裝 Tektronix AFG31000 系列任意函數信號產生器的 SCPI 指令。
指令對照來源：AFG31000_SCPI_Commands.xlsx

使用範例::

    from afg31000 import AFG31000, Waveform, TriggerSource

    with AFG31000("TCPIP0::192.168.0.10::inst0::INSTR") as afg:
        print(afg.idn())
        afg.set_function(Waveform.SINUSOID, channel=1)
        afg.set_frequency(1e6, channel=1)        # 1 MHz
        afg.set_amplitude(2.0, channel=1)        # 2 Vpp
        afg.set_output(True, channel=1)

需求：pip install pyvisa（以及一個 VISA backend，如 NI-VISA 或 pyvisa-py）
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Union

import pyvisa

from afg31000_commands import COMMANDS, COMMAND_BY_KEY


# --------------------------------------------------------------------------- #
# 列舉型別：對應 SCPI 指令允許的參數集合
# --------------------------------------------------------------------------- #
class Waveform(str, Enum):
    """[SOURce[1|2]]:FUNCtion[:SHAPe] 可用的波形形狀。"""
    SINUSOID = "SINusoid"
    SQUARE = "SQUare"
    PULSE = "PULSe"
    RAMP = "RAMP"
    PRNOISE = "PRNoise"
    DC = "DC"
    SINC = "SINC"
    GAUSSIAN = "GAUSsian"
    LORENTZ = "LORentz"
    ERISE = "ERISe"
    EDECAY = "EDECay"
    HAVERSINE = "HAVersine"
    EMEMORY1 = "EMEMory1"
    EMEMORY2 = "EMEMory2"
    EFILE = "EFILe"


class TriggerSource(str, Enum):
    """TRIGger[:SEQuence]:SOURce 可用的觸發來源。"""
    TIMER = "TIMer"       # 內部時脈
    EXTERNAL = "EXTernal"  # 外部觸發輸入


class Language(str, Enum):
    """SYSTem:ULANguage 可用的介面語言。"""
    ENGLISH = "ENGLish"
    FRENCH = "FRENch"
    GERMAN = "GERMan"
    JAPANESE = "JAPanese"
    KOREAN = "KORean"
    SIMPLIFIED_CHINESE = "SCHinese"
    TRADITIONAL_CHINESE = "TCHinese"
    RUSSIAN = "RUSSian"


# 數值型參數可接受的特殊關鍵字
_SPECIAL = {"MIN", "MINIMUM", "MAX", "MAXIMUM", "INF", "INFINITY", "DEF", "DEFAULT"}


class AFG31000:
    """Tektronix AFG31000 系列信號產生器控制介面。

    參數
    ----
    resource:
        VISA 資源字串，例如:
        * USB:   ``"USB0::0x0699::0x035E::C000000::INSTR"``
        * LAN:   ``"TCPIP0::192.168.0.10::inst0::INSTR"``
        * GPIB:  ``"GPIB0::11::INSTR"``
    timeout_ms:
        I/O 逾時（毫秒），預設 5000。
    resource_manager:
        自訂的 ``pyvisa.ResourceManager``；省略時自動建立
        （可用 ``AFG31000(..., visa_library="@py")`` 透過 pyvisa-py backend）。
    """

    # 機台通道數（AFG31000 系列為雙通道）
    N_CHANNELS = 2

    def __init__(
        self,
        resource: str,
        timeout_ms: int = 5000,
        resource_manager: Optional[pyvisa.ResourceManager] = None,
        visa_library: str = "",
    ) -> None:
        self._owns_rm = resource_manager is None
        self._rm = resource_manager or pyvisa.ResourceManager(visa_library)
        # 以 MessageBasedResource 開啟（USB/TCPIP/GPIB 皆屬此類）
        self._inst: pyvisa.resources.MessageBasedResource = (
            self._rm.open_resource(resource)
        )  # type: ignore[assignment]
        self._inst.timeout = timeout_ms
        # SCPI 以換行結尾
        self._inst.write_termination = "\n"
        self._inst.read_termination = "\n"

    # ------------------------------------------------------------------ #
    # context manager 支援
    # ------------------------------------------------------------------ #
    def __enter__(self) -> "AFG31000":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """關閉儀器連線並釋放資源。"""
        try:
            self._inst.close()
        finally:
            if self._owns_rm:
                self._rm.close()

    # ------------------------------------------------------------------ #
    # 低階傳輸
    # ------------------------------------------------------------------ #
    def write(self, command: str) -> None:
        """傳送一個不需回應的 SCPI 指令。"""
        self._inst.write(command)

    def query(self, command: str) -> str:
        """傳送查詢並回傳去除空白的字串回應。"""
        return self._inst.query(command).strip()

    def query_float(self, command: str) -> float:
        return float(self.query(command))

    # ------------------------------------------------------------------ #
    # 內部工具
    # ------------------------------------------------------------------ #
    def _check_channel(self, channel: int, allowed=None) -> int:
        allowed = tuple(allowed) if allowed else tuple(range(1, self.N_CHANNELS + 1))
        if channel not in allowed:
            raise ValueError(
                f"channel 必須為 {allowed}，收到 {channel!r}"
            )
        return channel

    @staticmethod
    def _value_token(value: Union[float, int, str]) -> str:
        """將數值或 MIN/MAX/INF 等關鍵字轉為 SCPI 參數字串。"""
        if isinstance(value, str):
            if value.strip().upper() in _SPECIAL:
                return value.strip().upper()
            return value  # 已帶單位的字串，如 "1.5KHZ"
        return repr(float(value))

    @staticmethod
    def _bool_token(state: Union[bool, int, str]) -> str:
        if isinstance(state, str):
            s = state.strip().upper()
            if s in ("ON", "OFF"):
                return s
            if s in ("1", "0"):
                return s
            raise ValueError(f"無效的開關值: {state!r}")
        if isinstance(state, bool):
            return "ON" if state else "OFF"
        return "ON" if int(state) != 0 else "OFF"

    @staticmethod
    def _parse_bool(resp: str) -> bool:
        return resp.strip() not in ("0", "OFF", "off")

    # ================================================================== #
    # 通用指令引擎（由 afg31000_commands.COMMANDS 資料表驅動）
    #   涵蓋手冊完整 187 條指令，無需為每條手刻方法。
    # ================================================================== #
    @staticmethod
    def list_commands():
        """回傳完整指令資料表（list of dict）。"""
        return COMMANDS

    @staticmethod
    def command_info(key: str) -> dict:
        """依 key 取得單條指令的定義（格式/參數/頁碼…）。"""
        try:
            return COMMAND_BY_KEY[key]
        except KeyError:
            raise KeyError(f"未知的指令 key: {key!r}") from None

    def _command_header(self, entry: dict, channel: int, element: int) -> str:
        """將指令模板的 {ch}/{n} 代入，產生實際 SCPI 標頭。"""
        ch = (
            self._check_channel(channel, entry["channels"])
            if entry["chan"] else channel
        )
        return entry["scpi"].format(ch=ch, n=int(element))

    def set_command(
        self, key: str, value=None, channel: int = 1, element: int = 1
    ) -> None:
        """依資料表送出任一條可寫入指令。

        value 依該指令的 ``kind`` 解讀：
          none    -> 忽略（僅送出指令本身，如 *RST）
          bool    -> ON/OFF/1/0/True/False
          numeric -> 數值、帶單位字串、或 MIN/MAX/INF
          enum    -> 選項字串（如 "SINusoid"）
          string  -> 原樣送出（必要時自行加引號）
          raw     -> 多參數指令，value 為完整引數字串（如 "CH1,CH2"）
        """
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

    def query_command(
        self, key: str, channel: int = 1, element: int = 1, arg=None
    ) -> str:
        """依資料表送出任一條可讀取指令的查詢，回傳字串回應。

        少數查詢需帶參數（qarg=True，如 ``MEMory:STATe:VALid? 1``），以 ``arg`` 傳入。
        """
        entry = self.command_info(key)
        if not entry["get"]:
            raise ValueError(f"指令 {entry['name']} 不支援讀取（set-only）")
        header = self._command_header(entry, channel, element)
        if entry["qarg"] and arg is not None:
            token = (
                self._value_token(arg) if entry["kind"] == "numeric" else str(arg)
            )
            return self.query(f"{header}? {token}")
        return self.query(f"{header}?")

    # ================================================================== #
    # IEEE-488.2 通用指令
    # ================================================================== #
    def idn(self) -> str:
        """``*IDN?`` — 查詢儀器識別字串。"""
        return self.query("*IDN?")

    def reset(self) -> None:
        """``*RST`` — 重置為原廠預設狀態。"""
        self.write("*RST")

    def clear_status(self) -> None:
        """``*CLS`` — 清除狀態與錯誤佇列。"""
        self.write("*CLS")

    def wait(self) -> None:
        """``*OPC?`` — 等待先前所有操作完成。"""
        self.query("*OPC?")

    def error(self) -> str:
        """``SYSTem:ERRor?`` — 讀取錯誤佇列中的下一筆錯誤。"""
        return self.query("SYSTem:ERRor?")

    # ================================================================== #
    # OUTPut[1|2][:STATe]  — 輸出啟用狀態（手冊 p.61）
    # ================================================================== #
    def set_output(self, state: Union[bool, int, str], channel: int = 1) -> None:
        """設定指定通道的 AFG 輸出啟用狀態。"""
        ch = self._check_channel(channel)
        self.write(f"OUTPut{ch}:STATe {self._bool_token(state)}")

    def get_output(self, channel: int = 1) -> bool:
        """查詢指定通道的輸出是否啟用。"""
        ch = self._check_channel(channel)
        return self._parse_bool(self.query(f"OUTPut{ch}:STATe?"))

    # ================================================================== #
    # OUTPut[1|2]:IMPedance — 輸出負載阻抗（手冊 p.59）
    # ================================================================== #
    def set_output_impedance(
        self, ohms: Union[float, str], channel: int = 1
    ) -> None:
        """設定輸出負載阻抗（1 Ω~10 kΩ，或 INFinity/MINimum/MAXimum）。"""
        ch = self._check_channel(channel)
        self.write(f"OUTPut{ch}:IMPedance {self._value_token(ohms)}")

    def get_output_impedance(self, channel: int = 1) -> float:
        """查詢輸出負載阻抗（Ω）。"""
        ch = self._check_channel(channel)
        return self.query_float(f"OUTPut{ch}:IMPedance?")

    # ================================================================== #
    # DISPlay:BRIGhtness — LCD 螢幕亮度（手冊 p.32）
    # ================================================================== #
    def set_brightness(self, brightness: Union[float, str]) -> None:
        """設定 LCD 顯示亮度（0.00~1.00，或 MINimum/MAXimum）。"""
        self.write(f"DISPlay:BRIGhtness {self._value_token(brightness)}")

    def get_brightness(self) -> float:
        """查詢 LCD 顯示亮度。"""
        return self.query_float("DISPlay:BRIGhtness?")

    # ================================================================== #
    # [SOURce[1|2]]:FREQuency[:CW|:FIXed] — 輸出頻率（手冊 p.108）
    # ================================================================== #
    def set_frequency(
        self, frequency: Union[float, str], channel: int = 1
    ) -> None:
        """設定輸出波形頻率（Hz 數值，或帶單位字串/MINimum/MAXimum）。"""
        ch = self._check_channel(channel)
        self.write(f"SOURce{ch}:FREQuency:FIXed {self._value_token(frequency)}")

    def get_frequency(self, channel: int = 1) -> float:
        """查詢輸出波形頻率（Hz）。"""
        ch = self._check_channel(channel)
        return self.query_float(f"SOURce{ch}:FREQuency:FIXed?")

    # ================================================================== #
    # [SOURce[1|2]]:VOLTage[...]:AMPLitude — 輸出振幅（手冊 p.149）
    # ================================================================== #
    def set_amplitude(
        self, amplitude: Union[float, str], channel: int = 1
    ) -> None:
        """設定波形輸出振幅（數值預設 Vpp，或帶單位字串/MINimum/MAXimum）。"""
        ch = self._check_channel(channel)
        self.write(
            f"SOURce{ch}:VOLTage:LEVel:IMMediate:AMPLitude "
            f"{self._value_token(amplitude)}"
        )

    def get_amplitude(self, channel: int = 1) -> float:
        """查詢波形輸出振幅。"""
        ch = self._check_channel(channel)
        return self.query_float(
            f"SOURce{ch}:VOLTage:LEVel:IMMediate:AMPLitude?"
        )

    # ================================================================== #
    # [SOURce[1|2]]:FUNCtion[:SHAPe] — 波形形狀（手冊 p.119）
    # ================================================================== #
    def set_function(
        self, waveform: Union[Waveform, str], channel: int = 1
    ) -> None:
        """設定輸出波形形狀（見 :class:`Waveform`）。"""
        ch = self._check_channel(channel)
        shape = waveform.value if isinstance(waveform, Waveform) else str(waveform)
        self.write(f"SOURce{ch}:FUNCtion:SHAPe {shape}")

    def get_function(self, channel: int = 1) -> str:
        """查詢輸出波形形狀。"""
        ch = self._check_channel(channel)
        return self.query(f"SOURce{ch}:FUNCtion:SHAPe?")

    # ================================================================== #
    # SYSTem:BEEPer:STATe — 蜂鳴器開關（手冊 p.159）
    # ================================================================== #
    def set_beeper(self, state: Union[bool, int, str]) -> None:
        """設定儀器嗶聲蜂鳴器開關狀態。"""
        self.write(f"SYSTem:BEEPer:STATe {self._bool_token(state)}")

    def get_beeper(self) -> bool:
        """查詢蜂鳴器開關狀態。"""
        return self._parse_bool(self.query("SYSTem:BEEPer:STATe?"))

    # ================================================================== #
    # TRIGger[:SEQuence]:SOURce — 觸發來源（手冊 p.169）
    # ================================================================== #
    def set_trigger_source(self, source: Union[TriggerSource, str]) -> None:
        """設定觸發訊號來源（TIMer 內部 / EXTernal 外部）。"""
        src = source.value if isinstance(source, TriggerSource) else str(source)
        self.write(f"TRIGger:SEQuence:SOURce {src}")

    def get_trigger_source(self) -> str:
        """查詢觸發訊號來源。"""
        return self.query("TRIGger:SEQuence:SOURce?")

    # ================================================================== #
    # INSTaview[1|2]:STATe — InstaView 功能（手冊 p.39）
    # ================================================================== #
    def set_instaview(self, state: Union[bool, int, str], channel: int = 1) -> None:
        """設定指定通道的 InstaView 功能狀態。"""
        ch = self._check_channel(channel)
        self.write(f"INSTaview{ch}:STATe {self._bool_token(state)}")

    def get_instaview(self, channel: int = 1) -> bool:
        """查詢指定通道的 InstaView 功能狀態。"""
        ch = self._check_channel(channel)
        return self._parse_bool(self.query(f"INSTaview{ch}:STATe?"))

    # ================================================================== #
    # SYSTem:ULANguage — 介面語言（手冊 p.166）
    # ================================================================== #
    def set_language(self, language: Union[Language, str]) -> None:
        """設定儀器螢幕顯示的語言（見 :class:`Language`）。"""
        lang = language.value if isinstance(language, Language) else str(language)
        self.write(f"SYSTem:ULANguage {lang}")

    def get_language(self) -> str:
        """查詢儀器螢幕顯示的語言。"""
        return self.query("SYSTem:ULANguage?")


__all__ = ["AFG31000", "Waveform", "TriggerSource", "Language"]
