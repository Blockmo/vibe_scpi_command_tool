# DAQ973A 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Keysight **DAQ973A** 資料擷取/開關量測系統的 SCPI 指令。
涵蓋程式設計手冊**完整 421 條**指令（含主機與 **DAQM909A 數位化模組**的 `*3` 子系統），
資料係與 NotebookLM 對該手冊逐子系統問答彙整而得（含每條頁碼）。

指令唯一權威來源為 `daq973a_commands.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`DAQ973A_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或安裝 NI-VISA / Keysight IO Libraries
```

## 快速開始

```python
from instrument import DAQ973A

with DAQ973A("TCPIP0::192.168.0.10::inst0::INSTR") as daq:
    print(daq.idn())
    # 設定 101~105 通道為直流電壓量測、範圍 10 V
    daq.set_command("configure_voltage_dc", "10", ch_list="101:105")
    daq.set_command("route_scan", ch_list="101:105")       # 設定掃描清單
    print(daq.query_command("read"))                        # 觸發並讀回掃描結果
    # 單通道即時量測
    print(daq.query_command("measure_voltage_dc", "10", ch_list="101"))
```

### 通用引擎

所有 421 條指令都用資料表驅動的 `set_command()` / `query_command()`：

- `key`：`daq973a_commands.py` 資料表中的鍵（亦可 `DAQ973A.list_commands()` / `command_info(key)` 查詢）。
- `value`：依該指令型態（bool / numeric / enum / string / raw）自動轉成 SCPI 參數；多參數指令（kind=raw）直接傳完整字串如 `"10,0.001"`。
- `ch_list`：DAQ973A 的通道清單參數，傳 `"101"`、`"101:105"`、`"101,103,110"`，會自動組成 `(@...)` 附加於指令後（查詢形式亦支援）。
- 讀取（`query_command`）只在該指令的查詢語法接受參數時才帶 `value`（資料表 `qarg`）：僅查詢指令（如 `MEASure:...? <range>`）照原樣帶；讀寫兩用指令只帶 MIN/MAX/DEF 等查詢關鍵字（`qopts`），一般寫入值（如 `ON`、`5`）不會被送成 `XXX? ON`。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，
以及低階 `write()` / `query()` / `query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

1. **連線**：按「Scan」列出 VISA 資源（GPIB 優先、附 `*IDN?`）由下拉選擇，或手動輸入資源字串，再按「連線」。指令區可用「Search」關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。
2. **選指令**：先用「群組」縮小範圍，再選 421 條中的任一條；下方顯示完整格式、讀寫屬性與頁碼。
   面板依型態自動彈出參數欄位；需要通道的指令會出現「通道清單 (@)」輸入欄（填如 `101:105`）。
3. **Write / Read**：按鈕依指令是否支援寫入/讀取自動啟用；結果顯示於大字區，下方記錄 SCPI 流量。

## 指令涵蓋範圍（依群組）

通用/流程、CONFigure、ROUTe、Sample/Trigger/Output、SENSe、CALCulate、Cal/Source/Unit、
Format/Display/HCopy/LXI、DATA、MMEMory、STATus、SYSTem、FETCh、MEASure，以及 DAQM909A
數位化模組的 Digitizer(`*3`) 子系統 —— 共 421 條。完整對照見 `DAQ973A_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `daq973a_commands.py` | **指令資料表（唯一權威來源，421 條）** |
| `instrument.py` | API 主模組（通用引擎 `DAQ973A`） |
| `ui.py` | Tkinter 圖形控制面板（資料表驅動） |
| `make_daq973a_xlsx.py` | 由資料表產生 Excel |
| `DAQ973A_SCPI_Commands.xlsx` | 指令對照表（由資料表產生） |
| `build_commands.py` | 由 `_specs/` 解析產生資料表的工具（可重跑） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格（資料來源佐證） |

> 若要更新指令：修改/補充 `_specs/*.txt` 後，重跑 `python build_commands.py` 再跑 `python make_daq973a_xlsx.py`。
