using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.Win32;

namespace InsureDataGate.Desktop;

public partial class ReviewWindow : Window
{
    private const int ReportLimit = 32 * 1024 * 1024;
    private const string EmptyDetails = "목록에서 검사 항목이나 확인한 파일을 선택하세요.";
    private static readonly UTF8Encoding Utf8 = new(false, true);
    private static readonly JsonSerializerOptions ReportOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower, MaxDepth = 12
    };
    private CancellationTokenSource? inspection;
    private string? reportJson;
    private string? verdict;
    private bool unsaved;

    public ReviewWindow()
    {
        InitializeComponent();
        Loaded += (_, _) => OpenManifestButton.Focus();
    }

    private async void OnOpenManifest(object sender, RoutedEventArgs e) => await PickManifest();
    private void OnOpenReport(object sender, RoutedEventArgs e) => PickReport();
    private void OnSaveReport(object sender, RoutedEventArgs e) => SaveReport();
    private void OnCancel(object sender, RoutedEventArgs e) => inspection?.Cancel();

    private async void OnKey(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape && inspection is not null)
        {
            inspection.Cancel();
            e.Handled = true;
        }
        else if (Keyboard.Modifiers == (ModifierKeys.Control | ModifierKeys.Shift) && e.Key == Key.O)
        {
            e.Handled = true;
            PickReport();
        }
        else if (Keyboard.Modifiers == ModifierKeys.Control && e.Key == Key.O)
        {
            e.Handled = true;
            await PickManifest();
        }
        else if (Keyboard.Modifiers == ModifierKeys.Control && e.Key == Key.S)
        {
            e.Handled = true;
            SaveReport();
        }
    }

    private void OnZoom(object sender, SelectionChangedEventArgs e) => FontSize = ZoomSelector.SelectedIndex switch
    {
        1 => 17.5, 2 => 21, _ => 14
    };

    private void OnClosing(object? sender, CancelEventArgs e)
    {
        if (inspection is not null)
        {
            inspection.Cancel();
            e.Cancel = true;
        }
        else e.Cancel = !CanDiscard();
    }

    private bool CanDiscard() => !unsaved || MessageBox.Show(this,
        "현재 검사 보고서를 저장하지 않았습니다. 이 결과를 닫을까요?",
        "미저장 보고서", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) == MessageBoxResult.Yes;

    private void OnDragOver(object sender, DragEventArgs e)
    {
        e.Effects = inspection is null && GetDroppedManifest(e) is not null ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    private async void OnDrop(object sender, DragEventArgs e)
    {
        e.Handled = true;
        if (inspection is null && GetDroppedManifest(e) is { } path) await CheckManifest(path);
    }

    private static string? GetDroppedManifest(DragEventArgs e) =>
        e.Data.GetData(DataFormats.FileDrop, autoConvert: false) is string[] { Length: 1 } paths &&
        string.Equals(Path.GetExtension(paths[0]), ".json", StringComparison.OrdinalIgnoreCase) ? paths[0] : null;

    private async Task PickManifest()
    {
        if (inspection is not null) return;
        var dialog = new OpenFileDialog { Title = "매니페스트 열기", Filter = "JSON 매니페스트 (*.json)|*.json" };
        if (dialog.ShowDialog(this) == true) await CheckManifest(dialog.FileName);
    }

    private async Task CheckManifest(string path)
    {
        if (!CanDiscard()) return;
        ClearResult();
        using var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        inspection = cancel;
        SetBusy(true);
        Status.Text = "매니페스트 검사 중…";
        Summary.Text = Path.GetFileName(path);
        try
        {
            var json = await RunChecker(path, cancel.Token);
            ShowReport(json, Path.GetFileName(path), isSaved: false);
        }
        catch (OperationCanceledException) { Status.Text = "검사가 중단됐습니다. 다시 검사하려면 매니페스트를 여세요."; }
        catch (Exception error) when (error is IOException or JsonException or InvalidDataException or Win32Exception or DecoderFallbackException)
        {
            Status.Text = "검사 결과를 불러오지 못했습니다. 압축을 모두 풀었는지 확인한 뒤 다시 여세요.";
        }
        finally
        {
            inspection = null;
            SetBusy(false);
        }
    }

    private static async Task<string> RunChecker(string manifest, CancellationToken token)
    {
        var start = new ProcessStartInfo(Path.Combine(AppContext.BaseDirectory, "python", "python.exe"))
        {
            UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true,
            RedirectStandardError = true, StandardOutputEncoding = Utf8, WorkingDirectory = AppContext.BaseDirectory
        };
        foreach (string argument in new[] { "-I", "-B", "-X", "utf8", "-m", "insuredatagate", "check", "--json", manifest })
            start.ArgumentList.Add(argument);
        using var process = Process.Start(start) ?? throw new IOException("Could not start the checker.");
        try
        {
            var errors = process.StandardError.BaseStream.CopyToAsync(Stream.Null, token);
            var result = new StringBuilder();
            var buffer = new char[4096];
            int read;
            while ((read = await process.StandardOutput.ReadAsync(buffer.AsMemory(), token)) != 0)
            {
                if (result.Length + read > ReportLimit) throw new InvalidDataException("Report too large.");
                result.Append(buffer, 0, read);
            }
            await process.WaitForExitAsync(token);
            await errors;
            if (process.ExitCode is not (0 or 1)) throw new IOException("Checker failed.");
            return result.ToString();
        }
        finally
        {
            if (!process.HasExited)
            {
                process.Kill();
                await process.WaitForExitAsync();
            }
        }
    }

    private void PickReport()
    {
        if (inspection is not null) return;
        var dialog = new OpenFileDialog { Title = "저장 보고서 열기", Filter = "JSON 검사 보고서 (*.json)|*.json" };
        if (dialog.ShowDialog(this) != true || !CanDiscard()) return;
        ClearResult();
        try
        {
            using var stream = File.OpenRead(dialog.FileName);
            if (stream.Length > ReportLimit) throw new InvalidDataException("Report too large.");
            using var reader = new StreamReader(stream, Utf8, detectEncodingFromByteOrderMarks: false);
            ShowReport(reader.ReadToEnd(), Path.GetFileName(dialog.FileName), isSaved: true);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or JsonException or InvalidDataException or DecoderFallbackException)
        {
            Status.Text = "보고서를 열 수 없습니다. InsureDataGate에서 저장한 JSON 검사 보고서를 선택하세요.";
        }
    }

    private void SaveReport()
    {
        if (inspection is not null || reportJson is null) return;
        var dialog = new SaveFileDialog
        {
            Title = "검사 보고서 저장", Filter = "JSON 검사 보고서 (*.json)|*.json",
            AddExtension = true, DefaultExt = ".json", OverwritePrompt = false
        };
        if (dialog.ShowDialog(this) != true) return;
        string temporary = Path.Combine(Path.GetDirectoryName(dialog.FileName)!, $".inspection-{Guid.NewGuid():N}.tmp");
        bool created = false;
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                created = true;
                using var writer = new StreamWriter(stream, Utf8);
                writer.Write(reportJson);
            }
            File.Move(temporary, dialog.FileName, overwrite: false);
            created = false;
            unsaved = false;
            Status.Text = $"{verdict} · 보고서 저장 완료 · {Path.GetFileName(dialog.FileName)}";
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            Status.Text = "보고서를 저장하지 못했습니다. 기존 파일은 보존했습니다. 새 이름과 쓰기 가능한 폴더를 선택하세요.";
        }
        finally
        {
            if (created)
            {
                try { File.Delete(temporary); }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
            }
        }
    }

    private void ClearResult()
    {
        reportJson = null;
        verdict = null;
        unsaved = false;
        SaveButton.IsEnabled = false;
        Issues.ItemsSource = Files.ItemsSource = null;
        Summary.Text = "";
        Details.Text = EmptyDetails;
    }

    private void ShowReport(string json, string title, bool isSaved)
    {
        var report = JsonSerializer.Deserialize<InspectionReport>(json, ReportOptions);
        if (report?.SchemaVersion != "insuredatagate.report.v1" || report.Status is not ("PASS" or "BLOCK") ||
            report.Issues is null || report.Files is null) throw new InvalidDataException("Invalid report schema.");
        reportJson = json;
        verdict = report.Status;
        unsaved = !isSaved;
        Status.Text = $"{report.Status} · 검사 항목 {report.Issues.Length:N0}개 · {(isSaved ? "저장 보고서" : "미저장")}";
        Summary.Text = $"{title} · 데이터셋 {report.DatasetId ?? "확인 불가"} · 버전 {report.Version ?? "확인 불가"}"
            + (report.ManifestSha256 is null ? "" : $"\n매니페스트 SHA-256 {report.ManifestSha256}");
        Issues.ItemsSource = report.Issues;
        Files.ItemsSource = report.Files;
        ResultsTabs.SelectedIndex = report.Issues.Length == 0 ? 1 : 0;
        var visible = ResultsTabs.SelectedIndex == 0 ? Issues : Files;
        if (visible.Items.Count > 0) visible.SelectedIndex = 0;
        SaveButton.IsEnabled = true;
    }

    private void OnSelection(object sender, SelectionChangedEventArgs e)
    {
        if (Details is null) return;
        Details.Text = ResultsTabs.SelectedIndex == 0 && Issues?.SelectedItem is Issue issue
            ? $"규칙  {issue.Code}\n입력 위치  {issue.Location}\n\n{issue.Message}"
            : ResultsTabs.SelectedIndex == 1 && Files?.SelectedItem is CheckedFile file
                ? $"파일  {file.Path}\n크기  {file.Bytes:N0} 바이트\n\nSHA-256\n{file.Sha256}"
                : EmptyDetails;
    }

    private void SetBusy(bool busy)
    {
        OpenManifestButton.IsEnabled = OpenReportButton.IsEnabled = !busy;
        SaveButton.IsEnabled = !busy && reportJson is not null;
        CancelButton.IsEnabled = busy;
    }

    private sealed record InspectionReport(string SchemaVersion, string Status, string? DatasetId,
        string? Version, string? ManifestSha256, Issue[] Issues, CheckedFile[] Files);
    private sealed record Issue(string Code, string Location, string Message);
    private sealed record CheckedFile(string Path, string Sha256, long Bytes);
}
