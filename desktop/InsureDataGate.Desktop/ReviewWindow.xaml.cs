using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Input;
using Microsoft.Win32;

namespace InsureDataGate.Desktop;

public partial class ReviewWindow : Window
{
    private const int ReportLimit = 32 * 1024 * 1024;
    private const string Caption = "InsureDataGate — 데이터 출고 검토";
    private const string EmptyDetails = "목록에서 검사 항목이나 확인한 파일을 선택하세요.";
    private static readonly UTF8Encoding Utf8 = new(false, true);
    private static readonly JsonSerializerOptions ReportOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower, MaxDepth = 12
    };
    private CancellationTokenSource? inspection;
    private string? reportJson;
    private string? verdict;
    private string? snapshot;
    private string? manifestHash;
    private string? liveManifest;
    private string? captionIdentity;
    private ICollectionView? findings;
    private int findingTotal;
    private bool unsaved, exporting;

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
        if (exporting) e.Cancel = true;
        else if (inspection is not null)
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
        e.Effects = !IsBusy && GetDroppedManifest(e) is not null ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    private async void OnDrop(object sender, DragEventArgs e)
    {
        e.Handled = true;
        if (!IsBusy && GetDroppedManifest(e) is { } path) await CheckManifest(path);
    }

    private static string? GetDroppedManifest(DragEventArgs e) =>
        e.Data.GetData(DataFormats.FileDrop, autoConvert: false) is string[] { Length: 1 } paths &&
        string.Equals(Path.GetExtension(paths[0]), ".json", StringComparison.OrdinalIgnoreCase) ? paths[0] : null;

    private async Task PickManifest()
    {
        if (IsBusy) return;
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
            ShowReport(json, path, isSaved: false);
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

    private static Process StartChecker(params string[] arguments)
    {
        var start = new ProcessStartInfo(Path.Combine(AppContext.BaseDirectory, "python", "python.exe"))
        {
            UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true,
            RedirectStandardError = true, StandardOutputEncoding = Utf8, WorkingDirectory = AppContext.BaseDirectory
        };
        foreach (string argument in new[] { "-I", "-B", "-X", "utf8", "-m", "insuredatagate" })
            start.ArgumentList.Add(argument);
        foreach (string argument in arguments) start.ArgumentList.Add(argument);
        return Process.Start(start) ?? throw new IOException("Could not start the checker.");
    }

    private static async Task<string> RunChecker(string manifest, CancellationToken token)
    {
        using var process = StartChecker("check", "--json", "--", manifest);
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
        if (IsBusy) return;
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
        if (IsBusy || reportJson is null) return;
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

    private async void OnExport(object sender, RoutedEventArgs e)
    {
        if (IsBusy || verdict != "PASS" || liveManifest is not { } manifest || manifestHash is not { } hash) return;
        var dialog = new SaveFileDialog
        {
            Title = "모델 입력 JSONL 저장", Filter = "모델 입력 (*.jsonl)|*.jsonl",
            AddExtension = true, DefaultExt = ".jsonl", OverwritePrompt = false
        };
        if (dialog.ShowDialog(this) != true) return;
        exporting = true;
        SetBusy(true);
        ExportState.Text = "재검사 중…";
        Status.Text = "파일을 다시 검사해 모델 입력을 내보내는 중입니다.";
        try
        {
            using var process = StartChecker("export-inputs", "--expected-manifest-sha256", hash, "--output", dialog.FileName, "--", manifest);
            await Task.WhenAll(process.StandardOutput.BaseStream.CopyToAsync(Stream.Null),
                process.StandardError.BaseStream.CopyToAsync(Stream.Null), process.WaitForExitAsync());
            switch (process.ExitCode)
            {
                case 0:
                    ExportState.Text = "저장 완료";
                    Status.Text = $"모델 입력 저장 완료 · {Path.GetFileName(dialog.FileName)}";
                    break;
                case 1:
                    liveManifest = null;
                    ValidationState.Text = "이전 PASS · 재검사 필요";
                    ExportState.Text = "내보내기 차단";
                    Title = $"InsureDataGate — 재검사 필요 · {captionIdentity}";
                    Status.Text = "현재 파일이 검사 당시와 다릅니다. 매니페스트를 다시 검사하세요.";
                    break;
                case 2:
                    ExportState.Text = "다른 경로 필요";
                    Status.Text = "모델 입력을 저장하지 못했습니다. 기존 파일은 보존했습니다. 새 경로를 선택하세요.";
                    break;
                default:
                    throw new IOException("Export failed.");
            }
        }
        catch (Exception error) when (error is IOException or Win32Exception)
        {
            ExportState.Text = "저장 실패";
            Status.Text = "내보내기 결과를 확인하지 못했습니다. 파일 경로를 확인하세요.";
        }
        finally
        {
            exporting = false;
            SetBusy(false);
        }
    }

    private void ClearResult()
    {
        reportJson = null;
        verdict = null;
        snapshot = manifestHash = liveManifest = null;
        captionIdentity = null;
        Title = Caption;
        unsaved = false;
        SaveButton.IsEnabled = false;
        ExportButton.IsEnabled = false;
        findings = null;
        findingTotal = 0;
        Files.ItemsSource = Issues.ItemsSource = null;
        FindingSearch.Text = "";
        FindingSearch.IsEnabled = false;
        UpdateFindings();
        ValidationState.Text = "대기";
        HumanState.Text = "별도 확인";
        ExportState.Text = "검사 필요";
        Summary.Text = "";
        Details.Text = EmptyDetails;
    }

    private void ShowReport(string json, string path, bool isSaved)
    {
        var report = JsonSerializer.Deserialize<InspectionReport>(json, ReportOptions);
        if (report?.SchemaVersion != "insuredatagate.report.v1" || report.Status is not ("PASS" or "BLOCK") ||
            report.Issues is null || report.Files is null ||
            report.Issues.Any(issue => string.IsNullOrEmpty(issue?.Code) || string.IsNullOrEmpty(issue.Location) || string.IsNullOrEmpty(issue.Message)) ||
            report.Files.Any(file => string.IsNullOrEmpty(file?.Path) || string.IsNullOrEmpty(file.Sha256) || file.Bytes < 0))
            throw new InvalidDataException("Invalid report schema.");
        reportJson = json;
        verdict = report.Status;
        liveManifest = isSaved ? null : path;
        manifestHash = report.ManifestSha256;
        unsaved = !isSaved;
        var origin = isSaved ? "저장 보고서" : "로컬 매니페스트";
        var title = Path.GetFileName(path);
        var identity = $"데이터셋 {report.DatasetId ?? "확인 불가"} · 버전 {report.Version ?? "확인 불가"}";
        captionIdentity = $"{CaptionPart(report.DatasetId, 28)} · 버전 {CaptionPart(report.Version, 16)}";
        Title = $"InsureDataGate — {(isSaved ? "보관된 " : "")}{verdict} · {captionIdentity}";
        Status.Text = $"{verdict} · 검사 항목 {report.Issues.Length:N0}개 · {(isSaved ? "저장 보고서 · 과거 결과" : "미저장")}";
        Summary.Text = $"{identity} · {title}";
        snapshot = $"{identity}\n{origin}  {title}\n\n매니페스트 SHA-256\n{manifestHash ?? "확인 불가"}";
        ValidationState.Text = isSaved ? $"보관된 {verdict}" : verdict;
        var reviewCount = report.Issues.Count(issue => issue.RequiresReview);
        HumanState.Text = reviewCount == 0 ? "별도 확인" : $"선언 확인 {reviewCount:N0}건";
        ExportState.Text = isSaved ? "매니페스트 필요" : verdict == "PASS" ? "재검사 후 가능" : "차단";
        findingTotal = report.Issues.Length;
        findings = CollectionViewSource.GetDefaultView(report.Issues);
        findings.Filter = item => item is Issue issue && MatchesSearch(issue);
        Issues.ItemsSource = findings;
        FindingSearch.IsEnabled = findingTotal > 0;
        UpdateFindings();
        Files.ItemsSource = report.Files;
        ResultsTabs.SelectedIndex = findingTotal == 0 ? 1 : 0;
        var visible = ResultsTabs.SelectedIndex == 0 ? Issues : Files;
        if (visible.Items.Count > 0) visible.SelectedIndex = 0;
        UpdateDetails();
        SaveButton.IsEnabled = true;
    }

    private bool MatchesSearch(Issue issue)
    {
        var query = FindingSearch.Text.Trim();
        return issue.Code.Contains(query, StringComparison.OrdinalIgnoreCase) ||
            issue.Location.Contains(query, StringComparison.OrdinalIgnoreCase) ||
            issue.Kind.Contains(query, StringComparison.OrdinalIgnoreCase);
    }

    private void OnSearch(object sender, TextChangedEventArgs e)
    {
        if (findings is null) return;
        var selected = Issues.SelectedItem;
        findings.Refresh();
        if (selected is not null && Issues.Items.Contains(selected)) Issues.SelectedItem = selected;
        else if (Issues.Items.Count > 0) Issues.SelectedIndex = 0;
        UpdateFindings();
        UpdateDetails();
    }

    private void UpdateFindings()
    {
        int shown = Issues.Items.Count;
        FindingCount.Text = $"{shown:N0} / {findingTotal:N0}";
        NoFindings.Visibility = shown == 0 ? Visibility.Visible : Visibility.Collapsed;
        NoFindings.Text = reportJson is null ? "검사 결과가 여기에 표시됩니다."
            : findingTotal == 0 ? "검사 항목이 없습니다." : "일치하는 규칙이나 입력 위치가 없습니다.";
    }

    private void OnSelection(object sender, SelectionChangedEventArgs e) => UpdateDetails();

    private void UpdateDetails()
    {
        if (Details is null) return;
        var evidence = ResultsTabs.SelectedIndex == 0 && Issues?.SelectedItem is Issue issue
            ? $"입력 위치  {issue.Location}\n규칙  {issue.Code} · {issue.Kind}\n\n{issue.Message}"
            : ResultsTabs.SelectedIndex == 1 && Files?.SelectedItem is CheckedFile file
                ? $"파일  {file.Path}\n크기  {file.Bytes:N0} 바이트\n\n파일 SHA-256\n{file.Sha256}"
                : EmptyDetails;
        Details.Text = snapshot is null ? evidence : $"{evidence}\n\n검사 시점의 스냅샷\n{snapshot}";
        Details.ScrollToHome();
    }

    private bool IsBusy => inspection is not null || exporting;

    private static string CaptionPart(string? value, int limit)
    {
        if (string.IsNullOrWhiteSpace(value)) return "확인 불가";
        var text = new StringInfo(string.Concat(value.Select(ch => char.IsControl(ch) ? ' ' : ch)));
        return text.LengthInTextElements <= limit ? text.String : text.SubstringByTextElements(0, limit) + "…";
    }

    private void SetBusy(bool busy)
    {
        OpenManifestButton.IsEnabled = OpenReportButton.IsEnabled = !busy;
        SaveButton.IsEnabled = !busy && reportJson is not null;
        ExportButton.IsEnabled = !busy && verdict == "PASS" && liveManifest is not null && manifestHash is not null;
        CancelButton.IsEnabled = inspection is not null;
        CancelButton.Visibility = inspection is not null ? Visibility.Visible : Visibility.Collapsed;
    }

    private sealed record InspectionReport(string SchemaVersion, string Status, string? DatasetId,
        string? Version, string? ManifestSha256, Issue[] Issues, CheckedFile[] Files);
    private sealed record Issue(string Code, string Location, string Message)
    {
        public bool RequiresReview => Code is "SOURCE_APPROVAL" or "GOLD_APPROVAL" or "SELF_REVIEW";
        public string Kind => RequiresReview ? "선언 확인" : Code == "CHECK_NOT_RUN" ? "미실행" : "실패";
    }
    private sealed record CheckedFile(string Path, string Sha256, long Bytes);
}
