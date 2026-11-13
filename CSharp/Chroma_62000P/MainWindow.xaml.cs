using System.Collections.ObjectModel;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;
using System.Windows.Threading;
using Chroma62000P.Core;

namespace Chroma62000P;

public sealed class LogEntry
{
    public string Time { get; init; } = "";
    public string Tag { get; init; } = "";
    public string Text { get; init; } = "";
    public string BrushKey { get; init; } = "Muted";
    public Brush Brush => (Brush)Application.Current.Resources[BrushKey];
}

public partial class MainWindow : Window
{
    private const string AllGroup = "\u0000all";

    private Chroma62000PDevice? _dev;
    private CommandSpec? _cur;
    private Func<string?> _getParam = () => null;
    private string _group = AllGroup;
    private readonly ObservableCollection<LogEntry> _log = new();
    private bool _busyConnect;
    private string _idn = "";

    public MainWindow()
    {
        InitializeComponent();
        LogList.ItemsSource = _log;

        SimBadge.Visibility = App.SimMode ? Visibility.Visible : Visibility.Collapsed;
        BuildGroupCombo();
        I18n.Changed += Retranslate;
        Retranslate();
        ApplyFilter(forceFirst: true);
        UpdateConnectionUi();

        PreviewKeyDown += (_, e) =>
        {
            if (e.Key == Key.F && Keyboard.Modifiers == ModifierKeys.Control)
            {
                SearchBox.Focus(); SearchBox.SelectAll(); e.Handled = true;
            }
        };
        Closing += (_, _) => _dev?.Dispose();
        SourceInitialized += (_, _) => ApplyTitleBar();
        BuildThemeSwatches();
        ThemeManager.Changed += OnThemeChanged;
    }

    // ================================================================== //
    // 文字 / 語言
    // ================================================================== //
    private void Lang_Checked(object sender, RoutedEventArgs e)
    {
        if (!IsInitialized) return;
        I18n.Set(sender == LangZh ? "zh" : "en");
    }

    private void Retranslate()
    {
        Title = I18n.Lang == "zh" ? "Chroma 62000P 控制面板" : "Chroma 62000P Control Panel";
        SubtitleText.Text = I18n.T("app_sub", CommandCatalog.All.Count);
        SimBadgeText.Text = I18n.T("sim_badge");
        ConnLabel.Text = I18n.T("conn_frame");
        VisaLabel.Text = I18n.T("visa");
        ScanText.Text = I18n.T("scan");
        CommandsLabel.Text = I18n.T("commands");
        SearchBox.Tag = I18n.T("search_ph") + "   Ctrl+F";
        EmptyText.Text = I18n.T("search_none");
        SyntaxLabel.Text = I18n.T("syntax");
        ParamLabel.Text = I18n.T("parameter");
        PreviewLabel.Text = I18n.T("preview");
        WriteText.Text = I18n.T("write");
        ReadText.Text = I18n.T("read");
        CopyText.Text = I18n.T("copy");
        ConsoleLabel.Text = I18n.T("console");
        LastRespLabel.Text = I18n.T("last_resp");
        ClearText.Text = I18n.T("clear");
        GroupLabel.Text = I18n.T("group");
        if (ThemeSwatches.Children.Count > 0) RetranslateThemeTips();
        BuildGroupCombo();
        UpdateConnectionUi();
        ApplyFilter(forceFirst: false);
        if (_cur != null) ShowCommand(_cur, rebuildEditor: false);
    }

    // ================================================================== //
    // 指令清單：群組 + 搜尋
    // ================================================================== //

    private bool _buildingGroups;

    /// <summary>群組下拉：第一項為「全部」，其餘為各 SCPI 群組（切換語言時重建以更新「全部」文字）。</summary>
    private void BuildGroupCombo()
    {
        _buildingGroups = true;
        var groups = CommandCatalog.Groups;
        GroupCombo.ItemsSource = new[] { I18n.T("all") }.Concat(groups).ToList();
        GroupCombo.SelectedIndex = _group == AllGroup ? 0 : groups.ToList().IndexOf(_group) + 1;
        _buildingGroups = false;
    }

