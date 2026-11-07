# MSO 5 Series 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Tektronix **5 Series MSO** 混合訊號示波器的 SCPI 指令。
涵蓋程式手冊中**「基礎操作核心」與「量測與分析」兩大範疇共 557 條**指令（ACQuire、HORizontal、
Vertical/CH、TRIGger、ZOOM、Display、CURSor、MATH、Waveform Transfer、MEASurement、SEARch），
資料係與 NotebookLM 對該手冊逐群組問答彙整而得（含頁碼）。

> 本專案目前不含 BUS 串列解碼、POWer 電源分析、Digital、DVM、PLOT、ACTONEVent 等進階/選配群組；
> 需要時可依 `_specs/` + `build_commands.py` 流程再補。

指令唯一權威來源為 `commands_mso5.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`MSO_5SERIES_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 編號模型

MSO 5 Series 把通道/項目的編號放在**指令標頭**（如 `CH<x>:SCAle`、`MEASurement:MEAS<x>:TYPe`、
`MATH:MATH<x>:DEFine`、`SEARCH:SEARCH<x>:...`）。資料表以 **`{n}`** 代表該編號，
呼叫時以 `element=` 傳入（預設 1）；GUI 會對這類指令顯示「Index n / 編號 n」欄位。

> 注意：`MEAS<x>`、`MATH<x>`、`B<x>`、`SEARCH<x>` 等是**動態物件**，需先送
> `MEASurement:ADDNew`、`MATH:ADDNew` 等建立後，對應標頭才會被儀器接受。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / TekVISA
```

## 快速開始

```python
from instrument import MSO5

with MSO5("TCPIP0::192.168.0.10::inst0::INSTR") as scope:
    print(scope.idn())
    scope.set_command("ch_n_scale", 0.5, element=1)        # CH1:SCAle 0.5 (V/div)
    scope.set_command("ch_n_coupling", "DC", element=1)    # CH1:COUPling DC
    scope.set_command("horizontal_scale", 1e-6)            # HORizontal:SCAle 1us/div
    scope.set_command("trigger_a_edge_source", "CH1")      # 觸發源
    scope.write("MEASurement:ADDNew \"MEAS1\"")            # 動態物件需先建立
    scope.set_command("measurement_meas_n_type", "FREQuency", element=1)
    print(scope.query_command("measurement_meas_n_results_currentacq_mean", element=1))
```

### 通用引擎

所有 557 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_mso5.py` 中的鍵（`MSO5.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。
- `element`：代入標頭編號 `{n}`（CH 的 1~8、MEAS/MATH/SEARCH 的 1~）；非編號指令可省略。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

先用「群組」下拉縮小範圍，再選指令；含標頭編號的指令會出現「Index n / 編號 n」輸入框。
右上角「Language」可切換英文/繁中（預設英文）。無實體儀器時勾選「Simulation mode」離線操作。

## 指令涵蓋範圍（依群組）

ACQuire、HORizontal、Vertical/CH、Zoom/Display、TRIGger、CURSor、MATH、Waveform Transfer、
MEASurement、SEARch —— 共 557 條。完整對照見 `MSO_5SERIES_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_mso5.py` | **指令資料表（唯一權威來源，557 條）** |
| `instrument.py` | API 主模組（通用引擎 `MSO5`，標頭編號 `{n}`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換、編號欄位） |
| `i18n.py` | 介面文字翻譯表 |
| `make_mso5_xlsx.py` | 由資料表產生 Excel |
| `MSO_5SERIES_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表（含 emoji 還原、`<x>`→`{n}`） |
| `_specs/` | 與 NotebookLM 協作取得的各群組原始規格 |

> 更新或擴充群組：改/增 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_mso5_xlsx.py`。
