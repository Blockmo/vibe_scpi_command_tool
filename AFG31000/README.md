# AFG31000 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Tektronix **AFG31000** 系列任意函數信號產生器的 SCPI 指令。
涵蓋 AFG31000 Series Programmer Manual（Sept 2019）**完整 187 條**指令，資料係與 NotebookLM 對該手冊逐條問答彙整而得（含每條手冊頁碼）。

指令的唯一權威來源為 `afg31000_commands.py` 中的 `COMMANDS` 資料表，一份表同時驅動：
API（`afg31000.py`）、指令對照 Excel（`AFG31000_SCPI_Commands.xlsx`）、與圖形面板（`ui.py`）。

## 安裝

```bash
pip install pyvisa
# 擇一 VISA backend：
#   NI-VISA（Windows 常用，需另裝驅動）  或
pip install pyvisa-py        # 純 Python backend
```

## 快速開始

```python
from afg31000 import AFG31000, Waveform, TriggerSource

with AFG31000("TCPIP0::192.168.0.10::inst0::INSTR") as afg:
    print(afg.idn())
    afg.set_function(Waveform.SINUSOID, channel=1)
    afg.set_frequency(1e6, channel=1)   # 1 MHz
    afg.set_amplitude(2.0, channel=1)   # 2 Vpp
    afg.set_output(True, channel=1)
```

VISA 資源字串範例：

| 介面 | 範例 |
|------|------|
| LAN  | `TCPIP0::192.168.0.10::inst0::INSTR` |
| USB  | `USB0::0x0699::0x035E::C000000::INSTR` |
| GPIB | `GPIB0::11::INSTR` |

用 `example.py` 內的 `list_instruments()` 可列出目前可連線的資源。

## API 使用方式

### 1. 通用指令引擎（涵蓋全部 187 條）

所有指令都能用資料表驅動的 `set_command()` / `query_command()` 送出，不必記方法名：

```python
from afg31000 import AFG31000

with AFG31000("TCPIP0::192.168.0.10::inst0::INSTR") as afg:
    afg.set_command("output_state", "ON", channel=1)        # OUTPut1:STATe ON
    afg.set_command("frequency", 1e6, channel=1)            # SOURce1:FREQuency:FIXed 1e6
    afg.set_command("function", "SQUare", channel=1)        # 波形形狀
    print(afg.query_command("amplitude", channel=1))        # 讀回振幅
    afg.set_command("seq_goto_index", 10, element=5)        # 含序列元素 n 的指令
    print(afg.query_command("mem_valid", arg=1))            # 需帶引數的查詢
```

`key` 即 `afg31000_commands.py` 資料表中的鍵；`value` 依該指令型態（bool/numeric/enum/string/raw）
自動轉成 SCPI 參數。需要通道的指令傳 `channel=`（雜訊源為 3/4），序列元素類傳 `element=`。
查詢全集與單條定義：`AFG31000.list_commands()`、`AFG31000.command_info("frequency")`。

### 2. 常用便利方法（具型別，向後相容）

常用指令另有具名方法，參數可用 `Waveform` / `TriggerSource` / `Language` 列舉：

| 方法 | SCPI 指令 | 手冊頁 |
|------|-----------|:---:|
| `set_output` / `get_output` | `OUTPut[1|2][:STATe]` | 61 |
| `set_output_impedance` / `get_output_impedance` | `OUTPut[1|2]:IMPedance` | 59 |
| `set_brightness` / `get_brightness` | `DISPlay:BRIGhtness` | 32 |
| `set_frequency` / `get_frequency` | `[SOURce[1|2]]:FREQuency[:CW|:FIXed]` | 108 |
| `set_amplitude` / `get_amplitude` | `[SOURce[1|2]]:VOLTage[...]:AMPLitude` | 149 |
| `set_function` / `get_function` | `[SOURce[1|2]]:FUNCtion[:SHAPe]` | 119 |
| `set_beeper` / `get_beeper` | `SYSTem:BEEPer:STATe` | 159 |
| `set_trigger_source` / `get_trigger_source` | `TRIGger[:SEQuence]:SOURce` | 169 |
| `set_instaview` / `get_instaview` | `INSTaview[1|2]:STATe` | 39 |
| `set_language` / `get_language` | `SYSTem:ULANguage` | 166 |

