import os
import sys
import json
import time
import signal
import random
import asyncio
import hashlib
import threading
import aiohttp

from urllib.parse import parse_qs, unquote

from utils.banner import show_banner

MY_PROJECT = "Farm Buddies Miniapp"
BASE_URL = "https://farm-buddies-api.htmmo2025.workers.dev/api"
REF_CODE = "3D024023"

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://farm-buddies.pages.dev",
    "referer": "https://farm-buddies.pages.dev/",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
}


_print_lock = threading.Lock()
_countdown_line = ""


def _sync_print(line):
    global _countdown_line
    with _print_lock:
        if _countdown_line:
            print(f"\r{' ' * (len(_countdown_line) + 4)}\r", end="", flush=True)
        print(line, flush=True)
        if _countdown_line:
            print(f"\r{YELLOW}{BOLD}{_countdown_line}{RESET}", end="", flush=True)


def log_green(msg):
    _sync_print(f"{GREEN}{BOLD}{msg}{RESET}")


def log_yellow(msg):
    _sync_print(f"{YELLOW}{BOLD}{msg}{RESET}")


def log_red(msg):
    _sync_print(f"{RED}{BOLD}{msg}{RESET}")


def signal_handler(sig, frame):
    print(flush=True)
    log_red("Script stopped by user")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def clean_text(value, fallback):
    if value is None:
        return str(fallback)
    text = str(value)
    for symbol in "[]|#!@$%^&*()-+=~`,:;'\"<>?/\\":
        text = text.replace(symbol, " ")
    text = "".join(char for char in text if ord(char) < 128)
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def format_amount(value):
    try:
        number = float(value)
    except Exception:
        return "0"
    if number != number or number == 0:
        return "0"
    text = f"{number:.8f}" if abs(number) < 1 else f"{number:.4f}"
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def display_name(account):
    for value in (account.get("username"), account.get("firstName")):
        name = clean_text(value, "")
        if name:
            return name
    return "Unknown"


def plural(count):
    return "task" if int(count) == 1 else "tasks"


def load_config():
    defaults = {"settings": {"sleep_seconds": 3600}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            loaded = json.load(handle)
    except Exception:
        return defaults
    settings = loaded.get("settings")
    if not isinstance(settings, dict):
        return defaults
    merged = dict(defaults["settings"])
    merged.update(settings)
    return {"settings": merged}


def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red(f"File {clean_text(filename, 'data.txt')} was not found")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    if required and not lines:
        log_red("File data.txt is empty and holds no initData string")
        sys.exit(1)
    return lines


def parse_init_data(line):
    value = line.strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0]
        value = value.split("&tgWebAppPlatform")[0]
        value = unquote(value)
    fields = parse_qs(value, keep_blank_values=True)
    raw_user = (fields.get("user") or [""])[0]
    if not raw_user:
        return None
    try:
        profile = json.loads(raw_user)
    except Exception:
        try:
            profile = json.loads(unquote(raw_user))
        except Exception:
            return None
    if not isinstance(profile, dict) or not profile.get("id"):
        return None
    return {
        "initData": value,
        "id": str(profile.get("id")),
        "username": str(profile.get("username") or ""),
        "firstName": str(profile.get("first_name") or ""),
        "lastName": str(profile.get("last_name") or ""),
        "startParam": str((fields.get("start_param") or [""])[0] or ""),
        "usdt": 0.0,
        "coins": 0.0,
        "level": 0,
        "rank": 0,
        "token": "",
        "fp": {},
    }


def referrer_code_of(account):
    value = clean_text(account.get("startParam") or REF_CODE, "")
    return value.replace(" ", "") or str(REF_CODE)


def load_device_cache():
    if not os.path.exists("device.json"):
        return {}
    try:
        with open("device.json") as handle:
            cached = json.load(handle)
    except Exception:
        return {}
    return cached if isinstance(cached, dict) else {}


def save_device_cache(cache):
    try:
        with open("device.json.tmp", "w") as handle:
            json.dump(cache, handle, indent=2)
        os.replace("device.json.tmp", "device.json")
    except Exception:
        pass


