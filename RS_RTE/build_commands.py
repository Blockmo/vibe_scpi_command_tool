# -*- coding: utf-8 -*-
"""
由 _specs/*.txt（與 NotebookLM 協作取得的 R&S RTE 指令規格）自動
產生 commands_rte.py 指令資料表（AFG 家族結構：編號以標頭 {n} 代入）。

_specs 每列格式（@@ 分隔，7 欄）：
    名稱 @@ 語法 @@ 參數 @@ 用途 @@ 頁碼 @@ RW(R/W/RW) @@ N(本機編號在標頭)
"""
from __future__ import annotations

import os
import re
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(HERE, "_specs")

# 檔案 -> 功能群組
FILE_GROUP = {
    "01": "Common/Run", "02": "TIMebase/ACQuire", "03": "CHANnel",
    "04": "PROBe", "05": "TRIGger", "06": "DISPlay/LAYout",
    "07": "ZOOM/REFCurve", "08": "MATH", "09": "History", "10": "CURSor",
    "11": "MEASurement", "12": "SEARch",
}

# 一列的正規表示式：以末三欄（頁碼 / RW / Y|N）作為穩固錨點
ROW_RE = re.compile(
    r"(?P<name>[^@]+?)@@(?P<syntax>[F]+?)@@(?P<params>[F]+?)@@(?P<desc>[F]+?)@@"
    r"\s*(?P<page>[0-9][0-9.\-]*)\s*@@\s*(?P<rw>RW|R|W)\s*@@\s*(?P<ch>Y|N)".replace(
        "[F]", r"(?:[^@]|@(?!@))"),
    re.DOTALL,
)

NAME_OK = re.compile(r"^[\*\[A-Za-z]")

# NotebookLM 把部分 SCPI 節點渲染成字母/圖示 emoji，還原回正確助記符
EMOJI = {
    "\U0001F170": ":A:",      # 🅰 TRIGger:A:
    "\U0001F171": ":B:",      # 🅱 TRIGger:B:
    "\U0001F3F7": ":LABel:",  # 🏷 LABel 節點
    "\U0001F68C": ":BUS:",    # 🚌 BUS 節點
    "\U0001F194": ":ID:",     # 🆔 ID 節點
    # CLI 把 :tv: :eye: :ab: :abcd: 等 shortcode 渲染成 emoji
    "\U0001F4FA": ":TV:",     # 📺 TRIGger<m>:TV:
    "\U0001F441": ":EYE:",    # 👁 MEASurement<m>:EYE:
    "\U0001F18E": ":AB:",     # 🆎 ...:AB:LOGic
    "\U0001F521": ":ABCD:",   # 🔡 ...:ABCD:LOGic
    "️": "",             # emoji 變體選擇符
}


def desmoji(s: str) -> str:
    for e, v in EMOJI.items():
        s = s.replace(e, v)
    return re.sub(r":{2,}", ":", s)   # 保險：避免意外雙冒號


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def name_to_scpi(name: str) -> str:
    """R&S 標頭含數值後綴 <m>/<n>：可省略節點 [..] 整段去除（SCPI 預設值）；
    第一個後綴 -> {n}（GUI 編號欄代入），其餘 -> 1。
    例外：TRIGger<m>:...<n> 以後面的後綴（如 LEVel<n> 來源通道）作為 {n}，TRIGger 固定 1。"""
    s = name.strip().rstrip("?").strip()
    # 含數值後綴的可省略節點（如 [:WAVeform<n>]）整段去除（預設 1）；
    # 其他可省略關鍵字（如 [:STATe]）保留展開 —— 寫全一定合法，且避免不同指令撞名
    s = re.sub(r"\[[^\[\]]*<[^>]*>[^\[\]]*\]", "", s)
    s = s.replace("[", "").replace("]", "")
    s = clean(s).replace(" ", "")
    sufs = list(re.finditer(r"<[^>]*>", s))
    pick = 0
    if len(sufs) > 1 and re.match(r"TRIG(ger)?<", s, re.I):
        pick = 1
    idx = [0]

    def rep(_m):
        i = idx[0]
        idx[0] += 1
        return "{n}" if i == pick else "1"

    s = re.sub(r"<[^>]*>", rep, s)
    return re.sub(r":{2,}", ":", s).strip(":") if not s.startswith("*") else s


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


def classify_from_params(params: str):
    """Chroma 慣例：選項列在「參數」欄（如 'OFF, ON, 0, 1'、'FAST|0, NORMAL|1'）。
    依參數欄判斷 bool / enum / numeric / None(無法判斷)。"""
    p = (params or "").strip()
    if not p or p in ("無", "-"):
        return None
    # 頂層分隔：有逗號→逗號(Chroma 風，選項內可能含 |別名)；否則→管線(Keithley 風)
    if "," in p or "、" in p:
        toks = [t.strip() for t in re.split(r"[,、]", p) if t.strip()]
        strip_alias = True
    else:
        toks = [t.strip() for t in p.split("|") if t.strip()]
        strip_alias = False
    bases = []
    for t in toks:
        b = re.sub(r"\(.*?\)", "", t)
        if strip_alias:
            b = re.sub(r"\|\s*\d+", "", b)
        b = b.strip()
        if b:
            bases.append(b)
    up = {b.upper() for b in bases}
    if up and up <= {"ON", "OFF", "0", "1"} and (up & {"ON", "OFF"}):
        return ("bool", None)
    # 數值範圍徵兆
    if re.search(r"[~]|NRf|NR1|NR2|\bto\b|至|範圍|\d\s*(A|V|W|Ω|OHM|Hz|HZ|s|ms|us|%|mV|mA)",
                 params, re.I):
        return ("numeric", None)
    # 離散文字選項（≥2 個、皆以字母開頭）
    opts = [b for b in bases if re.match(r"^[A-Za-z]", b)]
    if len(opts) >= 2 and len(opts) == len(bases):
        return ("enum", opts)
    return None


