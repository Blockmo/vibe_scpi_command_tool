using System.Windows;

namespace Chroma62000P;

public partial class App : Application
{
    /// <summary>以 <c>--sim</c> 啟動時使用虛擬儀器（介面上不提供此選項，僅供開發測試）。</summary>
    public static bool SimMode { get; private set; }

    protected override void OnStartup(StartupEventArgs e)
    {
        SimMode = e.Args.Any(a => a.Equals("--sim", StringComparison.OrdinalIgnoreCase));
        DispatcherUnhandledException += (_, ex) =>
        {
            MessageBox.Show(ex.Exception.Message, "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            ex.Handled = true;
        };
        Core.ThemeManager.LoadSaved();   // 套用上次選擇的色系
        base.OnStartup(e);
    }
}
