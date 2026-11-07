# Chroma 63600 控制 API

以 [PyVISA](https://pyvisa.readthedocs.io/) 封裝 **Chroma 63600 系列**直流電子負載的 SCPI 指令。
涵蓋程式手冊**完整 212 條**指令，資料係與 NotebookLM 對該手冊逐子系統問答彙整而得（含每條「章-頁」頁碼）。

指令唯一權威來源為 `commands_chroma63600.py` 的 `COMMANDS` 資料表，一份表同時驅動
API（`instrument.py`）、Excel（`Chroma_63600_SCPI_Commands.xlsx`）與圖形面板（`ui.py`）。

## 通道模型

Chroma 63600 以 **`CHANnel[:LOAD] <n>`**（`CHANnel:ACTive`）設定「作用中通道」，
之後所有通道相關指令都作用於該通道；**不使用** DAQ 那種 `(@通道清單)` 語法。
因此先下 `set_command("channel_load", n)` 選定通道，再操作其他指令即可。

## 安裝

```bash
pip install pyvisa
pip install pyvisa-py        # 或 NI-VISA
```

## 快速開始

```python
from instrument import Chroma63600

with Chroma63600("USB0::0x1698::0x0837::...::INSTR") as load:
    print(load.idn())
    load.set_command("channel_load", 1)          # 選定作用中通道 1
    load.set_command("mode", "CCH")              # 定電流高檔
    load.set_command("current_static_l1", 2.5)   # 設定 CC 位準（依資料表鍵名）
    load.set_command("load_state", "ON")         # 開始拉載
    print(load.query_command("fetch_voltage"))   # 讀回電壓
    print(load.query_command("fetch_current"))   # 讀回電流
```

### 通用引擎

所有 212 條指令都用 `set_command()` / `query_command()`：

- `key`：`commands_chroma63600.py` 中的鍵（`Chroma63600.list_commands()` / `command_info(key)` 可查）。
- `value`：依型態（bool/numeric/enum/string/raw）自動轉成 SCPI 參數。
- 本機無通道清單，故 `ch_list` 參數一般用不到（保留相容）。

IEEE-488.2 常用另有具名方法：`idn()`、`reset()`、`clear_status()`、`wait()`、`error()`，以及低階 `write()`/`query()`/`query_float()`。

## 圖形介面 (GUI)

```bash
python ui.py
```

用「群組」下拉縮小範圍後選指令；面板依型態自動彈出參數欄位（開關/列舉/數值/字串）。
無實體儀器時勾選「模擬模式」離線操作。Write/Read 按鈕依指令讀寫屬性自動啟用。

## 指令涵蓋範圍（依群組）

通用/CHANnel、CONFIGURE、CURRENT、Volt/Power/Res/Mode、ADVANCE、FETCH/MEASURE、
DIGITIZING/SYNC、PROGRAM、SPEC/STATUS、SYSTEM —— 共 212 條。完整對照見 `Chroma_63600_SCPI_Commands.xlsx`。

## 檔案

| 檔案 | 用途 |
|------|------|
| `commands_chroma63600.py` | **指令資料表（唯一權威來源，212 條）** |
| `instrument.py` | API 主模組（通用引擎 `Chroma63600`） |
| `ui.py` | Tkinter 圖形控制面板 |
| `make_chroma63600_xlsx.py` | 由資料表產生 Excel |
| `Chroma_63600_SCPI_Commands.xlsx` | 指令對照表 |
| `build_commands.py` | 由 `_specs/` 解析產生資料表的工具（可重跑） |
| `_specs/` | 與 NotebookLM 協作取得的各子系統原始規格 |

> 更新指令：改 `_specs/*.txt` 後重跑 `python build_commands.py`，再跑 `python make_chroma63600_xlsx.py`。
