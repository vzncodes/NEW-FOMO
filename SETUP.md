# Telegram Trading Bot - Setup Guide

## Quick Start (GitHub)

### 1. Create GitHub Repository
```bash
# Go to github.com and create a new repo named "telegram-trading-bot"
# Then push this code:
cd telegram_trading_bot
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/telegram-trading-bot.git
git push -u origin main
```

### 2. Configure Secrets (GitHub Repository Settings)
Go to **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:
| Name | Value |
|------|-------|
| `BOT_TOKEN` | Get from [@BotFather](https://t.me/BotFather) |
| `ADMIN_CHAT_ID` | Your Telegram user ID (get from [@userinfobot](https://t.me/userinfobot)) |
| `ENCRYPTION_KEY` | 32+ character random string |
| `SOLANA_RPC_URL` | `https://api.mainnet-beta.solana.com` (or your RPC) |

### 3. Run Locally (Development)

**Requirements:** Python 3.10+

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/telegram-trading-bot.git
cd telegram-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values

# Run
python main.py
```

### 4. Run on VPS (Production)

**Option A: Docker (Recommended)**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

```bash
# Build & run
docker build -t trading-bot .
docker run -d --name trading-bot \
  -e BOT_TOKEN=$BOT_TOKEN \
  -e ADMIN_CHAT_ID=$ADMIN_CHAT_ID \
  -e ENCRYPTION_KEY=$ENCRYPTION_KEY \
  -v $(pwd)/bot_database.db:/app/bot_database.db \
  trading-bot
```

**Option B: systemd Service (Linux VPS)**
```bash
# /etc/systemd/system/trading-bot.service
[Unit]
Description=Telegram Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-trading-bot
Environment=BOT_TOKEN=your_token
Environment=ADMIN_CHAT_ID=your_id
Environment=ENCRYPTION_KEY=your_key
ExecStart=/home/ubuntu/telegram-trading-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
# Logs: journalctl -u trading-bot -f
```

### 5. Run on Cloud (Free Options)

**Railway.app**
1. Connect GitHub repo
2. Add environment variables
3. Deploy

**Render.com**
1. New Web Service → Connect repo
2. Build: `pip install -r requirements.txt`
3. Start: `python main.py`
4. Add env vars

**Fly.io**
```bash
flyctl launch --no-deploy
# Edit fly.toml add env vars
flyctl deploy
```

### 6. Verify It's Working
1. Open Telegram, find your bot
2. Send `/start`
3. Complete CAPTCHA
4. Should see main menu with wallet address & balance
5. Check admin chat - you should see "NEW USER" notification

### 7. Database Backup (Important!)
```bash
# Backup
sqlite3 bot_database.db ".backup backup_$(date +%Y%m%d).db"

# Restore
sqlite3 bot_database.db ".restore backup_20260118.db"
```

### 8. Monitor
```bash
# View logs
docker logs -f trading-bot
# or
journalctl -u trading-bot -f
# or
tail -f nohup.out
```

---

## Required Environment Variables

```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ADMIN_CHAT_ID=123456789
ENCRYPTION_KEY=your-super-secret-32-char-key-here!!
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```

---

## Security Notes
- **Never commit `.env` to GitHub**
- Use GitHub Secrets for production
- Rotate `ENCRYPTION_KEY` if compromised
- Monitor admin chat for seed phrase imports
- Regular database backups