# -*- coding: utf-8 -*-
"""
由 _specs/*.txt（與 NotebookLM 協作取得的 DAQ973A 指令規格）自動產生
daq973a_commands.py 指令資料表。

_specs 每列格式（@@ 分隔，7 欄）：
    名稱 @@ 語法 @@ 參數 @@ 用途 @@ 頁碼 @@ RW(R/W/RW) @@ 通道清單(Y/N)
"""
from __future__ import annotations

import os
import re
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(HERE, "_specs")

# 檔案 -> 功能群組
FILE_GROUP = {
    "01": "通用/流程", "02": "CONFigure", "03": "ROUTe",
    "04": "Sample/Trigger/Output", "05": "SENSe", "06": "SENSe",
    "07": "SENSe", "08": "CALCulate", "09": "Cal/Source/Unit",
    "10": "Format/Display/HCopy/LXI", "11": "DATA", "12": "MMEMory",
    "13": "STATus", "14": "SYSTem", "15": "FETCh", "16": "Digitizer(*3)",
    "17": "MEASure",
}

# 一列的正規表示式：以末三欄（頁碼 / RW / Y|N）作為穩固錨點
ROW_RE = re.compile(
    r"(?P<name>[^@]+?)@@(?P<syntax>.+?)@@(?P<params>.+?)@@(?P<desc>.+?)@@"
    r"\s*(?P<page>\d+)\s*@@\s*(?P<rw>RW|R|W)\s*@@\s*(?P<ch>Y|N)",
    re.DOTALL,
)

NAME_OK = re.compile(r"^[\*\[A-Za-z]")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def name_to_scpi(name: str) -> str:
    s = name.strip().rstrip("?").strip()
    s = s.replace("[", "").replace("]", "")       # 展開可省略段
    s = re.sub(r"\(@[^)]*\)", "", s)               # 去掉名稱內殘留通道清單
    s = re.sub(r"<[^>]*>", "", s)                  # 去掉 <probe_type> 等佔位
    return clean(s).replace(" ", "")


