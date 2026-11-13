# -*- coding: utf-8 -*-
"""
由 _specs/*.txt（與 NotebookLM 協作取得的 Keithley Series 2400 SourceMeter 指令規格）
自動產生 commands_2400.py 指令資料表。

_specs 每列格式（@@ 分隔，7 欄）：
    名稱 @@ 語法 @@ 參數 @@ 用途 @@ 頁碼(章-頁) @@ RW(R/W/RW) @@ 通道清單(Y/N)

SCPI 正規化規則（name_to_scpi）：
  * 去掉開頭冒號與結尾問號。
  * 可省略的根節點 [:SENSe[1]] / [:SOURce[1]] 保留寫成 SENSe / SOURce（避免與 TRACe:DATA 等混淆）。
  * 可省略的數字後綴 [1]、其他可省略節點（[:LEVel][:IMMediate][:AMPLitude]、[:STATe]、
    [:SEQuence[1]] …）一律省略（Keithley 慣用的短形式，皆合法）。
  * 例外：[:LATest] 保留，以區分 CALCulate:DATA? 與 CALCulate:DATA:LATest?。
  * :CALCulate2:LIMitX:… （X = 2, 3, 5~12）→ LIMit{n}，以標頭編號 element 代入。
  * CONFigure[:<function>] / MEASure[:<function>]? 展開為 VOLTage / CURRent / RESistance 三條＋無功能形式。
"""
from __future__ import annotations

import os
import re
import glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(HERE, "_specs")

GROUP_ORDER = ["Common", "Measure", "SOURce", "SENSe", "OUTPut/ROUTe",
               "CALCulate1", "CALCulate2", "CALCulate3", "TRACe", "TRIGger",
               "FORMat", "DISPlay", "SOURce2", "STATus", "SYSTem"]

# 名稱中 :CONFigure[:<function>] / :MEASure[:<function>] 的功能展開
FUNCTIONS = ["VOLTage", "CURRent", "RESistance"]

# 手冊特例
OVERRIDES = {
    "FORMat": {"kind": "raw", "opts": None,
               "hint": "<type>[,<length>]：ASCii | REAL,32 | SREal"},
    "SYSTem:BEEPer": {"kind": "raw", "opts": None,
                      "hint": "<freq>,<time>：freq 65~2e6 Hz，time 0~7.9 s（例：2000,1）"},
}

ROW_RE = re.compile(
    r"(?P<name>[^@]+?)@@(?P<syntax>F+?)@@(?P<params>F+?)@@(?P<desc>F+?)@@"
    r"\s*(?P<page>[0-9][0-9.\-]*)\s*@@\s*(?P<rw>RW|R|W)\s*@@\s*(?P<ch>Y|N)".replace(
        "F", r"(?:[^@]|@(?!@))"),
    re.DOTALL,
)

NAME_OK = re.compile(r"^[\*\[:A-Za-z]")
SPECIAL_WORDS = ["UP", "DOWN", "DEFault", "MINimum", "MAXimum", "INFinite", "NONE", "NEXT"]


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def name_to_scpi(name: str) -> str:
    s = name.strip().replace(" ", "").rstrip("?")
    s = re.sub(r"^\[:(SENSe|SOURce)\[1\]\]", r"\1", s)
    s = s.lstrip(":")
    s = s.replace("[:LATest]", ":LATest")
    s = s.replace("LIMitX", "LIMit{n}")
    prev = None
    while prev != s:                       # 由內而外去掉可省略段
        prev = s
        s = re.sub(r"\[\d\]", "", s)
        s = re.sub(r"\[:[A-Za-z0-9]+\]", "", s)
    return s


def slug(scpi: str) -> str:
    s = scpi.replace("{n}", "_n_")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s or "cmd"


def group_of(scpi: str) -> str:
    if scpi.startswith("*"):
        return "Common"
    root = scpi.split(":")[0].upper()
    if root in ("CONFIGURE", "MEASURE", "FETCH", "READ"):
        return "Measure"
    if root in ("INITIATE", "ABORT", "ARM", "TRIGGER"):
        return "TRIGger"
    if root in ("OUTPUT", "ROUTE"):
        return "OUTPut/ROUTe"
    if root == "CALCULATE":
        return "CALCulate1"
    m = {"SOURCE": "SOURce", "SOURCE2": "SOURce2", "SENSE": "SENSe",
         "CALCULATE2": "CALCulate2", "CALCULATE3": "CALCulate3",
         "TRACE": "TRACe", "FORMAT": "FORMat", "DISPLAY": "DISPlay",
         "STATUS": "STATus", "SYSTEM": "SYSTem"}
    return m.get(root, "其他")


