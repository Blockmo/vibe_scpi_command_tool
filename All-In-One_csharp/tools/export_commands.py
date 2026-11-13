# -*- coding: utf-8 -*-
"""把各儀器 Python 版的指令資料表匯出成 C# All-In-One 使用的 Data/<id>.json。

用法：  python tools/export_commands.py
（指令唯一來源仍是各儀器資料夾的 commands 模組；更新後重跑本工具再重新建置。）
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
ROOT = os.path.dirname(APP)

# id（= JSON 檔名）, 資料夾, 指令模組
SOURCES = [
    ("2231A-30-3", "2231A-30-3", "commands_2231a"),
    ("E3633A", "E3633A", "commands_e3633a"),
    ("E36300", "E36300", "commands_e36300"),
    ("Chroma_62000P", "Chroma_62000P", "commands_chroma62000p"),
    ("DAQ973A", "DAQ973A", "daq973a_commands"),
    ("Chroma_63600", "Chroma_63600", "commands_chroma63600"),
    ("DPO_7SERIES", "DPO_7SERIES", "commands_dpo7"),
    ("MSO_5SERIES", "MSO_5SERIES", "commands_mso5"),
    ("RS_RTE", "RS_RTE", "commands_rte"),
    ("AFG3000", "AFG3000", "commands_afg3000"),
    ("AFG31000", "AFG31000", "afg31000_commands"),
    ("Series2400", "Series2400", "commands_2400"),
]

total = 0
for out_id, folder, mod in SOURCES:
    path = os.path.join(ROOT, folder)
    sys.path.insert(0, path)
    try:
        m = importlib.import_module(mod)
        cmds = m.COMMANDS
    finally:
        sys.path.remove(path)
        sys.modules.pop(mod, None)
    out = os.path.join(APP, "Data", f"{out_id}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cmds, f, ensure_ascii=False, indent=0)
    total += len(cmds)
    print(f"{out_id:15s} {len(cmds):4d} -> Data/{out_id}.json")
print(f"total {total} commands")
