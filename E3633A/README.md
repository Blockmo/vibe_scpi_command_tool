# E3633A 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Agilent/Keysight **E3633A** 單輸出直流電源供應器的 SCPI 指令。
涵蓋程式手冊**完整 59 條**指令（手冊同時適用 E3633A/E3634A 單輸出雙檔位機型），
資料係與 NotebookLM 對該手冊逐子系統問答彙整而得（含每條頁碼）。

指令唯一權威來源為 `commands_e3633a.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`E3633A_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 通道/檔位模型

E3633A 為**單輸出**，**無通道選擇**（沒有 `INSTrument:SELect`、也沒有 `(@通道清單)`）。
輸出範圍以**檔位切換**：`VOLTage:RANGe P8V`（LOW，8V/20A）或 `VOLTage:RANGe P20V`（HIGH，20V/10A）。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / Keysight IO Libraries
```

## 快速開始

```python
from instrument import E3633A

with E3633A("GPIB0::5::INSTR") as psu:
    print(psu.idn())
    psu.set_command("source_voltage_range", "P20V")                     # 選 20V 檔位
    psu.set_command("source_voltage_level_immediate_amplitude", 12.0)   # 設 12V
    psu.set_command("source_current_level_immediate_amplitude", 2.0)    # 限流 2A
    psu.set_command("output_state", "ON")                               # 開啟輸出
    print(psu.query_command("measure_voltage_dc"))                      # 量測輸出電壓
```

### 通用引擎

所有 59 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_e3633a.py` 中的鍵（`E3633A.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

用「群組」下拉縮小範圍後選指令；面板依型態自動彈出參數欄位（開關/列舉/數值/字串）。
右上角「Language」可切換英文/繁中（預設英文）。無實體儀器時勾選「Simulation mode」離線操作。

## 指令涵蓋範圍（依群組）

通用/System、Source/Measure、Output/Trig/Display/Cal/Status —— 共 59 條。
完整對照見 `E3633A_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_e3633a.py` | **指令資料表（唯一權威來源，59 條）** |
| `instrument.py` | API 主模組（通用引擎 `E3633A`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換） |
| `i18n.py` | 介面文字翻譯表 |
| `make_e3633a_xlsx.py` | 由資料表產生 Excel |
| `E3633A_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表的工具（可重跑） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格 |

> 更新指令：改 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_e3633a_xlsx.py`。
