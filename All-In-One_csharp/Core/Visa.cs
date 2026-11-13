using System.Runtime.InteropServices;
using System.Text;

namespace ScpiAllInOne.Core;

/// <summary>
/// 直接以 P/Invoke 呼叫系統 VISA（NI-VISA / Keysight IO Libraries 安裝的 visa32.dll），
/// 不需要任何 NuGet 套件。64 位元程式會載入 System32\visa32.dll（64 位元版）。
/// </summary>
internal static class VisaNative
{
    private const string Dll = "visa32.dll";

    public const int VI_SUCCESS = 0;
    public const int VI_NULL = 0;
    public const uint VI_ATTR_TMO_VALUE = 0x3FFF001A;
    public const uint VI_ATTR_TERMCHAR = 0x3FFF0018;
    public const uint VI_ATTR_TERMCHAR_EN = 0x3FFF0038;
    public const uint VI_ATTR_ASRL_END_IN = 0x3FFF00B3;
    public const int VI_ERROR_RSRC_NFOUND = unchecked((int)0xBFFF0011);
    public const int VI_SUCCESS_MAX_CNT = 0x3FFF0006;
    public const int VI_SUCCESS_TERM_CHAR = 0x3FFF0005;

    [DllImport(Dll, EntryPoint = "viOpenDefaultRM")]
    public static extern int viOpenDefaultRM(out int sesn);

    [DllImport(Dll, EntryPoint = "viOpen", CharSet = CharSet.Ansi)]
    public static extern int viOpen(int sesn, string rsrcName, int accessMode, int timeout, out int vi);

    [DllImport(Dll, EntryPoint = "viClose")]
    public static extern int viClose(int vi);

    [DllImport(Dll, EntryPoint = "viWrite")]
    public static extern int viWrite(int vi, byte[] buf, int count, out int retCount);

    [DllImport(Dll, EntryPoint = "viRead")]
    public static extern int viRead(int vi, byte[] buf, int count, out int retCount);

    [DllImport(Dll, EntryPoint = "viSetAttribute")]
    public static extern int viSetAttribute(int vi, uint attribute, int attrState);

    [DllImport(Dll, EntryPoint = "viFindRsrc", CharSet = CharSet.Ansi)]
    public static extern int viFindRsrc(int sesn, string expr, out int findList, out int retCnt, StringBuilder desc);

    [DllImport(Dll, EntryPoint = "viFindNext", CharSet = CharSet.Ansi)]
    public static extern int viFindNext(int findList, StringBuilder desc);

    [DllImport(Dll, EntryPoint = "viStatusDesc", CharSet = CharSet.Ansi)]
    public static extern int viStatusDesc(int vi, int status, StringBuilder desc);
}

public sealed class VisaException : Exception
{
    public int Status { get; }
    public VisaException(int status, string message) : base(message) { Status = status; }
}

/// <summary>傳輸層介面：真實 VISA 與模擬器共用。</summary>
public interface IScpiIo : IDisposable
{
    void Write(string command);
    string Query(string command);
}

/// <summary>一個 VISA 訊息式資源（GPIB / USB / TCPIP / ASRL）。</summary>
public sealed class VisaSession : IScpiIo
{
    private readonly int _rm;
    private readonly int _vi;
    private bool _closed;

    public string Resource { get; }

    public VisaSession(string resource, int timeoutMs = 5000)
    {
        Resource = resource;
        Check(VisaNative.viOpenDefaultRM(out _rm), 0, "viOpenDefaultRM");
        int st = VisaNative.viOpen(_rm, resource, 0, 2000, out _vi);
        if (st < 0)
        {
            string msg = Describe(_rm, st);
            VisaNative.viClose(_rm);
            throw new VisaException(st, $"viOpen({resource}): {msg}");
        }
        VisaNative.viSetAttribute(_vi, VisaNative.VI_ATTR_TMO_VALUE, timeoutMs);
        VisaNative.viSetAttribute(_vi, VisaNative.VI_ATTR_TERMCHAR, '\n');
        VisaNative.viSetAttribute(_vi, VisaNative.VI_ATTR_TERMCHAR_EN, 1);
        if (resource.StartsWith("ASRL", StringComparison.OrdinalIgnoreCase))
            VisaNative.viSetAttribute(_vi, VisaNative.VI_ATTR_ASRL_END_IN, 2); // VI_ASRL_END_TERMCHAR
    }

