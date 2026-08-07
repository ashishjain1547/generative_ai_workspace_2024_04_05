# ==========================================
# Windows System Report
# ==========================================

$OutFile = "system_report_$(Get-Date -Format yyyyMMdd_HHmmss).txt"

function Section($title) {
    Add-Content $OutFile ""
    Add-Content $OutFile ("=" * 80)
    Add-Content $OutFile $title
    Add-Content $OutFile ("=" * 80)
}

"Generated: $(Get-Date)" | Out-File $OutFile

Section "Computer"

Get-ComputerInfo | Out-String | Add-Content $OutFile

Section "Operating System"

systeminfo | Out-String | Add-Content $OutFile

Section "CPU"

Get-CimInstance Win32_Processor |
Format-List * | Out-String | Add-Content $OutFile

Section "Motherboard"

Get-CimInstance Win32_BaseBoard |
Format-List * | Out-String | Add-Content $OutFile

Section "BIOS"

Get-CimInstance Win32_BIOS |
Format-List * | Out-String | Add-Content $OutFile

Section "Memory"

Get-CimInstance Win32_PhysicalMemory |
Sort-Object BankLabel |
Format-Table Manufacturer,BankLabel,Capacity,Speed,ConfiguredClockSpeed,PartNumber -Auto |
Out-String | Add-Content $OutFile

Section "Memory Summary"

Get-CimInstance Win32_ComputerSystem |
Select-Object TotalPhysicalMemory |
Format-List | Out-String | Add-Content $OutFile

Section "GPU"

Get-CimInstance Win32_VideoController |
Format-List * | Out-String | Add-Content $OutFile

Section "Disk Drives"

Get-Disk |
Format-List * | Out-String | Add-Content $OutFile

Section "Volumes"

Get-Volume |
Format-Table DriveLetter,FileSystemLabel,FileSystem,SizeRemaining,Size |
Out-String | Add-Content $OutFile

Section "SMART"

Get-PhysicalDisk |
Format-List * | Out-String | Add-Content $OutFile

Section "Network"

Get-NetAdapter |
Format-Table Name,Status,LinkSpeed,MacAddress |
Out-String | Add-Content $OutFile

Section "IP Configuration"

ipconfig /all | Out-String | Add-Content $OutFile

Section "Battery"

try {
    Get-CimInstance Win32_Battery |
    Format-List * | Out-String | Add-Content $OutFile
}
catch {}

Section "Virtualization"

systeminfo | findstr /i "Hyper-V Virtualization VM Monitor SLAT"

Section "Windows Features"

dism /online /Get-Features |
Out-String | Add-Content $OutFile

Section "Environment Variables"

Get-ChildItem Env: |
Sort Name |
Out-String | Add-Content $OutFile

Section "PATH"

$env:PATH | Add-Content $OutFile

Section "Installed Software"

Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* ,
                 HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* `
    -ErrorAction SilentlyContinue |
Select DisplayName,DisplayVersion,Publisher |
Sort DisplayName |
Out-String | Add-Content $OutFile

Section "Python"

where python 2>$null | Out-String | Add-Content $OutFile
python --version 2>&1 | Out-String | Add-Content $OutFile
pip list 2>&1 | Out-String | Add-Content $OutFile

Section "Node"

node --version 2>&1 | Out-String | Add-Content $OutFile
npm --version 2>&1 | Out-String | Add-Content $OutFile

Section "Java"

java -version 2>&1 | Out-String | Add-Content $OutFile

Section "Git"

git --version 2>&1 | Out-String | Add-Content $OutFile

Section "Docker"

docker version 2>&1 | Out-String | Add-Content $OutFile
docker info 2>&1 | Out-String | Add-Content $OutFile

Section "WSL"

wsl --status 2>&1 | Out-String | Add-Content $OutFile
wsl -l -v 2>&1 | Out-String | Add-Content $OutFile

Section "GPU Drivers"

driverquery |
Out-String | Add-Content $OutFile

Section "Running Processes"

Get-Process |
Sort CPU -Descending |
Select -First 100 |
Out-String | Add-Content $OutFile

Write-Host ""
Write-Host "Report written to:"
Write-Host $OutFile