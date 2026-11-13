# AFG3000 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 Tektronix **AFG3000 系列**（AFG3000 / AFG3000B / AFG3000C）任意波形／函數信號產生器的 SCPI 指令。
涵蓋程式手冊**全部 13 個指令群組，共 144 條**，資料係與 NotebookLM（筆記本 `[ATE][AFG] AFG3000`）對該手冊逐群組問答彙整而得（含頁碼）。

指令唯一權威來源為 `commands_afg3000.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`AFG3000_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 通道模型

AFG3000 把通道放在**指令標頭**，資料表以 **`{ch}`** 代表，呼叫時以 `channel=` 傳入（預設 1）：

| 手冊寫法 | 資料表 | 可用通道 |
|----------|--------|----------|
| `[SOURce[1\|2]]:FREQuency`、`OUTPut[1\|2][:STATe]` | `SOURce{ch}:FREQuency`、`OUTPut{ch}:STATe` | 1, 2 |
| `SOURce<3\|4>:POWer[:LEVel]...`（內部雜訊疊加） | `SOURce{ch}:POWer:LEVel:IMMediate:AMPLitude` | 3（疊加於 CH1）, 4（疊加於 CH2） |

其餘可省略段（如 `[:LEVel][:IMMediate]`）以完整長格式送出；`[:CW|:FIXed]` 這類二選一的可省略段直接省略；`TRACe|DATA` 取 `TRACe`。
不符合的通道會被拒絕（例如對 `OUTPut{ch}` 傳 `channel=3` 會丟 `ValueError`）。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA / TekVISA
```

## 快速開始

```python
from instrument import AFG3000

with AFG3000("USB0::0x0699::0x0346::C000000::INSTR") as afg:
    print(afg.idn())
    afg.set_command("source_ch_function_shape", "SQUare", channel=1)        # SOURce1:FUNCtion:SHAPe SQUare
    afg.set_command("source_ch_frequency", 1e3, channel=1)                  # SOURce1:FREQuency 1000.0
    afg.set_command("source_ch_voltage_level_immediate_amplitude", 2, channel=1)
    afg.set_command("output_ch_state", "ON", channel=1)                     # OUTPut1:STATe ON
    afg.set_command("source_ch_power_level_immediate_amplitude", 10, channel=3)  # CH1 疊加 10% 雜訊
    print(afg.query_command("source_ch_frequency", channel=1))
```

### 通用引擎

所有 144 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_afg3000.py` 中的鍵（`AFG3000.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數；numeric 可用 `MIN`/`MAX`/`INF`。
- `channel`：代入標頭通道 `{ch}`；非通道指令可省略。
- `arg`（查詢）：需要查詢引數的指令（如 `MEMory:STATe:VALid? 0`、`TRACe:POINts? EMEMory1`、`DISPlay:BRIGHtness? MAX`）。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

先用「群組」下拉縮小範圍，再選指令；含通道的指令會出現「Channel / 通道」下拉（1/2，雜訊指令為 3/4）。
右上角「Language」可切換英文/繁中（預設英文）。連線列「Scan」可列出 VISA 資源（GPIB 優先、附 `*IDN?`）供下拉選擇；指令區「Search」可用關鍵字篩選指令。模擬模式已自介面隱藏，開發測試請用 `python ui.py --sim`。

## 指令涵蓋範圍（依群組）

| 群組 | 內容 | 條數 |
|------|------|------|
| Common/Status | IEEE-488.2 通用、STATus、`*OPC`/`*WAI`、CALibration/DIAGnostic | 25 |
| SYSTem | 蜂鳴器、按鍵鎖、密碼、語言、錯誤佇列、版本 | 12 |
| Display/Output/Trigger | DISPlay、OUTPut、TRIGger/ABORt、AFGControl:CSCopy、HCOPy | 17 |
| Memory/MMEMory | 面板設定記憶體 0~4、USB 檔案操作 | 13 |
| TRACe/DATA | 編輯記憶體 EMEMory / 使用者波形 USER1~4 | 10 |
| Source | FREQuency、FUNCtion、VOLTage、PHASe、PULSe、ROSCillator、雜訊、COMBine | 25 |
| Modulation | AM、FM、PM、FSKey、PWM | 28 |
| Sweep/Burst | SWEep、BURSt、FREQuency 掃描參數 | 14 |

完整對照見 `AFG3000_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_afg3000.py` | **指令資料表（唯一權威來源，144 條；由 build_commands.py 產生，勿手改）** |
| `instrument.py` | API 主模組（通用引擎 `AFG3000`，標頭通道 `{ch}`） |
| `ui.py` | Tkinter 圖形控制面板（英文/繁中切換、通道欄位） |
| `i18n.py` | 介面文字翻譯表 |
| `make_afg3000_xlsx.py` | 由資料表產生 Excel |
| `AFG3000_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表（`[1\|2]`/`<3\|4>`→`{ch}`、型態推斷） |
| `_specs/` | 與 NotebookLM 協作取得的各群組原始規格（`_fmt.txt` 為提問格式） |
| `_ask.sh`、`_ask2.sh` | 向 NotebookLM 抓取 `_specs/` 的批次腳本 |

> 更新：改/增 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_afg3000_xlsx.py`；
> C# All-In-One 需再跑 `All-In-One_csharp/tools/export_commands.py` 並重新建置。