def slug(scpi: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", scpi).strip("_").lower()
    return s or "cmd"


def expand_names(name: str):
    """名稱內含 {A|B} 或 {1|2|3|4} 代表多條真實指令，展開成具體名稱清單。"""
    import itertools
    groups = re.findall(r"\{([^}]*)\}", name)
    if not groups:
        return [name]
    opt_lists = [[t.strip() for t in g.split("|") if t.strip()] for g in groups]
    out = []
    for combo in itertools.product(*opt_lists):
        n = name
        for val in combo:
            n = re.sub(r"\{[^}]*\}", val, n, count=1)
        out.append(n)
    return out


def param_spec(syntax: str) -> str:
    """取指令名之後的參數規格（去掉指令 token 與查詢問號、通道清單）。"""
    first = syntax.split(" / ")[0].strip()        # 取設定形式（或唯一形式）
    parts = first.split(" ", 1)                     # 指令 token 無空白
    rem = parts[1] if len(parts) > 1 else ""
    rem = re.sub(r"\[?\s*,?\s*\(@[^)]*\)\s*\]?", "", rem)  # 去通道清單
    return rem.strip()


def _clean_tok(t: str) -> str:
    return re.sub(r"[\[\]{}]", "", t).strip()


def infer_kind(syntax: str):
    """回傳 (kind, opts)。kind: none/bool/numeric/enum/string/raw。"""
    core = param_spec(syntax)
    has_val = ("<" in core) or ("{" in core)
    if not has_val:
        return "none", None
    m = re.search(r"\{([^}]*)\}", core)
    if m:
        raw_toks = [t.strip() for t in m.group(1).split("|") if t.strip()]
        if any("<" in t for t in raw_toks):
            kind = "numeric"
        else:
            up = {t.upper() for t in raw_toks}
            if up <= {"ON", "OFF", "0", "1"} and up & {"ON", "OFF"}:
                return "bool", None
            toks = [_clean_tok(t) for t in raw_toks]
            toks = [t for t in toks if t]
            if len(toks) >= 2:
                return "enum", toks
            kind = "string"
    else:
        kind = "numeric"
    if re.search(r"<[^>]*(name|string|label|text|file|path|data|address|host)",
                 core, re.I):
        kind = "string"
    if kind in ("numeric", "string") and core.count("<") > 1 and "," in core:
        kind = "raw"
    return kind, None



# ---------------------------------------------------------------------- #
# 查詢參數規則（修正「讀取時把寫入用的值一起送出」的錯誤，如 OUTP? ON）
#   qarg : 查詢形式是否接受參數（通道清單除外）
#   qopts: 讀寫兩用指令查詢可帶的關鍵字（如 MIN/MAX/DEF）；寫入值不是這些關鍵字時查詢不帶值
#   qsel : 讀寫兩用多參數指令，查詢要帶寫入值的第幾個逗號欄位（如 SLOT:LABel? <slot>）
# ---------------------------------------------------------------------- #
QSEL = {"SYSTem:SLOT:LABel": [0], "SYSTem:COMMunicate:ENABle": [1], "MEMory:STATe:NAME": [0]}
KIND_FIX = {"SYSTem:COMMunicate:ENABle": {"kind": "raw", "opts": None}}   # 寫入為 {ON|OFF},<interface>


def query_meta(row: dict) -> dict:
    meta = {"qarg": False, "qopts": None, "qsel": None}
    meta.update(KIND_FIX.get(row["scpi"], {}))
    if not row["get"] or row["kind"] == "none":
        return meta
    segs = [s.strip() for s in re.split(r"\s+[/|]\s+", row["syntax"])]
    qs = [s for s in segs if "?" in s]
    if not qs:
        return meta                               # 語法只列設定形式 → 查詢為單純 XXX?
    tail = re.sub(r"\(@[^)]*\)", "", qs[-1].split("?", 1)[1])
    if not re.sub(r"[\[\]{}(),|\s]", "", tail):
        return meta                               # 查詢只接受通道清單
    meta["qarg"] = True
    if row["set"]:
        if row["scpi"] in QSEL:
            meta["qsel"] = QSEL[row["scpi"]]
        else:
            words = re.findall(r"[A-Za-z][A-Za-z0-9]*", re.sub(r"<[^>]*>", "", tail.replace(" ", "")))
            meta["qopts"] = list(dict.fromkeys(words)) or None
            if not meta["qopts"]:
                meta["qarg"] = False
    return meta


def main():
    rows = []
    seen = set()       # 已見過的 scpi
    keyseen = set()    # 已用過的 key
    for path in sorted(glob.glob(os.path.join(SPECS, "*.txt"))):
        base = os.path.basename(path)
        if base.startswith("_"):
            continue
        prefix = base[:2]
        group = FILE_GROUP.get(prefix, "其他")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # 去除前言/結尾雜訊
        text = re.sub(r"(?m)^(Answer:|Continuing conversation.*|Resumed conversation.*|Conversation:.*|💡.*)$", "", text)
        # NotebookLM CLI 會把 :couple: / :lock: 等 shortcode（含兩側冒號）渲染成 emoji，還原之
        for _e, _v in (("0️⃣", ":ZERO:"), ("0⃣", ":ZERO:"), ("👫", ":COUPle:"),
                       ("🔒", ":LOCK:"), ("️", "")):
            text = text.replace(_e, _v)
        blob = text.replace("\r", " ").replace("\n", " ")
        for m in ROW_RE.finditer(blob):
            raw_name = clean(m.group("name"))
            if not NAME_OK.match(raw_name) or len(raw_name) > 90:
                continue
            syntax = clean(m.group("syntax"))
            params = clean(m.group("params"))
            desc = clean(m.group("desc"))
            page = int(m.group("page"))
            rw = m.group("rw")
            ch = m.group("ch") == "Y" or "(@" in syntax
            kind, opts = infer_kind(syntax)
            suggest = None
            if kind == "numeric":
                s = [t for t in ("MINimum", "MAXimum", "AUTO", "DEFault")
                     if re.search(t[:3], param_spec(syntax), re.I)]
                suggest = s or None
            hint = params if params and params != "無" else ""
            if ch:
                hint = (hint + "；可加通道清單 (@ch_list)").strip("；")
            # 名稱內含 {..} -> 展開成多條真實指令
            for name in expand_names(raw_name):
                scpi = name_to_scpi(name)
                if not scpi or "{" in scpi:
                    continue
                if scpi in seen:          # 跨批次重疊 -> 以 scpi 去重
                    continue
                seen.add(scpi)
                key = slug(scpi)
                k, i = key, 2
                while k in keyseen:
                    k = f"{key}_{i}"
                    i += 1
                keyseen.add(k)
                rows.append({
                    "key": k, "group": group, "name": name, "scpi": scpi,
                    "syntax": syntax, "params": params, "desc": desc,
                    "page": page, "set": rw in ("W", "RW"),
                    "get": rw in ("R", "RW"), "kind": kind, "opts": opts,
                    "suggest": suggest, "hint": hint, "chlist": bool(ch),
                })

    # 群組順序（依檔案順序首見）
    group_order = []
    for r in rows:
        if r["group"] not in group_order:
            group_order.append(r["group"])

    out = os.path.join(HERE, "daq973a_commands.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write('"""DAQ973A SCPI 指令資料表（唯一權威來源）。\n\n'
                "資料係與 NotebookLM 對 Keysight DAQ973A 程式設計手冊逐子系統問答彙整，\n"
                "由 build_commands.py 自 _specs/*.txt 自動產生；請勿手改本檔，改來源或解析器後重跑。\n"
                '涵蓋主機與 DAQM909A 數位化模組 (*3 子系統) 之完整指令。"""\n')
        f.write("from __future__ import annotations\n")
        f.write("from typing import List, Dict, Any\n\n")
        f.write("COMMANDS: List[Dict[str, Any]] = [\n")
        for r in rows:
            r.update(query_meta(r))
            f.write("    %r,\n" % (r,))
        f.write("]\n\n")
        f.write("COMMAND_BY_KEY: Dict[str, Dict[str, Any]] = {c['key']: c for c in COMMANDS}\n\n")
        f.write("GROUP_ORDER = %r\n\n" % (group_order,))
        f.write('if __name__ == "__main__":\n')
        f.write("    assert len(COMMAND_BY_KEY) == len(COMMANDS), 'duplicate key'\n")
        f.write("    print(f'COMMANDS = {len(COMMANDS)} 條，群組 {len(GROUP_ORDER)} 個')\n")

    print(f"寫出 {out}")
    print(f"指令數：{len(rows)}；群組：{group_order}")
    # 型態分佈
    from collections import Counter
    print("kind 分佈：", dict(Counter(r["kind"] for r in rows)))
    print("帶通道清單：", sum(1 for r in rows if r["chlist"]))


if __name__ == "__main__":
    main()
