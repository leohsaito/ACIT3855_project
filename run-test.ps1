param(
    [int]$Threads = 10,
    [int]$Loops = 10
)

Remove-Item "results.jtl" -ErrorAction SilentlyContinue
Remove-Item "report" -Recurse -Force -ErrorAction SilentlyContinue

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