# -*- coding: utf-8 -*-
"""把 Python 版的指令資料表 (Chroma_62000P/commands_chroma62000p.py) 匯出成 C# 版使用的 Data/commands.json。

用法（在本資料夾的上一層或任何位置皆可）：
    python tools/export_commands.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
SRC = os.path.normpath(os.path.join(APP, "..", "..", "Chroma_62000P"))
sys.path.insert(0, SRC)

from commands_chroma62000p import COMMANDS  # noqa: E402

out = os.path.join(APP, "Data", "commands.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(COMMANDS, f, ensure_ascii=False, indent=1)
print(f"exported {len(COMMANDS)} commands -> {out}")
