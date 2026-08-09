$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $chrome) {
    Start-Sleep -Seconds 3
    Start-Process $chrome "--start-maximized https://www.instagram.com" -WindowStyle Maximized
}