def param_spec(syntax: str) -> str:
    """取設定形式中指令 token 之後的參數規格。"""
    first = syntax.split(" / ")[0].strip()
    parts = first.split(" ", 1)
    return parts[1].strip() if len(parts) > 1 else ""


def brace_tokens(params: str):
    """取參數欄中第一個 {A|B|C} 的選項（去掉 [] 可省略段的括號）。"""
    m = re.search(r"\{([^}]*)\}", params)
    if not m:
        return None
    toks = [t.strip() for t in m.group(1).split("|") if t.strip()]
    toks = [re.sub(r"[\[\]]", "", t) for t in toks]
    return [t for t in toks if "user" not in t.lower()]      # 去掉 "user-name" 佔位


def infer_kind(syntax: str, params: str):
    """回傳 (kind, opts, suggest)。kind: none/bool/numeric/enum/string/raw。"""
    core = param_spec(syntax)
    if not core or core.startswith(":") or core.startswith("["):
        return "none", None, None
    if core.startswith("<b>"):
        return "bool", None, None
    if "list" in core.lower() and not brace_tokens(params):
        return "raw", None, None
    toks = brace_tokens(params)
    if toks:
        if {t.upper() for t in toks} <= {"ON", "OFF", "1", "0"}:
            return "bool", None, None
        if any("<" in t for t in toks):
            sug = [t for t in toks if "<" not in t]
            return "numeric", None, sug or None
        if "ONCE" in [t.upper() for t in toks] or len(toks) >= 2:
            return "enum", toks, None
    if re.match(r"<(n|NRf|NDN|freq)>", core) or core.startswith("<NRf>|<NDN>"):
        rest = params.split("=", 1)[-1]
        sug = [w for w in SPECIAL_WORDS if re.search(r"(?<![A-Za-z])" + w + r"(?![A-Za-z])", rest)]
        # 純離散數字選項（如 0|1|2|3|4、50|60、4|5|6|7）
        disc = re.findall(r"(?<![\d.])(\d+)(?=\s*\|)|(?<=\|)\s*(\d+)(?![\d.])", rest)
        nums = [a or b for a, b in disc]
        if nums and "至" not in rest:
            seen = []
            for x in nums:
                if x not in seen:
                    seen.append(x)
            sug = seen + sug
        return "numeric", None, sug or None
    return "string", None, None


def expand(raw_name: str, rw: str):
    """回傳 [(name, rw)]：處理 CONFigure/MEASure 的 <function> 展開。"""
    if "<function>" not in raw_name:
        return [(raw_name, rw)]
    base = raw_name.replace("[:<function>]", "").replace(":<function>", "")
    out = []
    if raw_name.upper().startswith(":CONF"):
        out.append((base + "?", "R"))                       # CONFigure? 查詢目前功能
        out += [(f"{base}:{f}", "W") for f in FUNCTIONS]
    else:  # MEASure
        b = base.rstrip("?")
        out.append((b + "?", "R"))
        out += [(f"{b}:{f}?", "R") for f in FUNCTIONS]
    return out