    public int TimeoutMs
    {
        set => VisaNative.viSetAttribute(_vi, VisaNative.VI_ATTR_TMO_VALUE, value);
    }

    public void Write(string command)
    {
        byte[] data = Encoding.ASCII.GetBytes(command + "\n");
        Check(VisaNative.viWrite(_vi, data, data.Length, out _), _vi, "viWrite");
    }

    public string Read()
    {
        var sb = new StringBuilder();
        byte[] buf = new byte[4096];
        while (true)
        {
            int st = VisaNative.viRead(_vi, buf, buf.Length, out int n);
            Check(st, _vi, "viRead");
            sb.Append(Encoding.ASCII.GetString(buf, 0, n));
            if (st != VisaNative.VI_SUCCESS_MAX_CNT) break;
        }
        return sb.ToString().TrimEnd('\r', '\n');
    }

    public string Query(string command)
    {
        Write(command);
        return Read().Trim();
    }

    public void Dispose()
    {
        if (_closed) return;
        _closed = true;
        VisaNative.viClose(_vi);
        VisaNative.viClose(_rm);
    }

    private static void Check(int status, int vi, string where)
    {
        if (status < 0) throw new VisaException(status, $"{where}: {Describe(vi, status)}");
    }

    private static string Describe(int vi, int status)
    {
        var sb = new StringBuilder(512);
        try { VisaNative.viStatusDesc(vi, status, sb); } catch { /* ignore */ }
        return sb.Length > 0 ? sb.ToString() : $"VISA error 0x{status:X8}";
    }

    // ------------------------------------------------------------------ //
    // 掃描
    // ------------------------------------------------------------------ //

    /// <summary>列出所有 VISA 資源（GPIB → USB → TCPIP → VXI → ASRL 排序），非 ASRL 者附 *IDN?。</summary>
    public static List<ScanResult> Scan(int idnTimeoutMs = 1500)
    {
        var names = new List<string>();
        Check(VisaNative.viOpenDefaultRM(out int rm), 0, "viOpenDefaultRM");
        try
        {
            var desc = new StringBuilder(256);
            int st = VisaNative.viFindRsrc(rm, "?*::INSTR", out int list, out int cnt, desc);
            if (st == VisaNative.VI_ERROR_RSRC_NFOUND) return new List<ScanResult>();
            Check(st, rm, "viFindRsrc");
            names.Add(desc.ToString());
            for (int i = 1; i < cnt; i++)
            {
                desc.Clear();
                if (VisaNative.viFindNext(list, desc) < 0) break;
                names.Add(desc.ToString());
            }
            VisaNative.viClose(list);
        }
        finally { VisaNative.viClose(rm); }

        static int Rank(string r)
        {
            string u = r.ToUpperInvariant();
            if (u.StartsWith("GPIB")) return 0;
            if (u.StartsWith("USB")) return 1;
            if (u.StartsWith("TCPIP")) return 2;
            if (u.StartsWith("VXI")) return 3;
            if (u.StartsWith("ASRL")) return 5;
            return 4;
        }

        var results = new List<ScanResult>();
        foreach (string name in names.Distinct().OrderBy(Rank).ThenBy(n => n, StringComparer.OrdinalIgnoreCase))
        {
            string idn = "";
            if (!name.StartsWith("ASRL", StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    using var s = new VisaSession(name, idnTimeoutMs);
                    idn = s.Query("*IDN?");
                }
                catch { /* 無回應的資源只列名稱 */ }
            }
            results.Add(new ScanResult(name, idn));
        }
        return results;
    }
}

public sealed record ScanResult(string Resource, string Idn)
{
    public override string ToString() => string.IsNullOrEmpty(Idn) ? Resource : $"{Resource}    {Idn}";
}
