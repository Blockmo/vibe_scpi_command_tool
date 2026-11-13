using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;
using ScpiAllInOne.Core;

namespace ScpiAllInOne;

public partial class MainWindow : Window
{
    private readonly Dictionary<InstrumentDef, InstrumentSession> _sessions;
    private readonly Dictionary<int, InstrumentSession> _lastInCategory = new();
    private InstrumentSession _s;
    private CommandSpec? _cur;
    private Func<string?> _getParam = () => null;
    private bool _restoring;      // 切換儀器 / 重建下拉時，暫停事件連鎖

    private CmdStyle St => _s.Def.Style;

    public MainWindow()
    {
        InitializeComponent();
        _sessions = InstrumentCatalog.All.ToDictionary(d => d, d => new InstrumentSession(d));
        _s = _sessions[InstrumentCatalog.Categories[0].Instruments[0]];

        SimBadge.Visibility = App.SimMode ? Visibility.Visible : Visibility.Collapsed;
        BuildThemeSwatches();
        BuildFontSizeButtons();
        ThemeManager.Changed += OnThemeChanged;
        ThemeManager.FontChanged += () => { if (_cur != null) BuildPosition(_cur); };
        I18n.Changed += Retranslate;

        BuildCategoryCombo(0);
        Retranslate();

        PreviewKeyDown += (_, e) =>
        {
            if (e.Key == Key.F && Keyboard.Modifiers == ModifierKeys.Control)
            {
                SearchBox.Focus(); SearchBox.SelectAll(); e.Handled = true;
            }
        };
        Closing += (_, _) => { foreach (var s in _sessions.Values) s.Device?.Dispose(); };
        SourceInitialized += (_, _) => ApplyTitleBar();
    }

    // ================================================================== //
    // 語言
    // ================================================================== //
    private void Lang_Checked(object sender, RoutedEventArgs e)
    {
        if (!IsInitialized) return;
        I18n.Set(sender == LangZh ? "zh" : "en");
    }

    private void Retranslate()
    {
        Title = I18n.T("window_title");
        AppTitle.Text = I18n.T("aio_title");
        SubtitleText.Text = I18n.T("app_sub", InstrumentCatalog.All.Count(), InstrumentCatalog.All.Sum(d => d.Commands.Count));
        SimBadgeText.Text = I18n.T("sim_badge");
        InstLabel.Text = I18n.T("instrument_frame");
        InstSubLabel.Text = $"{I18n.T("category")} · {I18n.T("instrument")}";
        ConnLabel.Text = I18n.T("conn_frame");
        VisaLabel.Text = I18n.T("visa");
        ScanText.Text = I18n.T("scan");
        CommandsLabel.Text = I18n.T("commands");
        GroupLabel.Text = I18n.T("group");
        SearchBox.Tag = I18n.T("search_ph") + "   Ctrl+F";
        EmptyText.Text = I18n.T("search_none");
        SyntaxLabel.Text = I18n.T("syntax");
        ParamLabel.Text = I18n.T("parameter");
        PosLabel.Text = I18n.T("position");
        PreviewLabel.Text = I18n.T("preview");
        WriteText.Text = I18n.T("write");
        ReadText.Text = I18n.T("read");
        CopyText.Text = I18n.T("copy");
        ConsoleLabel.Text = I18n.T("console");
        LastRespLabel.Text = I18n.T("last_resp");
        ClearText.Text = I18n.T("clear");
        ThemeIcon.ToolTip = I18n.T("theme");
        FontIcon.ToolTip = I18n.T("font_size");
        foreach (RadioButton rb in FontSizeButtons.Children)
            if (rb.Tag is ThemeManager.FontSizeOption f) rb.Content = f.Label;
        foreach (RadioButton rb in ThemeSwatches.Children)
            if (rb.Tag is Palette p) rb.ToolTip = p.Name;

        BuildCategoryCombo(CategoryCombo.SelectedIndex < 0 ? 0 : CategoryCombo.SelectedIndex);
        UpdateInfo();
        BuildGroupCombo();
        UpdateConnectionUi();
        ApplyFilter(keepKey: _cur?.Key);
        if (_cur != null) ShowCommand(_cur, rebuildEditor: true);
    }

