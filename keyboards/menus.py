from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🚀 Tap /start to enjoy", callback_data="start_bot")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_captcha_keyboard(captcha_code: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for i, char in enumerate(captcha_code):
        row.append(InlineKeyboardButton(char, callback_data=f"captcha_{char}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="captcha_refresh")])
    keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="captcha_verify")])
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🟢 Buy", callback_data="menu_buy"),
            InlineKeyboardButton("🔴 Sell", callback_data="menu_sell")
        ],
        [
            InlineKeyboardButton("📋 Copy Trade", callback_data="menu_copy_trade"),
            InlineKeyboardButton("📊 Limit Orders", callback_data="menu_limit_orders")
        ],
        [
            InlineKeyboardButton("⚡ Auto Sell", callback_data="menu_auto_sell"),
            InlineKeyboardButton("💼 Positions", callback_data="menu_positions")
        ],
        [
            InlineKeyboardButton("👛 Wallet", callback_data="menu_wallet"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton("🔗 Connect SOL Wallet", callback_data="menu_connect_wallet")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wallet_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("💰 Deposit SOL", callback_data="wallet_deposit"),
            InlineKeyboardButton("📤 Withdraw", callback_data="wallet_withdraw")
        ],
        [
            InlineKeyboardButton("🔑 Import Wallet", callback_data="wallet_import"),
            InlineKeyboardButton("🔄 Refresh Balance", callback_data="wallet_refresh")
        ],
        [
            InlineKeyboardButton("📋 Transaction History", callback_data="wallet_history"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_buy_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🎯 By Token Address", callback_data="buy_by_address"),
            InlineKeyboardButton("🔍 Search Token", callback_data="buy_search")
        ],
        [
            InlineKeyboardButton("💎 Trending", callback_data="buy_trending"),
            InlineKeyboardButton("⭐ Favorites", callback_data="buy_favorites")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sell_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("💼 Sell from Positions", callback_data="sell_positions"),
            InlineKeyboardButton("🎯 Sell by Token Address", callback_data="sell_by_address")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_copy_trade_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Wallet to Copy", callback_data="copy_add_wallet"),
            InlineKeyboardButton("📋 My Copy Wallets", callback_data="copy_list_wallets")
        ],
        [
            InlineKeyboardButton("⚙️ Copy Trade Settings", callback_data="copy_settings"),
            InlineKeyboardButton("📊 Copy Trade History", callback_data="copy_history")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_limit_orders_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("➕ Create Limit Order", callback_data="limit_create"),
            InlineKeyboardButton("📋 My Limit Orders", callback_data="limit_list")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_auto_sell_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Auto Sell Rule", callback_data="autosell_add"),
            InlineKeyboardButton("📋 My Auto Sell Rules", callback_data="autosell_list")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_positions_keyboard(has_positions: bool = False) -> InlineKeyboardMarkup:
    keyboard = []
    if has_positions:
        keyboard.append([InlineKeyboardButton("🔄 Refresh Prices", callback_data="positions_refresh")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🎯 Slippage", callback_data="settings_slippage"),
            InlineKeyboardButton("⚡ Priority Fee", callback_data="settings_priority_fee")
        ],
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
            InlineKeyboardButton("🌐 Language", callback_data="settings_language")
        ],
        [
            InlineKeyboardButton("🔒 Security", callback_data="settings_security"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_connect_wallet_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📱 Phantom", callback_data="connect_phantom"),
            InlineKeyboardButton("🦊 Solflare", callback_data="connect_solflare")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard(action: str, confirm_data: str, cancel_data: str = "back_main") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
            InlineKeyboardButton("❌ Cancel", callback_data=cancel_data)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_amount_keyboard(action: str, amounts: List[float] = None) -> InlineKeyboardMarkup:
    if amounts is None:
        amounts = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
    
    keyboard = []
    row = []
    for amount in amounts:
        row.append(InlineKeyboardButton(f"{amount} SOL", callback_data=f"{action}_amount_{amount}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("✏️ Custom Amount", callback_data=f"{action}_custom"),
        InlineKeyboardButton("🔙 Back", callback_data="back_main")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_slippage_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("0.5%", callback_data="slippage_0.5"),
            InlineKeyboardButton("1%", callback_data="slippage_1"),
            InlineKeyboardButton("2%", callback_data="slippage_2")
        ],
        [
            InlineKeyboardButton("3%", callback_data="slippage_3"),
            InlineKeyboardButton("5%", callback_data="slippage_5"),
            InlineKeyboardButton("10%", callback_data="slippage_10")
        ],
        [
            InlineKeyboardButton("✏️ Custom", callback_data="slippage_custom"),
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_priority_fee_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("0.0001 SOL", callback_data="priority_0.0001"),
            InlineKeyboardButton("0.0005 SOL", callback_data="priority_0.0005"),
            InlineKeyboardButton("0.001 SOL", callback_data="priority_0.001")
        ],
        [
            InlineKeyboardButton("0.005 SOL", callback_data="priority_0.005"),
            InlineKeyboardButton("0.01 SOL", callback_data="priority_0.01"),
            InlineKeyboardButton("✏️ Custom", callback_data="priority_custom")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Buy/Sell Alerts", callback_data="notif_buy_sell"),
            InlineKeyboardButton("✅ Copy Trade Alerts", callback_data="notif_copy_trade")
        ],
        [
            InlineKeyboardButton("✅ Limit Order Alerts", callback_data="notif_limit"),
            InlineKeyboardButton("✅ Auto Sell Alerts", callback_data="notif_autosell")
        ],
        [
            InlineKeyboardButton("✅ Deposit/Withdraw", callback_data="notif_wallet"),
            InlineKeyboardButton("✅ Price Alerts", callback_data="notif_price")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_position_actions_keyboard(position_id: int, token_mint: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🟢 Buy More", callback_data=f"pos_buy_{position_id}"),
            InlineKeyboardButton("🔴 Sell", callback_data=f"pos_sell_{position_id}")
        ],
        [
            InlineKeyboardButton("📊 Set Limit Order", callback_data=f"pos_limit_{position_id}"),
            InlineKeyboardButton("⚡ Set Auto Sell", callback_data=f"pos_autosell_{position_id}")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"pos_refresh_{position_id}"),
            InlineKeyboardButton("🔙 Back", callback_data="menu_positions")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_copy_wallet_actions_keyboard(wallet_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit Settings", callback_data=f"copy_edit_{wallet_id}"),
            InlineKeyboardButton("🗑️ Remove", callback_data=f"copy_remove_{wallet_id}")
        ],
        [
            InlineKeyboardButton("📊 View Trades", callback_data=f"copy_trades_{wallet_id}"),
            InlineKeyboardButton("🔙 Back", callback_data="copy_list_wallets")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)