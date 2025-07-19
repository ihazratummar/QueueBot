# 🎮 Twitch Subscriber Queue Bot for Discord

This custom Discord bot manages a full automatic queue system for Twitch subscribers who want to join your voice chat and play with you. It tracks join order, moves users automatically, and logs all events in real-time — no manual input needed.

---

## ✅ Features

- 🎙️ Automatically tracks users who join the "Waiting Room"
- 🔁 Maintains a live queue with correct join order
- 🚀 Moves users from the waiting room to the game room as slots open
- 📋 Posts and updates a public queue in a text channel (e.g., `#game-queue`)
- 📓 Logs all queue events in a private mod/admin channel (e.g., `#queue-log`)
- ⚙️ Optional manual commands for admins (reset, skip, pause, resume)

---

## 🛠 Setup Guide

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** → Give it a name
3. Go to **Bot** tab → Click **"Add Bot"**
4. Enable the following **Privileged Gateway Intents**:
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ PRESENCE INTENT (optional)

---

### 2. OAuth2 URL & Permissions

#### **Scopes:**
- `bot`
- `applications.commands`

#### **Bot Permissions:**
- `View Channels`
- `Connect`
- `Move Members`
- `Send Messages`
- `Manage Messages` *(optional but recommended)*
- `Use Application Commands`

**Permission Integer:**  


Use the **OAuth2 → URL Generator** in Developer Portal to create your invite link.

---

### 3. Required Channels Setup

- 🎙️ **Voice Channel:** `Waiting Room`
- ✅ **Voice Channel:** `Game Room`
- 📝 **Text Channel:** `#game-queue` (public queue display)
- 🔒 **Text Channel:** `#queue-log` (private admin log)

Restrict access to voice channels to your Twitch subscriber role.

---

## 🔁 Automatic Queue Flow & Logic

### How it works:

1. **User joins `Waiting Room`:**
   - Bot adds them to the queue
   - Posts/updates public queue in `#game-queue`
   - Logs the join in `#queue-log`

2. **When a slot opens in `Game Room`:**
   - Bot moves the next user automatically
   - Updates the queue
   - Logs the move

3. **If someone leaves or is kicked:**
   - Bot detects and fills the slot
   - Queue is updated and logged

---
🔐 Smart Slot Control (Game-Based)
The bot only moves users if the owner is present in the Game Room.

A maximum of 3 guests will be moved in at once (COD squad logic).

As soon as a guest leaves or is kicked, the bot fills the spot from the queue.
---

### 📋 Public Queue Example (`#game-queue`)

🎮 Current Queue:

@PlayerOne

@PlayerTwo

@PlayerThree


Bot updates this message automatically as users join/leave.

---

### 📓 Log Channel Example (`#queue-log`)

✅ @PlayerOne joined the waiting room. Position: #1
✅ @PlayerTwo joined the waiting room. Position: #2
➡️ @PlayerOne moved to Game Room.
❌ @PlayerOne left Game Room early. Filled next slot.
➡️ @PlayerTwo moved to Game Room.



Timestamps can be added if needed.

---

## 🧪 Slash Commands (Optional)

These are admin-only and can be used for manual control:

| Command          | Description                                  |
|------------------|----------------------------------------------|
| `/queue show`    | Show the current queue                       |
| `/queue reset`   | Clear the queue                              |
| `/queue skip`    | Skip current player and move the next        |
| `/queue pause`   | Pause the automatic movement temporarily     |
| `/queue resume`  | Resume automatic movement                    |

These do **not interfere** with the automatic logic.

---

## 🗃️ Database and Core Logic

- **Database:** We will use Python's built-in `sqlite3` module for database operations. This avoids the need for external database servers.
- **Core Logic:**
    - When a user joins the "Waiting Room," the bot checks if a slot is available in the "Game Room."
    - If a slot is free and the server owner is present in the "Game Room," the bot will automatically move the user.
    - A command will be available for the owner to toggle this automatic movement feature on or off.

---

## 📦 requirements.txt

```txt
discord.py
python-dotenv


🚀 Summary
Fully automatic from join → move → log

Public queue lets users see their position

Private logs for transparency

Easy setup for streamers

Extendable with cooldowns, priority, limits, etc.
