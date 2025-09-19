#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tg-auto-checkin: 多账号 + Bot 管理 + 个人号发送 + 定时（上海时区）
- 多账号：/adduser /code /pass /listusers /removeuser
- 任务：/addtask /listtasks /deltask /toggle /test
- 实时：/status（全部账号） /me <alias> /whois <target>
- CRON：5字段 crontab；时区 Asia/Shanghai
- 任务字段：target/cron/message/account/remark/enabled
依赖：telethon, apscheduler（自动安装，兼容 PEP 668）
数据：config.json / accounts.json / tasks.json
会话文件：user-<alias>.session（个人号），bot.session（机器人）
"""

import asyncio
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 终端编码保护
os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ---------------- 依赖安装（兼容 PEP 668） ----------------
def ensure(pkgs):
    for p in pkgs:
        try:
            __import__(p)
        except Exception:
            print(f"未检测到 {p}，正在安装……")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", p])
            except subprocess.CalledProcessError:
                print(f"常规安装 {p} 失败，尝试 --break-system-packages ……")
                subprocess.check_call([sys.executable, "-m", "pip", "install", p, "--break-system-packages"])

ensure(["telethon", "apscheduler"])

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import UserStatusOnline, UserStatusOffline
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo  # Python3.9+

# ---------------- 常量/文件 ----------------
CONFIG = Path("config.json")
ACCOUNTS = Path("accounts.json")
TASKS = Path("tasks.json")
BOT_SESSION = "bot"  # 机器人会话
SH_TZ = ZoneInfo("Asia/Shanghai")

# ---------------- 基础工具 ----------------
def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def prompt(label, default=None):
    tip = f"{label}"
    if default is not None:
        tip += f" [{default}]"
    tip += ": "
    sys.stdout.write(tip); sys.stdout.flush()
    line = sys.stdin.buffer.readline()
    val = (line or b"").decode("utf-8", errors="ignore").strip()
    if not val and default is not None:
        val = str(default).strip()
    if not val:
        print("不能为空，请重输。")
        return prompt(label, default)
    return val

def parse_cron(expr: str) -> CronTrigger:
    # 5 字段 crontab，调度器采用上海时区
    return CronTrigger.from_crontab(expr, timezone=SH_TZ)

def fmt_entity(ent):
    name = getattr(ent, "title", None) or \
           (" ".join([getattr(ent, "first_name", "") or "", getattr(ent, "last_name", "") or ""]).strip() or "(无名)")
    uname = f"@{getattr(ent, 'username', None)}" if getattr(ent, "username", None) else "(无)"
    eid = getattr(ent, "id", None)
    kind = ent.__class__.__name__
    return f"{name} {uname} | id={eid} | type={kind}"

async def resolve_entity(client: TelegramClient, t: str):
    t = str(t).strip()
    if t.lower() in ("me", "self"):  # 收藏夹
        return await client.get_entity("me")
    if t.startswith("@") or "t.me/" in t:
        return await client.get_entity(t)
    if t.startswith("-100") or (t.startswith("-") and t[1:].isdigit()):
        return await client.get_entity(int(t))
    if t.isdigit():
        target_id = int(t)
        async for dialog in client.iter_dialogs():
            ent = dialog.entity
            if getattr(ent, "id", None) == target_id:
                return ent
        raise ValueError(f"无法通过数字ID {t} 找到对象；请先与其建立会话，或改用 @用户名 / t.me 链接 / -100群ID。")
    return await client.get_entity(t)

# ---------------- 配置与状态 ----------------
def ensure_config():
    cfg = load_json(CONFIG, {})
    if not cfg.get("api_id"):
        cfg["api_id"] = int(prompt("请输入 api_id（my.telegram.org 申请）"))
    if not cfg.get("api_hash"):
        cfg["api_hash"] = prompt("请输入 api_hash")
    if not cfg.get("bot_token"):
        cfg["bot_token"] = prompt("请输入 管理Bot 的 bot_token")
    if not cfg.get("admin_ids"):
        admin = prompt("请输入管理员用户ID（数字，可多个，逗号分隔）")
        ids = []
        for x in admin.split(","):
            x = x.strip()
            if x.isdigit():
                ids.append(int(x))
        cfg["admin_ids"] = ids
    save_json(CONFIG, cfg)
    return cfg

def ensure_accounts():
    data = load_json(ACCOUNTS, {"users": {}})  # { alias: {phone, session_file} }
    save_json(ACCOUNTS, data)
    return data

def ensure_tasks():
    data = load_json(TASKS, {"tasks": [], "seq": 1})
    save_json(TASKS, data)
    return data

# 运行时客户端池：{alias: TelegramClient}
CLIENTS: dict[str, TelegramClient] = {}
PENDING: dict[int, dict] = {}  # 管理员对话中的登录流程状态 {admin_id: {"alias":..., "phone":...}}

# ---------------- 账号管理 ----------------
def session_file_for(alias: str) -> str:
    return f"user-{alias}.session"

async def get_or_start_client(api_id, api_hash, alias: str) -> TelegramClient:
    if alias in CLIENTS:
        return CLIENTS[alias]
    sess = session_file_for(alias)
    client = TelegramClient(sess, api_id, api_hash)
    await client.connect()
    CLIENTS[alias] = client
    return client

async def user_status(client: TelegramClient):
    me = await client.get_me()
    st = getattr(me, "status", None)
    online = None; last = None
    if isinstance(st, UserStatusOnline):
        online = True
    elif isinstance(st, UserStatusOffline):
        online = False; last = st.was_online
    return me, online, last

# ---------------- 任务发送 ----------------
async def send_with_user(api_id, api_hash, alias: str, target: str, text: str):
    client = await get_or_start_client(api_id, api_hash, alias)
    if not await client.is_user_authorized():
        raise RuntimeError(f"账号 {alias} 未登录，请先在 Bot 中完成 /adduser → /code（→ /pass）流程。")
    ent = await resolve_entity(client, target)
    await client.send_message(ent, text)

# ---------------- 主流程 ----------------
async def main():
    cfg = ensure_config()
    acc = ensure_accounts()
    tasks_state = ensure_tasks()

    # 机器人
    bot = TelegramClient(BOT_SESSION, cfg["api_id"], cfg["api_hash"])
    await bot.start(bot_token=cfg["bot_token"])

    # 调度器（上海时区）
    scheduler = AsyncIOScheduler(timezone=SH_TZ)
    scheduler.start()

    # 恢复任务
    def add_job_from_task(t):
        if not t.get("enabled", True):
            return
        trig = parse_cron(t["cron"])
        scheduler.add_job(
            send_with_user,
            trigger=trig,
            args=[cfg["api_id"], cfg["api_hash"], t["account"], t["target"], t["message"]],
            id=str(t["id"]),
            replace_existing=True,
            coalesce=True,
            misfire_grace_time=120,
        )

    for t in tasks_state["tasks"]:
        try:
            add_job_from_task(t)
        except Exception as e:
            print(f"任务 {t.get('id')} 恢复失败：{e}")

    # 权限
    ADMINS = set(cfg["admin_ids"])
    def admin_ok(event): return event.sender_id in ADMINS

    # 漂亮的帮助
    def help_card():
        return (
            "🧭 *签到机器人 · 管理菜单*\n"
            "—— *任务管理* ——\n"
            "`/addtask` 目标 `|` CRON `|` 文本 `|` 账号别名 `|` 备注\n"
            "`/listtasks`  列出任务\n"
            "`/deltask` ID 删除任务\n"
            "`/toggle` ID 启/停任务\n"
            "`/test` 目标 `|` 文本 `|` 账号别名  立即测试一次\n\n"
            "—— *账号管理* ——\n"
            "`/adduser` 别名 `|` 手机号(含国家码)\n"
            "`/code`   别名 `|` 验证码\n"
            "`/pass`   别名 `|` 二步验证密码   （如需要）\n"
            "`/listusers` 列出账号\n"
            "`/removeuser` 别名  移除账号\n\n"
            "—— *状态/查询* ——\n"
            "`/status`        查看所有账号状态\n"
            "`/me` 别名       查看某账号登录信息\n"
            "`/whois` 目标     解析目标信息\n\n"
            "*CRON 示例*\n"
            "`0 9 * * *`  每天 09:00（上海时区）\n"
            "`*/10 * * * *`  每 10 分钟\n"
            "_目标可用：@用户名 / t.me 链接 / -100群ID / 数字用户ID（需在会话列表） / me_\n"
        )


    @bot.on(events.NewMessage(pattern=r"^/(start|help)$"))
    async def _(e):
        if not admin_ok(e): return
        await e.respond(help_card(), parse_mode="md")

    # ---------- 账号管理 ----------
    @bot.on(events.NewMessage(pattern=r"^/adduser\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        try:
            body = e.pattern_match.group(1).strip()
            alias, phone = [x.strip() for x in body.split("|", 1)]
            if not alias or not phone:
                await e.reply("格式：`/adduser 别名 | 手机号(含国家码)`", parse_mode="md"); return
            if alias in load_json(ACCOUNTS, {"users":{}})["users"]:
                await e.reply("该别名已存在，如需重登请先 `/removeuser 别名`。", parse_mode="md"); return
            # 启动临时 client 发验证码
            client = await get_or_start_client(cfg["api_id"], cfg["api_hash"], alias)
            await client.send_code_request(phone)
            PENDING[e.sender_id] = {"alias": alias, "phone": phone}
            await e.reply(f"已向 {phone} 发送验证码。\n请发送：`/code {alias} | 12345`", parse_mode="md")
        except Exception as ex:
            await e.reply(f"❌ 发送验证码失败：{ex}")

    @bot.on(events.NewMessage(pattern=r"^/code\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        try:
            body = e.pattern_match.group(1).strip()
            alias, code = [x.strip() for x in body.split("|", 1)]
            pend = PENDING.get(e.sender_id)
            if not pend or pend.get("alias") != alias:
                await e.reply("请先 `/adduser 别名 | 手机号` 以发送验证码。", parse_mode="md"); return
            client = await get_or_start_client(cfg["api_id"], cfg["api_hash"], alias)
            try:
                await client.sign_in(phone=pend["phone"], code=code)
                # 保存到账户清单
                data = ensure_accounts()
                data["users"][alias] = {"phone": pend["phone"], "session_file": session_file_for(alias)}
                save_json(ACCOUNTS, data)
                PENDING.pop(e.sender_id, None)
                me, online, last = await user_status(client)
                await e.reply(f"✅ 登录成功 {alias}\n{fmt_entity(me)}")
            except SessionPasswordNeededError:
                await e.reply(f"需要二步验证密码，请发送：`/pass {alias} | 你的密码`", parse_mode="md")
        except Exception as ex:
            await e.reply(f"❌ 登录失败：{ex}")

    @bot.on(events.NewMessage(pattern=r"^/pass\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        try:
            alias, pwd = [x.strip() for x in e.pattern_match.group(1).split("|", 1)]
            client = await get_or_start_client(cfg["api_id"], cfg["api_hash"], alias)
            await client.sign_in(password=pwd)
            pend = PENDING.pop(e.sender_id, None)
            phone = pend["phone"] if pend and pend.get("alias")==alias else "(未知)"
            data = ensure_accounts()
            data["users"][alias] = {"phone": phone, "session_file": session_file_for(alias)}
            save_json(ACCOUNTS, data)
            me, online, last = await user_status(client)
            await e.reply(f"✅ 登录成功 {alias}\n{fmt_entity(me)}")
        except Exception as ex:
            await e.reply(f"❌ 二步验证失败：{ex}")

    @bot.on(events.NewMessage(pattern=r"^/listusers$"))
    async def _(e):
        if not admin_ok(e): return
        data = ensure_accounts()["users"]
        if not data:
            await e.reply("暂无已登录账号。"); return
        lines = []
        for alias, info in data.items():
            sess = Path(info["session_file"])
            mtime = datetime.fromtimestamp(sess.stat().st_mtime).astimezone(SH_TZ).strftime("%Y-%m-%d %H:%M:%S") if sess.exists() else "N/A"
            lines.append(f"- {alias}（{info.get('phone','') }） session:{sess.name} mtime:{mtime}")
        await e.reply("👥 账号列表：\n" + "\n".join(lines))

    @bot.on(events.NewMessage(pattern=r"^/removeuser\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        alias = e.pattern_match.group(1).strip()
        data = ensure_accounts()
        if alias not in data["users"]:
            await e.reply("未找到该别名。"); return
        # 停止并删除会话文件
        try:
            if alias in CLIENTS:
                await CLIENTS[alias].disconnect()
                CLIENTS.pop(alias, None)
        except Exception:
            pass
        try:
            Path(session_file_for(alias)).unlink(missing_ok=True)
        except Exception:
            pass
        data["users"].pop(alias, None); save_json(ACCOUNTS, data)
        await e.reply(f"✅ 已移除账号 {alias}")

    # ---------- 任务管理 ----------
    @bot.on(events.NewMessage(pattern=r"^/addtask\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        try:
            body = e.pattern_match.group(1).strip()
            # 目标 | CRON | 文本 | 账号别名 | 备注
            parts = [x.strip() for x in body.split("|")]
            if len(parts) < 4:
                await e.reply("格式：`/addtask 目标 | CRON | 文本 | 账号别名 | 备注(可空)`", parse_mode="md"); return
            target, cron_expr, text, alias = parts[0], parts[1], parts[2], parts[3]
            remark = parts[4] if len(parts) >= 5 else ""
            # 验证：cron & 账号存在
            _ = parse_cron(cron_expr)
            if alias not in ensure_accounts()["users"]:
                await e.reply("账号别名不存在，请先 /listusers 查看或 /adduser 登陆。"); return

            tid = tasks_state["seq"]; tasks_state["seq"] += 1
            task = {"id": tid, "target": target, "cron": cron_expr, "message": text,
                    "account": alias, "remark": remark, "enabled": True}
            tasks_state["tasks"].append(task); save_json(TASKS, tasks_state)
            add_job_from_task(task)
            await e.reply(f"✅ 已添加任务 #{tid}\n[{alias}] {cron_expr} -> {target}\n备注：{remark or '（无）'}")
        except Exception as ex:
            await e.reply(f"❌ 添加失败：{ex}")

    @bot.on(events.NewMessage(pattern=r"^/listtasks$"))
    async def _(e):
        if not admin_ok(e): return
        if not tasks_state["tasks"]:
            await e.reply("暂无任务。"); return
        lines = []
        for t in tasks_state["tasks"]:
            lines.append(f"#{t['id']} [{'ON' if t.get('enabled', True) else 'OFF'}] "
                         f"[{t['account']}] {t['cron']} -> {t['target']} | {t['message'][:40]} "
                         f"｜备注:{(t.get('remark') or '无')}")
        await e.reply("📋 任务列表：\n" + "\n".join(lines))

    @bot.on(events.NewMessage(pattern=r"^/deltask\s+(\d+)"))
    async def _(e):
        if not admin_ok(e): return
        tid = int(e.pattern_match.group(1))
        before = len(tasks_state["tasks"])
        tasks_state["tasks"] = [x for x in tasks_state["tasks"] if x["id"] != tid]
        save_json(TASKS, tasks_state)
        try:
            scheduler.remove_job(str(tid))
        except Exception:
            pass
        await e.reply("✅ 已删除" if len(tasks_state["tasks"]) < before else "未找到该ID")

    @bot.on(events.NewMessage(pattern=r"^/toggle\s+(\d+)"))
    async def _(e):
        if not admin_ok(e): return
        tid = int(e.pattern_match.group(1))
        t = next((x for x in tasks_state["tasks"] if x["id"] == tid), None)
        if not t:
            await e.reply("未找到该ID"); return
        t["enabled"] = not t.get("enabled", True)
        save_json(TASKS, tasks_state)
        try:
            if t["enabled"]:
                add_job_from_task(t)
            else:
                scheduler.remove_job(str(tid))
        except Exception:
            pass
        await e.reply(f"任务 #{tid} 已切换为 {'ON' if t['enabled'] else 'OFF'}")

    @bot.on(events.NewMessage(pattern=r"^/test\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        try:
            body = e.pattern_match.group(1).strip()
            # 目标 | 文本 | 账号别名
            parts = [x.strip() for x in body.split("|")]
            if len(parts) != 3:
                await e.reply("格式：`/test 目标 | 文本 | 账号别名`", parse_mode="md"); return
            target, text, alias = parts
            await send_with_user(cfg["api_id"], cfg["api_hash"], alias, target, text)
            await e.reply(f"✅ 已尝试发送（{alias}）")
        except Exception as ex:
            await e.reply(f"❌ 发送失败：{ex}")

    # ---------- 状态/查询 ----------
    @bot.on(events.NewMessage(pattern=r"^/status$"))
    async def _(e):
        if not admin_ok(e): return
        data = ensure_accounts()["users"]
        if not data:
            await e.reply("暂无账号。先用 `/adduser 别名 | 手机号` 登录。", parse_mode="md"); return
        lines = ["🟢 账号状态（上海时区）"]
        for alias in data.keys():
            client = await get_or_start_client(cfg["api_id"], cfg["api_hash"], alias)
            if not await client.is_user_authorized():
                lines.append(f"- {alias}: 未登录")
                continue
            me, online, last = await user_status(client)
            last_txt = last.astimezone(SH_TZ).strftime("%Y-%m-%d %H:%M:%S") if last else "未知"
            lines.append(f"- {alias}: {'在线' if online else '离线'}  最近在线: {last_txt}  {fmt_entity(me)}")
        await e.reply("\n".join(lines))

    @bot.on(events.NewMessage(pattern=r"^/me\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        alias = e.pattern_match.group(1).strip()
        try:
            client = await get_or_start_client(cfg["api_id"], cfg["api_hash"], alias)
            if not await client.is_user_authorized():
                await e.reply("该账号未登录。"); return
            me, online, last = await user_status(client)
            await e.reply("👤 账号信息：\n" + fmt_entity(me))
        except Exception as ex:
            await e.reply(f"❌ 查询失败：{ex}")

    @bot.on(events.NewMessage(pattern=r"^/whois\s+(.+)"))
    async def _(e):
        if not admin_ok(e): return
        target = e.pattern_match.group(1).strip()
        # 用第一个已登录账号做解析（或提示）
        usable = [a for a in ensure_accounts()["users"].keys()]
        if not usable:
            await e.reply("请至少登录一个账号后使用 /whois。"); return
        client = await get_or_start_client(cfg["api_id"], cfg["api_hash"], usable[0])
        if not await client.is_user_authorized():
            await e.reply("可用账号未登录。"); return
        try:
            ent = await resolve_entity(client, target)
            await e.reply("🔎 解析成功：\n" + fmt_entity(ent))
        except Exception as ex:
            await e.reply(f"❌ 解析失败：{ex}")

    print("✅ 管理Bot已启动（上海时区）。用管理员账号给Bot发 /help 查看菜单。")

    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已退出。")
