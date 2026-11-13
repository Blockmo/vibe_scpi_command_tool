using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Chroma62000P.Core;

/// <summary>一條 SCPI 指令的規格（對應 Python 版 COMMANDS 的一列）。</summary>
public sealed class CommandSpec
{
    [JsonPropertyName("key")] public string Key { get; set; } = "";
    [JsonPropertyName("group")] public string Group { get; set; } = "";
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("scpi")] public string Scpi { get; set; } = "";
    [JsonPropertyName("syntax")] public string Syntax { get; set; } = "";
    [JsonPropertyName("params")] public string Params { get; set; } = "";
    [JsonPropertyName("desc")] public string Desc { get; set; } = "";
    [JsonPropertyName("page")] public string Page { get; set; } = "";
    [JsonPropertyName("set")] public bool CanSet { get; set; }
    [JsonPropertyName("get")] public bool CanGet { get; set; }
    /// <summary>none / bool / numeric / enum / raw</summary>
    [JsonPropertyName("kind")] public string Kind { get; set; } = "none";
    [JsonPropertyName("opts")] public List<string>? Opts { get; set; }
    [JsonPropertyName("suggest")] public List<string>? Suggest { get; set; }
    [JsonPropertyName("hint")] public string Hint { get; set; } = "";

    public bool HasParam => Kind != "none";
    public string AccessBadge => CanSet && CanGet ? "R/W" : CanSet ? "W" : "R";

    /// <summary>搜尋比對：空白分隔 AND、不分大小寫。</summary>
    public bool Matches(IEnumerable<string> terms)
    {
        string hay = string.Join("\n", Name, Scpi, Syntax, Desc, Params, Group).ToLowerInvariant();
        return terms.All(hay.Contains);
    }
}

public static class CommandCatalog
{
    private static List<CommandSpec>? _all;

    public static IReadOnlyList<CommandSpec> All => _all ??= Load();

    public static IReadOnlyList<string> Groups =>
        All.Select(c => c.Group).Distinct().ToList();

    private static List<CommandSpec> Load()
    {
        using Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("commands.json")
                         ?? throw new InvalidOperationException("commands.json resource missing");
        return JsonSerializer.Deserialize<List<CommandSpec>>(s) ?? new List<CommandSpec>();
    }
}