def main():
    rows, by_scpi, keyseen = [], {}, set()
    for path in sorted(glob.glob(os.path.join(SPECS, "*.txt"))):
        if os.path.basename(path).startswith("_"):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text = re.sub(r"(?m)^(Answer:|Continuing conversation.*|Resumed conversation.*|"
                      r"Conversation:.*|💡.*)$", "", text)
        blob = text.replace("\r", "").replace("\n", "")   # 終端機折行直接接回
        for m in ROW_RE.finditer(blob):
            raw_name = clean(m.group("name"))
            raw_name = re.sub(r"^[NY]\s*(?=[:\[\*A-Z])", "", raw_name).strip()
            if not NAME_OK.match(raw_name) or len(raw_name) > 90:
                continue
            syntax = clean(m.group("syntax"))
            params = clean(m.group("params"))
            desc = clean(m.group("desc"))
            page = m.group("page")
            for name, rw in expand(raw_name, m.group("rw")):
                scpi = name_to_scpi(name)
                if not scpi or re.search(r"[<>\[\]\s]", scpi) or "*" in scpi[1:]:
                    print("  略過無效:", name)
                    continue
                if re.search(r"[^ -~]", scpi + name):
                    print("  !! 非 ASCII:", name)
                is_func = name != raw_name
                kind, opts, suggest = (("none", None, None) if is_func
                                       else infer_kind(syntax, params))
                if scpi in by_scpi:        # 重複列（*OPC、INITiate…）→ 合併讀寫屬性
                    prev = by_scpi[scpi]
                    prev["set"] = prev["set"] or rw in ("W", "RW")
                    prev["get"] = prev["get"] or rw in ("R", "RW")
                    if prev["kind"] == "none" and kind != "none":
                        prev.update(kind=kind, opts=opts, suggest=suggest)
                    continue
                key = slug(scpi)
                k, i = key, 2
                while k in keyseen:
                    k, i = f"{key}_{i}", i + 1
                keyseen.add(k)
                hint = params if params and params != "無" else ""
                elem = "{n}" in scpi
                if kind == "string":
                    hint = (hint + '；字串需加引號（例 "ABC"）').strip("；")
                if elem:
                    hint = (hint.replace("，X = 2,3,5-12", "").replace("X = 2,3,5-12", "")
                            + "；編號 n = 2, 3, 5~12").strip("；")
                qsyn = syntax.split(" / ")[-1]
                qarg = rw == "R" and bool(re.search(r"\?\s+<", qsyn))
                syn_disp = syntax
                if is_func:
                    syn_disp = ":" + name
                row = {
                    "key": k, "group": group_of(scpi), "name": name, "scpi": scpi,
                    "syntax": syn_disp, "params": params, "desc": desc, "page": page,
                    "set": rw in ("W", "RW"), "get": rw in ("R", "RW"),
                    "kind": kind, "opts": opts, "suggest": suggest, "hint": hint,
                    "chan": False, "channels": (1,), "elem": elem,
                    "qarg": qarg, "qn": 0,
                }
                row.update(OVERRIDES.get(scpi, {}))
                rows.append(row)
                by_scpi[scpi] = row

    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    unknown = [r["scpi"] for r in rows if r["group"] not in order]
    if unknown:
        raise SystemExit(f"未知群組：{unknown}")
    group_order = [g for g in GROUP_ORDER if any(r["group"] == g for r in rows)]

    out = os.path.join(HERE, "commands_2400.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write('"""Keithley Series 2400 SourceMeter SCPI 指令資料表（唯一權威來源）。\n\n'
                "資料係與 NotebookLM 對 Series 2400 SourceMeter User's Manual（第 16~18 章）逐子系統問答彙整，\n"
                "由 build_commands.py 自 _specs/*.txt 自動產生；請勿手改本檔，改來源或解析器後重跑。\n"
                "標頭編號以 {n} 代入（僅 CALCulate2:LIMit{n}，n = 2, 3, 5~12）。\"\"\"\n")
        f.write("from __future__ import annotations\n")
        f.write("from typing import List, Dict, Any\n\n")
        f.write("COMMANDS: List[Dict[str, Any]] = [\n")
        for r in rows:
            f.write("    %r,\n" % (r,))
        f.write("]\n\n")
        f.write("COMMAND_BY_KEY: Dict[str, Dict[str, Any]] = {c['key']: c for c in COMMANDS}\n\n")
        f.write("GROUP_ORDER = %r\n\n" % (group_order,))
        f.write('if __name__ == "__main__":\n')
        f.write("    assert len(COMMAND_BY_KEY) == len(COMMANDS), 'duplicate key'\n")
        f.write("    print(f'COMMANDS = {len(COMMANDS)} 條，群組 {len(GROUP_ORDER)} 個')\n")

    print(f"寫出 {out}")
    print(f"指令數：{len(rows)}")
    print("群組：", dict(Counter(r["group"] for r in rows)))
    print("kind 分佈：", dict(Counter(r["kind"] for r in rows)))
    print("含編號 {n}：", sum(1 for r in rows if r["elem"]), "；qarg：",
          [r["scpi"] for r in rows if r["qarg"]])


if __name__ == "__main__":
    main()
