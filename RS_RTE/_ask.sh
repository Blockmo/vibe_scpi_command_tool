#!/bin/bash
cd "$(dirname "$0")/_specs"
FMT="$(cat _fmt.txt)"
ask() {
  [ -s "$1" ] && [ "$(grep -c '@@' "$1")" -gt 0 ] && { echo "$1: skip"; return; }
  for try in 1 2 3; do
    notebooklm ask "請列出 R&S RTE 示波器使用手冊第 17 章遠端控制指令中「$2」的全部 SCPI 指令。$FMT" > "$1" 2>&1
    n=$(grep -c '@@' "$1"); [ "$n" -gt 0 ] && break; sleep 20
  done
  echo "$1: $n lines"
}
ask 01_common.txt "Common Commands（*CAL? *CLS *ESE *ESR? *IDN? *IST? *OPC *OPT? *PRE *PSC *RST *SRE *STB? *TRG *TST? *WAI）以及 RUN、RUNCont、SINGle、STOP、RUNSingle、AUToscale 等基本運作控制指令"
ask 02_acquire.txt "Acquisition and Setup 中的 TIMebase、ACQuire 子系統（含 ACQuire:POINts、SRATe、RESolution、MODE、AVAilable、COUNt、ARIThmetic、CDTA、INTerpolate、SEGMented 等）"
ask 03_channel.txt "Acquisition and Setup 中的 CHANnel<m> 子系統（STATe、COUPling、SCALe、RANGe、POSition、OFFSet、BANDwidth、IMPedance、INVert、DIGFilter、SKEW、WAVeform<n> 類型/資料等）以及 HDEFinition（High definition）與 FORMat:DATA、波形資料讀取 CHANnel<m>:DATA"
ask 04_probe.txt "Probes 探棒設定 PROBe<m> 子系統全部指令（SETup、ATTenuation、GAIN、OFFSet、DEGauss、ID、PMETer 等）"
ask 05a_trigger.txt "Trigger 中的通用觸發設定（TRIGger<m>:SOURce、TYPE、LEVel<n>、EDGE、HOLDoff、MODE、SEQuence、FILTermode、ROBust、QUALify、FORCe、OUT 觸發輸出）"
ask 05b_trigger.txt "Trigger 中的 Glitch、Width、Runt、Window、Timeout、Interval、Slew rate 觸發類型相關指令"
ask 05c_trigger.txt "Trigger 中的 Data2Clock(Setup & Hold)、State、Pattern、Serial pattern、TV/Video、Line、Sequence(A/B/R)、Zone/Event 觸發相關指令"
ask 06_display.txt "DISPlay 子系統與 LAYout 子系統（螢幕顯示、diagram、signal bar、持續性 persistence、強度、顏色等）"
ask 07_zoom_ref.txt "Waveform Analysis 中的 ZOOM 子系統與 REFCurve/Reference waveforms 參考波形指令"
ask 08_math.txt "Waveform Analysis 中的 CALCulate:MATH<m> 數學運算指令（含 FFT 相關設定）"
ask 09_history.txt "Waveform Analysis 中的 History 歷史波形相關指令（CHANnel<m>:HISTory、ACQuire:HISTory 等）"
ask 10_cursor.txt "Cursor Measurements 的 CURSor<m> 全部指令"
ask 11a_meas.txt "Automatic Measurements 中的通用測量設定（MEASurement<m>:ENABle、SOURce、CATegory、MAIN、ADDitional、RESult、ARES、CLEar、MULTiple、REFLevel 參考位準等）"
ask 11b_meas.txt "Automatic Measurements 中的 STATistics 統計、GATE 門限、TRACk、HISTogram 直方圖測量與 Long term/LTMeas 指令"
ask 11c_meas.txt "Automatic Measurements 中的眼圖 (Eye/Jitter) 測量、頻譜測量 (Spectrum measurement)、Limit check、Delay/Phase 相關 MEASurement<m> 指令"
ask 12a_search.txt "Search 中的通用搜尋設定（SEARch:ADD、REMove、ALL、CLEar、SOURce、TRIGger 類型選擇、RESult、RCOunt、RESDiagram、ONLine、GATE）"
ask 12b_search.txt "Search 中各搜尋事件條件（Edge、Width、Glitch、Runt、Timeout、Window、Interval、Slew rate、Data2Clock、State、Pattern 等 SEARch:TRIGger:... 指令）"
