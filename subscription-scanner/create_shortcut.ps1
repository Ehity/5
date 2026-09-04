# Создаёт ярлык «Сканер подписок» на рабочем столе с иконкой icon.ico

$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Сканер подписок.lnk"

$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = "c:\Python\subscription-scanner\run_scanner.bat"
$lnk.WorkingDirectory = "c:\Python\subscription-scanner"
$lnk.IconLocation = "c:\Python\subscription-scanner\icon.ico,0"
$lnk.Description = "Сканер подписок: найдёт подписки в выписке и посчитает экономию"
$lnk.Save()

if (Test-Path $lnkPath) {
    Write-Output "SHORTCUT OK: $lnkPath"
} else {
    Write-Output "SHORTCUT FAILED"
}
