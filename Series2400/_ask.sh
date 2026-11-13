#!/bin/bash
cd "$(dirname "$0")/_specs"
FMT="$(cat _fmt.txt)"
ask() { # file subject
  for try in 1 2 3; do
    notebooklm ask "請列出 Series 2400 SourceMeter 手冊中「$2」的全部 SCPI 指令。名稱與語法請用完整 SCPI 樹狀路徑（例如 :SOURce[1]:VOLTage[:LEVel][:IMMediate][:AMPLitude]），選項請用 {A|B} 大括號表示（例如 {ON|OFF}），數值參數用 <n>。$FMT" > "$1" 2>&1
    n=$(grep -c '@@' "$1"); [ "$n" -gt 0 ] && break; sleep 20
  done
  echo "$1: $n lines"
}
for a in "$@"; do
  case $a in
    01) ask 01_common.txt "IEEE-488.2 通用指令（*CLS *ESE *ESR? *IDN? *OPC *OPT? *RCL *RST *SAV *SRE *STB? *TRG *TST? *WAI 等，第 16 章）以及 Signal Oriented 量測指令 CONFigure、FETCh?、READ?、MEASure?（第 17 章）、INITiate、ABORt" ;;
    02) ask 02_calc1_calc3.txt "CALCulate1 子系統（Math Expressions，含 MATH:EXPRession、UNITs、CATalog、NAME、DEFine、DELete、STATe、DATA）與 CALCulate3 子系統（FORMat、DATA buffer statistics）" ;;
    03) ask 03_calc2.txt "CALCulate2 子系統（FEED、NULL 偏移、LIMit/LIMit2/LIMit3/LIMit5~12 上下限、COMPliance、PASS:SOURce2、CLIMits、BCONtrol、MODE、CLEar、IMMediate、DATA）" ;;
    04) ask 04_disp_form_outp_route.txt "DISPlay 子系統、FORMat 子系統、OUTPut 子系統、ROUTe 子系統" ;;
    05) ask 05_sense.txt "SENSe1 子系統（FUNCtion、DATA、RESistance MODE/OCOMpensated、CURRent/VOLTage/RESistance 的 RANGe/AUTO/NPLCycles/PROTection、AVERage、CURRent/VOLTage 的 PROTection RSYNchronize 等全部）" ;;
    06) ask 06_source_basic.txt "SOURce1 子系統中的 CLEar、FUNCtion、DELay、CURRent 與 VOLTage（MODE、RANGe、AUTO、LEVel、TRIGgered、PROTection、STARt/STOP/STEP/SPAN/CENTer）" ;;
    07) ask 07_source_sweep_list.txt "SOURce1 子系統中的 SWEep（SPACing、POINts、DIRection、RANGing、CABort）、LIST（CURRent、VOLTage、APPend、POINts）、MEMory（SAVE、RECall、POINts）、PULSe（WIDTh、DELay）、SOAK" ;;
    08) ask 08_source2_status.txt "SOURce2 子系統（Digital I/O、TTL、BSIZe、TTL4 MODE/BSTate、CLEar AUTO/DELay）以及 STATus 子系統（MEASurement、OPERation、QUEStionable、PRESet、QUEue）" ;;
    09) ask 09_system.txt "SYSTem 子系統（PRESet、POSetup、VERSion、ERRor、CLEar、KEY、BEEPer、AZERo、LFRequency、TIME、RSENse、GUARd、CCHeck、RCMode、MEP、MEMory、LOCal/REMote/RWLock、ACCess 等全部）" ;;
    11) ask 11_limit4.txt "CALCulate2:LIMit4（contact check，2400-C）" ;;
    10) ask 10_trace_trigger.txt "TRACe 子系統（DATA、CLEar、FREE、POINts、FEED、CONTrol、TSTamp）以及 TRIGger 子系統與 ARM 層（INITiate、ABORt、ARM COUNt/SOURce/TIMer/DIRection/ILINe/OLINe/OUTPut、TRIGger CLEar/COUNt/DELay/SOURce/TCONfigure 等全部）" ;;
  esac
done
