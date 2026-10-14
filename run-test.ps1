param(
    [int]$Threads = 10,
    [int]$Loops = 10
)

Remove-Item "$PSScriptRoot\results.jtl" -ErrorAction SilentlyContinue
Remove-Item "$PSScriptRoot\report" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "$Threads threads, $Loops loops"

$JMeter = Join-Path $PSScriptRoot "apache-jmeter-5.6.3\bin\jmeter.bat"

& $JMeter `
    -n `
    -t "$PSScriptRoot\soccer-test.jmx" `
    "-Jthreads=$Threads" `
    "-Jloops=$Loops" `
    -l "$PSScriptRoot\results.jtl" `
    -e `
    -o "$PSScriptRoot\report"

Write-Host ""
Write-Host "Database row counts:"

docker compose `
    -f "$PSScriptRoot\docker-compose.yml" `
    exec db `
    mysql `
    -u soccer_user `
    -psoccer_password `
    soccer_events `
    -e "SELECT COUNT(*) AS attendance_count FROM attendance; SELECT COUNT(*) AS ticket_sale_count FROM ticket_sale;"