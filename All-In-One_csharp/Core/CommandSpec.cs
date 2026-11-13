using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ScpiAllInOne.Core;

/// <summary>一條 SCPI 指令的規格（對應 Data/&lt;儀器&gt;.json 的一個元素）。</summary>
public sealed class CommandSpec
{
    [JsonPropertyName("key")] public string Key { get; set; } = "";
    [JsonPropertyName("group")] public string Group { get; set; } = "";
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("scpi")] public string Scpi { get; set; } = "";
    [JsonPropertyName("syntax")] public string Syntax { get; set; } = "";
    [JsonPropertyName("params")] public string Params { get; set; } = "";
    [JsonPropertyName("desc")] public string Desc { get; set; } = "";
    [JsonPropertyName("page"), JsonConverter(typeof(FlexStringConverter))] public string Page { get; set; } = "";
    [JsonPropertyName("set")] public bool CanSet { get; set; }
    [JsonPropertyName("get")] public bool CanGet { get; set; }
    /// <summary>none / bool / numeric / enum / string / raw</summary>
    [JsonPropertyName("kind")] public string Kind { get; set; } = "none";
    [JsonPropertyName("opts")] public List<string>? Opts { get; set; }
    [JsonPropertyName("suggest")] public List<string>? Suggest { get; set; }
    [JsonPropertyName("hint")] public string Hint { get; set; } = "";

    // ---- 位置欄位（依儀器範本而定） ----
    /// <summary>通道清單型：指令可附 (@通道清單)</summary>
    [JsonPropertyName("chlist")] public bool ChList { get; set; }
    /// <summary>標頭編號型：標頭含 {ch}，需選通道</summary>
    [JsonPropertyName("chan")] public bool Chan { get; set; }
    [JsonPropertyName("channels")] public List<int>? Channels { get; set; }
    /// <summary>標頭編號型：標頭含 {n}，需填編號</summary>
    [JsonPropertyName("elem")] public bool Elem { get; set; }
    /// <summary>查詢可帶引數（如 MEMory:STATe:VALid? 1）</summary>
    [JsonPropertyName("qarg")] public bool QArg { get; set; }
    /// <summary>多參數指令查詢只帶前 qn 個參數（R&amp;S：SEARch:...:STATe? &lt;SearchName&gt;）；0 = 整串</summary>
    [JsonPropertyName("qn")] public int QN { get; set; }
    /// <summary>通道清單型讀寫兩用指令：查詢可帶的關鍵字（如 MIN/MAX/DEF）；寫入值非這些關鍵字時查詢不帶值</summary>
    [JsonPropertyName("qopts")] public List<string>? QOpts { get; set; }
    /// <summary>通道清單型讀寫兩用多參數指令：查詢要帶寫入值的第幾個逗號欄位（如 SLOT:LABel? &lt;slot&gt;）</summary>
    [JsonPropertyName("qsel")] public List<int>? QSel { get; set; }

    public bool HasParam => Kind != "none";
    public string AccessBadge => CanSet && CanGet ? "R/W" : CanSet ? "W" : "R";

    /// <summary>搜尋比對：空白分隔 AND、不分大小寫（比對 name/scpi/syntax/desc/params/group）。</summary>
    public bool Matches(IEnumerable<string> terms)
    {
        string hay = string.Join("\n", Name, Scpi, Syntax, Desc, Params, Group).ToLowerInvariant();
        return terms.All(hay.Contains);
    }

    /// <summary>從內嵌資源載入某台儀器的指令表。</summary>
    public static List<CommandSpec> LoadResource(string dataId)
    {
        using Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(dataId + ".json")
                         ?? throw new InvalidOperationException($"resource {dataId}.json missing");
        return JsonSerializer.Deserialize<List<CommandSpec>>(s) ?? new List<CommandSpec>();
    }
}

/// <summary>頁碼有的是數字（123）、有的是字串（"5-12"），一律讀成字串。</summary>
public sealed class FlexStringConverter : JsonConverter<string>
{
    public override string Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options) =>
        reader.TokenType switch
        {
            JsonTokenType.String => reader.GetString() ?? "",
            JsonTokenType.Number => reader.TryGetInt64(out long l) ? l.ToString() : reader.GetDouble().ToString(),
            JsonTokenType.Null => "",
            _ => JsonDocument.ParseValue(ref reader).RootElement.ToString(),
        };

    public override void Write(Utf8JsonWriter writer, string value, JsonSerializerOptions options) =>
        writer.WriteStringValue(value);
}
