# Usage: powershell -NoProfile -File mei_poll.ps1 <item folder> <out file> <stop file>
# Records each %TEMP%\_MEI<n> folder loaded by a DotExpress process whose exe is under
# <item folder>, one per line in <out file>, until <stop file> exists. run_item.sh then removes
# only these folders (F-13 review fix phase): a folder of another agent's or the user's
# DotExpress is never listed. A process that ends between two polls is missed and its folder
# is left behind (the safe direction).
param([string]$Folder, [string]$Out, [string]$Stop)
$prefix = $Folder.TrimEnd('\') + '\'
$seen = @{}
while (-not (Test-Path -LiteralPath $Stop)) {
	foreach ($p in @(Get-Process DotExpress -ErrorAction SilentlyContinue)) {
		try {
			if (-not $p.Path -or -not $p.Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { continue }
			foreach ($m in $p.Modules) {
				$hit = [regex]::Match($m.FileName, '^(.*\\_MEI\d+)\\', 'IgnoreCase')
				if ($hit.Success -and -not $seen.ContainsKey($hit.Groups[1].Value)) {
					$seen[$hit.Groups[1].Value] = $true
					Add-Content -LiteralPath $Out -Value $hit.Groups[1].Value
				}
			}
		} catch {}
	}
	Start-Sleep -Milliseconds 250
}