    private void GroupCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_buildingGroups || GroupCombo.SelectedIndex < 0) return;
        int i = GroupCombo.SelectedIndex;
        string g = i == 0 ? AllGroup : CommandCatalog.Groups[i - 1];
        if (g == _group) return;
        _group = g;
        ApplyFilter(forceFirst: true);
    }

    private void ApplyFilter(bool forceFirst)
    {
        string[] terms = SearchBox.Text.ToLowerInvariant()
            .Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var items = CommandCatalog.All
            .Where(c => _group == AllGroup || c.Group == _group)
            .Where(c => terms.Length == 0 || c.Matches(terms))
            .ToList();

        var keep = _cur;
        CommandList.ItemsSource = items;
        CountText.Text = I18n.T("search_count", items.Count, CommandCatalog.All.Count);
        EmptyState.Visibility = items.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        ClearSearchBtn.Visibility = SearchBox.Text.Length > 0 ? Visibility.Visible : Visibility.Collapsed;

        if (items.Count == 0) return;               // 無符合：保留目前指令詳情
        if (!forceFirst && keep != null && items.Contains(keep))
            CommandList.SelectedItem = keep;
        else
            CommandList.SelectedIndex = 0;
        CommandList.ScrollIntoView(CommandList.SelectedItem);
    }

    private void Search_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (IsInitialized) ApplyFilter(forceFirst: true);
    }

    private void Search_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape) { SearchBox.Clear(); e.Handled = true; }
        else if (e.Key == Key.Down && CommandList.Items.Count > 0)
        {
            CommandList.Focus();
            (CommandList.ItemContainerGenerator.ContainerFromIndex(CommandList.SelectedIndex) as ListBoxItem)?.Focus();
            e.Handled = true;
        }
    }

    private void ClearSearch_Click(object sender, RoutedEventArgs e)
    {
        SearchBox.Clear();
        SearchBox.Focus();
    }

    private void CommandList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CommandList.SelectedItem is CommandSpec c && c != _cur) ShowCommand(c, rebuildEditor: true);
    }

    // ================================================================== //
    // 指令詳情 + 參數編輯器
    // ================================================================== //
    private void ShowCommand(CommandSpec c, bool rebuildEditor)
    {
        _cur = c;
        GroupTag.Text = c.Group;
        PageTag.Text = I18n.T("manual_p", c.Page);
        AccessTag.Text = c.CanSet && c.CanGet ? I18n.T("access_rw") : c.CanSet ? I18n.T("access_w") : I18n.T("access_r");
        CmdName.Text = c.Name;
        CmdDesc.Text = c.Desc;
        CmdSyntax.Text = c.Syntax.Replace(" / ", "\n");
        ParamHint.Text = c.Kind == "raw" ? c.Hint : "";   // 數值型的提示已在輸入框 placeholder
        ParamHint.Visibility = string.IsNullOrEmpty(ParamHint.Text) ? Visibility.Collapsed : Visibility.Visible;
        WriteBtn.IsEnabled = c.CanSet;
        ReadBtn.IsEnabled = c.CanGet;
        PreviewWriteRow.Visibility = c.CanSet ? Visibility.Visible : Visibility.Collapsed;
        PreviewReadRow.Visibility = c.CanGet ? Visibility.Visible : Visibility.Collapsed;
        PreviewReadRow.Margin = c.CanSet ? new Thickness(0, 6, 0, 0) : new Thickness(0);
        if (rebuildEditor) BuildEditor(c);
        else if (!c.HasParam) BuildEditor(c);
        UpdatePreview();
    }

    private void BuildEditor(CommandSpec c)
    {
        if (!c.HasParam || !c.CanSet)
        {
            var np = new TextBlock
            {
                Text = I18n.T("no_param"),
                FontStyle = FontStyles.Italic, FontSize = 13, Margin = new Thickness(2, 6, 0, 0),
            };
            np.SetResourceReference(TextBlock.ForegroundProperty, "Faint");
            ParamHost.Content = np;
            _getParam = () => null;
            return;
        }

        List<string>? choices = c.Kind switch
        {
            "bool" => new List<string> { "ON", "OFF" },
            "enum" => c.Opts,
            _ => null,
        };

        if (choices is { Count: > 0 } && choices.Count <= 8)
        {
            var wrap = new WrapPanel();
            string group = "p_" + c.Key;
            string? selected = null;
            foreach (string opt in choices)
            {
                var rb = new RadioButton { Style = (Style)FindResource("Segment"), GroupName = group, Content = opt };
                rb.Checked += (_, _) => { selected = opt; UpdatePreview(); };
                wrap.Children.Add(rb);
            }
            ParamHost.Content = wrap;
            _getParam = () => selected;
            return;
        }

        if (choices is { Count: > 0 })
        {
            var cb = new ComboBox { ItemsSource = choices };
            cb.SelectionChanged += (_, _) => UpdatePreview();
            ParamHost.Content = cb;
            _getParam = () => cb.SelectedItem as string;
            return;
        }

        // numeric / raw
        var panel = new StackPanel();
        var tb = new TextBox
        {
            Tag = c.Kind == "raw" ? I18n.T("parameter") + "…" : c.Hint,
            FontFamily = (FontFamily)FindResource("MonoFont"),
        };
        tb.TextChanged += (_, _) => UpdatePreview();
        tb.KeyDown += (_, e) => { if (e.Key == Key.Enter) Write_Click(tb, new RoutedEventArgs()); };
        panel.Children.Add(tb);
        if (c.Suggest is { Count: > 0 })
        {
            var chips = new WrapPanel { Margin = new Thickness(0, 8, 0, 0) };
            foreach (string s in c.Suggest)
            {
                var b = new Button { Content = s, Style = (Style)FindResource("GhostButton") };
                b.SetResourceReference(ForegroundProperty, "Accent");
                b.Click += (_, _) => { tb.Text = s; tb.Focus(); tb.CaretIndex = tb.Text.Length; };
                chips.Children.Add(b);
            }
            panel.Children.Add(chips);
        }
        ParamHost.Content = panel;
        _getParam = () => tb.Text;
    }

    private string? ParamValue()
    {
        string? v = _getParam();
        return string.IsNullOrWhiteSpace(v) ? null : v.Trim();
    }

    private void UpdatePreview()
    {
        if (_cur == null) return;
        string? v = ParamValue();
        if (_cur.CanSet)
        {
            string text;
            try
            {
                text = _cur.HasParam && v == null
                    ? $"{_cur.Scpi} ‹{(string.IsNullOrEmpty(_cur.Hint) ? "value" : _cur.Hint)}›"
                    : Chroma62000PDevice.BuildWrite(_cur, v);
            }
            catch (Exception ex) { text = ex.Message; }
            PreviewWrite.Text = text;
            PreviewWrite.SetResourceReference(TextBlock.ForegroundProperty, _cur.HasParam && v == null ? "Faint" : "Text");
        }
        if (_cur.CanGet) PreviewRead.Text = Chroma62000PDevice.BuildQuery(_cur);
    }

    // ================================================================== //
    // Write / Read / Copy
    // ================================================================== //
    private async void Write_Click(object sender, RoutedEventArgs e)
    {
        if (_cur is not { CanSet: true } c) return;
        if (!EnsureConnected()) return;
        string? v = ParamValue();
        if (c.HasParam && v == null) { ShowToast(I18n.T("missing_param"), error: true); return; }
        string cmd;
        try { cmd = Chroma62000PDevice.BuildWrite(c, v); }
        catch (Exception ex) { ShowToast(ex.Message, error: true); return; }
        try
        {
            AddLog("TX", cmd, "Accent");
            await _dev!.WriteAsync(cmd);
        }
        catch (Exception ex) { AddLog("ERR", ex.Message, "Danger"); ShowToast(ex.Message, error: true); }
    }

    private async void Read_Click(object sender, RoutedEventArgs e)
    {
        if (_cur is not { CanGet: true } c) return;
        if (!EnsureConnected()) return;
        string cmd = Chroma62000PDevice.BuildQuery(c);
        try
        {
            AddLog("TX", cmd, "Sky");
            string resp = await _dev!.QueryAsync(cmd);
            AddLog("RX", resp, "Success");
            LastResp.Text = resp;
            FlashLastResp();
        }
        catch (Exception ex) { AddLog("ERR", ex.Message, "Danger"); ShowToast(ex.Message, error: true); }
    }

    private void Copy_Click(object sender, RoutedEventArgs e)
    {
        if (_cur is not { } c) return;
        string? v = ParamValue();
        string cmd;
        try
        {
            if (c.CanSet && (!c.HasParam || v != null)) cmd = Chroma62000PDevice.BuildWrite(c, v);
            else if (c.CanGet) cmd = Chroma62000PDevice.BuildQuery(c);
            else cmd = c.Scpi;
            Clipboard.SetText(cmd);
            ShowToast(I18n.T("copied", cmd));
        }
        catch (Exception ex) { ShowToast(ex.Message, error: true); }
    }

    private bool EnsureConnected()
    {
        if (_dev != null) return true;
        ShowToast(I18n.T("not_connected"), error: true);
        return false;
    }

    // ================================================================== //
    // 連線 / 掃描
    // ================================================================== //
    private string ResourceName() =>
        (ResourceCombo.Text ?? "").Trim().Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? "";

    private async void Connect_Click(object sender, RoutedEventArgs e)
    {
        if (_busyConnect) return;
        if (_dev != null)
        {
            _dev.Dispose();
            _dev = null;
            _idn = "";
            AddLog("SYS", "Disconnected", "Muted");
            UpdateConnectionUi();
            return;
        }

        string res = ResourceName();
        if (!App.SimMode && res.Length == 0) return;
        _busyConnect = true;
        ConnectBtn.IsEnabled = false;
        ConnectText.Text = I18n.T("connecting");
        try
        {
            var dev = await Task.Run(() => App.SimMode ? Chroma62000PDevice.OpenSimulated() : Chroma62000PDevice.Open(res));
            try { _idn = await dev.IdnAsync(); }
            catch { dev.Dispose(); throw; }
            _dev = dev;
            AddLog("SYS", (App.SimMode ? "[SIM] " : "") + $"Connected {dev.Resource} → {_idn}", "Success");
        }
        catch (Exception ex)
        {
            AddLog("ERR", ex.Message, "Danger");
            MessageBox.Show(this, ex.Message, I18n.T("conn_fail"), MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            _busyConnect = false;
            ConnectBtn.IsEnabled = true;
            UpdateConnectionUi();
        }
    }

    private void UpdateConnectionUi()
    {
        bool on = _dev != null;
        ConnectText.Text = I18n.T(on ? "disconnect" : "connect");
        ConnectIcon.Text = on ? "" : "";
        ConnectBtn.Style = (Style)FindResource(on ? "OutlineButton" : "PrimaryButton");
        ResourceCombo.IsEnabled = !on;
        ScanBtn.IsEnabled = !on;
        StatusDot.SetResourceReference(Shape.FillProperty, on ? "Success" : "Faint");
        StatusText.Text = on ? $"{I18n.T("connected")}  ·  {_idn}" : I18n.T("disconnected");
        StatusPill.ToolTip = on ? _idn : null;
        StatusPill.SetResourceReference(Border.BorderBrushProperty, on ? "SuccessDim" : "BorderBrush");
        FooterText.Text = on
            ? $"{(App.SimMode ? "SIM" : _dev!.Resource)}  ·  {I18n.T("ready")}"
            : I18n.T("ready");
    }

    private async void Scan_Click(object sender, RoutedEventArgs e)
    {
        ScanBtn.IsEnabled = false;
        ScanText.Text = I18n.T("scanning");
        StatusText.Text = I18n.T("scanning");
        var spin = new DoubleAnimation(0, 360, TimeSpan.FromSeconds(1)) { RepeatBehavior = RepeatBehavior.Forever };
        var rot = new RotateTransform();
        ScanIcon.RenderTransformOrigin = new Point(0.5, 0.5);
        ScanIcon.RenderTransform = rot;
        ScanIcon.Text = "";
        rot.BeginAnimation(RotateTransform.AngleProperty, spin);
        try
        {
            var results = await Task.Run(() => VisaSession.Scan());
            var items = results.Select(r => r.ToString()).ToList();
            ResourceCombo.ItemsSource = items;
            AddLog("SCAN", items.Count == 0 ? "(none)" : string.Join("  |  ", results.Select(r => r.Resource)), "Amber");
            if (items.Count > 0)
            {
                ResourceCombo.SelectedIndex = 0;
                ResourceCombo.IsDropDownOpen = true;
            }
        }
        catch (Exception ex)
        {
            AddLog("ERR", ex.Message, "Danger");
            MessageBox.Show(this, ex.Message, I18n.T("scan_fail"), MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            rot.BeginAnimation(RotateTransform.AngleProperty, null);
            ScanIcon.RenderTransform = null;
            ScanIcon.Text = "";
            ScanText.Text = I18n.T("scan");
            UpdateConnectionUi();   // 狀態列直接回到連線狀態（不顯示 Found n 提示）
        }
    }

    // ================================================================== //
    // Log / Toast / 視覺小工具
    // ================================================================== //
    private void AddLog(string tag, string text, string brushKey)
    {
        _log.Add(new LogEntry
        {
            Time = DateTime.Now.ToString("HH:mm:ss.fff"),
            Tag = tag,
            Text = text,
            BrushKey = brushKey,
        });
        if (_log.Count > 2000) _log.RemoveAt(0);
        LogList.ScrollIntoView(_log[^1]);
    }

    private void ClearLog_Click(object sender, RoutedEventArgs e)
    {
        _log.Clear();
        LastResp.Text = "—";
    }

    private void FlashLastResp()
    {
        var anim = new DoubleAnimation(0.25, 1, TimeSpan.FromMilliseconds(350));
        LastResp.BeginAnimation(OpacityProperty, anim);
    }

    private void ShowToast(string text, bool error = false)
    {
        ToastText.Text = text;
        ToastIcon.Text = error ? "" : "";
        ToastIcon.SetResourceReference(TextBlock.ForegroundProperty, error ? "Danger" : "Success");
        var sb = new Storyboard();
        var fade = new DoubleAnimationUsingKeyFrames();
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.Zero)));
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(1, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(160))));
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(1, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(2000))));
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(2400))));
        Storyboard.SetTarget(fade, Toast);
        Storyboard.SetTargetProperty(fade, new PropertyPath(OpacityProperty));
        sb.Children.Add(fade);
        var tt = new TranslateTransform();
        Toast.RenderTransform = tt;
        tt.BeginAnimation(TranslateTransform.YProperty,
            new DoubleAnimation(10, 0, TimeSpan.FromMilliseconds(200)) { EasingFunction = new CubicEase() });
        sb.Begin();
    }

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

    // ================================================================== //
    // 色系
    // ================================================================== //
    private void BuildThemeSwatches()
    {
        ThemeSwatches.Children.Clear();
        foreach (var p in ThemeManager.All)
        {
            var rb = new RadioButton
            {
                Style = (Style)FindResource("Swatch"), GroupName = "theme",
                Background = ThemeManager.SwatchBrush(p), Tag = p,
                IsChecked = p == ThemeManager.Current, ToolTip = p.Name,
            };
            rb.Checked += (_, _) => { if (ThemeManager.Current != p) ThemeManager.Apply(p); };
            ThemeSwatches.Children.Add(rb);
        }
    }

    private void OnThemeChanged()
    {
        ApplyTitleBar();
        // 紀錄的顏色是依 key 取的，重新放一次讓 ListBox 重繪
        var items = _log.ToList();
        _log.Clear();
        foreach (var it in items) _log.Add(it);
    }

    private void RetranslateThemeTips()
    {
        ThemeIcon.ToolTip = I18n.T("theme");
        foreach (RadioButton rb in ThemeSwatches.Children)
            if (rb.Tag is Palette p) rb.ToolTip = p.Name;
    }

    private void ApplyTitleBar()
    {
        try
        {
            IntPtr hwnd = new WindowInteropHelper(this).Handle;
            if (hwnd == IntPtr.Zero) return;
            var pal = ThemeManager.Current;
            int dark = pal.IsDark ? 1 : 0;
            DwmSetWindowAttribute(hwnd, 20, ref dark, sizeof(int));        // DWMWA_USE_IMMERSIVE_DARK_MODE
            var c = (Color)ColorConverter.ConvertFromString(pal.Bg);
            int caption = c.R | (c.G << 8) | (c.B << 16);                   // COLORREF 0x00BBGGRR
            DwmSetWindowAttribute(hwnd, 35, ref caption, sizeof(int));     // DWMWA_CAPTION_COLOR (Win11)
            int text = pal.IsDark ? 0x00F4EDE7 : 0x002D2018;
            DwmSetWindowAttribute(hwnd, 36, ref text, sizeof(int));        // DWMWA_TEXT_COLOR
        }
        catch { /* 舊版 Windows 忽略 */ }
    }
}
