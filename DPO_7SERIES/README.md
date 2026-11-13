# DPO 7 Series 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Tektronix **DPO7000 系列**數位螢光示波器的 SCPI 指令。
涵蓋程式手冊中**「基礎操作核心」與「量測與分析」兩大範疇共 482 條**指令（ACQuire、HORizontal、
Vertical/CH、TRIGger、ZOOM、Display、CURSor、MATH、Waveform Transfer、MEASurement、SEARch/MARK），
資料係與 NotebookLM 對該手冊逐群組問答彙整而得（含頁碼）。

> 本專案目前不含 BUS 串列解碼、HISTogram/PLOT、ACTONEVent、SAVe/RECall、FILESystem、STATus/SYSTem、
> DIAg 等群組；需要時可依 `_specs/` + `build_commands.py` 流程再補。

指令唯一權威來源為 `commands_dpo7.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`DPO_7SERIES_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 編號模型

DPO7000 把通道/項目編號放在**指令標頭**（`CH<x>:SCAle`、`MEASurement:MEAS<x>:...`、`MATH<x>`、
`SEARCH:SEARCH<x>:...`）。資料表以 **`{n}`** 代表該編號，呼叫時以 `element=` 傳入（預設 1）；
GUI 對這類指令顯示「Index n / 編號 n」欄位。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / TekVISA
```

## 快速開始

```python
from instrument import DPO7

with DPO7("TCPIP0::192.168.0.10::inst0::INSTR") as scope:
    print(scope.idn())
    scope.set_command("ch_n_scale", 0.5, element=1)        # CH1:SCAle 0.5
    scope.set_command("horizontal_scale", 1e-6)            # HORizontal:SCAle 1us/div
    scope.set_command("measurement_meas_n_type", "FREQuency", element=1)
    print(scope.query_command("measurement_meas_n_value", element=1))
```

### 通用引擎

所有 482 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_dpo7.py` 中的鍵（`DPO7.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。
- `element`：代入標頭編號 `{n}`（CH 的 1~4、MEAS/MATH/SEARCH 的 1~）；非編號指令可省略。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

先用「群組」下拉縮小範圍，再選指令；含標頭編號的指令會出現「Index n / 編號 n」輸入框。
右上角「Language」可切換英文/繁中（預設英文）。連線列「Scan」可列出 VISA 資源（GPIB 優先、附 `*IDN?`）供下拉選擇；指令區「Search」可用關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。

## 指令涵蓋範圍（依群組）

ACQuire、HORizontal、Vertical/CH、Zoom/Display、TRIGger、CURSor、MATH、Waveform Transfer、
MEASurement、SEARch —— 共 482 條。完整對照見 `DPO_7SERIES_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_dpo7.py` | **指令資料表（唯一權威來源，482 條）** |
| `instrument.py` | API 主模組（通用引擎 `DPO7`，標頭編號 `{n}`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換、編號欄位） |
| `i18n.py` | 介面文字翻譯表 |
| `make_dpo7_xlsx.py` | 由資料表產生 Excel |
| `DPO_7SERIES_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表（含 emoji 還原、`<x>`→`{n}`） |
| `_specs/` | 與 NotebookLM 協作取得的各群組原始規格 |

> 更新或擴充群組：改/增 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_dpo7_xlsx.py`。
