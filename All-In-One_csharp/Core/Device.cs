using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Media;

namespace ScpiAllInOne.Core;

/// <summary>一台已連線的儀器：傳輸層 + 序列化鎖（可在背景執行緒送收）。</summary>
public sealed class Device : IDisposable
{
    private readonly IScpiIo _io;
    private readonly SemaphoreSlim _lock = new(1, 1);

    public string Resource { get; }
    public bool IsSimulated { get; }

    private Device(IScpiIo io, string resource, bool sim) { _io = io; Resource = resource; IsSimulated = sim; }

    public static Device Open(string resource) => new(new VisaSession(resource), resource, false);
    public static Device OpenSimulated(string idn) => new(new SimulatedInstrument(idn), "SIM", true);

    public async Task WriteAsync(string cmd)
    {
        await _lock.WaitAsync();
        try { await Task.Run(() => _io.Write(cmd)); }
        finally { _lock.Release(); }
    }

    public async Task<string> QueryAsync(string cmd)
    {
        await _lock.WaitAsync();
        try { return await Task.Run(() => _io.Query(cmd)); }
        finally { _lock.Release(); }
    }

    public void Dispose() => _io.Dispose();
}

/// <summary>
/// 通用虛擬儀器（僅以 <c>--sim</c> 啟動時使用）：記住每個標頭最後寫入的值，查詢時回傳；
/// *IDN? 回傳該儀器的模擬識別字串。
/// </summary>
internal sealed class SimulatedInstrument : IScpiIo
{
    private readonly Dictionary<string, string> _state = new(StringComparer.OrdinalIgnoreCase);

    public SimulatedInstrument(string idn)
    {
        _state["*IDN"] = idn + " (SIM)";
        _state["*OPC"] = "1";
        _state["SYSTem:ERRor"] = "0,\"No error\"";
    }

    public void Write(string command)
    {
        Thread.Sleep(10);
        string cmd = command.Trim();
        int sp = cmd.IndexOf(' ');
        string head = sp < 0 ? cmd : cmd[..sp];
        _state[head] = sp < 0 ? "1" : cmd[(sp + 1)..].Trim();
    }

    public string Query(string command)
    {
        Thread.Sleep(15);
        string head = command.Trim().Split(' ')[0].TrimEnd('?');
        return _state.TryGetValue(head, out var s) ? s : "0";
    }

    public void Dispose() { }
}

public sealed class LogEntry
{
    public string Time { get; init; } = "";
    public string Tag { get; init; } = "";
    public string Text { get; init; } = "";
    public string BrushKey { get; init; } = "Muted";
    public Brush Brush => (Brush)Application.Current.Resources[BrushKey];
}

/// <summary>
/// 每台儀器各自的工作狀態（切換儀器時保留）：連線、資源、掃描結果、篩選、目前指令、紀錄。
/// 因此可同時連線多台儀器。
/// </summary>
public sealed class InstrumentSession : INotifyPropertyChanged
{
    public InstrumentDef Def { get; }
    public string Name => Def.Name;

    public InstrumentSession(InstrumentDef def) { Def = def; }

    private Device? _device;
    public Device? Device
    {
        get => _device;
        set { _device = value; OnChanged(); OnChanged(nameof(IsConnected)); }
    }
    public bool IsConnected => _device != null;

    public string Idn { get; set; } = "";
    public string ResourceText { get; set; } = "GPIB0::9::INSTR";
    public List<string> ScanItems { get; set; } = new();
    public string? Group { get; set; }            // null = 全部
    public string Search { get; set; } = "";
    public string? CommandKey { get; set; }
    public string LastResponse { get; set; } = "—";
    public string ChList { get; set; } = "";
    public int Channel { get; set; } = 1;
    public int Element { get; set; } = 1;
    public ObservableCollection<LogEntry> Log { get; } = new();

    public void AddLog(string tag, string text, string brushKey)
    {
        Log.Add(new LogEntry { Time = DateTime.Now.ToString("HH:mm:ss.fff"), Tag = tag, Text = text, BrushKey = brushKey });
        if (Log.Count > 2000) Log.RemoveAt(0);
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnChanged([CallerMemberName] string? p = null) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(p));
}
