# 34970/34970A 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Keysight/Agilent **34970A/34972A** 資料擷取/開關量測單元的 SCPI 指令。
涵蓋使用與程式手冊**完整 179 條**指令，資料係與 NotebookLM 對該手冊逐子系統問答彙整而得（含每條頁碼）。

指令唯一權威來源為 `commands_34970.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`34970_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或安裝 NI-VISA / Keysight IO Libraries
```

## 快速開始

```python
from instrument import K34970

with K34970("GPIB0::9::INSTR") as daq:
    print(daq.idn())
    daq.set_command("configure_voltage_dc", "10", ch_list="101:110")  # 設定量測功能
    daq.set_command("route_scan", ch_list="101:110")                  # 掃描清單
    print(daq.query_command("read"))                                   # 觸發並讀回
    print(daq.query_command("measure_voltage_dc", "10", ch_list="101"))  # 單通道即時量測
```

### 通用引擎

所有 179 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_34970.py` 中的鍵（`K34970.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數；多參數傳完整字串如 `"10,0.001"`。
- `ch_list`：通道清單，傳 `"101"`、`"101:110"`、`"101,103"`，自動組成 `(@...)` 附加（查詢亦支援）。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

用「群組」下拉縮小範圍後選指令；面板依型態自動彈出參數欄位，需要通道的指令出現「通道清單 (@)」欄（填如 `101:110`）。
無實體儀器時勾選「模擬模式」離線操作。Write/Read 按鈕依指令讀寫屬性自動啟用。

## 指令涵蓋範圍（依群組）

通用/流程、CONFigure/MEASure、ROUTe、SENSe、CALCulate/CAL、TRIGger、System/Display/Unit、
FORMat/DATA/DIAG、Memory/Source/Output/Status —— 共 179 條。完整對照見 `34970_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_34970.py` | **指令資料表（唯一權威來源，179 條）** |
| `instrument.py` | API 主模組（通用引擎 `K34970`） |
| `ui.py` | Tkinter 圖形控制面板 |
| `make_34970_xlsx.py` | 由資料表產生 Excel |
| `34970_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表的工具（可重跑） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格 |

> 更新指令：改 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_34970_xlsx.py`。
