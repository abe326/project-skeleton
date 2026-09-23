<#
.SYNOPSIS
  project-skeleton をグローバル skill `new-project` として配備する(Windows)。

.DESCRIPTION
  既定  : %USERPROFILE%\.claude\skills\new-project → このリポ のジャンクションを作る(管理者権限不要)
  -Force: 既存のジャンクション・ディレクトリを置き換える
  -Copy : ジャンクションではなくコピーで配備する(INSTALLED-AS-COPY.txt を置く)

  実行例:
    powershell -ExecutionPolicy Bypass -File scripts\install-global.ps1
    powershell -ExecutionPolicy Bypass -File scripts\install-global.ps1 -Force

  外すとき(Remove-Item -Recurse は使わない。ジャンクション先の正本まで消える恐れがある):
    cmd /c rmdir "%USERPROFILE%\.claude\skills\new-project"
#>
param(
    [switch]$Force,
    [switch]$Copy
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Skeleton = (Resolve-Path "$PSScriptRoot\..").Path
$SkillsDir = Join-Path $env:USERPROFILE ".claude\skills"
$Link = Join-Path $SkillsDir "new-project"

if (-not (Test-Path (Join-Path $Skeleton "SKILL.md"))) {
    Write-Error "$Skeleton に SKILL.md がありません"
    exit 1
}
if (-not (Test-Path $SkillsDir)) {
    New-Item -ItemType Directory -Path $SkillsDir | Out-Null
}

function Remove-LinkOrDir([string]$Path) {
    $item = Get-Item $Path -Force
    if ($item.LinkType) {
        # ジャンクション / シンボリックリンクは rmdir で外す(中身は消えない)
        cmd /c rmdir "$Path"
    } else {
        Remove-Item -Recurse -Force $Path
    }
}

# --- 既存の確認 ---------------------------------------------------------
if (Test-Path $Link) {
    $item = Get-Item $Link -Force
    $target = $null
    if ($item.LinkType) {
        $target = @($item.Target)[0]
        if ($target) { $target = $target.TrimEnd("\") }
    }
    if (-not $Copy -and $item.LinkType -eq "Junction" -and $target -eq $Skeleton.TrimEnd("\")) {
        Write-Host "OK 設定済み: $Link -> $Skeleton"
        exit 0
    }
    if (-not $Force) {
        if ($item.LinkType) {
            Write-Warning "$Link は別の先を指しています: $target"
        } else {
            Write-Warning "$Link が既に存在します(ジャンクションではありません)"
        }
        Write-Warning "置き換えるには -Force を付けてください"
        exit 1
    }
    Remove-LinkOrDir $Link
}

# --- 配備 -----------------------------------------------------------------
if ($Copy) {
    Copy-Item -Recurse -Path $Skeleton -Destination $Link
    $gitDir = Join-Path $Link ".git"
    if (Test-Path $gitDir) { Remove-Item -Recurse -Force $gitDir }
    $note = @(
        "このフォルダは project-skeleton のコピーです(ジャンクションではありません)。",
        "正本: $Skeleton",
        "コピー日: $(Get-Date -Format 'yyyy-MM-dd')",
        "正本を更新したら install-global.ps1 -Copy -Force で配備し直してください。"
    ) -join "`n"
    [System.IO.File]::WriteAllText((Join-Path $Link "INSTALLED-AS-COPY.txt"), $note + "`n", (New-Object System.Text.UTF8Encoding $false))
    Write-Host "コピーで配備しました: $Link"
} else {
    New-Item -ItemType Junction -Path $Link -Target $Skeleton | Out-Null
    Write-Host "ジャンクションを作成しました: $Link -> $Skeleton"
}

# --- 検証 -----------------------------------------------------------------
$fail = 0
Get-Item $Link -Force | Select-Object LinkType, Target | Format-List | Out-String | Write-Host
if (Test-Path (Join-Path $Link "SKILL.md")) {
    Write-Host "OK $Link\SKILL.md を読めます"
} else {
    Write-Host "NG $Link\SKILL.md を読めません"
    $fail = 1
}

Write-Host ""
Write-Host "次に:"
Write-Host "  1. Claude Code を新規セッションで起動し、/ を打って new-project が出ることを確認"
Write-Host "  2. ~/.claude/CLAUDE.md への追記は SETUP.md §4 の文面をそのまま使う"
Write-Host "  3. ~/.claude はマシンごとに別です。もう一方のマシンでも同じ手順が必要です"
Write-Host ""
Write-Host "外すとき: cmd /c rmdir `"$Link`"(Remove-Item -Recurse は使わない)"

exit $fail
