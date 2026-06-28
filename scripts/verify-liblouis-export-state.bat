@echo off
setlocal EnableExtensions

set "ROOT=%~dp0.."
set "CUR_DLL=%ROOT%\client\braille\liblouis.dll"
set "REF_DLL=%ROOT%\ref\nvda\build\x86_64\liblouis\liblouis.dll"

if not exist "%CUR_DLL%" (
    echo Missing current DLL: "%CUR_DLL%"
    exit /b 1
)

if not exist "%REF_DLL%" (
    echo Missing NVDA reference DLL: "%REF_DLL%"
    echo Continuing with current DLL only.
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "function Get-Exports([string]$Path) {" ^
  "  $fs = [System.IO.File]::OpenRead($Path);" ^
  "  try {" ^
  "    $br = New-Object System.IO.BinaryReader($fs);" ^
  "    if ($br.ReadUInt16() -ne 0x5A4D) { throw 'Missing MZ signature' }" ^
  "    $fs.Position = 0x3C; $peOffset = $br.ReadInt32();" ^
  "    $fs.Position = $peOffset; if ($br.ReadUInt32() -ne 0x00004550) { throw 'Missing PE signature' }" ^
  "    $machine = $br.ReadUInt16(); $sections = $br.ReadUInt16(); $fs.Position += 12; $sizeOpt = $br.ReadUInt16(); $fs.Position += 2;" ^
  "    $optStart = $fs.Position; $magic = $br.ReadUInt16(); if ($magic -eq 0x10B) { $is64 = $false } elseif ($magic -eq 0x20B) { $is64 = $true } else { throw ('Unknown optional header magic: {0:X4}' -f $magic) }" ^
  "    $dataDirStart = $optStart + ($(if ($is64) { 0x70 } else { 0x60 }));" ^
  "    $fs.Position = $dataDirStart; $exportRva = $br.ReadUInt32(); $exportSize = $br.ReadUInt32();" ^
  "    if ($exportRva -eq 0) { return @() }" ^
  "    $sectionTable = $optStart + $sizeOpt;" ^
  "    function Convert-RvaToOffset([uint32]$Rva) {" ^
  "      for ($i = 0; $i -lt $sections; $i++) {" ^
  "        $fs.Position = $sectionTable + (40 * $i) + 8;" ^
  "        $virtualSize = $br.ReadUInt32();" ^
  "        $virtualAddress = $br.ReadUInt32();" ^
  "        $sizeOfRawData = $br.ReadUInt32();" ^
  "        $pointerToRawData = $br.ReadUInt32();" ^
  "        if ($Rva -ge $virtualAddress -and $Rva -lt ($virtualAddress + [Math]::Max($virtualSize, $sizeOfRawData))) { return [int]($pointerToRawData + ($Rva - $virtualAddress)) }" ^
  "      }" ^
  "      throw ('Could not map RVA 0x{0:X8} to file offset' -f $Rva)" ^
  "    }" ^
  "    $exportDir = Convert-RvaToOffset $exportRva;" ^
  "    $fs.Position = $exportDir + 12; $nameRva = $br.ReadUInt32(); $base = $br.ReadUInt32(); $numberOfFunctions = $br.ReadUInt32(); $numberOfNames = $br.ReadUInt32(); $addressOfFunctions = $br.ReadUInt32(); $addressOfNames = $br.ReadUInt32(); $addressOfNameOrdinals = $br.ReadUInt32();" ^
  "    $namePtrOffset = Convert-RvaToOffset $addressOfNames;" ^
  "    $ordOffset = Convert-RvaToOffset $addressOfNameOrdinals;" ^
  "    $exports = New-Object System.Collections.Generic.List[string];" ^
  "    for ($i = 0; $i -lt $numberOfNames; $i++) {" ^
  "      $fs.Position = $namePtrOffset + (4 * $i); $rva = $br.ReadUInt32(); $nameOffset = Convert-RvaToOffset $rva; $fs.Position = $nameOffset; $bytes = New-Object System.Collections.Generic.List[byte]; while (($b = $br.ReadByte()) -ne 0) { $bytes.Add($b) } $exports.Add([System.Text.Encoding]::ASCII.GetString($bytes.ToArray()))" ^
  "    }" ^
  "    return $exports" ^
  "  } finally { $fs.Dispose() }" ^
  "}" ^
  "function Show-Exports([string]$Label, [string]$Path, [string[]]$Symbols) {" ^
  "  Write-Host $Label;" ^
  "  Write-Host ('  ' + (Resolve-Path $Path));" ^
  "  $exports = Get-Exports $Path;" ^
  "  foreach ($symbol in $Symbols) { if ($exports -contains $symbol) { Write-Host ('  OK: ' + $symbol) } else { Write-Host ('  MISSING: ' + $symbol) } }" ^
  "}" ^
  "$symbols = @('lou_freeTableFile','lou_freeTableFiles','lou_freeTableInfo','lou_findTable','lou_findTables','lou_getTableInfo','lou_listTables','lou_charSize','lou_version');" ^
  "Show-Exports 'Current DLL' '%CUR_DLL%' $symbols;" ^
  "if (Test-Path '%REF_DLL%') { Show-Exports 'NVDA reference DLL' '%REF_DLL%' $symbols }"

exit /b %ERRORLEVEL%
