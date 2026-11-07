# SCPI 儀器控制套件

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝九台量測儀器的 SCPI 指令。每一台都是**獨立且資料驅動**的子專案（一份指令資料表同時驅動 API、Excel 對照表與圖形面板），指令資料皆係與 NotebookLM 對各自原廠手冊逐子系統問答彙整而得（含頁碼）。

## 共用啟動器

```bash
python launcher.py
```

一個視窗列出九台儀器，點選即以子行程開啟該台的控制面板（各台自成資料夾、獨立執行，互不干擾）。無實體儀器時，各面板勾選「Simulation mode」即可離線操作測試。

**語言**：啟動器與九台面板的介面皆支援 **英文 / 繁體中文**，**預設英文**，右上角「Language」下拉可即時切換（翻譯表為各資料夾內的 `i18n.py`；指令名稱/語法/頁碼為手冊資料，不翻譯）。

## 九台儀器

| 儀器 | 類型 | 指令數 | 資料夾 | 通道模型 |
|------|------|:---:|------|------|
| **AFG31000** | 任意函數信號產生器 (Tektronix) | 187 | `AFG31000/` | `SOURce{1\|2}` 標頭索引 |
| **DAQ973A** | 資料擷取/開關量測系統 (Keysight) | 421 | `DAQ973A/` | `(@通道清單)` 參數 |
| **34970 / 34972A** | 資料擷取/開關單元 (Keysight/Agilent) | 179 | `34970/` | `(@通道清單)` 參數 |
| **Chroma 63600** | 直流電子負載 (Chroma) | 212 | `Chroma_63600/` | `CHANnel <n>` 作用中通道 |
| **E36300** | 三輸出直流電源供應器 (Keysight) | 101 | `E36300/` | `(@1:3)` 通道清單 |
| **2231A-30-3** | 三通道直流電源供應器 (Keithley) | 76 | `2231A-30-3/` | `INST:SEL` 作用中通道 |
| **E3633A** | 單輸出直流電源供應器 (Agilent/Keysight) | 59 | `E3633A/` | 單輸出、無通道（`VOLT:RANGe` 檔位） |
| **MSO 5 Series** | 混合訊號示波器 (Tektronix) | 557 | `MSO_5SERIES/` | 標頭編號 `CH{n}`/`MEAS{n}`/`MATH{n}` |
| **DPO 7 Series** | 數位螢光示波器 (Tektronix) | 482 | `DPO_7SERIES/` | 標頭編號 `CH{n}`/`MEAS{n}`/`MATH{n}` |

合計 **2274 條** SCPI 指令。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或安裝 NI-VISA / Keysight IO Libraries
```

啟動器與 GUI 僅需 Python 內建 tkinter；連實體儀器時各台需 pyvisa。

## 各子專案的共同結構

| 檔案 | 用途 |
|------|------|
| `*_commands.py`（AFG 為 `afg31000_commands.py`） | **指令資料表（唯一權威來源）** |
| `instrument.py`（AFG 為 `afg31000.py`） | API 主模組：通用引擎 `set_command()` / `query_command()` |
| `ui.py` | Tkinter 圖形控制面板（群組下拉、依型態自動產生參數欄位、模擬模式、SCPI 流量紀錄、英文/繁中切換） |
| `i18n.py` | 介面文字翻譯表（英文 / 繁體中文，預設英文） |
| `make_*_xlsx.py` | 由資料表產生 Excel 對照表 |
| `*_SCPI_Commands.xlsx` | 指令對照表（分群組、含頁碼、可篩選） |
| `README.md` | 該台專屬說明與程式範例 |
| `build_commands.py` + `_specs/` | 由 NotebookLM 協作規格自動產生資料表的可重現管線（DAQ973A / 34970 / Chroma 有） |

> AFG31000 是最早建立的專案，直接手寫資料表（無 `build_commands.py`/`_specs/`）；其餘三台因指令量大，改以 `_specs/` + `build_commands.py` 自動產生。

## 程式化使用（範例）

```python
# 以 DAQ973A 為例（在 DAQ973A/ 資料夾內或將其加入 sys.path）
from instrument import DAQ973A

with DAQ973A("TCPIP0::192.168.0.10::inst0::INSTR") as daq:
    print(daq.idn())
    daq.set_command("configure_voltage_dc", "10", ch_list="101:105")
    daq.set_command("route_scan", ch_list="101:105")
    print(daq.query_command("read"))
```

各台的鍵名與用法詳見其資料夾內的 `README.md`。

## 維護

要更新某台的指令：修改該台 `_specs/*.txt`（或 AFG 的 `afg31000_commands.py`），重跑
`python build_commands.py`，再跑 `python make_*_xlsx.py` 重新產生 Excel。
