# Keithley Series 2400 SourceMeter 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Keithley **Series 2400 SourceMeter**（2400 / 2401 / 2410 / 2420 / 2425 / 2430 / 2440 等）
的 SCPI 指令。涵蓋使用手冊**第 16 章（IEEE-488.2 通用）、第 17 章（Signal Oriented 量測）、第 18 章（SCPI 子系統）完整共 255 條**指令，
資料係與 NotebookLM 對該手冊逐子系統問答彙整而得（含頁碼「章-頁」）。

指令唯一權威來源為 `commands_2400.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`Series2400_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 指令形式

2400 為單通道 SMU，指令不需選擇通道。資料表採 Keithley 慣用的**短形式**：

- 可省略的節點一律省略：`:SOURce[1]:VOLTage[:LEVel][:IMMediate][:AMPLitude]` → `SOURce:VOLTage`、
  `:OUTPut[1][:STATe]` → `OUTPut`、`:ARM[:SEQuence[1]][:LAYer[1]]:COUNt` → `ARM:COUNt`。
- 可省略的根節點 `[:SENSe[1]]` / `[:SOURce[1]]` 保留寫出（`SENSe:CURRent:RANGe`、`SOURce:SWEep:POINts`）。
- `[:LATest]` 保留，以區分 `CALCulate2:DATA?` 與 `CALCulate2:DATA:LATest?`。
- `CONFigure[:<function>]` / `MEASure[:<function>]?` 展開為 `VOLTage` / `CURRent` / `RESistance` 三條＋無功能形式。

### 唯一的標頭編號：`CALCulate2:LIMit{n}`

手冊中 `:CALCulate2:LIMitX:…`（X = 2, 3, 5~12，分級/分類極限測試）以 `{n}` 表示，呼叫時用 `element=` 傳入；
GUI 會出現「Index n / 編號 n」欄位。`LIMit1`（Compliance）與 `LIMit4`（接觸檢查，2400-C）各自為獨立指令。

### 查詢

讀取只送 `標頭?`；唯一帶引數的查詢是 `SENSe:FUNCtion:STATe? <name>`（資料表 `qarg`）。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / Keysight VISA
```

## 快速開始

```python
from instrument import K2400

with K2400("GPIB0::24::INSTR") as smu:
    print(smu.idn())
    smu.reset()
    smu.set_command("source_function", "VOLTage")              # SOURce:FUNCtion VOLTage
    smu.set_command("source_voltage", 5)                       # SOURce:VOLTage 5
    smu.set_command("sense_current_protection", 0.01)          # SENSe:CURRent:PROTection 0.01
    smu.set_command("sense_function", '"CURRent:DC"')          # SENSe:FUNCtion "CURRent:DC"
    smu.set_command("output", True)                            # OUTPut ON
    print(smu.query_command("read"))                           # READ?
    smu.set_command("output", False)

    smu.set_command("calculate2_limit_n_upper", 1e-3, element=2)   # CALCulate2:LIMit2:UPPer 0.001
    print(smu.query_command("sense_function_state", arg='"VOLT"')) # SENSe:FUNCtion:STATe? "VOLT"
```

### 通用引擎

所有 255 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_2400.py` 中的鍵（`K2400.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數；字串參數（如 `DISPlay:TEXT:DATA`）需自帶引號。
- `element`：代入 `CALCulate2:LIMit{n}` 的編號；其他指令可省略。
- `arg`：查詢引數（僅 `SENSe:FUNCtion:STATe?`）。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

先用「群組」下拉縮小範圍，再選指令；`LIMit{n}` 類指令會出現「Index n / 編號 n」輸入框。
右上角「Language」可切換英文/繁中（預設英文）。連線列「Scan」可列出 VISA 資源（GPIB 優先、附 `*IDN?`）供下拉選擇；指令區「Search」可用關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。

## 指令涵蓋範圍（依群組）

| 群組 | 指令數 | 群組 | 指令數 |
|------|:---:|------|:---:|
| Common（*IEEE-488.2） | 14 | CALCulate3（緩衝區統計） | 2 |
| Measure（CONFigure/FETCh/READ/MEASure） | 10 | TRACe（資料緩衝區） | 8 |
| SOURce（輸出、掃描、LIST、記憶體、脈衝） | 53 | TRIGger（INITiate/ABORt/ARM/TRIGger） | 18 |
| SENSe（量測功能、檔位、NPLC、Compliance、平均） | 37 | FORMat | 6 |
| OUTPut/ROUTe | 5 | DISPlay | 11 |
| CALCulate1（數學運算式） | 9 | SOURce2（Digital I/O） | 8 |
| CALCulate2（NULL、極限測試 LIMit1~12、CLIMits） | 28 | STATus | 14 |
|  |  | SYSTem | 32 |

共 255 條。完整對照見 `Series2400_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_2400.py` | **指令資料表（唯一權威來源，255 條）** |
| `instrument.py` | API 主模組（通用引擎 `K2400`，標頭編號 `{n}`、`qarg` 查詢） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換、編號欄位） |
| `i18n.py` | 介面文字翻譯表 |
| `make_2400_xlsx.py` | 由資料表產生 Excel |
| `Series2400_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表（短形式正規化、`LIMitX`→`LIMit{n}`、`<function>` 展開） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格（`_ask.sh` 為擷取腳本） |

> 更新：改/增 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_2400_xlsx.py`；
> 若要同步 C# 版 All-In-One，再跑 `../All-In-One_csharp/tools/export_commands.py` 並重新建置。
