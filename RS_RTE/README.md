# R&S RTE 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Rohde & Schwarz **RTE 系列**數位示波器
（RTE1022 / 1024 / 1032 / 1034 / 1052 / 1054 / 1102 / 1104 / 1152 / 1154 / 1202 / 1204）的 SCPI 指令。
涵蓋使用手冊第 17 章中**「基礎操作核心」與「量測與分析」兩大範疇共 552 條**指令，
資料係與 NotebookLM 對該手冊逐群組問答彙整而得（含頁碼）。

> 本專案目前不含 Protocols（BUS 串列解碼/觸發）、MSO 數位通道 (B1)、波形產生器 (B6)、Power 分析 (K31)、
> Spectrum (K18)、MASK、MMEMory/EXPort/REPort、SYSTem/HCOPy/FORMat 一般設定、STATus/DIAG/CAL/TRACe 等群組；
> 需要時可依 `_specs/` + `build_commands.py` 流程再補。

指令唯一權威來源為 `commands_rte.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`RS_RTE_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 編號模型

RTE 把通道/項目編號以**數值後綴**放在指令標頭（`CHANnel<m>:SCALe`、`MEASurement<m>:MAIN`、
`CALCulate:MATH<m>`、`CURSor<m>`、`PROBe<m>`、`REFCurve<m>`）。資料表以 **`{n}`** 代表該編號，
呼叫時以 `element=` 傳入（預設 1）；GUI 對這類指令顯示「Index n / 編號 n」欄位。

- 可省略且含後綴的節點（如 `[:WAVeform<n>]`）一律省略＝預設 1。
- 其他可省略關鍵字（如 `[:STATe]`、`[:VALue]`）保留展開寫全（寫全一定合法，也避免不同指令撞名）。
- `TRIGger<m>:…:LEVel<n>` 類：`{n}` 代入**來源通道** `LEVel<n>`，觸發事件固定 `TRIGger1`（A 事件）。

## 多參數指令（SEARch 等）

部分指令有多個參數，最常見的是 SEARch 系列 `SEARch:TRIGger:EDGE[:STATe] <SearchName>, <State>`。
這類指令型態為 `raw`，值以逗號分隔整串輸入（如 `MySearch, ON`）；查詢時自動只帶前導參數
（資料表欄位 `qn`），即 `SEARch:TRIGger:EDGE:STATe? MySearch`。GUI 中寫入與讀取共用同一個參數欄，
直接填 `MySearch, ON` 即可兩者皆正確。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / R&S VISA
```

## 快速開始

```python
from instrument import RTE

with RTE("TCPIP0::192.168.0.10::inst0::INSTR") as scope:
    print(scope.idn())
    scope.set_command("channel_n_scale", 0.5, element=1)          # CHANnel1:SCALe 0.5
    scope.set_command("timebase_scale", 1e-6)                      # TIMebase:SCALe 1us/div
    scope.set_command("trigger1_level_n_value", 0.2, element=1)    # TRIGger1:LEVel1:VALue 0.2
    scope.set_command("measurement_n_main", "FREQuency", element=1)
    scope.set_command("measurement_n_enable", True, element=1)
    print(scope.query_command("measurement_n_result_actual", element=1))

    scope.set_command("search_add", "'MySearch'")                  # SEARch:ADD 'MySearch'
    scope.set_command("search_trigger_edge_state", "'MySearch', ON")
    print(scope.query_command("search_rcount", arg="'MySearch'"))  # SEARch:RCOunt? 'MySearch'
```

### 通用引擎

所有 552 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_rte.py` 中的鍵（`RTE.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。
- `element`：代入標頭編號 `{n}`（CHANnel/PROBe 的 1~4、MEASurement 的 1~8、MATH/CURSor 等）；非編號指令可省略。
- `arg`：查詢引數（`qarg` 指令，如 `SEARch:RCOunt? <SearchName>`、`CHANnel<m>:DATA:VALues? [<Start>, <Stop>]`）。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

先用「群組」下拉縮小範圍，再選指令；含標頭編號的指令會出現「Index n / 編號 n」輸入框。
右上角「Language」可切換英文/繁中（預設英文）。連線列「Scan」可列出 VISA 資源（GPIB 優先、附 `*IDN?`）供下拉選擇；指令區「Search」可用關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。

## 指令涵蓋範圍（依群組）

| 群組 | 指令數 | 群組 | 指令數 |
|------|:---:|------|:---:|
| Common/Run（*IEEE、RUN/SINGle/STOP、AUToscale） | 22 | ZOOM/REFCurve | 33 |
| TIMebase/ACQuire | 26 | MATH（CALCulate:MATH、FFT） | 40 |
| CHANnel（含 HDEFinition、波形資料） | 18 | History | 11 |
| PROBe | 45 | CURSor | 38 |
| TRIGger | 87 | MEASurement | 85 |
| DISPlay/LAYout | 33 | SEARch | 114 |

共 552 條。完整對照見 `RS_RTE_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_rte.py` | **指令資料表（唯一權威來源，552 條）** |
| `instrument.py` | API 主模組（通用引擎 `RTE`，標頭編號 `{n}`、多參數查詢 `qn`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換、編號欄位） |
| `i18n.py` | 介面文字翻譯表 |
| `make_rte_xlsx.py` | 由資料表產生 Excel |
| `RS_RTE_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表（emoji 還原、`<m>`→`{n}`、多參數判斷） |
| `_specs/` | 與 NotebookLM 協作取得的各群組原始規格（`_ask.sh` 為擷取腳本） |

> 更新或擴充群組：改/增 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_rte_xlsx.py`；
> 若要同步 C# 版 All-In-One，再跑 `../All-In-One_csharp/tools/export_commands.py` 並重新建置。
