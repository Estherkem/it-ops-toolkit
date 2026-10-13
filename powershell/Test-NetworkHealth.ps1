<#
.SYNOPSIS
    Quick connectivity check: ping, DNS resolution and TCP port tests against a list of targets.

.DESCRIPTION
    Useful first step when someone says "the internet is down" or a SaaS app won't load.
    Targets are "host" or "host:port". Hosts without a port get a ping + DNS check only.

.PARAMETER Targets
    One or more targets. Defaults to a sensible set of public endpoints.

.EXAMPLE
    .\Test-NetworkHealth.ps1
.EXAMPLE
    .\Test-NetworkHealth.ps1 -Targets 'google.com:443','8.8.8.8','mail.example.com:993'
#>
[CmdletBinding()]
param(
    [string[]]$Targets = @('8.8.8.8', 'google.com:443', 'github.com:443', 'outlook.office365.com:443')
)

$results = foreach ($t in $Targets) {
    $hostName, $port = $t -split ':', 2

    $dns = $null
    try {
        $dns = (Resolve-DnsName -Name $hostName -ErrorAction Stop |
                Where-Object { $_.IPAddress } | Select-Object -First 1).IPAddress
    } catch { }

    $ping = Test-Connection -ComputerName $hostName -Count 2 -Quiet -ErrorAction SilentlyContinue

    $portOpen = $null
    if ($port) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $portOpen = $client.ConnectAsync($hostName, [int]$port).Wait(3000)
        } catch {
            $portOpen = $false
        } finally {
            $client.Dispose()
        }
    }

    [PSCustomObject]@{
        Target   = $t
        Resolved = if ($dns) { $dns } else { 'FAILED' }
        Ping     = if ($ping) { 'OK' } else { 'NO REPLY' }
        Port     = if ($null -eq $portOpen) { '-' } elseif ($portOpen) { 'OPEN' } else { 'CLOSED' }
    }
}

$results | Format-Table -AutoSize

$failed = $results | Where-Object { $_.Resolved -eq 'FAILED' -or $_.Port -eq 'CLOSED' }
if ($failed) {
    Write-Warning "$(@($failed).Count) target(s) failed. Note: some hosts block ping, so check DNS and port results first."
}
