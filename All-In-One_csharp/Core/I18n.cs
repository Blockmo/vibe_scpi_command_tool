namespace ScpiAllInOne.Core;

/// <summary>介面文字翻譯（英文 / 繁體中文）。</summary>
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
        ["aio_title"]     = ("SCPI Command Tool", "SCPI 指令工具"),
        ["app_sub"]       = ("{0} instruments  ·  {1:N0} SCPI commands", "{0} 台儀器  ·  {1:N0} 條 SCPI 指令"),
        ["window_title"]  = ("SCPI Command Tool", "SCPI 指令工具"),
        // 儀器選擇
        ["instrument_frame"] = ("INSTRUMENT", "儀器"),
        ["category"]      = ("Category", "分類"),
        ["instrument"]    = ("Instrument", "儀器"),
        ["cat_psu"]       = ("Power Supply", "電源供應器"),
        ["cat_daq"]       = ("DAQ", "資料擷取 DAQ"),
        ["cat_eload"]     = ("E-Load", "電子負載"),
        ["cat_scope"]     = ("Oscilloscope", "示波器"),
        ["cat_fgen"]      = ("Function Generator", "函數信號產生器"),
        ["cat_meter"]     = ("Meter / SMU", "電錶 / 電源量測單元"),
        ["aio_info"]      = ("{0}  ·  {1} commands", "{0}　·　{1} 條指令"),
        ["conn_count"]    = ("Connected: {0}", "已連線：{0} 台"),
        ["conn_none"]     = ("No instrument connected", "尚無已連線儀器"),
        // 連線
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
        // 指令
        ["commands"]      = ("COMMANDS", "指令"),
        ["group"]         = ("Group", "群組"),
        ["search_ph"]     = ("Search commands…", "搜尋指令…"),
        ["all"]           = ("All", "全部"),
        ["search_count"]  = ("{0} of {1}", "{0} / {1} 條"),
        ["search_none"]   = ("No matching command", "沒有符合的指令"),
        ["manual_p"]      = ("Manual p.{0}", "手冊 p.{0}"),
        ["syntax"]        = ("SYNTAX", "語法"),
        ["parameter"]     = ("PARAMETER", "參數"),
        ["no_param"]      = ("This command takes no parameter", "此指令沒有參數"),
        ["qarg_hint"]     = ("optional query argument", "選填的查詢引數"),
        ["position"]      = ("POSITION", "位置"),
        ["channel"]       = ("Channel", "通道"),
        ["seq_elem"]      = ("Seq element n", "序列元素 n"),
        ["index_n"]       = ("Index n", "編號 n"),
        ["chlist"]        = ("Channel list (@)", "通道清單 (@)"),
        ["chlist_ph"]     = ("e.g. 101:105 or 1,2", "例：101:105 或 1,2"),
        ["preview"]       = ("SCPI PREVIEW", "SCPI 預覽"),
        ["write"]         = ("Write", "寫入"),
        ["read"]          = ("Read", "讀取"),
        ["copy"]          = ("Copy", "複製"),
        ["copied"]        = ("Copied: {0}", "已複製：{0}"),
        ["missing_param"] = ("Please enter a parameter value", "請先輸入參數值"),
        ["not_connected"] = ("Connect to the instrument first", "請先連線這台儀器"),
        // 主控台
        ["console"]       = ("CONSOLE", "主控台"),
        ["last_resp"]     = ("Last response", "最新回應"),
        ["clear"]         = ("Clear", "清除"),
        ["ready"]         = ("Ready", "就緒"),
        ["access_rw"]     = ("Read / Write", "可讀寫"),
        ["access_w"]      = ("Write only", "僅寫入"),
        ["access_r"]      = ("Query only", "僅查詢"),
        ["theme"]         = ("Color theme", "色系"),
        ["font_size"]     = ("Font size", "字體大小"),
    };

    public static string T(string key, params object[] args)
    {
        if (!S.TryGetValue(key, out var e)) return key;
        string s = Lang == "zh" ? e.Zh : e.En;
        return args.Length > 0 ? string.Format(s, args) : s;
    }
}