另含 IEEE-488.2 通用指令：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，
以及低階 `write()` / `query()` / `query_float()` 可直接送任意 SCPI。

### 指令涵蓋範圍（依群組）

通用/狀態、Display、Output、Source（Reference / Frequency / Function / Phase / Voltage /
Pulse / Burst / Sweep / AM / FM / PM / PWM / FSK / Combine / Mode / Noise）、Trigger、Sync、
Cal/Diag、AFG Control、Screen Copy、Memory、Mass Memory、System、InstaView、Trace、License、
Sequence Control、Sequence、Waveform List —— 共 187 條。完整對照見 `AFG31000_SCPI_Commands.xlsx`。

## 參數說明

- **通道**：所有通道相關方法的 `channel` 參數為 `1` 或 `2`（AFG31000 為雙通道）。
- **開關值**：接受 `True/False`、`1/0`、或 `"ON"/"OFF"`。
- **數值參數**：
  - 直接給數字（SI 基本單位，如頻率用 Hz、振幅用 Vpp）：`set_frequency(1e6)`。
  - 或給帶單位字串：`set_frequency("1.5kHz")`。
  - 或給關鍵字：`"MIN"` / `"MAX"` / `"INF"`（阻抗適用）。
- **列舉型別**：
  - `Waveform`：SINUSOID / SQUARE / PULSE / RAMP / PRNOISE / DC / SINC / GAUSSIAN /
    LORENTZ / ERISE / EDECAY / HAVERSINE / EMEMORY1 / EMEMORY2 / EFILE
  - `TriggerSource`：TIMER（內部時脈）/ EXTERNAL（外部觸發）
  - `Language`：ENGLISH / FRENCH / GERMAN / JAPANESE / KOREAN /
    SIMPLIFIED_CHINESE / TRADITIONAL_CHINESE / RUSSIAN

## 圖形介面 (GUI)

```bash
python ui.py
```

操作流程：

1. **連線**：輸入 VISA 資源字串後按「連線」。沒有實體儀器時，勾選「**模擬模式**」即可離線操作測試整個介面。
2. **選指令**：先用「群組」下拉縮小範圍（或選「全部」），再用「Command」下拉選擇 187 條中的任一條；
   下方會顯示該指令的完整格式與手冊頁碼。面板依指令型態自動彈出對應欄位：
   - 開關類 → `ON`/`OFF` 下拉
   - 列舉類 → 選項下拉
   - 數值類 → 可直接輸入數值，下拉另提供 `MIN`/`MAX`/`INF` 等建議值
   - 字串/多參數（raw）類 → 文字輸入（多參數請輸入完整引數字串，如 `CH1,CH2`）
   - 需要通道的指令出現「通道」下拉（雜訊源為 3/4）；序列元素類出現「序列元素 n」
3. **Write 寫入 / Read 讀取**：按鈕會依該指令是否支援寫入/讀取自動啟用或停用。
4. 讀取結果顯示於大字區；下方「紀錄 / SCPI 流量」逐筆記錄每次動作與結果。

## 檔案

| 檔案 | 用途 |
|------|------|
| `afg31000_commands.py` | **指令資料表（唯一權威來源，187 條）** |
| `afg31000.py` | API 主模組（通用引擎 + 便利方法） |
| `ui.py`       | Tkinter 圖形控制面板（資料表驅動） |
| `make_afg31000_xlsx.py` | 由資料表產生 Excel 對照表 |
| `example.py`  | 程式化使用範例 |
| `AFG31000_SCPI_Commands.xlsx` | 指令對照表（由資料表產生） |
