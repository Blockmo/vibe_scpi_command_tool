namespace ScpiAllInOne.Core;

/// <summary>儀器範本：決定位置欄位與 SCPI 組字串方式。</summary>
public enum CmdStyle
{
    /// <summary>通道清單型：值在前、(@通道清單) 在後，以逗號相接；查詢只在語法接受時才帶值。</summary>
    ChList,
    /// <summary>標頭編號型：標頭內 {ch}/{n} 代入通道與編號；部分查詢可帶引數。</summary>
    Index,
}

/// <summary>一台儀器的定義（對應 Python 版 All-In-One 的 INSTRUMENTS）。</summary>
public sealed class InstrumentDef
{
    public required string Name { get; init; }
    public required string DataId { get; init; }      // Data/<DataId>.json，也是原 Python 資料夾名
    public required CmdStyle Style { get; init; }
    public required string SimIdn { get; init; }
    public required string KindEn { get; init; }
    public required string KindZh { get; init; }
    /// <summary>編號欄位的標籤 i18n 鍵（index_n / seq_elem）</summary>
    public string ElemLabelKey { get; init; } = "index_n";

    public string Kind => I18n.Lang == "zh" ? KindZh : KindEn;

    private List<CommandSpec>? _commands;
    public IReadOnlyList<CommandSpec> Commands => _commands ??= CommandSpec.LoadResource(DataId);

    private List<string>? _groups;
    public IReadOnlyList<string> Groups => _groups ??= Commands.Select(c => c.Group).Distinct().ToList();
}

public sealed record Category(string LabelKey, IReadOnlyList<InstrumentDef> Instruments);

public static class InstrumentCatalog
{
    private static InstrumentDef Def(string name, string id, CmdStyle st, string idn, string en, string zh, string elem = "index_n") =>
        new() { Name = name, DataId = id, Style = st, SimIdn = idn, KindEn = en, KindZh = zh, ElemLabelKey = elem };

    public static readonly IReadOnlyList<Category> Categories = new[]
    {
        new Category("cat_psu", new[]
        {
            Def("2231A-30-3", "2231A-30-3", CmdStyle.ChList, "Keithley instruments,2231A-30-3,SIM0000,1.0.0",
                "Triple-channel DC Power Supply (Keithley)", "三通道直流電源供應器 (Keithley)"),
            Def("E3633A", "E3633A", CmdStyle.ChList, "Agilent Technologies,E3633A,SIM0000,1.0",
                "Single-output DC Power Supply (Agilent/Keysight)", "單輸出直流電源供應器 (Agilent/Keysight)"),
            Def("E36300", "E36300", CmdStyle.ChList, "Keysight Technologies,E36313A,SIM0000,1.0.0",
                "Triple-output DC Power Supply (Keysight)", "三輸出直流電源供應器 (Keysight)"),
            Def("Chroma 62000P", "Chroma_62000P", CmdStyle.ChList, "Chroma ATE,62012P-80-60,SIM0000,1.00",
                "Programmable DC Power Supply (Chroma)", "可程式直流電源供應器 (Chroma)"),
        }),
        new Category("cat_daq", new[]
        {
            Def("DAQ973A", "DAQ973A", CmdStyle.ChList, "Keysight Technologies,DAQ973A,SIM0000,A.01.00",
                "Data Acquisition / Switch System (Keysight)", "資料擷取 / 開關量測系統 (Keysight)"),
        }),
        new Category("cat_eload", new[]
        {
            Def("Chroma 63600", "Chroma_63600", CmdStyle.ChList, "Chroma,63600,SIM0000,1.00",
                "DC Electronic Load (Chroma)", "直流電子負載 (Chroma)"),
        }),
        new Category("cat_scope", new[]
        {
            Def("DPO 7 Series", "DPO_7SERIES", CmdStyle.Index, "TEKTRONIX,DPO7254,SIM0000,CF:91.1CT FV:1.0",
                "Digital Phosphor Oscilloscope (Tektronix)", "數位螢光示波器 (Tektronix)"),
            Def("MSO 5 Series", "MSO_5SERIES", CmdStyle.Index, "TEKTRONIX,MSO54,SIM0000,CF:91.1CT FV:1.0",
                "Mixed-Signal Oscilloscope (Tektronix)", "混合訊號示波器 (Tektronix)"),
            Def("R&S RTE", "RS_RTE", CmdStyle.Index, "Rohde&Schwarz,RTE1104,1326.0003K04/SIM0000,4.70.1.0",
                "Digital Oscilloscope (Rohde & Schwarz)", "數位示波器 (Rohde & Schwarz)"),
        }),
        new Category("cat_fgen", new[]
        {
            Def("AFG3000", "AFG3000", CmdStyle.Index, "TEKTRONIX,AFG3252,SIM0000,SCPI:99.0 FV:3.1.1",
                "Arbitrary/Function Generator (Tektronix)", "任意波形／函數信號產生器 (Tektronix)"),
            Def("AFG31000", "AFG31000", CmdStyle.Index, "TEKTRONIX,AFG31052,SIM0000,SCPI:99.0 FV:1.0",
                "Arbitrary Function Generator (Tektronix)", "任意函數信號產生器 (Tektronix)", elem: "seq_elem"),
        }),
        new Category("cat_meter", new[]
        {
            Def("Series 2400", "Series2400", CmdStyle.Index, "KEITHLEY INSTRUMENTS INC.,MODEL 2400,SIM0000,C32   Oct  4 2010 14:20:11/A02  /S/K",
                "SourceMeter / SMU (Keithley)", "電源量測單元 SMU (Keithley)"),
        }),
    };

    public static IEnumerable<InstrumentDef> All => Categories.SelectMany(c => c.Instruments);
}
