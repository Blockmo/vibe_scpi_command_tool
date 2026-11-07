# -*- coding: utf-8 -*-
"""AFG31000 API 使用範例。

執行前請先將 RESOURCE 改為實際儀器的 VISA 位址。
若無實體儀器，可用 list_instruments() 查看可用資源。
"""
import pyvisa

from afg31000 import AFG31000, Waveform, TriggerSource, Language


RESOURCE = "TCPIP0::192.168.0.10::inst0::INSTR"


def list_instruments():
    """列出目前可連線的 VISA 資源。"""
    rm = pyvisa.ResourceManager()
    print("可用 VISA 資源:")
    for r in rm.list_resources():
        print("  ", r)
    rm.close()


def demo():
    with AFG31000(RESOURCE) as afg:
        # 基本資訊
        print("IDN :", afg.idn())
        afg.reset()

        # 通道 1：1 MHz / 2 Vpp 正弦波
        afg.set_function(Waveform.SINUSOID, channel=1)
        afg.set_frequency(1e6, channel=1)
        afg.set_amplitude(2.0, channel=1)
        afg.set_output_impedance("INFinity", channel=1)  # 高阻抗
        afg.set_output(True, channel=1)

        # 通道 2：方波，頻率設為最大
        afg.set_function(Waveform.SQUARE, channel=2)
        afg.set_frequency("MAX", channel=2)
        afg.set_output(True, channel=2)

        # 系統設定
        afg.set_trigger_source(TriggerSource.TIMER)
        afg.set_language(Language.TRADITIONAL_CHINESE)
        afg.set_brightness(0.8)
        afg.set_beeper(False)

        # 回讀驗證
        print("CH1 波形 :", afg.get_function(1))
        print("CH1 頻率 :", afg.get_frequency(1), "Hz")
        print("CH1 振幅 :", afg.get_amplitude(1), "Vpp")
        print("CH1 輸出 :", afg.get_output(1))
        print("CH2 頻率 :", afg.get_frequency(2), "Hz")
        print("觸發來源 :", afg.get_trigger_source())
        print("錯誤佇列 :", afg.error())


if __name__ == "__main__":
    list_instruments()
    # demo()   # 連線到實體儀器後取消註解