    // ================================================================== //
    // 分類 / 儀器
    // ================================================================== //
    private void BuildCategoryCombo(int index)
    {
        _restoring = true;
        CategoryCombo.ItemsSource = InstrumentCatalog.Categories.Select(c => I18n.T(c.LabelKey)).ToList();
        CategoryCombo.SelectedIndex = index;
        _restoring = false;
        if (InstrumentCombo.ItemsSource == null) FillInstrumentCombo(index);
    }

    private void Category_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_restoring || CategoryCombo.SelectedIndex < 0) return;
        FillInstrumentCombo(CategoryCombo.SelectedIndex);
    }

    private void FillInstrumentCombo(int catIndex)
    {
        var list = InstrumentCatalog.Categories[catIndex].Instruments.Select(d => _sessions[d]).ToList();
        InstrumentCombo.ItemsSource = list;
        InstrumentCombo.SelectedItem = _lastInCategory.TryGetValue(catIndex, out var last) ? last : list[0];
    }

    private void Instrument_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (InstrumentCombo.SelectedItem is not InstrumentSession s) return;
        _lastInCategory[CategoryCombo.SelectedIndex] = s;
        if (s != _s || _cur == null) SwitchTo(s);
    }

    private void SaveSessionUi()
    {
        _s.ResourceText = ResourceCombo.Text;
        _s.Search = SearchBox.Text;
        _s.CommandKey = _cur?.Key;
        _s.LastResponse = LastResp.Text;
    }

    private void SwitchTo(InstrumentSession s)
    {
        if (_cur != null) SaveSessionUi();
        _s = s;
        _cur = null;
        _restoring = true;
        LogList.ItemsSource = s.Log;
        ResourceCombo.ItemsSource = s.ScanItems;
        ResourceCombo.Text = s.ResourceText;
        SearchBox.Text = s.Search;
        LastResp.Text = s.LastResponse;
        _restoring = false;

        BuildGroupCombo();
        UpdateInfo();
        UpdateConnectionUi();
        ApplyFilter(keepKey: s.CommandKey);
        ScrollLogToEnd();
    }

    private void UpdateInfo()
    {
        InfoText.Text = I18n.T("aio_info", _s.Def.Kind, _s.Def.Commands.Count, _s.Def.DataId);
        ConsoleInst.Text = "· " + _s.Name;
    }

    // ================================================================== //
    // 指令清單：群組 + 搜尋
    // ================================================================== //
    private void BuildGroupCombo()
    {
        _restoring = true;
        var groups = _s.Def.Groups;
        GroupCombo.ItemsSource = new[] { I18n.T("all") }.Concat(groups).ToList();
        int idx = _s.Group == null ? 0 : groups.ToList().IndexOf(_s.Group) + 1;
        GroupCombo.SelectedIndex = Math.Max(0, idx);
        _restoring = false;
    }

    private void GroupCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_restoring || GroupCombo.SelectedIndex < 0) return;
        int i = GroupCombo.SelectedIndex;
        string? g = i == 0 ? null : _s.Def.Groups[i - 1];
        if (g == _s.Group) return;
        _s.Group = g;
        ApplyFilter(keepKey: null);
    }

    private void ApplyFilter(string? keepKey)
    {
        string[] terms = SearchBox.Text.ToLowerInvariant().Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var all = _s.Def.Commands;
        var items = all
            .Where(c => _s.Group == null || c.Group == _s.Group)
            .Where(c => terms.Length == 0 || c.Matches(terms))
            .ToList();

        CommandList.ItemsSource = items;
        CountText.Text = I18n.T("search_count", items.Count, all.Count);
        EmptyState.Visibility = items.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        ClearSearchBtn.Visibility = SearchBox.Text.Length > 0 ? Visibility.Visible : Visibility.Collapsed;

        if (items.Count == 0)
        {
            // 無符合：保留目前指令詳情；切換儀器時沒有目前指令，則顯示該台第一條
            if (_cur == null && all.Count > 0) ShowCommand(all[0], rebuildEditor: true);
            return;
        }
        var keep = keepKey == null ? null : items.FirstOrDefault(c => c.Key == keepKey);
        CommandList.SelectedItem = keep ?? items[0];
        CommandList.ScrollIntoView(CommandList.SelectedItem);
    }

    private void Search_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (!IsInitialized || _restoring) return;
        _s.Search = SearchBox.Text;
        ApplyFilter(keepKey: null);
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
    // 指令詳情 + 參數 / 位置編輯器
    // ================================================================== //
    private void ShowCommand(CommandSpec c, bool rebuildEditor)
    {
        _cur = c;
        _s.CommandKey = c.Key;
        GroupTag.Text = c.Group;
        PageTag.Text = I18n.T("manual_p", c.Page);
        AccessTag.Text = c.CanSet && c.CanGet ? I18n.T("access_rw") : c.CanSet ? I18n.T("access_w") : I18n.T("access_r");
        CmdName.Text = c.Name;
        CmdName.ToolTip = c.Name;
        CmdDesc.Text = c.Desc;
        CmdSyntax.Text = c.Syntax.Replace(" / ", "\n");
        CmdSyntax.ToolTip = c.Syntax;
        PreviewWriteRow.Visibility = c.CanSet ? Visibility.Visible : Visibility.Collapsed;
        PreviewReadRow.Visibility = c.CanGet ? Visibility.Visible : Visibility.Collapsed;
        PreviewReadRow.Margin = c.CanSet ? new Thickness(0, 6, 0, 0) : new Thickness(0);
        if (rebuildEditor)
        {
            BuildEditor(c);
            BuildPosition(c);
        }
        UpdateActionState();
        UpdatePreview();
    }

    /// <summary>參數編輯器是否需要：可寫入，或查詢也會帶參數（ChList 型 / qarg）。</summary>
    private bool ShowsParam(CommandSpec c) =>
        c.HasParam && (c.CanSet || St == CmdStyle.ChList || c.QArg);

    private void BuildEditor(CommandSpec c)
    {
        string hint = c.Kind == "raw" || c.Kind == "string" ? c.Hint : "";
        if (!c.CanSet && c.QArg) hint = I18n.T("qarg_hint") + (c.Hint.Length > 0 ? "：" + c.Hint : "");
        ParamHint.Text = hint;
        ParamHint.Visibility = string.IsNullOrEmpty(hint) ? Visibility.Collapsed : Visibility.Visible;

        if (!ShowsParam(c))
        {
            var np = new TextBlock
            {
                Text = I18n.T("no_param"), FontStyle = FontStyles.Italic,
                Margin = new Thickness(2, 6, 0, 0),
            };
            np.SetResourceReference(TextBlock.FontSizeProperty, "Fs13");
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

        if (choices is { Count: > 0 } && choices.Count <= 6 && choices.Sum(o => o.Length) <= 48)
        {
            var wrap = new WrapPanel();
            string group = "p_" + _s.Def.DataId + c.Key;
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
            // 選項多：可編輯下拉（也允許輸入縮寫或其他值）
            var cb = new ComboBox { ItemsSource = choices, IsEditable = true };
            cb.SelectionChanged += (_, _) => Dispatcher.BeginInvoke(UpdatePreview);
            cb.AddHandler(System.Windows.Controls.Primitives.TextBoxBase.TextChangedEvent, new TextChangedEventHandler((_, _) => UpdatePreview()));
            ParamHost.Content = cb;
            _getParam = () => cb.Text;
            return;
        }

        // numeric / string / raw
        var panel = new StackPanel();
        var tb = new TextBox
        {
            Tag = c.Kind is "raw" or "string" ? I18n.T("parameter") + "…" : (c.Hint.Length > 0 ? c.Hint : I18n.T("parameter") + "…"),
            FontFamily = (FontFamily)FindResource("MonoFont"),
        };
        tb.TextChanged += (_, _) => UpdatePreview();
        tb.KeyDown += (_, e) => { if (e.Key == Key.Enter && c.CanSet) Write_Click(tb, new RoutedEventArgs()); };
        panel.Children.Add(tb);
        if (c.Suggest is { Count: > 0 })
        {
            var chips = new WrapPanel { Margin = new Thickness(0, 6, 0, 0) };
            foreach (string sug in c.Suggest)
            {
                var b = new Button { Content = sug, Style = (Style)FindResource("GhostButton") };
                b.SetResourceReference(ForegroundProperty, "Accent");
                b.Click += (_, _) => { tb.Text = sug; tb.Focus(); tb.CaretIndex = tb.Text.Length; };
                chips.Children.Add(b);
            }
            panel.Children.Add(chips);
        }
        ParamHost.Content = panel;
        _getParam = () => tb.Text;
    }

    private void BuildPosition(CommandSpec c)
    {
        PosHost.Children.Clear();
        bool hasChList = St == CmdStyle.ChList && c.ChList;
        bool hasChan = St == CmdStyle.Index && c.Chan;
        bool hasElem = St == CmdStyle.Index && c.Elem;
        PosSection.Visibility = hasChList || hasChan || hasElem ? Visibility.Visible : Visibility.Collapsed;

        if (hasChList)
        {
            var tb = new TextBox
            {
                Width = 240, Text = _s.ChList, Tag = I18n.T("chlist_ph"),
                FontFamily = (FontFamily)FindResource("MonoFont"),
            };
            tb.TextChanged += (_, _) => { _s.ChList = tb.Text; UpdatePreview(); };
            PosHost.Children.Add(Field(I18n.T("chlist"), tb));
        }
        if (hasChan)
        {
            var chs = c.Channels is { Count: > 0 } l ? l : new List<int> { 1, 2 };
            if (!chs.Contains(_s.Channel)) _s.Channel = chs[0];
            var cb = new ComboBox { Width = 90, ItemsSource = chs, SelectedItem = _s.Channel };
            cb.SelectionChanged += (_, _) => { if (cb.SelectedItem is int ch) { _s.Channel = ch; UpdatePreview(); } };
            PosHost.Children.Add(Field(I18n.T("channel"), cb));
        }
        if (hasElem)
        {
            var tb = new TextBox
            {
                Width = 64, Text = _s.Element.ToString(), HorizontalContentAlignment = HorizontalAlignment.Center,
                FontFamily = (FontFamily)FindResource("MonoFont"),
            };
            tb.TextChanged += (_, _) =>
            {
                if (int.TryParse(tb.Text, out int n) && n >= 1) { _s.Element = n; UpdatePreview(); }
            };
            Button Step(string glyph, int d)
            {
                var b = new Button
                {
                    Style = (Style)FindResource("GhostButton"), Width = 30, Height = 38, Padding = new Thickness(0),
                    Content = new TextBlock { Style = (Style)FindResource("Icon"), Text = glyph, FontSize = 11 * ThemeManager.FontScale },
                };
                b.Click += (_, _) => tb.Text = Math.Max(1, _s.Element + d).ToString();
                return b;
            }
            var row = new StackPanel { Orientation = Orientation.Horizontal };
            row.Children.Add(Step("", -1));
            row.Children.Add(tb);
            row.Children.Add(Step("", +1));
            PosHost.Children.Add(Field(I18n.T(_s.Def.ElemLabelKey), row));
        }

        FrameworkElement Field(string label, FrameworkElement editor)
        {
            var sp = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 18, 6) };
            var lb = new TextBlock { Text = label, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(2, 0, 10, 0) };
            lb.SetResourceReference(TextBlock.FontSizeProperty, "Fs12_5");
            lb.SetResourceReference(TextBlock.ForegroundProperty, "Muted");
            sp.Children.Add(lb);
            sp.Children.Add(editor);
            return sp;
        }
    }

    private string? ParamValue()
    {
        string? v = _getParam();
        return string.IsNullOrWhiteSpace(v) ? null : v.Trim();
    }

    private Position Pos(CommandSpec c) => new(
        ChList: St == CmdStyle.ChList && c.ChList ? _s.ChList : null,
        Channel: _s.Channel,
        Element: _s.Element);

    private void UpdatePreview()
    {
        if (_cur is not { } c) return;
        string? v = ParamValue();
        var pos = Pos(c);
        if (c.CanSet)
        {
            bool missing = ScpiBuilder.MissingValue(St, c, v, pos);
            string text;
            try
            {
                if (missing)
                {
                    string head = St == CmdStyle.Index ? ScpiBuilder.Header(c, pos) : c.Scpi;
                    text = $"{head} ‹{(string.IsNullOrEmpty(c.Hint) ? "value" : c.Hint)}›";
                }
                else text = ScpiBuilder.BuildWrite(St, c, v, pos);
            }
            catch (Exception ex) { text = ex.Message; missing = true; }
            PreviewWrite.Text = text;
            PreviewWrite.SetResourceReference(TextBlock.ForegroundProperty, missing ? "Faint" : "Text");
        }
        if (c.CanGet)
        {
            try { PreviewRead.Text = ScpiBuilder.BuildQuery(St, c, v, pos); }
            catch (Exception ex) { PreviewRead.Text = ex.Message; }
        }
    }

    private void UpdateActionState()
    {
        WriteBtn.IsEnabled = _cur?.CanSet == true;
        ReadBtn.IsEnabled = _cur?.CanGet == true;
    }

    // ================================================================== //
    // Write / Read / Copy
    // ================================================================== //
    private async void Write_Click(object sender, RoutedEventArgs e)
    {
        if (_cur is not { CanSet: true } c) return;
        _lastWasRead = false;
        var s = _s;
        if (!EnsureConnected(s)) return;
        string? v = ParamValue();
        var pos = Pos(c);
        if (ScpiBuilder.MissingValue(St, c, v, pos)) { ShowToast(I18n.T("missing_param"), error: true); return; }
        string cmd;
        try { cmd = ScpiBuilder.BuildWrite(St, c, v, pos); }
        catch (Exception ex) { ShowToast(ex.Message, error: true); return; }
        try
        {
            Log(s, "TX", cmd, "Accent");
            await s.Device!.WriteAsync(cmd);
        }
        catch (Exception ex) { Log(s, "ERR", ex.Message, "Danger"); ShowToast(ex.Message, error: true); }
    }

    private async void Read_Click(object sender, RoutedEventArgs e)
    {
        if (_cur is not { CanGet: true } c) return;
        _lastWasRead = true;
        var s = _s;
        if (!EnsureConnected(s)) return;
        string cmd;
        try { cmd = ScpiBuilder.BuildQuery(St, c, ParamValue(), Pos(c)); }
        catch (Exception ex) { ShowToast(ex.Message, error: true); return; }
        try
        {
            Log(s, "TX", cmd, "Sky");
            string resp = await s.Device!.QueryAsync(cmd);
            Log(s, "RX", resp, "Success");
            s.LastResponse = resp;
            if (s == _s)
            {
                LastResp.Text = resp;
                LastResp.BeginAnimation(OpacityProperty, new DoubleAnimation(0.25, 1, TimeSpan.FromMilliseconds(350)));
            }
        }
        catch (Exception ex) { Log(s, "ERR", ex.Message, "Danger"); ShowToast(ex.Message, error: true); }
    }

    /// <summary>使用者最後一次按的是 Write 還是 Read（決定 Copy 複製 W 或 R 那行）；null = 都還沒按過。</summary>
    private bool? _lastWasRead;

    /// <summary>
    /// Copy：最後按的是 Read → 複製 R 指令；最後按的是 Write 或都還沒按 → 複製 W 指令。
    /// 該指令不支援所需方向時改用另一種（只能查詢的指令一律複製 R、只能寫入的一律複製 W）。
    /// </summary>
    private void Copy_Click(object sender, RoutedEventArgs e)
    {
        if (_cur is not { } c) return;
        bool wantRead = _lastWasRead == true;
        if (wantRead && !c.CanGet) wantRead = false;
        if (!wantRead && !c.CanSet) wantRead = true;
        try
        {
            string? v = ParamValue();
            var pos = Pos(c);
            if (!wantRead && ScpiBuilder.MissingValue(St, c, v, pos))
            {
                ShowToast(I18n.T("missing_param"), error: true);
                return;
            }
            string cmd = wantRead ? ScpiBuilder.BuildQuery(St, c, v, pos) : ScpiBuilder.BuildWrite(St, c, v, pos);
            Clipboard.SetText(cmd);
            ShowToast(I18n.T("copied", cmd));
        }
        catch (Exception ex) { ShowToast(ex.Message, error: true); }
    }

    private bool EnsureConnected(InstrumentSession s)
    {
        if (s.IsConnected) return true;
        ShowToast(I18n.T("not_connected"), error: true);
        return false;
    }

    // ================================================================== //
    // 連線 / 掃描（每台儀器各自一個 session，可同時連線多台）
    // ================================================================== //
    private string ResourceName() =>
        (ResourceCombo.Text ?? "").Trim().Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? "";

    private bool _busyConnect;

    private async void Connect_Click(object sender, RoutedEventArgs e)
    {
        if (_busyConnect) return;
        var s = _s;
        if (s.Device != null)
        {
            s.Device.Dispose();
            s.Device = null;
            s.Idn = "";
            Log(s, "SYS", "Disconnected", "Muted");
            UpdateConnectionUi();
            return;
        }

        string res = ResourceName();
        if (!App.SimMode && res.Length == 0) return;
        s.ResourceText = ResourceCombo.Text;
        _busyConnect = true;
        ConnectBtn.IsEnabled = false;
        ConnectText.Text = I18n.T("connecting");
        try
        {
            var dev = await Task.Run(() => App.SimMode ? Device.OpenSimulated(s.Def.SimIdn) : Device.Open(res));
            try { s.Idn = await dev.QueryAsync("*IDN?"); }
            catch { dev.Dispose(); throw; }
            s.Device = dev;
            Log(s, "SYS", (App.SimMode ? "[SIM] " : "") + $"Connected {dev.Resource} → {s.Idn}", "Success");
        }
        catch (Exception ex)
        {
            Log(s, "ERR", ex.Message, "Danger");
            MessageBox.Show(this, ex.Message, $"{I18n.T("conn_fail")} — {s.Name}", MessageBoxButton.OK, MessageBoxImage.Error);
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
        bool on = _s.IsConnected;
        ConnectText.Text = I18n.T(on ? "disconnect" : "connect");
        ConnectIcon.Text = on ? "" : "";
        ConnectBtn.Style = (Style)FindResource(on ? "OutlineButton" : "PrimaryButton");
        ResourceCombo.IsEnabled = !on;
        ScanBtn.IsEnabled = !on;
        StatusDot.SetResourceReference(Shape.FillProperty, on ? "Success" : "Faint");
        StatusText.Text = on ? $"{I18n.T("connected")}  ·  {_s.Idn}" : I18n.T("disconnected");
        StatusPill.ToolTip = on ? _s.Idn : null;
        StatusPill.SetResourceReference(Border.BorderBrushProperty, on ? "SuccessDim" : "BorderBrush");

        var conn = _sessions.Values.Where(x => x.IsConnected).ToList();
        ConnCountText.Text = I18n.T("conn_count", conn.Count);
        ConnCountPill.SetResourceReference(Border.BorderBrushProperty, conn.Count > 0 ? "SuccessDim" : "BorderBrush");
        ConnCountPill.ToolTip = conn.Count > 0 ? string.Join("\n", conn.Select(x => $"{x.Name}  —  {x.Device!.Resource}")) : null;
        FooterText.Text = conn.Count > 0
            ? string.Join("     ", conn.Select(x => $"● {x.Name} ({x.Device!.Resource})"))
            : I18n.T("conn_none");
    }

    private async void Scan_Click(object sender, RoutedEventArgs e)
    {
        var s = _s;
        ScanBtn.IsEnabled = false;
        ScanText.Text = I18n.T("scanning");
        StatusText.Text = I18n.T("scanning");
        var rot = new RotateTransform();
        ScanIcon.RenderTransformOrigin = new Point(0.5, 0.5);
        ScanIcon.RenderTransform = rot;
        ScanIcon.Text = "";
        rot.BeginAnimation(RotateTransform.AngleProperty,
            new DoubleAnimation(0, 360, TimeSpan.FromSeconds(1)) { RepeatBehavior = RepeatBehavior.Forever });
        try
        {
            var results = await Task.Run(() => VisaSession.Scan());
            s.ScanItems = results.Select(r => r.ToString()).ToList();
            Log(s, "SCAN", s.ScanItems.Count == 0 ? "(none)" : string.Join("  |  ", results.Select(r => r.Resource)), "Amber");
            if (s == _s)
            {
                ResourceCombo.ItemsSource = s.ScanItems;
                if (s.ScanItems.Count > 0)
                {
                    ResourceCombo.SelectedIndex = 0;
                    ResourceCombo.IsDropDownOpen = true;
                }
            }
        }
        catch (Exception ex)
        {
            Log(s, "ERR", ex.Message, "Danger");
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
    // Log / Toast
    // ================================================================== //
    private void Log(InstrumentSession s, string tag, string text, string brushKey)
    {
        s.AddLog(tag, text, brushKey);
        if (s == _s) ScrollLogToEnd();
    }

    private void ScrollLogToEnd()
    {
        if (_s.Log.Count > 0) LogList.ScrollIntoView(_s.Log[^1]);
    }

    private void ClearLog_Click(object sender, RoutedEventArgs e)
    {
        _s.Log.Clear();
        _s.LastResponse = "—";
        LastResp.Text = "—";
    }

    private void ShowToast(string text, bool error = false)
    {
        ToastText.Text = text;
        ToastIcon.Text = error ? "" : "";
        ToastIcon.SetResourceReference(TextBlock.ForegroundProperty, error ? "Danger" : "Success");
        var fade = new DoubleAnimationUsingKeyFrames();
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.Zero)));
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(1, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(160))));
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(1, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(2000))));
        fade.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(2400))));
        Toast.BeginAnimation(OpacityProperty, fade);
        var tt = new TranslateTransform();
        Toast.RenderTransform = tt;
        tt.BeginAnimation(TranslateTransform.YProperty,
            new DoubleAnimation(10, 0, TimeSpan.FromMilliseconds(200)) { EasingFunction = new CubicEase() });
    }

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

    private void BuildFontSizeButtons()
    {
        FontSizeButtons.Children.Clear();
        foreach (var f in ThemeManager.FontSizes)
        {
            var rb = new RadioButton
            {
                Style = (Style)FindResource("LangSeg"), GroupName = "fontsize", Tag = f,
                Content = f.Label, MinWidth = 34, IsChecked = f == ThemeManager.CurrentFont,
            };
            rb.Checked += (_, _) => { if (ThemeManager.CurrentFont != f) ThemeManager.ApplyFont(f); };
            FontSizeButtons.Children.Add(rb);
        }
    }

    private void OnThemeChanged()
    {
        ApplyTitleBar();
        // 紀錄的顏色依 key 取得，重新繫結讓 ListBox 重繪
        LogList.ItemsSource = null;
        LogList.ItemsSource = _s.Log;
        ScrollLogToEnd();
    }

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

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
