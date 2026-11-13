# 2231A-30-3 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Keithley **2231A-30-3** 三通道直流電源供應器的 SCPI 指令。
涵蓋程式手冊**完整 76 條**指令，資料係與 NotebookLM 對該手冊逐子系統問答彙整而得（含每條頁碼）。

指令唯一權威來源為 `commands_2231a.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`2231A-30-3_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 通道模型

2231A-30-3 採用**「作用中通道」**模型：先用 `INSTrument[:SELect] {CH1|CH2|CH3}`
（或 `INSTrument:NSELect {1|2|3}`）切換作用中通道，之後的 `SOURce`/`MEASure` 等指令即作用於該通道；
**不使用** `(@通道清單)` 語法。（例外：`APPLy` 可一次帶入通道或三通道數值。）

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA
```

## 快速開始

```python
from instrument import K2231A

with K2231A("USB0::0x05E6::0x2231::...::INSTR") as psu:
    print(psu.idn())
    psu.set_command("instrument_select", "CH1")           # 選作用中通道 CH1
    psu.set_command("source_voltage_level_immediate_amplitude", 5.0)   # CH1 = 5V
    psu.set_command("source_current_level_immediate_amplitude", 1.0)   # CH1 限流 1A
    psu.set_command("output_state_all", "ON")             # 開啟輸出
    print(psu.query_command("measure_voltage_dc"))        # 量測作用中通道電壓
```

### 通用引擎

所有 76 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_2231a.py` 中的鍵（`K2231A.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。
- 本機用作用中通道模型，故 `ch_list` 參數一般用不到（保留相容）。
- 讀取（`query_command`）只在該指令的查詢語法接受參數時才帶 `value`（資料表 `qarg`）：僅查詢指令（如 `MEASure:...? <range>`）照原樣帶；讀寫兩用指令只帶 MIN/MAX/DEF 等查詢關鍵字（`qopts`），一般寫入值（如 `ON`、`5`）不會被送成 `XXX? ON`。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

用「群組」下拉縮小範圍後選指令；面板依型態自動彈出參數欄位（開關/列舉/數值/字串）。
右上角「Language」可切換英文/繁中（預設英文）。連線列「Scan」可列出 VISA 資源（GPIB 優先、附 `*IDN?`）供下拉選擇；指令區「Search」可用關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。

## 指令涵蓋範圍（依群組）

通用/APPLy/INSTrument、SOURce、Output/Measure、System/Display/Cal、STATus —— 共 76 條。
完整對照見 `2231A-30-3_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_2231a.py` | **指令資料表（唯一權威來源，76 條）** |
| `instrument.py` | API 主模組（通用引擎 `K2231A`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換） |
| `i18n.py` | 介面文字翻譯表 |
| `make_2231a_xlsx.py` | 由資料表產生 Excel |
| `2231A-30-3_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表的工具（可重跑） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格 |

> 更新指令：改 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_2231a_xlsx.py`。
