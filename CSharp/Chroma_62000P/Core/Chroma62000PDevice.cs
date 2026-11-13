using System.Globalization;

namespace Chroma62000P.Core;

/// <summary>
/// Chroma 62000P 控制引擎（資料表驅動），邏輯與 Python 版 instrument.py 一致：
/// 每條指令以 <see cref="BuildWrite"/> / <see cref="BuildQuery"/> 組字串，再送給傳輸層。
/// 62000P 為單輸出電源，指令不需選擇通道。
/// </summary>
public sealed class Chroma62000PDevice : IDisposable
{
    public const string Model = "Chroma 62000P";
    public const string SimIdn = "Chroma ATE,62012P-80-60,SIM0000,1.00";

    private static readonly HashSet<string> Special = new(StringComparer.OrdinalIgnoreCase)
    { "MIN", "MINIMUM", "MAX", "MAXIMUM", "INF", "INFINITY", "DEF", "DEFAULT", "AUTO", "ONCE" };

    private readonly IScpiIo _io;
    private readonly SemaphoreSlim _lock = new(1, 1);

    public bool IsSimulated { get; }
    public string Resource { get; }

    private Chroma62000PDevice(IScpiIo io, string resource, bool sim)
    {
        _io = io; Resource = resource; IsSimulated = sim;
    }

    public static Chroma62000PDevice Open(string resource) =>
        new(new VisaSession(resource), resource, false);

    public static Chroma62000PDevice OpenSimulated() =>
        new(new SimulatedPsu(), "SIM", true);

    // ------------------------------------------------------------------ //
    // SCPI 字串組合（不需要連線，Copy Command 也用這裡）
    // ------------------------------------------------------------------ //
    public static string ParamToken(CommandSpec c, string? value)
    {
        if (c.Kind == "none" || string.IsNullOrWhiteSpace(value)) return "";
        string v = value.Trim();
        switch (c.Kind)
        {
            case "bool":
                string u = v.ToUpperInvariant();
                if (u is "ON" or "OFF" or "1" or "0") return u;
                throw new ArgumentException($"Invalid ON/OFF value: {value}");
            case "numeric":
                if (Special.Contains(v)) return v.ToUpperInvariant();
                return v; // 原樣送出（避免整數被轉成 32.0）
            default:      // enum / raw
                return v;
        }
    }

    public static string BuildWrite(CommandSpec c, string? value)
    {
        string p = ParamToken(c, value);
        return p.Length == 0 ? c.Scpi : $"{c.Scpi} {p}";
    }

    public static string BuildQuery(CommandSpec c) => c.Scpi + "?";

    // ------------------------------------------------------------------ //
    // 傳輸（序列化，可在背景執行緒呼叫）
    // ------------------------------------------------------------------ //
    public async Task WriteAsync(string command)
    {
        await _lock.WaitAsync();
        try { await Task.Run(() => _io.Write(command)); }
        finally { _lock.Release(); }
    }

    public async Task<string> QueryAsync(string command)
    {
        await _lock.WaitAsync();
        try { return await Task.Run(() => _io.Query(command)); }
        finally { _lock.Release(); }
    }

    public Task<string> IdnAsync() => QueryAsync("*IDN?");

    public void Dispose() => _io.Dispose();

    public static bool TryParseNumber(string s, out double v) =>
        double.TryParse(s.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out v);
}