def device_profile(telegram_id):
    cache = load_device_cache()
    key = str(telegram_id)
    cached = cache.get(key)
    if isinstance(cached, dict) and cached.get("deviceId"):
        return cached, True
    seed = int("".join(char for char in key if char.isdigit()) or 0)
    engine = random.Random(seed)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    device_id = "web-" + "".join(engine.choice(alphabet) for _ in range(20))
    profile = {
        "deviceId": device_id,
        "width": engine.choice([360, 384, 392, 412, 432]),
        "height": engine.choice([640, 740, 780, 800, 915]),
        "dpr": engine.choice([1, 1.5, 2, 2.625, 3]),
        "lang": "en-US",
        "timezone": "Asia/Jakarta",
        "platform": "Linux armv8l",
        "cores": engine.choice([4, 6, 8]),
        "tgPlatform": "android",
    }
    cache[key] = profile
    save_device_cache(cache)
    return profile, False


def fingerprint_of(profile):
    raw = "|".join([
        HEADERS_BASE["user-agent"],
        profile["lang"],
        profile["timezone"],
        f"{profile['width']}x{profile['height']}x24",
        profile["platform"],
        str(profile["cores"]),
        profile["tgPlatform"],
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def error_code(payload):
    if isinstance(payload, dict):
        code = payload.get("code")
        if code:
            return str(code)
    return ""


def error_message(payload):
    if isinstance(payload, dict):
        for key in ("message", "error"):
            message = payload.get(key)
            if message:
                return str(message)
    return ""


def busy_error(status, payload):
    if status in (429, 500, 502, 503, 504):
        return True
    message = error_message(payload).lower()
    return "busy" in message or "timeout" in message or "too many" in message


def number_float(mapping, key, fallback=0.0):
    try:
        value = mapping.get(key)
    except Exception:
        return fallback
    if value is None or value == "":
        return fallback
    try:
        return float(value)
    except Exception:
        return fallback


def number_of(mapping, key, fallback=0):
    return int(number_float(mapping, key, fallback))


def text_of(mapping, key, fallback):
    try:
        value = mapping.get(key)
    except Exception:
        return str(fallback)
    if value is None:
        return str(fallback)
    return str(value)


def format_duration(seconds):
    total = int(max(seconds, 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


PENDING_GAPS = {}


async def countdown(seconds, label):
    global _countdown_line
    left = int(max(seconds, 0))
    if left < 1:
        return
    text = clean_text(label, "Next cycle")
    try:
        while left > 0:
            line = f"{text} {format_duration(left)}"
            with _print_lock:
                _countdown_line = line
                print(f"\r{YELLOW}{BOLD}{line}{RESET}", end="", flush=True)
            await asyncio.sleep(1)
            left -= 1
    finally:
        with _print_lock:
            _countdown_line = ""
            print(f"\r{' ' * (len(text) + 15)}\r", end="", flush=True)




async def api_call(session, account, path, body=None, proxy=None, method="POST"):
    url = f"{BASE_URL}{path}"
    headers = dict(HEADERS_BASE)
    headers["x-farm-fp"] = account["fp"]["hash"]
    if account.get("token"):
        headers["authorization"] = f"Bearer {account['token']}"
    last_status = 0
    last_payload = None
    for attempt in range(1, 4):
        pause = 4 * attempt
        try:
            request = session.request(
                method,
                url,
                headers=headers,
                json=body,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=40),
            )
            async with request as response:
                last_status = response.status
                text = await response.text()
                try:
                    last_payload = json.loads(text)
                except Exception:
                    last_payload = None
                if response.status < 400 or not busy_error(response.status, last_payload):
                    return last_status, last_payload
                if response.status == 429:
                    pause = 8 * attempt
        except Exception:
            last_status = 0
            last_payload = None
        if attempt < 3:
            await asyncio.sleep(pause)
    return last_status, last_payload


def store_profile(account, payload):
    profile = payload.get("profile") if isinstance(payload, dict) else None
    if not isinstance(profile, dict):
        return {}
    account["usdt"] = number_float(profile, "usdt")
    account["coins"] = number_float(profile, "coins")
    account["level"] = number_of(profile, "level")
    account["adsToday"] = number_of(profile, "adsToday")
    account["todayEarned"] = number_float(profile, "todayEarned")
    return profile


async def read_state(session, account, proxy):
    status, payload = await api_call(session, account, "/user/me", None, proxy, "GET")
    if status == 200 and isinstance(payload, dict) and payload.get("ok"):
        return store_profile(account, payload)
    return {}


async def run_auth(session, account, proxy):
    profile, _ = device_profile(account["id"])
    account["fp"] = {"raw": profile, "hash": fingerprint_of(profile)}
    body = {
        "initData": account["initData"],
        "deviceId": profile["deviceId"],
        "fingerprint": account["fp"]["hash"],
        "referralCode": referrer_code_of(account),
    }
    status, payload = await api_call(session, account, "/auth/telegram", body, proxy)
    if status == 200 and isinstance(payload, dict) and payload.get("ok") and payload.get("token"):
        account["token"] = str(payload["token"])
        return store_profile(account, payload)
    status, payload = await api_call(
        session, account, "/auth/telegram",
        {"initData": account["initData"], "deviceId": profile["deviceId"],
         "fingerprint": account["fp"]["hash"]}, proxy
    )
    if status == 200 and isinstance(payload, dict) and payload.get("ok") and payload.get("token"):
        account["token"] = str(payload["token"])
        return store_profile(account, payload)
    return {}


async def run_terms(session, account, proxy):
    status, payload = await api_call(session, account, "/user/accept-terms", {}, proxy)
    if status == 200 and isinstance(payload, dict) and payload.get("ok"):
        return True
    return False


async def run_ad_task(session, account, task, proxy, counter, lock):
    task_id = number_of(task, "id")
    label = shorten(task.get("title"), "ad task", 22)
    async with lock:
        if counter["left"] <= 0:
            log_yellow("The daily ad cap for this account is already used up")
            return 0, 0.0, False
    slot = await open_slot(session, account, task_id, proxy)
    if slot is None:
        return 0, 0.0, True
    status, session_payload = await api_call(
        session, account, f"/ads/task/{task_id}/session", {"slotIndex": slot}, proxy
    )
    if status != 200 or not isinstance(session_payload, dict) or not session_payload.get("ok"):
        code = error_code(session_payload)
        if code in ("SLOT_COOLING_DOWN", "TASK_COOLING_DOWN"):
            remember_ready(account, cooldown_secs(session_payload))
            return 0, 0.0, True
        return 0, 0.0, False
    session_id = text_of(session_payload, "sessionId", "")
    provider = text_of(session_payload, "provider", "adsgram")
    wait_secs = number_of(session_payload, "minWatchSec", 1)
    await asyncio.sleep(wait_secs + 1)
    status, done = await api_call(
        session, account, f"/ads/task/{task_id}/complete",
        {"sessionId": session_id, "slotIndex": slot, "provider": provider,
         "clicked": False}, proxy
    )
    if status != 200 or not isinstance(done, dict) or not done.get("ok"):
        code = error_code(done)
        if code in ("SLOT_COOLING_DOWN", "TASK_COOLING_DOWN"):
            remember_ready(account, cooldown_secs(done))
            return 0, 0.0, True
        return 0, 0.0, False
    reward = number_float(done, "reward")
    remember_ready(account, cooldown_secs(done))
    async with lock:
        counter["left"] -= 1
    store_profile(account, done)
    used = number_of(done, "usedToday")
    if used <= 0:
        used = slot
    log_green(
        f"{clean_text(label, 'ad task')} slot {clean_text(used, 0)} paid "
        f"{clean_text(format_amount(reward), 0)} coins to this account"
    )
    return 1, reward, False


async def open_slot(session, account, task_id, proxy):
    status, payload = await api_call(
        session, account, f"/tasks/{task_id}/slots", None, proxy, "GET"
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        return None
    slots = payload.get("slots")
    if not isinstance(slots, list):
        return None
    for entry in slots:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == "ready":
            return number_of(entry, "index")
    return None


def cooldown_secs(payload):
    if not isinstance(payload, dict):
        return -1
    for key in ("availableAt", "readyAt", "nextAdAt", "nextClaimAt"):
        value = number_of(payload, key)
        if value <= 0:
            continue
        if value > 100000000000:
            value = int(value / 1000)
        gap = value - int(time.time())
        if gap > 0:
            return gap
    return -1


def remember_ready(account, secs):
    if secs <= 0:
        return
    ready_at = int(time.time()) + int(secs)
    current = number_of(account, "slot_ready_at", 0)
    if current <= 0 or ready_at < current:
        account["slot_ready_at"] = ready_at


def gap_hint(account):
    ready_at = number_of(account, "slot_ready_at", 0)
    if ready_at <= 0:
        return -1
    gap = ready_at - int(time.time())
    if gap <= 0:
        return 0
    return gap


async def soonest_gap(session, account, task_ids, proxy):
    now_ms = int(time.time() * 1000)
    soonest = 0
    for task_id in task_ids:
        status, payload = await api_call(
            session, account, f"/tasks/{task_id}/slots", None, proxy, "GET"
        )
        if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
            continue
        slots = payload.get("slots")
        if not isinstance(slots, list):
            continue
        for entry in slots:
            if not isinstance(entry, dict) or entry.get("status") != "cooling":
                continue
            available = number_of(entry, "availableAt")
            if available <= 0:
                continue
            if soonest == 0 or available < soonest:
                soonest = available
    if soonest == 0:
        return -1
    gap_ms = soonest - now_ms
    if gap_ms <= 0:
        return 0
    return int(gap_ms / 1000) + 1


async def pending_gap(session, account, task_ids, proxy):
    tasks = await read_tasks(session, account, proxy)
    now_ms = int(time.time() * 1000)
    soonest = 0
    for entry in tasks:
        if number_of(entry, "id") not in task_ids:
            continue
        target = number_float(entry, "nextClaimAt")
        if target <= now_ms:
            continue
        if soonest == 0 or target < soonest:
            soonest = target
    if soonest == 0:
        return -1
    return int((soonest - now_ms) / 1000) + 1


async def account_gap(session, account, proxy):
    tasks = await read_tasks(session, account, proxy)
    ids = [number_of(entry, "id") for entry in tasks if number_of(entry, "id") > 0]
    if not ids:
        return -1
    gap = await soonest_gap(session, account, ids, proxy)
    if gap < 0:
        gap = await pending_gap(session, account, ids, proxy)
    return gap


async def run_bonus_reward(session, account, task, proxy):
    task_id = number_of(task, "id")
    label = shorten(task.get("title"), "bonus task", 22)
    status, payload = await api_call(session, account, f"/ads/task/{task_id}/reward", {}, proxy)
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        code = error_code(payload)
        if code in ("SLOT_COOLING_DOWN", "TASK_COOLING_DOWN"):
            remember_ready(account, cooldown_secs(payload))
            return 0.0, True
        return 0.0, False
    if payload.get("already"):
        log_yellow(f"{clean_text(label, 'bonus task')} was already claimed for this account")
        return 0.0, False
    reward = number_float(payload, "reward")
    remember_ready(account, cooldown_secs(payload))
    fresh = await read_state(session, account, proxy)
    after = number_float(fresh, "usdt", account["usdt"])
    account["usdt"] = after
    used = number_of(payload, "usedToday")
    total = number_of(payload, "total")
    log_green(
        f"{clean_text(label, 'bonus task')} paid {clean_text(format_amount(reward), 0)} coins, "
        f"slot {clean_text(used, 0)} of {clean_text(total, 0)} today"
    )
    return reward, False


async def read_tasks(session, account, proxy):
    status, payload = await api_call(session, account, "/tasks", None, proxy, "GET")
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list):
        return []
    return [entry for entry in tasks if isinstance(entry, dict)]


def task_state(tasks, task_id):
    for entry in tasks:
        if number_of(entry, "id") == task_id:
            return entry
    return {}


async def farm_state(session, account, proxy):
    status, payload = await api_call(session, account, "/farm", None, proxy, "GET")
    state = payload.get("farm") if isinstance(payload, dict) else None
    return state if isinstance(state, dict) else {}


async def run_farm_ad(session, account, ref, proxy):
    status, payload = await api_call(session, account, "/ads/farm/session", {"ref": ref}, proxy)
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        return False
    session_id = text_of(payload, "sessionId", "")
    provider = text_of(payload, "provider", "adsgram")
    wait_secs = number_of(payload, "minWatchSec", 1)
    await asyncio.sleep(wait_secs + 1)
    status, done = await api_call(
        session, account, "/ads/farm/complete",
        {"sessionId": session_id, "ref": ref, "provider": provider, "clicked": False}, proxy
    )
    if status == 200 and isinstance(done, dict) and done.get("ok"):
        store_profile(account, done)
        return True
    return False


async def run_link_task(session, account, task, proxy):
    task_id = number_of(task, "id")
    label = shorten(task.get("title"), "link task", 22)
    tasks = await read_tasks(session, account, proxy)
    entry = task_state(tasks, task_id)
    if clean_text(entry.get("state"), "").lower() in ("done", "claimed", "completed"):
        return "done", 0.0
    status, payload = await api_call(
        session, account, f"/tasks/{task_id}/start", {}, proxy
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        code = error_code(payload)
        if code in ("TASK_ALREADY_CLAIMED", "TASK_DONE"):
            return "done", 0.0
        if code in ("NOT_JOINED", "JOIN_REQUIRED", "CHANNEL_REQUIRED"):
            return "join", 0.0
        if code in ("TASK_COOLING_DOWN", "SMARLINK_PENDING", "SLOT_COOLING_DOWN"):
            remember_ready(account, cooldown_secs(payload))
            return "cooling", 0.0
        return "failed", 0.0
    dwell = number_of(payload, "dwellSec", 8)
    verify = number_of(payload, "verifySec", 5)
    await asyncio.sleep(max(dwell, verify) + 1)
    claim = {}
    for attempt in range(4):
        status, claim = await api_call(
            session, account, f"/tasks/{task_id}/claim", {}, proxy
        )
        if status == 200 and isinstance(claim, dict) and claim.get("ok"):
            reward = number_float(claim, "reward")
            store_profile(account, claim)
            log_green(
                f"Task {clean_text(label, 'link task')} paid "
                f"{clean_text(format_amount(reward), 0)} coins on watch 1 for this account"
            )
            return "paid", reward
        if error_code(claim) == "SMARLINK_PENDING":
            await asyncio.sleep(6)
            continue
        break
    code = error_code(claim)
    if code in ("NOT_JOINED", "JOIN_REQUIRED", "CHANNEL_REQUIRED"):
        return "join", 0.0
    if code in ("TASK_ALREADY_CLAIMED", "TASK_DONE"):
        return "done", 0.0
    if code in ("TASK_COOLING_DOWN", "SMARLINK_PENDING", "SLOT_COOLING_DOWN"):
        remember_ready(account, cooldown_secs(claim))
        return "cooling", 0.0
    return "failed", 0.0


async def handle_task(session, account, task, proxy, counter, lock):
    kind = clean_text(task.get("kind"), "task").lower()
    if kind == "ad":
        if number_of(task, "adSlots") <= 0:
            return {}
        if task.get("adsgramTask"):
            gained, cooling = await run_bonus_reward(session, account, task, proxy)
            if gained > 0:
                async with lock:
                    counter["left"] -= 1
                return {"result": "paid", "reward": gained, "slots": 1}
            if cooling:
                return {"result": "cooling"}
            return {}
        slots_paid, gained, pending = await run_ad_task(
            session, account, task, proxy, counter, lock
        )
        if pending:
            return {"result": "pending", "task": task, "reward": gained, "slots": slots_paid}
        if slots_paid <= 0:
            return {}
        return {"result": "paid", "reward": gained, "slots": slots_paid}
    result, reward = await run_link_task(session, account, task, proxy)
    if result == "paid":
        return {"result": "paid", "reward": reward, "slots": 1}
    return {"result": result, "reward": 0.0, "slots": 0}


async def run_tasks(session, account, bootstrap, proxy):
    tasks = bootstrap.get("tasks") if isinstance(bootstrap, dict) else None
    if not isinstance(tasks, list) or not tasks:
        log_yellow("The task list was not returned by the server")
        return 0.0
    ads = bootstrap.get("ads") if isinstance(bootstrap, dict) else None
    cap = ads.get("cap") if isinstance(ads, dict) else None
    cap_left = number_of(cap, "remaining") if isinstance(cap, dict) else 0
    if cap_left <= 0:
        cap_left = 200
    counter = {"left": cap_left}
    lock = asyncio.Lock()
    open_tasks = []
    done = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        if clean_text(task.get("state"), "open").lower() in ("claimed", "completed"):
            done += 1
            continue
        open_tasks.append(task)
    if open_tasks:
        log_yellow(
            f"{clean_text(len(open_tasks), 0)} {clean_text(plural(len(open_tasks)), 'tasks')} "
            "are worked side by side on this account"
        )
    earned = 0.0
    paid = 0
    joins = 0
    cooling = 0
    failed = 0
    cooling_ids = set()
    pending = list(open_tasks)
    rounds = 0
    stall = 0
    idle = 0
    while pending and counter["left"] > 0 and rounds < 400:
        rounds += 1
        results = list(
            await asyncio.gather(
                *[
                    handle_task(session, account, task, proxy, counter, lock)
                    for task in pending
                ]
            )
        )
        again = []
        moved = 0
        for task, item in zip(pending, results):
            if not item:
                continue
            earned += item.get("reward", 0.0) or 0.0
            result = item.get("result")
            if result == "paid":
                paid += item.get("slots", 1)
                moved += 1
            elif result == "pending":
                again.append(task)
            elif result == "cooling":
                again.append(task)
                task_id = number_of(task, "id")
                if task_id not in cooling_ids:
                    cooling_ids.add(task_id)
                    cooling += 1
            elif result == "join":
                joins += 1
            elif result == "done":
                done += 1
            elif result == "failed":
                failed += 1
        pending = again
        if not pending:
            break
        if not moved:
            idle += 1
            ids = [number_of(item, "id") for item in pending]
            gap = await soonest_gap(session, account, ids, proxy)
            if gap < 0:
                gap = await pending_gap(session, account, ids, proxy)
            hint = gap_hint(account)
            if hint >= 0 and (gap <= 0 or hint < gap):
                gap = hint
            if gap > 0:
                account["slot_gap"] = gap
            if gap < 0:
                break
            if gap == 0:
                stall += 1
                if stall >= 3:
                    break
                await asyncio.sleep(2)
                continue
            stall = 0
            if idle > 6 or gap > 420:
                log_yellow(
                    "The rest of the slots open later and are left to the next cycle"
                )
                break
            await countdown(gap + 1, "Reward slots are still cooling down, ready in")
        else:
            idle = 0
    if paid:
        log_green(f"{clean_text(paid, 0)} reward slots were paid on this account")
    if joins:
        log_yellow(f"{clean_text(joins, 0)} {clean_text(plural(joins), 'tasks')} skipped because a channel join is required")
    if done:
        log_yellow(f"{clean_text(done, 0)} {clean_text(plural(done), 'tasks')} were already claimed on this account")
    if cooling:
        log_yellow(
            f"{clean_text(cooling, 0)} {clean_text(plural(cooling), 'tasks')} needed "
            "more cooldown time on this account"
        )
    if failed:
        log_yellow(f"{clean_text(failed, 0)} {clean_text(plural(failed), 'tasks')} refused by the server on this run")
    return earned


async def run_harvest_ad(session, account, idx, proxy):
    status, payload = await api_call(
        session, account, "/ads/harvest/session", {"idx": idx}, proxy
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        status, fallback = await api_call(
            session, account, "/farm/harvest", {"idx": idx}, proxy
        )
        if status == 200 and isinstance(fallback, dict) and fallback.get("ok"):
            store_profile(account, fallback)
            return number_float(fallback, "reward")
        return 0.0
    session_id = text_of(payload, "sessionId", "")
    provider = text_of(payload, "provider", "adsgram")
    wait_secs = number_of(payload, "minWatchSec", 1)
    await asyncio.sleep(wait_secs + 1)
    status, done = await api_call(
        session, account, "/ads/harvest/complete",
        {"sessionId": session_id, "provider": provider, "clicked": False}, proxy
    )
    if status == 200 and isinstance(done, dict) and done.get("ok"):
        reward = number_float(done, "reward")
        store_profile(account, done)
        return reward
    return 0.0


async def run_farm(session, account, bootstrap, proxy):
    farm = await farm_state(session, account, proxy)
    if not farm:
        farm = bootstrap.get("farm") if isinstance(bootstrap, dict) else None
    if not isinstance(farm, dict) or not farm:
        log_yellow("The farm state was not returned by the server")
        return 0.0
    earned = 0.0
    planted = 0
    watered = 0
    refills = 0
    for round_index in range(4):
        crops = [entry for entry in (farm.get("crops") or []) if isinstance(entry, dict)]
        plots = [
            plot for plot in (farm.get("plots") or [])
            if isinstance(plot, dict) and not plot.get("locked")
        ]
        limit = number_of(farm, "maxSameCrop", 1)
        if limit <= 0:
            limit = 1
        seeds = {}
        for plot in plots:
            crop_id = clean_text(plot.get("crop"), "")
            if crop_id:
                seeds[crop_id] = seeds.get(crop_id, 0) + 1
        moved = False
        for plot in plots:
            idx = number_of(plot, "idx")
            if plot.get("state") == "ready":
                payout = await run_harvest_ad(session, account, idx, proxy)
                if payout > 0:
                    earned += payout
                    moved = True
                    log_green(
                        f"Plot {clean_text(idx + 1, 0)} harvested "
                        f"{clean_text(format_amount(payout), 0)} coins on this account"
                    )
                continue
            if plot.get("state") != "empty":
                continue
            crop = ""
            for entry in crops:
                if entry.get("locked"):
                    continue
                if number_of(entry, "leftToday") <= 0:
                    continue
                crop_id = clean_text(entry.get("id"), "")
                if seeds.get(crop_id, 0) >= limit:
                    continue
                crop = crop_id
                break
            if not crop:
                break
            status, payload = await api_call(
                session, account, "/farm/plant", {"idx": idx, "crop": crop}, proxy
            )
            if status == 200 and isinstance(payload, dict) and payload.get("ok"):
                planted += 1
                seeds[crop] = seeds.get(crop, 0) + 1
                moved = True
                log_green(
                    f"Plot {clean_text(idx + 1, 0)} was seeded with "
                    f"{clean_text(crop, 'crop')} on this account"
                )
        fresh = await farm_state(session, account, proxy)
        if fresh:
            farm = fresh
            plots = [
                plot for plot in (farm.get("plots") or [])
                if isinstance(plot, dict) and not plot.get("locked")
            ]
        water_left = number_of(farm, "water")
        water_cost = number_of(farm, "waterCost", 1)
        if water_cost <= 0:
            water_cost = 1
        for plot in plots:
            if plot.get("watered") or plot.get("state") != "growing":
                continue
            if water_left < water_cost:
                if refills < 2 and await run_farm_ad(session, account, "water", proxy):
                    refills += 1
                    fresh = await farm_state(session, account, proxy)
                    if fresh:
                        farm = fresh
                    water_left = number_of(farm, "water")
                    log_green("The water can was refilled with a reward ad on this account")
                else:
                    break
            status, payload = await api_call(
                session, account, "/farm/water", {"idx": number_of(plot, "idx")}, proxy
            )
            if status == 200 and isinstance(payload, dict) and payload.get("ok"):
                watered += 1
                water_left -= water_cost
                moved = True
                log_green(
                    f"Plot {clean_text(number_of(plot, 'idx') + 1, 0)} watered "
                    "for a faster harvest"
                )
        status, payload = await api_call(
            session, account, "/farm/harvest", {"idx": None}, proxy
        )
        if status == 200 and isinstance(payload, dict) and payload.get("ok"):
            reward = number_float(payload, "reward")
            earned += max(0.0, reward)
            moved = True
            log_green(
                f"The ready crops were collected for "
                f"{clean_text(format_amount(reward), 0)} coins on this account"
            )
        fresh = await farm_state(session, account, proxy)
        if fresh:
            farm = fresh
        plots = [
            plot for plot in (farm.get("plots") or [])
            if isinstance(plot, dict) and not plot.get("locked")
        ]
        ready = [plot for plot in plots if plot.get("state") == "ready"]
        empty = [plot for plot in plots if plot.get("state") == "empty"]
        if not ready and not empty and not moved:
            break
    if planted:
        log_green(f"{clean_text(planted, 0)} crop plots were seeded on this account")
    if watered:
        log_green(f"{clean_text(watered, 0)} crop plots were watered on this account")
    if refills:
        log_green(f"The water can was filled {clean_text(refills, 0)} times on this account")
    return earned


async def run_streak(session, account, proxy):
    status, payload = await api_call(
        session, account, "/user/streak/bio-check", None, proxy, "GET"
    )
    if status == 200 and isinstance(payload, dict) and not payload.get("verified"):
        log_yellow("The streak needs the referral link inside the Telegram bio first")
        return 0.0
    before = account["usdt"]
    status, payload = await api_call(session, account, "/user/streak/claim", {}, proxy)
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        code = error_code(payload)
        if code == "STREAK_BIO_REQUIRED":
            log_yellow("The streak needs the referral link inside the Telegram bio first")
        elif code == "STREAK_ALREADY_CLAIMED":
            log_yellow("The daily streak was already claimed for this account")
        return 0.0
    fresh = await read_state(session, account, proxy)
    after = number_float(fresh, "usdt", account["usdt"])
    gain = round(after - before, 8)
    account["usdt"] = after
    if gain > 0:
        day = number_of(payload, "day")
        log_green(
            f"Daily streak day {clean_text(day, 0)} credited "
            f"{clean_text(format_amount(gain), 0)} coins to this account"
        )
        return gain
    return 0.0


async def run_leaderboard(session, account, proxy):
    status, payload = await api_call(
        session, account, "/leaderboard?metric=referrals&limit=3", None, proxy, "GET"
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        log_yellow("The leaderboard position was not returned by the server")
        return
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    for entry in items:
        if isinstance(entry, dict) and entry.get("isMe"):
            account["rank"] = number_of(entry, "rank")
            total = number_of(payload, "total", len(items))
            log_green(
                f"Leaderboard position {clean_text(account['rank'], 0)} of "
                f"{clean_text(total, 0)} farmers"
            )
            return
    log_yellow("This account is not ranked on the leaderboard yet")


async def process_account(line, proxy, index):
    account = parse_init_data(line)
    if not account:
        log_red(f"Credential line {clean_text(index, 1)} is not valid initData")
        return

    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        profile = await run_auth(session, account, proxy)
        if not profile:
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return

        name = display_name(account)
        log_green(
            f"Signed in {clean_text(shorten(name, 'account', 18), 'account')} with "
            f"{clean_text(format_amount(account['usdt']), 0)} USDT and "
            f"{clean_text(format_amount(account['coins']), 0)} coins"
        )

        code = referrer_code_of(account)
        log_green(f"Referral code used for this account is {clean_text(code, 'code')}")

        await run_terms(session, account, proxy)
        status, bootstrap = await api_call(session, account, "/user/bootstrap", None, proxy, "GET")
        if status != 200 or not isinstance(bootstrap, dict) or not bootstrap.get("ok"):
            log_red("The account bootstrap was refused by the server on this run")
            return
        store_profile(account, bootstrap)

        await asyncio.gather(
            run_tasks(session, account, bootstrap, proxy),
            run_farm(session, account, bootstrap, proxy),
            run_streak(session, account, proxy),
            run_leaderboard(session, account, proxy),
        )
        await read_state(session, account, proxy)
        ads = bootstrap.get("ads") if isinstance(bootstrap, dict) else None
        cap = ads.get("cap") if isinstance(ads, dict) else None
        cap_done = isinstance(cap, dict) and number_of(cap, "remaining") <= 0
        gap = account.pop("slot_gap", 0)
        if gap <= 0:
            gap = gap_hint(account)
        if gap <= 0 and not cap_done:
            gap = await account_gap(session, account, proxy)
        if cap_done:
            gap = 0
        if gap > 0:
            PENDING_GAPS[index] = gap

        log_green(
            f"Cycle closed with {clean_text(format_amount(account['usdt']), 0)} USDT and "
            f"{clean_text(format_amount(account['coins']), 0)} coins"
        )


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        jobs = []
        for index, line in enumerate(accounts):
            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")
            jobs.append(process_account(line, proxy_url, index + 1))
        if jobs:
            log_yellow(
                f"{clean_text(len(jobs), 0)} {clean_text(plural(len(jobs)), 'accounts')} "
                "run at the same time instead of one after another"
            )
            await asyncio.gather(*jobs)

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        gaps = [value for value in PENDING_GAPS.values() if value > 0]
        PENDING_GAPS.clear()
        wait_secs = int(sleep_secs)
        if gaps:
            wait_secs = min(int(min(gaps)) + 2, wait_secs)
        await countdown(wait_secs, "Next cycle starts in")
        show_banner(MY_PROJECT)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    settings = load_config().get("settings", {})
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    try:
        asyncio.run(main_async(accounts, proxies, settings["sleep_seconds"]))
    except KeyboardInterrupt:
        print(flush=True)
        log_red("Script stopped by user")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


if __name__ == "__main__":
    main()