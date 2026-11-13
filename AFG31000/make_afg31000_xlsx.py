# -*- coding: utf-8 -*-
"""由 afg31000_commands.COMMANDS 產生 AFG31000 SCPI 指令對照 Excel。"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from afg31000_commands import COMMANDS, GROUP_ORDER

_order = {g: i for i, g in enumerate(GROUP_ORDER)}
rows_src = sorted(COMMANDS, key=lambda c: (_order.get(c["group"], 999), c["page"], c["scpi"]))

headers = ["功能群組", "command名稱", "command格式", "command參數",
           "command說明", "頁碼", "讀寫", "通道"]

wb = Workbook()
ws = wb.active
ws.title = "AFG31000 SCPI"

header_fill = PatternFill("solid", fgColor="1F6F3D")
group_fill = PatternFill("solid", fgColor="D9EAD3")
header_font = Font(color="FFFFFF", bold=True, size=11)
cell_font = Font(size=10)
group_font = Font(size=10, bold=True)
thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap_top = Alignment(vertical="top", wrap_text=True)
center = Alignment(vertical="center", horizontal="center")

ncol = len(headers)
ws.append(headers)
for c in range(1, ncol + 1):
    cell = ws.cell(row=1, column=c)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = center
    cell.border = border


def rw_text(c):
    return "RW" if c["set"] and c["get"] else ("R" if c["get"] else "W")


def pos_text(c):
    """通道欄：通道指令列出可用通道（如 1/2）；序列元素指令標 n（編號）。"""
    bits = []
    if c.get("chan"):
        bits.append("/".join(str(x) for x in c["channels"]))
    if c.get("elem"):
        bits.append("n")
    return ", ".join(bits)


for c in rows_src:
    ws.append([c["group"], c["name"], c["syntax"], c["params"], c["desc"],
               c["page"], rw_text(c), pos_text(c)])

for ri in range(2, len(rows_src) + 2):
    for ci in range(1, ncol + 1):
        cell = ws.cell(row=ri, column=ci)
        cell.font = cell_font
        cell.border = border
        cell.alignment = center if ci in (1, 6, 7, 8) else wrap_top
    ws.cell(row=ri, column=1).fill = group_fill
    ws.cell(row=ri, column=1).font = group_font

widths = [20, 40, 60, 34, 34, 8, 8, 10]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[chr(64 + i)].width = w

ws.freeze_panes = "A2"
ws.row_dimensions[1].height = 22
ws.auto_filter.ref = f"A1:H{len(rows_src) + 1}"

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "AFG31000_SCPI_Commands.xlsx")
wb.save(out)
print("Saved:", out, "rows:", len(rows_src))
