# Welcome Bot

A professional Discord welcome bot. New members get a Components V2 card
(brand, greeting, Verify/Read links, member + account info, community goal bar)
plus a rendered navy banner built around **their own profile picture**.

**No configuration files.** The only thing in `.env` is the token — the channel,
goal, wording, colours and links are all set inside Discord with slash commands.

## What it does

- Rich Components V2 message: container, sections, separators, media gallery
- 1024×384 banner with avatar ring/glow, member number and goal bar
- Avatar reused as the message thumbnail; initials fallback when there is none
- 7 slash commands cover 100% of the configuration, validated and confirmed
  with an ephemeral summary
- Settings persist across restarts, commands sync automatically to every server

## Setup

Requires Python 3.10+ and the **Server Members Intent** (Developer Portal →
Bot → Privileged Gateway Intents).

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env      # paste DISCORD_TOKEN only
python bot.py
```

Invite the bot with View Channel, Send Messages, Attach Files and Embed Links,
then run `/setup` in your server. Settings are stored in `data/settings.json`,
created on first use — never edit it by hand.

## Slash commands

All commands require **Manage Server** and reply ephemerally.

| Command | Options | What it does |
| --- | --- | --- |
| `/setup` | `channel`, `goal` | Welcome channel and community goal |
| `/brand` | `brand_line`, `title`, `tagline`, `card_title`, `card_footer`, `flags` | Every piece of wording |
| `/theme` | `accent`, `card_top`, `card_bottom`, `border`, `bar_track`, `bar_fill` | Full palette (hex) |
| `/links` | `verify_role`, `rules_channel`, `verify_text`, `read_text`, `clear` | Verify / Read targets |
| `/preview` | `name`, `position` | Post a dummy welcome to check the look |
| `/settings` | — | Show the current configuration |
| `/reset` | `confirm` | Restore the shipped defaults |

Only the options you pass are changed; everything else stays as it is.



## Project layout

```
bot.py            client, join event, startup
commands.py       slash commands
welcome.py        message composition
settings.py       defaults, persistence, colour parsing
render/card.py    Pillow banner + avatar renderer
```
