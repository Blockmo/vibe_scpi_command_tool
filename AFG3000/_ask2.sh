#!/bin/bash
cd "$(dirname "$0")/_specs"
FMT="$(cat _fmt.txt)"
ask() {
  for try in 1 2 3; do
    notebooklm ask "請列出 AFG3000 程式手冊中「$2」的全部 SCPI 指令。$FMT" > "$1" 2>&1
    n=$(grep -c '@@' "$1"); [ "$n" -gt 0 ] && break; sleep 20
  done
  echo "$1: $n lines"
}
ask 06a_source_basic.txt "SOURce 子系統中的 FREQuency（CW/FIXed、CONCurrent）、FUNCtion（SHAPe、EFILe、RAMP:SYMMetry）、VOLTage（AMPLitude、OFFSet、HIGH、LOW、UNIT、LIMit、CONCurrent）、PHASe（ADJust、INITiate）"
ask 06b_source_pulse.txt "SOURce 子系統中的 PULSe（DCYCle、DELay、HOLD、PERiod、TRANsition、WIDTh）、ROSCillator:SOURce，以及 SOURce<3|4>:POWer 內部雜訊、COMBine:FEED"
ask 07_modulation.txt "SOURce 子系統中的 AM、FM、PM、FSKey、PWM 調變指令"
ask 08_sweep_burst.txt "SOURce 子系統中的 SWEep、BURSt 與 FREQuency 掃描相關指令(FREQuency:STARt/STOP/CENTer/SPAN/MODE)"
