#!/usr/bin/env python3
"""
ViewTurbo 每日自动签到 — GitHub Actions 版（多账号）
从 VT_ACCOUNTS 环境变量读取 JSON 账号列表，逐个登录签到。
格式: [{"email":"...","password":"..."}, ...]
"""

import os
import sys
import json
import hashlib
import requests
from datetime import datetime

API_BASES = [
    "https://api.viewturbo.info",
    "https://api.mambo-mambo.com",
    "https://api.vpn-test.org",
]

COMMON_QS = "platform=web&cur_version=0.0.0&token={token}&deviceinfo=&lang=hk&code=Others"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def api_call(path, method="GET", body=None, token=""):
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


def checkin_one(email, password):
    """单个账号签到，返回 (success, message)"""
    log(f"--- 账号: {email} ---")

    # 1. 登录
    md5_pass = md5(password)
    login_body = json.dumps({"email": email, "password": md5_pass})
    login_resp = api_call("/appuser/reglogin", method="POST", body=login_body)

    if not login_resp or login_resp.get("code") != 0:
        msg = login_resp.get("msg", "无响应") if login_resp else "无响应"
        log(f"❌ 登录失败: {msg}")
        return False, f"{email}: 登录失败 - {msg}"

    token = login_resp.get("data", {}).get("token", "")
    if not token:
        log("❌ 登录失败: 返回中无 token")
        return False, f"{email}: 无 token"

    log("登录成功")

    # 2. 签到
    checkin_resp = api_call("/appuser/checkin", method="POST", body="{}", token=token)

    if checkin_resp and checkin_resp.get("code") == 0:
        data = checkin_resp.get("data", {})
        reward = data.get("reward_display", "?")
        consecutive = data.get("consecutive", "?")
        log(f"✅ 签到成功! 连续 {consecutive} 天, 本次奖励 {reward}")
        return True, f"{email}: 签到成功, 奖励 {reward}"
    else:
        code = checkin_resp.get("code") if checkin_resp else "N/A"
        msg = checkin_resp.get("msg", "无响应") if checkin_resp else "无响应"
        log(f"⚠️ 签到返回: code={code} msg={msg}")
        # 今天已签到也算成功
        if "已签到" in msg:
            return True, f"{email}: 今天已签到"
        return False, f"{email}: {msg}"


def main():
    accounts_json = os.environ.get("VT_ACCOUNTS", "")

    if not accounts_json:
        log("错误: 缺少环境变量 VT_ACCOUNTS")
        sys.exit(1)

    try:
        accounts = json.loads(accounts_json)
    except json.JSONDecodeError as e:
        log(f"错误: VT_ACCOUNTS JSON 解析失败: {e}")
        sys.exit(1)

    log(f"===== ViewTurbo 签到开始 ({len(accounts)} 个账号) =====")

    results = []
    for i, acc in enumerate(accounts):
        email = acc.get("email", "")
        password = acc.get("password", "")
        if not email or not password:
            log(f"⚠️ 账号 {i+1} 缺少 email 或 password，跳过")
            continue
        ok, msg = checkin_one(email, password)
        results.append((ok, msg))
        log("")

    # 汇总
    success = sum(1 for ok, _ in results if ok)
    fail = len(results) - success
    log(f"===== 签到结束: {success} 成功, {fail} 失败 =====")

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()