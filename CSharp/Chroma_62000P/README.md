# Chroma 62000P 控制面板（C# / WPF 版）

Python 版 `../../Chroma_62000P/` 的 C# 移植版，指令資料相同（72 條，手冊第 5 章），介面重新設計為深色現代風格。

## 需求

- Windows 10/11 x64
- [.NET 8 Desktop Runtime](https://dotnet.microsoft.com/download/dotnet/8.0)（建置需 .NET 8 以上的 SDK）
- 系統 VISA（NI-VISA 或 Keysight IO Libraries），程式直接 P/Invoke `visa32.dll`，**不需任何 NuGet 套件**

## 建置與執行

```bash
dotnet build -c Release
bin\Release\net8.0-windows\Chroma62000P.exe          # 一般模式
bin\Release\net8.0-windows\Chroma62000P.exe --sim    # 模擬模式（開發測試用，介面上不提供此選項）
```

發佈成單一 exe（目標電腦不用另外安裝 .NET）：

```bash
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```

## 介面功能

| 區域 | 功能 |
|------|------|
| 標題列 | 型號、指令數、**色系選擇**（石墨青 / 午夜靛藍 / 琥珀暖橘 / 晨光淺色，記憶於 `%APPDATA%\Chroma62000P\settings.json`）、EN / 繁中 切換；`--sim` 時顯示「SIMULATION」標籤 |
| 連線 | 可編輯的 VISA 資源下拉（預設 `GPIB0::9::INSTR`）＋ **Scan**（GPIB → USB → TCPIP → VXI → ASRL 排序，非 ASRL 附 `*IDN?`）＋ Connect；右側狀態膠囊顯示 IDN |
| 指令清單 | **群組下拉選單**（全部 / Common / ABORt / …）＋ 關鍵字**搜尋**（空白分隔 AND、Ctrl+F 聚焦、Esc 清除），每條顯示 R/W 權限 |
| 指令詳情 | 群組 / 手冊頁碼 / 權限標籤、語法、依型態自動產生的參數編輯器（ON/OFF 與列舉用分段按鈕、數值與多參數用輸入框）、Write/Read 的 **SCPI 即時預覽** |
| 動作 | Write、Read、**Copy**（複製目前組好的 SCPI 字串）；數值輸入框按 Enter 直接寫入 |
| 主控台 | 最新回應大字顯示＋含時間戳記的 TX / RX / ERR / SCAN 彩色紀錄 |

## 檔案

| 檔案 | 用途 |
|------|------|
| `Chroma62000P.csproj` | 專案檔（.NET 8、WPF、x64） |
| `App.xaml(.cs)` | 程式進入點，解析 `--sim` |
| `MainWindow.xaml(.cs)` | 主視窗版面與互動邏輯 |
| `Themes/Theme.xaml` | 色彩 tokens 與所有控制項樣式（按鈕、輸入框、下拉、分段按鈕、捲軸） |
| `Core/Visa.cs` | VISA P/Invoke、`VisaSession`、資源掃描 |
| `Core/CommandSpec.cs` | 指令規格與載入（`Data/commands.json` 內嵌為資源） |
| `Core/Chroma62000PDevice.cs` | 控制引擎：組 SCPI 字串、非同步 Write/Query |
| `Core/SimulatedPsu.cs` | 虛擬 62000P（`--sim` 用，記住設定值並回應查詢） |
| `Core/I18n.cs` | 介面文字英文 / 繁中 |
| `Core/ThemeManager.cs` | 四套色系定義與執行時切換（介面全用 DynamicResource） |
| `Data/commands.json` | 指令資料表（由 Python 版匯出） |
| `tools/export_commands.py` | 從 `../../Chroma_62000P/commands_chroma62000p.py` 重新匯出 JSON |

> 指令資料唯一來源仍是 Python 版的 `commands_chroma62000p.py`。更新後執行 `python tools/export_commands.py` 再重新建置即可。
