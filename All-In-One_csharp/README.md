# SCPI Command Tool（SCT，C# / WPF 版）

一個視窗整合 **16 台儀器、4,741 條 SCPI 指令**的 WPF 控制程式，
介面沿用 `../CSharp/Chroma_62000P/` 的設計（兩種色系、三種字體大小、EN / 繁中）。

| 分類 | 儀器 | 範本 |
|------|------|------|
| 電源供應器 | 2231A-30-3 / E3633A / E36300 / Chroma 62000P | 通道清單型 |
| 資料擷取 DAQ | DAQ973A / 34970 / 34972A | 通道清單型 |
| 電子負載 | Chroma 63600 | 通道清單型 |
| 示波器 | DPO 7 Series / TDS 7000 Series / MSO 5 Series / R&S RTE / Infiniium 9000 | 標頭編號型 |
| 函數信號產生器 | 33220A | 通道清單型（單輸出） |
| 函數信號產生器 | AFG3000 / AFG31000 | 標頭編號型 |
| 電錶 / 電源量測單元 | Series 2400 | 標頭編號型 |

## 需求

- Windows 10/11 x64、[.NET 8 Desktop Runtime](https://dotnet.microsoft.com/download/dotnet/8.0)
- 系統 VISA（NI-VISA 或 Keysight IO Libraries）；程式以 P/Invoke 呼叫 `visa32.dll`，不需任何 NuGet 套件

## 建置與執行

```bash
dotnet build -c Release
bin\Release\net8.0-windows\SCT.exe          # 一般模式
bin\Release\net8.0-windows\SCT.exe --sim    # 模擬模式（開發測試用，介面上不提供）
```

單一 exe（目標電腦不用安裝 .NET）：

```bash
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```

**16 台的指令表都已內嵌在 exe 裡**，執行與發佈都不需要其他資料夾。

## 介面

| 區域 | 功能 |
|------|------|
| 標題列 | 色系（石墨青 / 晨光淺色）、字體大小（M / L / XL = 1.0 / 1.15 / 1.3 倍）、EN / 繁中；色系與字體記憶於 `%APPDATA%\SCPI_AllInOne\settings.json` |
| 儀器 | **分類 → 儀器** 兩個下拉選單；已連線的儀器前面有綠點；右側顯示已連線台數（滑鼠停留列出明細） |
| 連線 | VISA 資源下拉（預設 `GPIB0::9::INSTR`）＋ **Scan** ＋ Connect；**每台儀器各自連線，可同時連多台** |
| 指令清單 | 群組下拉選單 ＋ 關鍵字搜尋（空白分隔 AND、Ctrl+F、Esc 清除） |
| 指令詳情 | 語法、參數編輯器、**位置欄位**（通道清單 `(@…)`／通道／編號 n 或序列元素 n，依指令自動顯示）、W/R 即時預覽、寫入 / 讀取 / 複製 |
| 複製 | 最後按的是**讀取** → 複製 R 那行；最後按的是**寫入**或兩者都還沒按 → 複製 W 那行。只能查詢的指令一律複製 R、只能寫入的一律複製 W；要複製 W 但參數未填時會提示先輸入。複製不需連線、不會送出到儀器 |
| 主控台 | 每台儀器各自的最新回應與 TX / RX / ERR / SCAN 紀錄 |
| 底部 | 所有已連線儀器與資源 |

切換儀器時，該台的連線、資源、掃描結果、群組 / 搜尋、目前指令、通道設定與紀錄都會保留。

## SCPI 組字串規則

- **通道清單型**：參數 = `值`、`(@通道清單)` 以逗號相接；寫入 `SCPI 參數`；查詢 `SCPI? (@通道清單)`，值只在查詢語法接受時才帶（`qarg`；讀寫兩用指令僅 `qopts` 關鍵字如 MIN/MAX/DEF，或 `qsel` 指定的欄位）。有填通道清單時可不填值。
- **標頭編號型**：標頭的 `{ch}`/`{n}` 代入通道與編號；寫入 `標頭 值`；查詢 `標頭?`（qarg 指令帶引數為 `標頭? 引數`）。
- 數值原樣送出（`MIN/MAX/DEF…` 轉大寫），ON/OFF 只接受 `ON|OFF|1|0`。

移除 Python 版前，已以原 Python 驅動對當時全部 13 台指令產生的寫入 / 查詢字串逐一比對，結果完全一致。

## 檔案

| 檔案 | 用途 |
|------|------|
| `ScpiAllInOne.csproj` | 專案檔（輸出 `SCT.exe`；.NET 8、WPF、x64；`Data\*.json` 內嵌為資源） |
| `App.xaml(.cs)` | 進入點，解析 `--sim`、套用上次色系 |
| `MainWindow.xaml(.cs)` | 主視窗版面與互動邏輯 |
| `Assets/app.ico` | 應用程式圖示（視窗左上角 / 工作列 / exe） |
| `Themes/Theme.xaml` | 所有控制項樣式（顏色以 DynamicResource 參照） |
| `Core/Instruments.cs` | 分類與 16 台儀器的登錄表（範本、模擬 IDN、說明） |
| `Core/CommandSpec.cs` | 指令規格與內嵌資源載入 |
| `Core/ScpiBuilder.cs` | SCPI 組字串引擎（兩種範本） |
| `Core/Device.cs` | 連線裝置、虛擬儀器、每台儀器的 session 狀態 |
| `Core/Visa.cs` | VISA P/Invoke 與資源掃描 |
| `Core/ThemeManager.cs` | 兩套色系、三種字體大小與執行時切換（字級以 `Fs*` 資源參照） |
| `Core/I18n.cs` | 介面文字英文 / 繁中 |
| `Data/*.json` | 16 台的指令表（**唯一來源**，編譯時內嵌） |

## 指令表格式（`Data/<儀器>.json`）

每台一個 JSON 陣列，每個元素是一條指令。新增 / 修改指令直接編輯後重新建置；新增儀器另需在 `Core/Instruments.cs` 登錄（`DataId` = JSON 檔名）。

| 欄位 | 說明 |
|------|------|
| `key` | 唯一鍵 |
| `group` / `name` | 群組（群組下拉）、手冊指令名稱 |
| `scpi` | 實際送出的標頭；標頭編號型以 `{ch}` / `{n}` 代表通道 / 編號 |
| `syntax` / `params` / `desc` / `page` / `hint` | 手冊語法、參數說明、用途、頁碼、輸入提示（僅顯示用） |
| `set` / `get` | 可寫入 / 可查詢 |
| `kind` | 參數型態：`none` / `bool` / `numeric` / `enum` / `string` / `raw` |
| `opts` / `suggest` | `enum` 選項、`numeric` 建議值（如 MIN/MAX） |
| `chlist` | 通道清單型：可附加 `(@通道清單)` |
| `chan` / `channels` / `elem` | 標頭編號型：標頭含 `{ch}`（可用通道）/ `{n}` |
| `qarg` | 查詢可帶參數（通道清單除外） |
| `qopts` / `qsel` | 通道清單型讀寫兩用指令：查詢可帶的關鍵字 / 多參數寫入值中查詢要帶的欄位索引 |
| `qn` | 標頭編號型多參數指令：查詢只帶前 `qn` 個參數 |

各儀器的指令對照表與手冊原始規格在根目錄 `Docs/`。
