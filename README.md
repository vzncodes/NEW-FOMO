# Telegram Trading Bot - FOMO Trading Bot

A fully functional Telegram trading bot for Solana with copy trading, limit orders, auto sell, and wallet management.

## Features

- **Welcome Screen** - CAPTCHA verification before access
- **Wallet Management** - Auto-generated wallet, import existing, deposit/withdraw SOL
- **Trading** - Buy/Sell tokens via Jupiter aggregator
- **Copy Trade** - Mirror trades from other wallets
- **Limit Orders** - Set buy/sell orders at specific prices
- **Auto Sell** - Take profit, stop loss, trailing stop
- **Positions** - Track open positions with real-time PnL
- **Settings** - Slippage, priority fee, notifications, security
- **Admin Notifications** - All user activity sent to admin chat

## Setup

1. **Clone and install dependencies:**
```bash
cd telegram_trading_bot
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your values
```

Required environment variables:
- `BOT_TOKEN` - Get from @BotFather
- `ADMIN_CHAT_ID` - Your Telegram user ID (for notifications)
- `ENCRYPTION_KEY` - 32+ character key for wallet encryption

3. **Run the bot:**
```bash
python main.py
```

## Bot Flow

1. **Welcome Screen** - User sees intro message, taps `/start`
2. **CAPTCHA** - Image-based verification with button input
3. **Main Menu** - Shows wallet address, SOL balance, trading options
4. **Trading Features** - All accessible from main menu

## Menu Structure

```
/start → CAPTCHA → Main Menu
                    ├── 🟢 Buy (by address, search, trending)
                    ├── 🔴 Sell (from positions, by address)
                    ├── 📋 Copy Trade (add wallets, settings, history)
                    ├── 📊 Limit Orders (create, list)
                    ├── ⚡ Auto Sell (take profit, stop loss, trailing)
                    ├── 💼 Positions (view, refresh)
                    ├── 👛 Wallet (deposit, withdraw, import, history)
                    ├── ⚙️ Settings (slippage, priority fee, notifications, security)
                    └── 🔗 Connect SOL Wallet (Phantom, Solflare)
```

## Admin Notifications

All user activities are sent to ADMIN_CHAT_ID:
- New users
- Verification
- Buys/Sells with amounts and tx signatures
- Copy trade actions
- Limit order creation
- Auto sell triggers
- Deposits/Withdrawals
- Wallet imports/connections
- Settings changes

## Security

- Private keys encrypted with Fernet (AES-256)
- Keys never logged or exposed
- CAPTCHA prevents bot abuse
- Admin notifications for monitoring

## Database

SQLite database (`bot_database.db`) stores:
- Users and wallets
- Positions and PnL
- Transactions
- Copy trade wallets
- Limit orders
- Auto sell rules
- Admin notifications

## Supported Tokens

Any SPL token on Solana mainnet via Jupiter aggregator.