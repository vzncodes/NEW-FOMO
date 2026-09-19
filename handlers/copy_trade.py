import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.solana import solana_service
from services.notifications import notification_service
from models.database import db, User, CopyTradeWallet, Transaction, Position
from keyboards.menus import (
    get_copy_trade_keyboard, get_main_menu_keyboard,
    get_confirm_keyboard, get_amount_keyboard, get_copy_wallet_actions_keyboard
)
from config.settings import config

logger = logging.getLogger(__name__)

SOL_MINT = "So11111111111111111111111111111111111111112"


async def copy_trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    message = "📋 <b>Copy Trade</b>\n\nMirror trades from other wallets automatically."
    
    await query.edit_message_text(
        message,
        reply_markup=get_copy_trade_keyboard(),
        parse_mode="HTML"
    )


async def copy_add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["awaiting_copy_wallet_address"] = True
    
    await query.edit_message_text(
        "➕ <b>Add Wallet to Copy</b>\n\n"
        "Send the wallet address you want to copy trade from.\n\n"
        "Example: <code>7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU</code>",
        reply_markup=get_confirm_keyboard("copy", "copy_add_cancel", "menu_copy_trade"),
        parse_mode="HTML"
    )


async def copy_add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("awaiting_copy_wallet_address", None)
    await copy_trade_menu(update, context)


async def handle_copy_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_copy_wallet_address"):
        return False
    
    wallet_address = update.message.text.strip()
    context.user_data.pop("awaiting_copy_wallet_address", None)
    
    try:
        from solders.pubkey import Pubkey
        Pubkey.from_string(wallet_address)
    except:
        await update.message.reply_text("❌ Invalid Solana address format")
        return True
    
    context.user_data["copy_wallet_address"] = wallet_address
    context.user_data["awaiting_copy_wallet_name"] = True
    
    await update.message.reply_text(
        f"✅ Address valid: <code>{wallet_address}</code>\n\n"
        f"Enter a name for this wallet:",
        parse_mode="HTML"
    )
    return True


async def handle_copy_wallet_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_copy_wallet_name"):
        return False
    
    wallet_name = update.message.text.strip()
    wallet_address = context.user_data.get("copy_wallet_address")
    context.user_data.pop("awaiting_copy_wallet_name", None)
    context.user_data.pop("copy_wallet_address", None)
    
    user_id = update.effective_user.id
    
    wallet = CopyTradeWallet(
        user_id=user_id,
        wallet_address=wallet_address,
        wallet_name=wallet_name,
        is_active=True,
        buy_percentage=100.0,
        sell_percentage=100.0,
        max_buy_sol=1.0,
        min_buy_sol=0.01
    )
    db.add_copy_trade_wallet(wallet)
    
    await notification_service.notify_copy_trade(user_id, update.effective_user.username or "Unknown", wallet_address, "ADDED", f"Name: {wallet_name}")
    
    await update.message.reply_text(
        f"✅ Wallet added to copy trade!\n\n"
        f"Name: {wallet_name}\n"
        f"Address: <code>{wallet_address}</code>\n\n"
        f"Configure settings in Copy Trade Settings.",
        parse_mode="HTML"
    )
    return True


