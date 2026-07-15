#!/usr/bin/env python3
"""
笑话机器人 — 定时从网上拉取中文笑话发送到飞书群

策略：
- 每天 08:30～12:00 和 14:00～19:30 之间发送笑话
- 每次发送后，随机等待 15～60 分钟再发送下一次
- 跨天自动重置，保证每天的上班时间都发
- 多个中文笑话源随机切换，抓取失败自动换源

State file: ~/.hermes/scripts/joke_state.json
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, time as dtime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── 配置 ─────────────────────────────────────────────
STATE_FILE = os.path.expanduser("~/.hermes/scripts/joke_state.json")
TZ_HOUR_OFFSET = 8  # 北京时间 UTC+8

# 工作时间段（扩大：最早 08:30，最晚 19:30）
MORNING_START = dtime(8, 30)    # 08:30
MORNING_END = dtime(12, 0)      # 12:00
AFTERNOON_START = dtime(14, 0)  # 14:00
AFTERNOON_END = dtime(19, 30)   # 19:30

# 随机间隔范围（分钟）
MIN_INTERVAL = 15
MAX_INTERVAL = 60

# ── 中文笑话源 ───────────────────────────────────────────
JOKE_SOURCES = [
    {
        "name": "毒鸡汤",
        "url": "https://api.shadiao.pro/du",
        "headers": {"User-Agent": "JokeBot/1.0"},
        "parser": lambda data: json.loads(data).get("data", {}).get("text", ""),
    },
    {
        "name": "彩虹屁",
        "url": "https://api.shadiao.pro/chp",
        "headers": {"User-Agent": "JokeBot/1.0"},
        "parser": lambda data: json.loads(data).get("data", {}).get("text", ""),
    },
    {
        "name": "一言",
        "url": "https://api.btstu.cn/yan/api.php?charset=utf-8&encode=json",
        "headers": {"User-Agent": "JokeBot/1.0"},
        "parser": lambda data: json.loads(data).get("text", ""),
    },
]


# ── 时间工具 ─────────────────────────────────────────

def now_bj() -> datetime:
    """返回当前北京时间"""
    return datetime.utcnow() + timedelta(hours=TZ_HOUR_OFFSET)


def is_work_hour(dt: datetime = None) -> bool:
    """判断给定时间是否在工作时间段内"""
    if dt is None:
        dt = now_bj()
    t = dt.time()
    return (MORNING_START <= t < MORNING_END) or (AFTERNOON_START <= t < AFTERNOON_END)


def next_work_start(dt: datetime = None) -> datetime:
    """从 dt 开始，下一个工作段的起始时间"""
    if dt is None:
        dt = now_bj()
    t = dt.time()

    # 如果当前就在工作时间内，返回当前时间
    if is_work_hour(dt):
        return dt

    # 上午之前 → 今天 08:30
    if t < MORNING_START:
        return dt.replace(hour=8, minute=30, second=0, microsecond=0)

    # 午休时段 (12:00 ~ 14:00)
    if MORNING_END <= t < AFTERNOON_START:
        return dt.replace(hour=14, minute=0, second=0, microsecond=0)

    # 下午之后 → 明天 08:30
    tomorrow = dt + timedelta(days=1)
    return tomorrow.replace(hour=8, minute=30, second=0, microsecond=0)


# ── State 管理 ───────────────────────────────────────

def load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── 笑话抓取 ─────────────────────────────────────────

def fetch_joke() -> str:
    """从随机中文源抓取一条笑话/段子，失败自动换源"""
    sources = JOKE_SOURCES[:]
    random.shuffle(sources)

    for src in sources:
        try:
            req = Request(src["url"], headers=src["headers"])
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
            text = src["parser"](data)
            if text and len(text.strip()) > 2 and len(text) < 1000:
                return f"[{src['name']}]\n{text.strip()}"
        except Exception:
            continue

    return None


# ── 主逻辑 ───────────────────────────────────────────

def main():
    state = load_state()
    now = now_bj()
    today_str = now.strftime("%Y-%m-%d")

    # ── 初始化 or 跨天重置 ──
    last_date = state.get("joke_date")
    if last_date != today_str:
        # 新的一天：重置状态
        if is_work_hour(now):
            # 现在就在工作时间内 → 立即发送
            next_send = now
        else:
            # 不在工作时间 → 下一个工作段开始时发送
            next_send = next_work_start(now)

        save_state({
            "next_send": next_send.isoformat(),
            "last_send": state.get("last_send"),
            "joke_date": today_str,   # 标记今天已初始化
        })

        # 如果还没到工作时间，不输出，等下次 cron tick
        if not is_work_hour(now):
            return

    # ── 读取 next_send ──
    next_send_str = state.get("next_send") or state.get("next_send_time")
    if not next_send_str:
        return  # 没有计划

    try:
        next_send = datetime.fromisoformat(next_send_str)
    except (ValueError, TypeError):
        return

    # ── 判断是否该发送 ──
    if not is_work_hour(now):
        return  # 非工作时间，安静

    if now < next_send:
        return  # 还没到时间，安静

    # ═════════ 该发笑话了 ═════════
    joke = fetch_joke()
    if joke is None:
        # 所有源都挂了，15分钟后重试
        save_state({
            "next_send": (now + timedelta(minutes=15)).isoformat(),
            "last_send": state.get("last_send"),
            "joke_date": today_str,
        })
        return

    # ── 计算下一次发送时间 ──
    raw_interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
    next_send = now + timedelta(minutes=raw_interval)
    next_time_only = next_send.time()

    # 如果跨过午休 → 推到 14:00
    if now.time() < MORNING_END and next_time_only >= MORNING_END:
        next_send = now.replace(hour=14, minute=0, second=0, microsecond=0)
    # 如果跨过下班 → 如果是最后一轮能发出就压到最后时间，否则明天
    elif now.time() < AFTERNOON_END and next_time_only >= AFTERNOON_END:
        remaining = (AFTERNOON_END.hour * 60 + AFTERNOON_END.minute) - (now.hour * 60 + now.minute)
        if remaining >= MIN_INTERVAL:
            safe_interval = min(remaining, random.randint(MIN_INTERVAL, remaining))
            next_send = now + timedelta(minutes=safe_interval)
        else:
            next_send = now.replace(hour=8, minute=30, second=0, microsecond=0) + timedelta(days=1)

    # ═════════ 输出笑话（Hermes cron 会将其发到群） ═════════
    print(f"🤣 打工人的快乐源泉 🤣")
    print()
    print(joke)

    # ── 更新状态 ──
    save_state({
        "next_send": next_send.isoformat(),
        "last_send": now.isoformat(),
        "joke_date": today_str,
    })


if __name__ == "__main__":
    main()
