using System.Globalization;

namespace Chroma62000P.Core;

/// <summary>
/// 虛擬 62000P（僅以 <c>--sim</c> 啟動時使用）：記住寫入的設定值、查詢時回傳，
/// 量測值依設定電壓/電流加上少量雜訊，讓量測面板有真實感。
/// </summary>
internal sealed class SimulatedPsu : IScpiIo
{
    private readonly Dictionary<string, string> _state = new(StringComparer.OrdinalIgnoreCase);
    private readonly Random _rng = new();
    private const double LoadOhms = 4.7;

    public SimulatedPsu()
    {
        _state["*IDN"] = Chroma62000PDevice.SimIdn + " (SIM)";
        _state["SOURce:VOLTage"] = "12";
        _state["SOURce:CURRent"] = "5";
        _state["CONFigure:OUTPut"] = "OFF";
        _state["SYSTem:ERRor"] = "0,\"No error\"";
        _state["*OPC"] = "1";
        _state["*STB"] = "0";
        _state["*ESR"] = "0";
        _state["FETCh:STATus"] = "0";
    }

    public void Write(string command)
    {
        Thread.Sleep(15);
        string cmd = command.Trim();
        int sp = cmd.IndexOf(' ');
        string head = sp < 0 ? cmd : cmd[..sp];
        string arg = sp < 0 ? "" : cmd[(sp + 1)..].Trim();
        if (head.Equals("*RST", StringComparison.OrdinalIgnoreCase))
        {
            _state["CONFigure:OUTPut"] = "OFF";
            _state["SOURce:VOLTage"] = "0";
            _state["SOURce:CURRent"] = "0";
            return;
        }
        if (head.Equals("ABORt", StringComparison.OrdinalIgnoreCase))
        {
            _state["CONFigure:OUTPut"] = "OFF";
            return;
        }
        _state[head] = arg.Length == 0 ? "1" : arg;
    }

    public string Query(string command)
    {
        Thread.Sleep(20);
        string head = command.Trim().Split(' ')[0].TrimEnd('?');
        string u = head.ToUpperInvariant();

        bool on = Get("CONFigure:OUTPut").Equals("ON", StringComparison.OrdinalIgnoreCase)
                  || Get("CONFigure:OUTPut") == "1";
        double vSet = Num("SOURce:VOLTage"), iSet = Num("SOURce:CURRent");
        double i = on ? Math.Min(vSet / LoadOhms, iSet) : 0;
        double v = on ? (i >= iSet ? iSet * LoadOhms : vSet) : 0;

        if (u.EndsWith(":VOLTAGE") && (u.StartsWith("MEAS") || u.StartsWith("FETC")))
            return Fmt(v + Noise(v, 0.0008));
        if (u.EndsWith(":CURRENT") && (u.StartsWith("MEAS") || u.StartsWith("FETC")))
            return Fmt(i + Noise(i, 0.0015));
        if (u.EndsWith(":POWER") && (u.StartsWith("MEAS") || u.StartsWith("FETC")))
            return Fmt(v * i + Noise(v * i, 0.002));
        if (u == "FETCH:STATUS" || u == "FETC:STAT")
            return on ? (i >= iSet ? "CC" : "CV") : "OFF";

        return _state.TryGetValue(head, out var s) ? s : "0";
    }

    private string Get(string k) => _state.TryGetValue(k, out var s) ? s : "";

    private double Num(string k) =>
        double.TryParse(Get(k), NumberStyles.Float, CultureInfo.InvariantCulture, out var d) ? d : 0;

    private double Noise(double x, double rel) => (_rng.NextDouble() - 0.5) * 2 * rel * Math.Max(Math.Abs(x), 0.01);

    private static string Fmt(double d) => d.ToString("0.0000", CultureInfo.InvariantCulture);

    public void Dispose() { }
}