async def copy_list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    wallets = db.get_copy_trade_wallets(user_id)
    
    if not wallets:
        message = "📋 <b>My Copy Wallets</b>\n\nNo wallets added yet."
    else:
        message = "📋 <b>My Copy Wallets</b>\n\n"
        for w in wallets:
            status = "🟢 Active" if w.is_active else "🔴 Inactive"
            message += (
                f"{status} <b>{w.wallet_name}</b>\n"
                f"   Address: <code>{w.wallet_address[:8]}...{w.wallet_address[-6:]}</code>\n"
                f"   Buy: {w.buy_percentage}% | Sell: {w.sell_percentage}%\n"
                f"   Max Buy: {w.max_buy_sol} SOL | Min Buy: {w.min_buy_sol} SOL\n\n"
            )
    
    keyboard = []
    for w in wallets:
        keyboard.append([
            InlineKeyboardButton(
                f"{'🟢' if w.is_active else '🔴'} {w.wallet_name}",
                callback_data=f"copy_wallet_{w.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_copy_trade")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def copy_wallet_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    wallet_id = int(query.data.replace("copy_wallet_", ""))
    user_id = query.from_user.id
    wallets = db.get_copy_trade_wallets(user_id)
    wallet = next((w for w in wallets if w.id == wallet_id), None)
    
    if not wallet:
        await query.edit_message_text("❌ Wallet not found", reply_markup=get_copy_trade_keyboard(), parse_mode="HTML")
        return
    
    status = "🟢 Active" if wallet.is_active else "🔴 Inactive"
    message = (
        f"📋 <b>{wallet.wallet_name}</b>\n\n"
        f"Status: {status}\n"
        f"Address: <code>{wallet.wallet_address}</code>\n"
        f"Buy Percentage: {wallet.buy_percentage}%\n"
        f"Sell Percentage: {wallet.sell_percentage}%\n"
        f"Max Buy: {wallet.max_buy_sol} SOL\n"
        f"Min Buy: {wallet.min_buy_sol} SOL\n"
        f"Added: {wallet.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_copy_wallet_actions_keyboard(wallet_id),
        parse_mode="HTML"
    )


async def copy_edit_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    wallet_id = int(query.data.replace("copy_edit_", ""))
    context.user_data["editing_copy_wallet_id"] = wallet_id
    
    message = (
        "⚙️ <b>Edit Copy Trade Settings</b>\n\n"
        "Select what to change:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Toggle Active", callback_data=f"copy_toggle_{wallet_id}")],
        [InlineKeyboardButton("📊 Buy %", callback_data=f"copy_buy_pct_{wallet_id}"),
         InlineKeyboardButton("📊 Sell %", callback_data=f"copy_sell_pct_{wallet_id}")],
        [InlineKeyboardButton("💰 Max Buy SOL", callback_data=f"copy_max_buy_{wallet_id}"),
         InlineKeyboardButton("💰 Min Buy SOL", callback_data=f"copy_min_buy_{wallet_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"copy_wallet_{wallet_id}")]
    ]
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def copy_toggle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    wallet_id = int(query.data.replace("copy_toggle_", ""))
    user_id = query.from_user.id
    wallets = db.get_copy_trade_wallets(user_id)
    wallet = next((w for w in wallets if w.id == wallet_id), None)
    
    if wallet:
        wallet.is_active = not wallet.is_active
        db.update_copy_trade_wallet(wallet)
        
        await notification_service.notify_copy_trade(user_id, query.from_user.username or "Unknown", wallet.wallet_address, "TOGGLED", f"Active: {wallet.is_active}")
    
    await copy_wallet_detail(update, context)


async def copy_remove_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    wallet_id = int(query.data.replace("copy_remove_", ""))
    user_id = query.from_user.id
    wallets = db.get_copy_trade_wallets(user_id)
    wallet = next((w for w in wallets if w.id == wallet_id), None)
    
    if wallet:
        await notification_service.notify_copy_trade(user_id, query.from_user.username or "Unknown", wallet.wallet_address, "REMOVED", f"Name: {wallet.wallet_name}")
        db.delete_copy_trade_wallet(wallet_id)
    
    await copy_list_wallets(update, context)


async def copy_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    settings = user.get_settings()
    
    global_buy_pct = settings.get("copy_global_buy_pct", 100)
    global_sell_pct = settings.get("copy_global_sell_pct", 100)
    global_max_buy = settings.get("copy_global_max_buy", 1.0)
    global_min_buy = settings.get("copy_global_min_buy", 0.01)
    
    message = (
        f"⚙️ <b>Copy Trade Settings</b>\n\n"
        f"Global Buy %: {global_buy_pct}%\n"
        f"Global Sell %: {global_sell_pct}%\n"
        f"Global Max Buy: {global_max_buy} SOL\n"
        f"Global Min Buy: {global_min_buy} SOL\n\n"
        f"Per-wallet settings override global settings."
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Global Buy %", callback_data="copy_set_global_buy"),
         InlineKeyboardButton("📊 Global Sell %", callback_data="copy_set_global_sell")],
        [InlineKeyboardButton("💰 Global Max Buy", callback_data="copy_set_global_max"),
         InlineKeyboardButton("💰 Global Min Buy", callback_data="copy_set_global_min")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_copy_trade")]
    ]
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def copy_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    transactions = db.get_transactions(user_id, limit=20)
    copy_txs = [tx for tx in transactions if tx.tx_type.startswith("copy_")]
    
    if not copy_txs:
        message = "📊 <b>Copy Trade History</b>\n\nNo copy trades yet."
    else:
        message = "📊 <b>Copy Trade History</b>\n\n"
        for tx in copy_txs:
            action = "BOUGHT" if "buy" in tx.tx_type else "SOLD"
            message += (
                f"{'🟢' if 'buy' in tx.tx_type else '🔴'} {action} {tx.amount:.6f} {tx.token_symbol}\n"
                f"   SOL: {tx.sol_amount:.4f}\n"
                f"   Tx: <code>{tx.tx_signature[:16]}...</code>\n"
                f"   {tx.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
    
    await query.edit_message_text(
        message,
        reply_markup=get_copy_trade_keyboard(),
        parse_mode="HTML"
    )