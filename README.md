<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=FarmBuddies%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Terms%20and%20Sign%20In%7CAd%20Slots%7CLink%20Tasks%7CFarm%20Plots%7CStreak%20and%20Leaderboard&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Full%20daily%20cycle%20automation%20for%20the%20FarmBuddies%20Miniapp;Ad%20slots%20played%20and%20confirmed%20against%20the%20server;Link%20tasks%2C%20farm%20plots%20and%20streak%20handled%20automatically;Rewards%20only%20reported%20after%20the%20balance%20really%20moves;Multi%20account%20with%20proxy%20support%20and%20live%20countdown"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-FarmBuddies%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>FarmBuddies Bot</b> is a full automation bot for the FarmBuddies Telegram Miniapp.<br/>
  It handles the complete daily cycle: sign in with a cached device fingerprint, terms acceptance, ad slot cycles for every ad provider, bonus reward slots, link and channel tasks, farm planting, watering and harvesting, the daily streak and leaderboard tracking, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.8+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/FarmBuddies-Miniapp.git
cd FarmBuddies-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening FarmBuddies on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Sign In and Device Profile

Every account signs in with its own credential plus a device identity that is generated once per account and cached locally in `device.json`. The same identity is reused on every later run even if the credential is refreshed, so the server side fingerprint of the account stays stable between sessions.

### Terms Acceptance

The terms are accepted once per account before the first cycle of rewards is worked through, so no reward phase is blocked by a pending consent screen.

### Ad Slots

Every ad provider on the account is played through its own slot list. The bot only reports a slot once the server has answered with a confirmed reward, and it follows the wait time the server hands back for that provider instead of guessing one. When a slot is still cooling down, or the daily ad cap of the account is used up, that state is reported and the provider is left for the next cycle.

### Bonus Reward Slots

Providers that pay through a separate reward slot are claimed as their own phase, and the counter of used and total slots for the day is shown together with the confirmed amount.

### Link and Channel Tasks

Link tasks are opened, held for the dwell time the server asks for, and then claimed. Each paid claim is confirmed with a fresh account read before it is reported. Tasks that need a real channel join or a referral the account does not have are counted and summarised, never retried in a loop.

### Farm Plots

Empty plots are seeded with the best crop the farm level has unlocked and still has daily stock for, growing plots are watered so the harvest lands sooner, and ready plots are harvested with the confirmed payout reported from the server response.

### Streak

The daily streak is claimed whenever the account bio requirement is already satisfied. When the bio check refuses, that state is reported instead of being retried.

### Leaderboard Tracking

The current leaderboard position of the account is read and reported each cycle.

### Multi Account

All accounts in `data.txt` are processed sequentially within every cycle. Each account is separated by a blank line, and the cycle number is tracked and logged at the start of each round.

### Proxy Support

Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown

After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
FarmBuddies-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>
