#!/bin/bash
cd "$(dirname "$0")/_specs"
FMT="$(cat _fmt.txt)"
ask() { # file  subject
  notebooklm ask "請列出 AFG3000 程式手冊中「$2」的全部 SCPI 指令。$FMT" > "$1" 2>&1
  echo "$1: $(grep -c '@@' "$1") lines"
}
ask 01_common.txt "IEEE-488.2 通用指令(*IDN? *RST *CLS *ESE *ESR? *OPC *WAI *OPT? *PSC *RCL *SAV *SRE *STB? *TRG *TST? *CAL?)、STATus 子系統全部指令、CALibration[:ALL]、DIAGnostic[:ALL]"
ask 02_system.txt "SYSTem 子系統"
ask 03_disp_out_trig.txt "DISPlay 子系統、OUTPut 子系統、TRIGger 子系統(含 ABORt)、AFGControl:CSCopy、HCOPy:SDUMp"
ask 04_memory.txt "MEMory 子系統與 MMEMory 子系統"
ask 05_trace.txt "TRACe|DATA 子系統"
ask 06_source_basic.txt "SOURce 子系統中的 FREQuency、FUNCtion、VOLTage、PHASe、PULSe、ROSCillator，以及 SOURce<3|4>:POWer 雜訊與 COMBine 指令"
ask 07_modulation.txt "SOURce 子系統中的 AM、FM、PM、FSKey、PWM 調變指令"
ask 08_sweep_burst.txt "SOURce 子系統中的 SWEep、BURSt 與 FREQuency 掃描相關指令(FREQuency:STARt/STOP/CENTer/SPAN/MODE)"
