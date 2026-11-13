namespace Chroma62000P.Core;

/// <summary>介面文字翻譯（英文 / 繁體中文），鍵名與 Python 版 i18n.py 對應。</summary>
public static class I18n
{
    public static string Lang { get; private set; } = "en";
    public static event Action? Changed;

    public static void Set(string lang)
    {
        if (lang != "en" && lang != "zh" || lang == Lang) return;
        Lang = lang;
        Changed?.Invoke();
    }

    private static readonly Dictionary<string, (string En, string Zh)> S = new()
    {
        ["app_sub"]       = ("Programmable DC Power Supply  ·  {0} SCPI commands", "可程式直流電源供應器  ·  {0} 條 SCPI 指令"),
        ["conn_frame"]    = ("CONNECTION", "連線"),
        ["visa"]          = ("VISA resource", "VISA 資源"),
        ["scan"]          = ("Scan", "掃描"),
        ["scanning"]      = ("Scanning…", "掃描中…"),
        ["scan_fail"]     = ("Scan failed", "掃描失敗"),
        ["connect"]       = ("Connect", "連線"),
        ["connecting"]    = ("Connecting…", "連線中…"),
        ["disconnect"]    = ("Disconnect", "中斷連線"),
        ["connected"]     = ("Connected", "已連線"),
        ["disconnected"]  = ("Not connected", "未連線"),
        ["conn_fail"]     = ("Connection failed", "連線失敗"),
        ["sim_badge"]     = ("SIMULATION", "模擬模式"),
        ["commands"]      = ("COMMANDS", "指令"),
        ["search_ph"]     = ("Search commands…", "搜尋指令…"),
        ["theme"]         = ("Color theme", "色系"),
        ["group"]         = ("Group", "群組"),
        ["all"]           = ("All", "全部"),
        ["search_count"]  = ("{0} of {1}", "{0} / {1} 條"),
        ["search_none"]   = ("No matching command", "沒有符合的指令"),
        ["manual_p"]      = ("Manual p.{0}", "手冊 p.{0}"),
        ["syntax"]        = ("SYNTAX", "語法"),
        ["parameter"]     = ("PARAMETER", "參數"),
        ["no_param"]      = ("This command takes no parameter", "此指令沒有參數"),
        ["preview"]       = ("SCPI PREVIEW", "SCPI 預覽"),
        ["write"]         = ("Write", "寫入"),
        ["read"]          = ("Read", "讀取"),
        ["copy"]          = ("Copy", "複製"),
        ["copied"]        = ("Copied: {0}", "已複製：{0}"),
        ["missing_param"] = ("Please enter a parameter value", "請先輸入參數值"),
        ["not_connected"] = ("Connect to an instrument first", "請先連線儀器"),
        ["console"]       = ("CONSOLE", "主控台"),
        ["last_resp"]     = ("Last response", "最新回應"),
        ["clear"]         = ("Clear", "清除"),
        ["ready"]         = ("Ready", "就緒"),
        ["error"]         = ("Error", "錯誤"),
        ["access_rw"]     = ("Read / Write", "可讀寫"),
        ["access_w"]      = ("Write only", "僅寫入"),
        ["access_r"]      = ("Query only", "僅查詢"),
    };

    public static string T(string key, params object[] args)
    {
        if (!S.TryGetValue(key, out var e)) return key;
        string s = Lang == "zh" ? e.Zh : e.En;
        return args.Length > 0 ? string.Format(s, args) : s;
    }
}
