import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.notifications import notification_service
from models.database import db, User
from keyboards.menus import (
    get_settings_keyboard, get_main_menu_keyboard,
    get_slippage_keyboard, get_priority_fee_keyboard,
    get_notification_keyboard
)
from config.settings import config

logger = logging.getLogger(__name__)


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    settings = user.get_settings()
    
    slippage = settings.get("slippage", config.DEFAULT_SLIPPAGE)
    priority_fee = settings.get("priority_fee", config.DEFAULT_PRIORITY_FEE)
    notifications = settings.get("notifications", {})
    
    message = (
        f"⚙️ <b>Settings</b>\n\n"
        f"🎯 Slippage: {slippage}%\n"
        f"⚡ Priority Fee: {priority_fee:.4f} SOL\n"
        f"🔔 Notifications: {'Enabled' if notifications.get('enabled', True) else 'Disabled'}\n\n"
        f"Select setting to change:"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


async def settings_slippage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎯 <b>Slippage Tolerance</b>\n\nSelect slippage:",
        reply_markup=get_slippage_keyboard(),
        parse_mode="HTML"
    )


async def slippage_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("slippage_"):
        value = data.replace("slippage_", "")
        if value == "custom":
            context.user_data["awaiting_slippage"] = True
            await query.edit_message_text(
                "✏️ Enter custom slippage %:",
                reply_markup=get_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        slippage = float(value)
    else:
        return
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    settings = user.get_settings()
    settings["slippage"] = slippage
    user.set_settings(settings)
    db.update_user(user)
    
    await notification_service.notify_settings_change(user_id, query.from_user.username or "Unknown", "Slippage", f"{slippage}%")
    
    await settings_menu(update, context)


async def handle_slippage_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_slippage"):
        return False
    
    try:
        slippage = float(update.message.text.strip())
        if slippage < 0.1 or slippage > 50:
            await update.message.reply_text("❌ Slippage must be between 0.1% and 50%")
            return True
        
        user_id = update.effective_user.id
        user = db.get_user(user_id)
        settings = user.get_settings()
        settings["slippage"] = slippage
        user.set_settings(settings)
        db.update_user(user)
        
        await notification_service.notify_settings_change(user_id, update.effective_user.username or "Unknown", "Slippage", f"{slippage}%")
        
        await update.message.reply_text(f"✅ Slippage set to {slippage}%")
        context.user_data.pop("awaiting_slippage", None)
        return True
    except ValueError:
        await update.message.reply_text("❌ Invalid value")
        return True


async def settings_priority_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚡ <b>Priority Fee</b>\n\nSelect priority fee:",
        reply_markup=get_priority_fee_keyboard(),
        parse_mode="HTML"
    )


async def priority_fee_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("priority_"):
        value = data.replace("priority_", "")
        if value == "custom":
            context.user_data["awaiting_priority_fee"] = True
            await query.edit_message_text(
                "✏️ Enter custom priority fee (SOL):",
                reply_markup=get_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        priority_fee = float(value)
    else:
        return
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    settings = user.get_settings()
    settings["priority_fee"] = priority_fee
    user.set_settings(settings)
    db.update_user(user)
    
    await notification_service.notify_settings_change(user_id, query.from_user.username or "Unknown", "Priority Fee", f"{priority_fee:.4f} SOL")
    
    await settings_menu(update, context)


async def handle_priority_fee_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_priority_fee"):
        return False
    
    try:
        priority_fee = float(update.message.text.strip())
        if priority_fee < 0 or priority_fee > 0.1:
            await update.message.reply_text("❌ Priority fee must be between 0 and 0.1 SOL")
            return True
        
        user_id = update.effective_user.id
        user = db.get_user(user_id)
        settings = user.get_settings()
        settings["priority_fee"] = priority_fee
        user.set_settings(settings)
        db.update_user(user)
        
        await notification_service.notify_settings_change(user_id, update.effective_user.username or "Unknown", "Priority Fee", f"{priority_fee:.4f} SOL")
        
        await update.message.reply_text(f"✅ Priority fee set to {priority_fee:.4f} SOL")
        context.user_data.pop("awaiting_priority_fee", None)
        return True
    except ValueError:
        await update.message.reply_text("❌ Invalid value")
        return True


async def settings_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    settings = user.get_settings()
    notifications = settings.get("notifications", {"enabled": True})
    
    await query.edit_message_text(
        "🔔 <b>Notifications</b>\n\nToggle notification types:",
        reply_markup=get_notification_keyboard(notifications.get("enabled", True)),
        parse_mode="HTML"
    )


async def settings_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔑 Export Private Key", callback_data="settings_export_key")],
        [InlineKeyboardButton("🔒 Change Encryption", callback_data="settings_change_encryption")],
        [InlineKeyboardButton("🗑️ Delete Account", callback_data="settings_delete_account")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")]
    ]
    
    await query.edit_message_text(
        "🔒 <b>Security</b>\n\nManage your wallet security:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def settings_export_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if not user.private_key_encrypted:
        await query.edit_message_text("❌ No wallet to export", reply_markup=get_settings_keyboard(), parse_mode="HTML")
        return
    
    from services.solana import solana_service
    private_key = solana_service.decrypt_private_key(user.private_key_encrypted)
    
    await query.message.reply_text(
        f"🔑 <b>Private Key (Base64)</b>\n\n"
        f"<code>{private_key}</code>\n\n"
        f"⚠️ Keep this secure! Anyone with this key controls your wallet.",
        parse_mode="HTML"
    )


async def settings_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete Everything", callback_data="settings_delete_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="menu_settings")
        ]
    ]
    
    await query.edit_message_text(
        "🗑️ <b>Delete Account</b>\n\n"
        "This will permanently delete:\n"
        "- Your wallet and private key\n"
        "- All positions and orders\n"
        "- Copy trade wallets\n"
        "- Transaction history\n\n"
        "This action cannot be undone!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def settings_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    from models.database import db
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM positions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM copy_trade_wallets WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM limit_orders WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM auto_sell_rules WHERE user_id = ?", (user_id,))
    db.conn.commit()
    
    await query.edit_message_text(
        "✅ Account deleted successfully.\n\n"
        "Use /start to create a new account.",
        parse_mode="HTML"
    )