<#
.SYNOPSIS
    Collects hardware and OS details from the local Windows machine for an asset register.

.DESCRIPTION
    Gathers hostname, manufacturer, model, serial number, CPU, RAM, disks, OS version,
    last boot time and logged-on user, then prints them or exports to CSV/JSON.
    Run it on each laptop (or via your RMM tool) and append the output to your register.

.PARAMETER OutFile
    Optional path ending in .csv or .json. If omitted, results print to the console.

.EXAMPLE
    .\Get-SystemInventory.ps1
.EXAMPLE
    .\Get-SystemInventory.ps1 -OutFile .\inventory.csv
#>
[CmdletBinding()]
param(
    [string]$OutFile
)

$cs   = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS
$os   = Get-CimInstance Win32_OperatingSystem
$cpu  = Get-CimInstance Win32_Processor | Select-Object -First 1
$disks = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    "{0} {1:N0}GB ({2:N0}GB free)" -f $_.DeviceID, ($_.Size / 1GB), ($_.FreeSpace / 1GB)
}

$record = [PSCustomObject]@{
    Hostname     = $env:COMPUTERNAME
    Manufacturer = $cs.Manufacturer
    Model        = $cs.Model
    SerialNumber = $bios.SerialNumber
    CPU          = $cpu.Name.Trim()
    RamGB        = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
    Disks        = $disks -join '; '
    OS           = "$($os.Caption) ($($os.Version))"
    LastBoot     = $os.LastBootUpTime.ToString('yyyy-MM-dd HH:mm')
    CurrentUser  = $cs.UserName
    CollectedAt  = (Get-Date).ToString('yyyy-MM-dd HH:mm')
}

if (-not $OutFile) {
    $record
    return
}

switch ([IO.Path]::GetExtension($OutFile).ToLower()) {
    '.csv'  {
        # Append so the same file can collect many machines
        $record | Export-Csv -Path $OutFile -NoTypeInformation -Append
    }
    '.json' { $record | ConvertTo-Json | Set-Content -Path $OutFile -Encoding utf8 }
    default { throw "OutFile must end in .csv or .json" }
}
Write-Host "Inventory for $($record.Hostname) written to $OutFile"
