# SCPI 儀器控制套件（C# / WPF）

以 C# / WPF 實作的 SCPI 儀器控制程式，涵蓋十六台量測儀器、共 **4,741 條** SCPI 指令。
指令資料皆係與 NotebookLM 對各原廠手冊逐子系統問答彙整而得（含頁碼）。

## 程式

| 資料夾 | 說明 |
|------|------|
| [`All-In-One_csharp/`](All-In-One_csharp/README.md) | **SCPI Command Tool（SCT.exe）**：單一視窗整合全部 16 台儀器（分類 → 儀器下拉、可同時連線多台、Scan / Search / Copy、EN / 繁中） |
| [`CSharp/Chroma_62000P/`](CSharp/Chroma_62000P/README.md) | Chroma 62000P 單機版控制程式 |

需求：Windows 10/11 x64、.NET 8 Desktop Runtime、系統 VISA（NI-VISA 或 Keysight IO Libraries）。
建置：在程式資料夾執行 `dotnet build -c Release`。

## 十六台儀器

| 儀器 | 類型 | 指令數 | 通道模型 |
|------|------|:---:|------|
| **2231A-30-3** | 三通道直流電源供應器 (Keithley) | 76 | `INST:SEL` 作用中通道 |
| **E3633A** | 單輸出直流電源供應器 (Agilent/Keysight) | 59 | 單輸出、無通道 |
| **E36300** | 三輸出直流電源供應器 (Keysight) | 101 | `(@1:3)` 通道清單 |
| **Chroma 62000P** | 可程式直流電源供應器 (Chroma) | 72 | 單輸出、無通道 |
| **DAQ973A** | 資料擷取/開關量測系統 (Keysight) | 421 | `(@通道清單)` 參數 |
| **34970 / 34972A** | 資料擷取/開關單元 (Keysight/Agilent) | 179 | `(@通道清單)` 參數 |
| **Chroma 63600** | 直流電子負載 (Chroma) | 212 | `CHANnel <n>` 作用中通道 |
| **DPO 7 Series** | 數位螢光示波器 (Tektronix) | 482 | 標頭編號 `CH{n}`/`MEAS{n}`/`MATH{n}` |
| **TDS 7000 Series** | 數位螢光示波器 (Tektronix) | 764 | 標頭編號 `CH{n}`/`MEAS{n}`/`MATH{n}`/`SEARCH{n}` |
| **MSO 5 Series** | 混合訊號示波器 (Tektronix) | 557 | 標頭編號 `CH{n}`/`MEAS{n}`/`MATH{n}` |
| **R&S RTE** | 數位示波器 (Rohde & Schwarz) | 552 | 數值後綴 `CHANnel{n}`/`MEASurement{n}` |
| **Infiniium 9000** | Infiniium 示波器 (Agilent/Keysight) | 535 | 標頭編號 `CHANnel{n}`/`FUNCtion{n}`/`WMEMory{n}` |
| **33220A** | 函數／任意波形產生器 (Agilent/Keysight) | 145 | 單輸出、無通道 |
| **AFG3000** | 任意波形／函數信號產生器 (Tektronix) | 144 | `SOURce{1\|2}` 標頭通道 |
| **AFG31000** | 任意函數信號產生器 (Tektronix) | 187 | `SOURce{1\|2}` 標頭索引 |
| **Series 2400** | 電源量測單元 SourceMeter (Keithley) | 255 | 單通道；`CALCulate2:LIMit{n}` 標頭編號 |

## 指令資料與參考文件

- **指令資料（唯一來源）**：`All-In-One_csharp/Data/<儀器>.json`（編譯時內嵌進 exe）；單機版為 `CSharp/Chroma_62000P/Data/commands.json`。
  新增或修改指令時直接編輯 JSON 後重新建置。
- **`Docs/*_SCPI_Commands.xlsx`**：各儀器的指令對照表（分群組、含手冊頁碼、可篩選）。
- **`Docs/specs/<儀器>/`**：與 NotebookLM 協作擷取的手冊原始規格（每列以 `@@` 分隔：名稱、語法、參數、用途、頁碼、讀寫、通道清單）。

> 原 Python 版（各儀器 Tkinter 面板、驅動程式、Python All-In-One 與產生指令表的腳本）已移除，需要時可從 git 歷史取回（commit `1ed74f1`）。
