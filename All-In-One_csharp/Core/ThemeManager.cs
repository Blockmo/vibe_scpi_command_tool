using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Effects;

namespace ScpiAllInOne.Core;

/// <summary>一套色系：所有介面顏色 token。</summary>
public sealed record Palette(
    string Id, string NameEn, string NameZh, bool IsDark,
    string Bg, string Surface, string Surface2, string Surface3,
    string Border, string BorderHi, string Text, string Muted, string Faint,
    string Accent, string AccentHover, string Secondary, string Amber,
    string Danger, string Success, string OnAccent, string Logo2,
    double ShadowOpacity)
{
    public string Name => I18n.Lang == "zh" ? NameZh : NameEn;
}

/// <summary>
/// 執行時切換色系：把各顏色 token 寫入 Application.Resources，
/// 介面全部以 DynamicResource 參照，所以會即時更新。字體大小同理（字級 token Fs*）。
/// 選擇會存在 %APPDATA%\SCPI_AllInOne\settings.json。
/// </summary>
public static class ThemeManager
{
    public static readonly IReadOnlyList<Palette> All = new[]
    {
        new Palette("graphite", "Graphite Teal", "石墨青", true,
            "#0E1217", "#151B23", "#1B2330", "#232D3B", "#2A3544", "#3A4759",
            "#E7EDF4", "#8A97A8", "#5C6878",
            "#2DD4BF", "#5EEAD4", "#38BDF8", "#FBBF24", "#F87171", "#34D399", "#06231F", "#38BDF8", 0.35),

        new Palette("paper", "Paper Light", "晨光淺色", false,
            "#F2F4F7", "#FFFFFF", "#F6F8FB", "#E8ECF2", "#DCE2EA", "#C2CBD7",
            "#18202D", "#596577", "#949FAF",
            "#0D9488", "#0F766E", "#2563EB", "#B45309", "#DC2626", "#059669", "#FFFFFF", "#3B82F6", 0.10),
    };

    public static Palette Current { get; private set; } = All[0];
    public static event Action? Changed;

    // ------------------------------------------------------------------ //
    // 字體大小：M / L / XL
    // ------------------------------------------------------------------ //
    public sealed record FontSizeOption(string Id, string LabelEn, string LabelZh, double Scale)
    {
        public string Label => I18n.Lang == "zh" ? LabelZh : LabelEn;
    }

    public static readonly IReadOnlyList<FontSizeOption> FontSizes = new[]
    {
        new FontSizeOption("m", "M", "M", 1.0),
        new FontSizeOption("l", "L", "L", 1.15),
        new FontSizeOption("xl", "XL", "XL", 1.3),
    };

    /// <summary>介面用到的基準字級；實際值 = 基準 × 倍率，寫入資源 Fs10、Fs12_5 …</summary>
    private static readonly double[] BaseSizes = { 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 15, 22, 23, 28 };

    public static FontSizeOption CurrentFont { get; private set; } = FontSizes[0];
    public static double FontScale => CurrentFont.Scale;
    public static event Action? FontChanged;

    public static void ApplyFont(FontSizeOption f, bool save = true)
    {
        CurrentFont = f;
        var r = Application.Current.Resources;
        foreach (double b in BaseSizes)
            r["Fs" + b.ToString(System.Globalization.CultureInfo.InvariantCulture).Replace(".", "_")] = Math.Round(b * f.Scale, 1);
        if (save) Save();
        FontChanged?.Invoke();
    }

    private static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "SCPI_AllInOne", "settings.json");

    public static void LoadSaved()
    {
        string id = All[0].Id, font = "m";
        try
        {
            if (File.Exists(SettingsPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(SettingsPath));
                if (doc.RootElement.TryGetProperty("theme", out var t)) id = t.GetString() ?? id;
                if (doc.RootElement.TryGetProperty("font", out var fz)) font = fz.GetString() ?? font;
            }
        }
        catch { /* 設定檔損毀時用預設 */ }
        // 已移除的色系（如舊設定的 indigo / ember）會回到預設
        Apply(All.FirstOrDefault(p => p.Id == id) ?? All[0], save: false);
        ApplyFont(FontSizes.FirstOrDefault(f => f.Id == font) ?? FontSizes[0], save: false);   // 舊設定 "s" 會回到 M
    }

    public static void Apply(Palette p, bool save = true)
    {
        Current = p;
        var r = Application.Current.Resources;
        static SolidColorBrush B(string hex, byte? alpha = null)
        {
            var c = (Color)ColorConverter.ConvertFromString(hex);
            if (alpha.HasValue) c.A = alpha.Value;
            var b = new SolidColorBrush(c);
            b.Freeze();
            return b;
        }

        r["Bg"] = B(p.Bg);
        r["Surface"] = B(p.Surface);
        r["Surface2"] = B(p.Surface2);
        r["Surface3"] = B(p.Surface3);
        r["BorderBrush"] = B(p.Border);
        r["BorderHi"] = B(p.BorderHi);
        r["Text"] = B(p.Text);
        r["Muted"] = B(p.Muted);
        r["Faint"] = B(p.Faint);
        r["Accent"] = B(p.Accent);
        r["AccentDim"] = B(p.Accent, p.IsDark ? (byte)0x1F : (byte)0x1A);
        r["AccentHover"] = B(p.AccentHover);
        r["Sky"] = B(p.Secondary);
        r["Amber"] = B(p.Amber);
        r["AmberDim"] = B(p.Amber, 0x26);
        r["Danger"] = B(p.Danger);
        r["Success"] = B(p.Success);
        r["SuccessDim"] = B(p.Success, 0x66);
        r["OnAccent"] = B(p.OnAccent);

        var logo = new LinearGradientBrush(
            (Color)ColorConverter.ConvertFromString(p.Accent),
            (Color)ColorConverter.ConvertFromString(p.Logo2), new Point(0, 0), new Point(1, 1));
        logo.Freeze();
        r["LogoGradient"] = logo;

        var shadow = new DropShadowEffect
        {
            BlurRadius = 24, ShadowDepth = 4, Direction = 270, Opacity = p.ShadowOpacity, Color = Colors.Black,
        };
        shadow.Freeze();
        r["CardShadow"] = shadow;

        if (save) Save();
        Changed?.Invoke();
    }

    private static void Save()
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath)!);
            File.WriteAllText(SettingsPath, JsonSerializer.Serialize(new { theme = Current.Id, font = CurrentFont.Id }));
        }
        catch { /* 無法寫入時忽略 */ }
    }

    /// <summary>色票小圓點：左上為背景色、右下為強調色。</summary>
    public static Brush SwatchBrush(Palette p)
    {
        var g = new LinearGradientBrush { StartPoint = new Point(0, 0), EndPoint = new Point(1, 1) };
        var bg = (Color)ColorConverter.ConvertFromString(p.Surface2);
        var ac = (Color)ColorConverter.ConvertFromString(p.Accent);
        g.GradientStops.Add(new GradientStop(bg, 0));
        g.GradientStops.Add(new GradientStop(bg, 0.5));
        g.GradientStops.Add(new GradientStop(ac, 0.5));
        g.GradientStops.Add(new GradientStop(ac, 1));
        g.Freeze();
        return g;
    }
}
