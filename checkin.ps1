# ============================================================
#  ViewTurbo 每日自动签到脚本
#  接口: POST https://api.viewturbo.info/appuser/checkin
#  奖励: 每日签到领 100MB 流量，连续 7 天有额外奖励
# ============================================================

# ---------- 配置区（填入你的账号）----------
$Email    = "YOUR_EMAIL@example.com"   # ← 改成你的登录邮箱
$Password = "YOUR_PASSWORD"            # ← 改成你的登录密码（明文，脚本会自动 MD5）
# ------------------------------------------

# API 基础域名（多域名容灾，依次降级）
$ApiBases = @(
    "https://api.viewturbo.info",
    "https://api.mambo-mambo.com",
    "https://api.vpn-test.org"
)

# 日志文件
$LogFile = Join-Path $PSScriptRoot "checkin.log"

function Write-Log {
    param([string]$Msg)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# 计算 MD5（与前端 tm = MD5 一致）
function Get-Md5 {
    param([string]$Text)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash = $md5.ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace "-", "").ToLower()
}

# 构造带公共参数的 URL
function Build-Url {
    param([string]$Base, [string]$Path, [string]$Token = "")
    $qs = "platform=web&cur_version=0.0.0&token=$Token&deviceinfo=&lang=hk&code=Others"
    return "$Base$Path`?$qs"
}

# 带降级的请求
function Invoke-Api {
    param([string]$Path, [string]$Method = "GET", [string]$Body = $null, [string]$Token = "")
    foreach ($base in $ApiBases) {
        $url = Build-Url -Base $base -Path $Path -Token $Token
        try {
            $params = @{
                Uri             = $url
                Method          = $Method
                UseBasicParsing = $true
                ErrorAction     = "Stop"
            }
            if ($Body) {
                $params.Body = $Body
                $params.Headers = @{ "Content-Type" = "application/json" }
            }
            $resp = Invoke-WebRequest @params
            return $resp.Content | ConvertFrom-Json
        } catch {
            Write-Log "  $base 请求失败: $($_.Exception.Message)"
            continue
        }
    }
    return $null
}

# ---------- 主流程 ----------
Write-Log "===== ViewTurbo 签到开始 ====="

if ($Email -like "YOUR_EMAIL*" -or $Password -like "YOUR_PASSWORD*") {
    Write-Log "错误: 请先在脚本配置区填入邮箱和密码。"
    exit 1
}

# 1. 登录
Write-Log "正在登录 $Email ..."
$md5Pass = Get-Md5 -Text $Password
$loginBody = @{ email = $Email; password = $md5Pass } | ConvertTo-Json -Compress
$loginResp = Invoke-Api -Path "/appuser/reglogin" -Method "POST" -Body $loginBody

if (-not $loginResp -or $loginResp.code -ne 0) {
    Write-Log "登录失败: $($loginResp.msg)"
    exit 1
}

$token = $loginResp.data.token
if (-not $token) {
    Write-Log "登录失败: 返回中无 token。响应: $($loginResp | ConvertTo-Json -Compress)"
    exit 1
}
Write-Log "登录成功，已获取 token。"

# 2. 查签到状态
$statusResp = Invoke-Api -Path "/appuser/checkin_status" -Method "GET" -Token $token
if ($statusResp -and $statusResp.code -eq 0) {
    Write-Log "当前签到状态: $($statusResp.data | ConvertTo-Json -Compress)"
}

# 3. 执行签到
Write-Log "正在签到 ..."
$checkinResp = Invoke-Api -Path "/appuser/checkin" -Method "POST" -Body "{}" -Token $token

if ($checkinResp -and $checkinResp.code -eq 0) {
    Write-Log "签到成功!  返回: $($checkinResp | ConvertTo-Json -Compress)"
} else {
    $msg = if ($checkinResp) { $checkinResp.msg } else { "无响应" }
    Write-Log "签到返回: code=$($checkinResp.code) msg=$msg  (可能是今天已签到，属正常)"
}

# 4. 查签到后状态
$statusResp2 = Invoke-Api -Path "/appuser/checkin_status" -Method "GET" -Token $token
if ($statusResp2 -and $statusResp2.code -eq 0) {
    Write-Log "签到后状态: $($statusResp2.data | ConvertTo-Json -Compress)"
}

Write-Log "===== 签到结束 ====="