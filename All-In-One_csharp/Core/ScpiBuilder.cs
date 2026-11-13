namespace ScpiAllInOne.Core;

/// <summary>位置欄位：通道清單 (@…)、通道 {ch}、編號 {n}。</summary>
public sealed record Position(string? ChList = null, int Channel = 1, int Element = 1);

/// <summary>
/// SCPI 組字串引擎：
/// <list type="bullet">
/// <item>ChList 型（DAQ973A / 34970 / E36300 / 2231A / E3633A / Chroma）：參數 = [值, (@通道清單)] 以逗號相接；
///   寫入 <c>SCPI 參數</c>、查詢 <c>SCPI? 參數</c>（值只在查詢語法接受時才帶，見 ChListQueryValue）。</item>
/// <item>Index 型（AFG31000 / AFG3000 / MSO5 / DPO7 / R&amp;S RTE / Series 2400）：標頭 {ch}/{n} 代入；寫入 <c>標頭 值</c>；
///   查詢 <c>標頭?</c>，qarg 指令帶引數時為 <c>標頭? 引數</c>。</item>
/// </list>
/// 數值一律原樣送出（MIN/MAX 等關鍵字轉大寫），避免 32 被送成 32.0。
/// </summary>
public static class ScpiBuilder
{
    private static readonly HashSet<string> Special = new(StringComparer.OrdinalIgnoreCase)
    { "MIN", "MINIMUM", "MAX", "MAXIMUM", "INF", "INFINITY", "DEF", "DEFAULT", "AUTO", "ONCE" };

    public static string NumberToken(string v)
    {
        v = v.Trim();
        return Special.Contains(v) ? v.ToUpperInvariant() : v;
    }

    public static string BoolToken(string v)
    {
        string s = v.Trim().ToUpperInvariant();
        if (s is "ON" or "OFF" or "1" or "0") return s;
        throw new ArgumentException($"Invalid ON/OFF value: {v}");
    }

    public static string ChListToken(string s)
    {
        s = s.Trim();
        if (s.Length == 0) return "";
        if (s.StartsWith("(@")) return s;
        return $"(@{s.TrimStart('@')})";
    }

    private static string ValueToken(CommandSpec c, string v) => c.Kind switch
    {
        "bool" => BoolToken(v),
        "numeric" => NumberToken(v),
        _ => v,
    };

    // ------------------------------------------------------------------ //
    // ChList 型
    // ------------------------------------------------------------------ //
    private static string ChListParam(CommandSpec c, string? value, string? chList)
    {
        var parts = new List<string>();
        if (c.Kind != "none" && !string.IsNullOrWhiteSpace(value)) parts.Add(ValueToken(c, value.Trim()));
        if (c.ChList && !string.IsNullOrWhiteSpace(chList)) parts.Add(ChListToken(chList));
        return string.Join(",", parts);
    }

    /// <summary>
    /// 通道清單型查詢要帶的值：只在查詢語法接受參數時才帶，
    /// 避免把寫入值送成 OUTP? ON。僅查詢指令照原樣帶；讀寫兩用指令依 qsel 取欄位，或只帶 qopts 關鍵字。
    /// </summary>
    private static string? ChListQueryValue(CommandSpec c, string? value)
    {
        if (string.IsNullOrWhiteSpace(value) || !c.QArg) return null;
        if (!c.CanSet) return value;
        if (c.QSel is { Count: > 0 } sel)
        {
            var parts = value.Split(',').Select(p => p.Trim()).ToArray();
            if (parts.Length <= sel.Max()) return value.Trim();
            return string.Join(",", sel.Select(i => parts[i]));
        }
        string v = value.Trim().ToUpperInvariant();
        foreach (var opt in c.QOpts ?? new List<string>())
        {
            string shortForm = new string(opt.Where(ch => char.IsUpper(ch) || char.IsDigit(ch)).ToArray());
            if (v == opt.ToUpperInvariant() || v == shortForm) return v;
        }
        return null;
    }

    // ------------------------------------------------------------------ //
    // Index 型
    // ------------------------------------------------------------------ //
    public static string Header(CommandSpec c, Position pos)
    {
        if (c.Chan && c.Channels is { Count: > 0 } chs && !chs.Contains(pos.Channel))
            throw new ArgumentException($"channel must be one of ({string.Join(", ", chs)}), got {pos.Channel}");
        return c.Scpi.Replace("{ch}", pos.Channel.ToString()).Replace("{n}", pos.Element.ToString());
    }

    // ------------------------------------------------------------------ //
    // 公開 API
    // ------------------------------------------------------------------ //
    /// <summary>寫入是否缺參數（ChList 型若有填通道清單則可不填值）。</summary>
    public static bool MissingValue(CmdStyle st, CommandSpec c, string? value, Position pos) =>
        c.Kind != "none" && string.IsNullOrWhiteSpace(value)
        && !(st == CmdStyle.ChList && c.ChList && !string.IsNullOrWhiteSpace(pos.ChList));

    public static string BuildWrite(CmdStyle st, CommandSpec c, string? value, Position pos)
    {
        if (!c.CanSet) throw new InvalidOperationException($"{c.Name} does not support write (query-only)");
        if (st == CmdStyle.ChList)
        {
            string p = ChListParam(c, value, pos.ChList);
            return p.Length == 0 ? c.Scpi : $"{c.Scpi} {p}";
        }
        string header = Header(c, pos);
        if (c.Kind == "none") return header;
        if (string.IsNullOrWhiteSpace(value)) throw new ArgumentException($"{c.Name} requires a value");
        return $"{header} {ValueToken(c, value.Trim())}";
    }

    public static string BuildQuery(CmdStyle st, CommandSpec c, string? value, Position pos)
    {
        if (!c.CanGet) throw new InvalidOperationException($"{c.Name} does not support read (set-only)");
        if (st == CmdStyle.ChList)
        {
            string p = ChListParam(c, ChListQueryValue(c, value), pos.ChList);
            return p.Length == 0 ? c.Scpi + "?" : $"{c.Scpi}? {p}";
        }
        string header = Header(c, pos);
        if (c.QArg && !string.IsNullOrWhiteSpace(value))
        {
            if (c.QN > 0)
            {
                var parts = value.Split(',').Select(p => p.Trim()).ToArray();
                if (parts.Length > c.QN) value = string.Join(", ", parts.Take(c.QN));
            }
            string tok = c.Kind == "numeric" ? NumberToken(value) : value.Trim();
            return $"{header}? {tok}";
        }
        return header + "?";
    }
}
