# Chroma 62000P 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Chroma **62000P 系列**可程式直流電源供應器的 SCPI 指令。
涵蓋 *Chroma 62000P Series Operating & Programming Manual* 第 5 章（Remote Operation）**完整 72 條**指令，
資料係與 NotebookLM（筆記本 `[ATE][POWER]Chroma 62000P`）對該手冊逐子系統問答彙整而得（含每條頁碼，格式為「章-頁」如 `5-16`）。

指令唯一權威來源為 `commands_chroma62000p.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`Chroma_62000P_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 通道模型

62000P 為**單輸出**，指令**不需選擇通道**（沒有 `INSTrument:SELect`、也沒有 `(@通道清單)`）。
多台並聯/串聯主從控制以 `CONFigure:MSTSLV:*` 指令設定。

手冊特色：
- 輸出開關在 `CONFigure:OUTPut ON|OFF`（沒有獨立的 `OUTPut` 子系統）
- 狀態查詢為 `FETCh:STATus?`（沒有獨立的 `STATus` 子系統）
- 序列輸出在 `PROGram` 子系統（LIST / STEP 模式）

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / Keysight IO Libraries
```

## 快速開始

```python
from instrument import Chroma62000P

with Chroma62000P("TCPIP0::192.168.0.20::inst0::INSTR") as psu:
    print(psu.idn())
    psu.set_command("source_voltage", 12)              # SOURce:VOLTage 12
    psu.set_command("source_current", 2)               # SOURce:CURRent 2
    psu.set_command("source_voltage_protect_high", 15) # OVP 15V
    psu.set_command("configure_output", "ON")          # CONFigure:OUTPut ON
    print(psu.query_command("measure_voltage"))        # MEASure:VOLTage?
    print(psu.query_command("fetch_status"))           # FETCh:STATus?
```

### PROGram 序列（LIST 模式）範例

```python
psu.set_command("program_selected", 1)                       # 編輯 Program 1
psu.set_command("program_mode", "LIST")
psu.set_command("program_sequence_selected", 1)              # 第 1 個 Sequence
psu.set_command("program_sequence", "AUTO,10,1,2,1,0,1")     # Type,V,V_SR,I,I_SR,TTL,Time
psu.set_command("program_save")
psu.set_command("program_run", "ON")
```

### 通用引擎

所有 72 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_chroma62000p.py` 中的鍵（`Chroma62000P.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。
- 讀取（`query_command`）只在該指令的查詢語法接受參數時才帶 `value`（資料表 `qarg`）：僅查詢指令（如 `MEASure:...? <range>`）照原樣帶；讀寫兩用指令只帶 MIN/MAX/DEF 等查詢關鍵字（`qopts`），一般寫入值（如 `ON`、`5`）不會被送成 `XXX? ON`。

## 圖形介面 (GUI)

```bash
python ui.py
```

連線列「Scan」可列出 VISA 資源（GPIB 優先、附 `*IDN?`）供下拉選擇；指令區「Search」可用關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。

也已整合進 `../All-In-One/all_in_one.py` 的 **Power Supply** 分類。

## 指令涵蓋範圍（依群組）

| 群組 | 指令數 | 手冊頁碼 |
|------|:---:|------|
| Common（IEEE 488.2） | 10 | 5-7 ～ 5-9 |
| ABORt | 1 | 5-11 |
| SYSTem | 1 | 5-25 |
| CONFigure | 17 | 5-11 ～ 5-15 |
| SOURce | 14 | 5-15 ～ 5-17 |
| FETCh/MEASure | 7 | 5-19 ～ 5-20 |
| PROGram | 22 | 5-20 ～ 5-25 |

完整對照見 `Chroma_62000P_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_chroma62000p.py` | **指令資料表（唯一權威來源，72 條）** |
| `instrument.py` | API 主模組（通用引擎 `Chroma62000P`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換） |
| `i18n.py` | 介面文字翻譯表 |
| `make_chroma62000p_xlsx.py` | 由資料表產生 Excel |
| `Chroma_62000P_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表的工具（可重跑） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格 |

> 更新指令：改 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_chroma62000p_xlsx.py`。
