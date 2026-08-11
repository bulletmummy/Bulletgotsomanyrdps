# Set wallpaper
$wp = "C:\Windows\Temp\bullet_wallpaper.png"
if (Test-Path $wp) {
    $code = 'using System; using System.Runtime.InteropServices; public class WP2 { [DllImport("user32.dll",CharSet=CharSet.Auto)] public static extern int SystemParametersInfo(int a,int b,string c,int d); }'
    Add-Type -TypeDefinition $code -Language CSharp -ErrorAction SilentlyContinue
    [WP2]::SystemParametersInfo(20, 0, $wp, 3) | Out-Null
}

# Launch Chrome
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $chrome) {
    Start-Sleep -Seconds 3
    Start-Process $chrome "--start-maximized https://www.instagram.com" -WindowStyle Maximized
}
