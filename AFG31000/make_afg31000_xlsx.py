# -*- coding: utf-8 -*-
"""Generate the full AFG31000 SCPI command Excel from afg31000_commands.COMMANDS.

資料來源：與 NotebookLM 對 AFG31000 Series Programmer Manual (Sept 2019) 問答彙整，
涵蓋手冊完整指令集。欄位：群組 / 指令名稱 / 指令格式 / 指令參數 / 指令說明 / 說明書頁碼。
"""
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from afg31000_commands import COMMANDS, GROUP_ORDER

# 依群組順序、再依頁碼排序
_order = {g: i for i, g in enumerate(GROUP_ORDER)}
rows_src = sorted(COMMANDS, key=lambda c: (_order.get(c["group"], 999), c["page"]))

headers = ["功能群組", "command名稱", "command格式", "command參數", "command說明", "說明書頁碼"]

wb = Workbook()
ws = wb.active
ws.title = "AFG31000 SCPI"

header_fill = PatternFill("solid", fgColor="305496")
group_fill = PatternFill("solid", fgColor="D9E1F2")
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

for c in rows_src:
    ws.append([c["group"], c["name"], c["syntax"], c["params"], c["desc"], c["page"]])

for ri in range(2, len(rows_src) + 2):
    for ci in range(1, ncol + 1):
        cell = ws.cell(row=ri, column=ci)
        cell.font = cell_font
        cell.border = border
        # 群組欄與頁碼欄置中，其餘靠上換行
        cell.alignment = center if ci in (1, ncol) else wrap_top
    # 群組欄加底色、粗體
    gcell = ws.cell(row=ri, column=1)
    gcell.fill = group_fill
    gcell.font = group_font

widths = [16, 44, 60, 40, 34, 10]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[chr(64 + i)].width = w

ws.freeze_panes = "A2"
ws.row_dimensions[1].height = 22
ws.auto_filter.ref = f"A1:F{len(rows_src) + 1}"

out = r"D:\mo_code\SCPI_Command\AFG31000_SCPI_Commands.xlsx"
wb.save(out)
print("Saved:", out, "rows:", len(rows_src))
