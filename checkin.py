#!/usr/bin/env python3
"""
ViewTurbo 每日自动签到 — GitHub Actions 版
登录 → 签到 → 输出结果
"""

import os
import sys
import json
import hashlib
import requests
from datetime import datetime

# API 基础域名（多域名容灾，依次降级）
API_BASES = [
    "https://api.viewturbo.info",
    "https://api.mambo-mambo.com",
    "https://api.vpn-test.org",
]

# 公共 query 参数
COMMON_QS = "platform=web&cur_version=0.0.0&token={token}&deviceinfo=&lang=hk&code=Others"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def api_call(path, method="GET", body=None, token=""):
    """带多域名降级的 API 请求"""
    for base in API_BASES:
        url = f"{base}{path}?{COMMON_QS.format(token=token)}"
        try:
            headers = {"Content-Type": "application/json"}
            if method == "POST":
                resp = requests.post(url, data=body or "{}", headers=headers, timeout=30)
            else:
                resp = requests.get(url, headers=headers, timeout=30)
            return resp.json()
        except Exception as e:
            log(f"  {base} 请求失败: {e}")
            continue
    return None


def main():
    email = os.environ.get("VT_EMAIL", "")
    password = os.environ.get("VT_PASSWORD", "")

    if not email or not password:
        log("错误: 缺少环境变量 VT_EMAIL 或 VT_PASSWORD")
        sys.exit(1)

    log("===== ViewTurbo 签到开始 =====")

    # 1. 登录
    log(f"正在登录 {email} ...")
    md5_pass = md5(password)
    login_body = json.dumps({"email": email, "password": md5_pass})
    login_resp = api_call("/appuser/reglogin", method="POST", body=login_body)

    if not login_resp or login_resp.get("code") != 0:
        msg = login_resp.get("msg", "无响应") if login_resp else "无响应"
        log(f"登录失败: {msg}")
        sys.exit(1)

    token = login_resp.get("data", {}).get("token", "")
    if not token:
        log(f"登录失败: 返回中无 token。响应: {json.dumps(login_resp, ensure_ascii=False)}")
        sys.exit(1)
    log("登录成功，已获取 token。")

    # 2. 查签到状态
    status_resp = api_call("/appuser/checkin_status", method="GET", token=token)
    if status_resp and status_resp.get("code") == 0:
        log(f"签到前状态: {json.dumps(status_resp.get('data'), ensure_ascii=False)}")

    # 3. 执行签到
    log("正在签到 ...")
    checkin_resp = api_call("/appuser/checkin", method="POST", body="{}", token=token)

    if checkin_resp and checkin_resp.get("code") == 0:
        log(f"✅ 签到成功! 返回: {json.dumps(checkin_resp, ensure_ascii=False)}")
    else:
        code = checkin_resp.get("code") if checkin_resp else "N/A"
        msg = checkin_resp.get("msg", "无响应") if checkin_resp else "无响应"
        log(f"⚠️ 签到返回: code={code} msg={msg} (可能是今天已签到，属正常)")

    # 4. 查签到后状态
    status_resp2 = api_call("/appuser/checkin_status", method="GET", token=token)
    if status_resp2 and status_resp2.get("code") == 0:
        log(f"签到后状态: {json.dumps(status_resp2.get('data'), ensure_ascii=False)}")

    log("===== 签到结束 =====")


if __name__ == "__main__":
    main()