def infer_kind(syntax: str, params: str = ""):
    """回傳 (kind, opts)。kind: none/bool/numeric/enum/string/raw。"""
    core = param_spec(syntax)
    has_val = ("<" in core) or ("{" in core)
    if len(re.findall(r"<[^>]+>", core)) > 1 and "," in core:
        return "raw", None        # R&S 多參數（如 <SearchName>, <State>）-> 逗號分隔整串輸入
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
        # 無大括號：改由參數欄判斷（Chroma 慣例）
        byp = classify_from_params(params)
        if byp:
            return byp
        kind = "numeric"
    if re.search(r"<[^>]*(name|string|label|text|file|path|data|address|host|"
                 r"expression|color)", core, re.I) or re.search(r"\bstring\b", params, re.I):
        kind = "string"
    if kind in ("numeric", "string") and core.count("<") > 1 and "," in core:
        kind = "raw"
    return kind, None


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
        text = desmoji(text)      # 還原 emoji 節點
        # CLI 輸出在 80 欄硬斷行（可能斷在 token 中，如 "113\n0"、"@\n@"）；
        # 斷在空白處時行尾保留空白，故以空字串接回
        blob = text.replace("\r", "").replace("\n", "")
        for m in ROW_RE.finditer(blob):
            raw_name = clean(m.group("name"))
            # 修掉斷行把前一列 ch 欄(N/Y)黏到名稱前的情形（如 "N OUTPut"/"NOUTPut" -> OUTPut）
            raw_name = re.sub(r"^[NY]\s*(?=[A-Z*])", "", raw_name).strip()
            if not NAME_OK.match(raw_name) or len(raw_name) > 90:
                continue
            syntax = clean(m.group("syntax"))
            params = clean(m.group("params"))
            desc = clean(m.group("desc"))
            page = m.group("page")      # Chroma 頁碼為「章-頁」字串，如 5-20
            rw = m.group("rw")
            ch = m.group("ch") == "Y" or "(@" in syntax
            kind, opts = infer_kind(syntax, params)
            suggest = None
            if kind == "numeric":
                s = [t for t in ("MINimum", "MAXimum", "AUTO", "DEFault")
                     if re.search(t[:3], param_spec(syntax), re.I)]
                suggest = s or None
            hint = params if params and params != "無" else ""
            core = param_spec(syntax)
            nargs = len(re.findall(r"<[^>]+>", core))
            qn = 0
            if kind == "raw" and nargs > 1 and "," in core:
                hint = core + (" ; " + hint if hint else "")
                if rw == "RW":
                    qn = nargs - 1        # 查詢帶前導參數（如 ...? <SearchName>）
            # 查詢語法本身帶參數（如 SEARch:RCOunt? <SearchName>）
            qsyn = re.search(r"\?\s*[\[<]", syntax)
            scpi = name_to_scpi(raw_name)
            # 允許 {n} 編號佔位；其餘 <> { } 或殘留 * 視為斷行雜訊 -> 跳過
            chk = scpi.replace("{n}", "")
            if not scpi or re.search(r"[<>{}]", chk) or "*" in chk[1:]:
                continue
            if scpi in seen:              # 跨批次重疊 -> 以 scpi 去重
                continue
            seen.add(scpi)
            key = slug(scpi)
            k, i = key, 2
            while k in keyseen:
                k = f"{key}_{i}"
                i += 1
            keyseen.add(k)
            rows.append({
                "key": k, "group": group, "name": raw_name, "scpi": scpi,
                "syntax": syntax, "params": params, "desc": desc,
                "page": page, "set": rw in ("W", "RW"),
                "get": rw in ("R", "RW"), "kind": kind, "opts": opts,
                "suggest": suggest, "hint": hint,
                "chan": False, "channels": (1,), "elem": "{n}" in scpi,
                "qarg": bool(qn) or (rw != "W" and bool(qsyn)),
                "qn": qn,
            })

    # 群組順序（依檔案順序首見）
    group_order = []
    for r in rows:
        if r["group"] not in group_order:
            group_order.append(r["group"])

    out = os.path.join(HERE, "commands_rte.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write('"""R&S RTE SCPI 指令資料表（唯一權威來源）。\n\n'
                "資料係與 NotebookLM 對 R&S RTE 數位示波器使用手冊（第 17 章）逐群組問答彙整，\n"
                "由 build_commands.py 自 _specs/*.txt 自動產生；請勿手改本檔，改來源或解析器後重跑。\n"
                '標頭編號以 {n} 代入（如 CHANnel{n}、MEASurement{n}）。涵蓋所選群組之指令。"""\n')
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
    print(f"指令數：{len(rows)}；群組：{group_order}")
    from collections import Counter
    print("kind 分佈：", dict(Counter(r["kind"] for r in rows)))
    print("含編號 {n}：", sum(1 for r in rows if r["elem"]))


if __name__ == "__main__":
    main()
