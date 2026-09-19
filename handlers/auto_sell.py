import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.notifications import notification_service
from models.database import db, User, AutoSellRule, Position
from keyboards.menus import (
    get_auto_sell_keyboard, get_main_menu_keyboard,
    get_confirm_keyboard
)
from config.settings import config

logger = logging.getLogger(__name__)


async def auto_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    message = "⚡ <b>Auto Sell</b>\n\nAutomatically sell based on price targets, stop loss, or trailing stops."
    
    await query.edit_message_text(
        message,
        reply_markup=get_auto_sell_keyboard(),
        parse_mode="HTML"
    )


async def autosell_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    positions = db.get_positions(user_id, active_only=True)
    
    if not positions:
        await query.edit_message_text(
            "❌ No positions to set auto sell on",
            reply_markup=get_auto_sell_keyboard(),
            parse_mode="HTML"
        )
        return
    
    keyboard = []
    for pos in positions[:10]:
        keyboard.append([InlineKeyboardButton(f"{pos.token_symbol}", callback_data=f"autosell_pos_{pos.id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_auto_sell")])
    
    await query.edit_message_text(
        "⚡ <b>Add Auto Sell Rule</b>\n\nSelect position:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def autosell_pos_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    position_id = int(query.data.replace("autosell_pos_", ""))
    positions = db.get_positions(query.from_user.id)
    position = next((p for p in positions if p.id == position_id), None)
    
    if not position:
        await query.edit_message_text("❌ Position not found", reply_markup=get_auto_sell_keyboard(), parse_mode="HTML")
        return
    
    context.user_data["autosell_position_id"] = position_id
    context.user_data["autosell_token_symbol"] = position.token_symbol
    context.user_data["autosell_token_mint"] = position.token_mint
    
    keyboard = [
        [InlineKeyboardButton("🎯 Take Profit %", callback_data="autosell_type_tp")],
        [InlineKeyboardButton("🛑 Stop Loss %", callback_data="autosell_type_sl")],
        [InlineKeyboardButton("📉 Trailing Stop %", callback_data="autosell_type_ts")],
        [InlineKeyboardButton("🔙 Back", callback_data="autosell_add")]
    ]
    
    await query.edit_message_text(
        f"⚡ <b>Auto Sell for {position.token_symbol}</b>\n\n"
        f"Select rule type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def autosell_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    rule_type = query.data.replace("autosell_type_", "")
    context.user_data["autosell_rule_type"] = rule_type
    
    type_names = {"tp": "Take Profit", "sl": "Stop Loss", "ts": "Trailing Stop"}
    type_name = type_names.get(rule_type, rule_type.upper())
    
    context.user_data["awaiting_autosell_percent"] = True
    
    await query.edit_message_text(
        f"⚡ <b>{type_name} %</b>\n\n"
        f"Enter percentage (e.g., 50 for 50%):",
        reply_markup=get_confirm_keyboard("autosell", "autosell_cancel", "menu_auto_sell"),
        parse_mode="HTML"
    )


async def handle_autosell_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_autosell_percent"):
        return False
    
    try:
        percent = float(update.message.text.strip())
        context.user_data["autosell_percent"] = percent
        context.user_data.pop("awaiting_autosell_percent", None)
        
        rule_type = context.user_data.get("autosell_rule_type")
        token_symbol = context.user_data.get("autosell_token_symbol")
        
        type_names = {"tp": "Take Profit", "sl": "Stop Loss", "ts": "Trailing Stop"}
        type_name = type_names.get(rule_type, rule_type.upper())
        
        message = (
            f"⚡ <b>Confirm {type_name}</b>\n\n"
            f"Token: {token_symbol}\n"
            f"Trigger: {percent}%\n\n"
            f"Confirm?"
        )
        
        await update.message.reply_text(
            message,
            reply_markup=get_confirm_keyboard("autosell", "autosell_execute", "menu_auto_sell"),
            parse_mode="HTML"
        )
        return True
    except ValueError:
        await update.message.reply_text("❌ Invalid percentage")
        return True


async def autosell_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    position_id = context.user_data.get("autosell_position_id")
    token_mint = context.user_data.get("autosell_token_mint")
    token_symbol = context.user_data.get("autosell_token_symbol")
    rule_type = context.user_data.get("autosell_rule_type")
    percent = context.user_data.get("autosell_percent", 0)
    
    rule = AutoSellRule(
        user_id=user_id,
        token_mint=token_mint,
        token_symbol=token_symbol,
        rule_type=rule_type,
        target_percent=percent if rule_type == "tp" else 0,
        stop_loss_percent=percent if rule_type == "sl" else 0,
        take_profit_percent=percent if rule_type == "tp" else 0,
        trailing_stop_percent=percent if rule_type == "ts" else 0,
        is_active=True
    )
    db.add_auto_sell_rule(rule)
    
    type_names = {"tp": "TAKE PROFIT", "sl": "STOP LOSS", "ts": "TRAILING STOP"}
    type_name = type_names.get(rule_type, rule_type.upper())
    
    await notification_service.notify_auto_sell(user_id, query.from_user.username or "Unknown", token_symbol, type_name, f"{percent}%")
    
    await query.edit_message_text(
        f"✅ Auto sell rule created!\n\n"
        f"{type_name} {percent}% on {token_symbol}",
        reply_markup=get_auto_sell_keyboard(),
        parse_mode="HTML"
    )
    
    context.user_data.clear()


async def autosell_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    rules = db.get_auto_sell_rules(user_id)
    
    if not rules:
        message = "📋 <b>My Auto Sell Rules</b>\n\nNo active auto sell rules."
    else:
        message = "📋 <b>My Auto Sell Rules</b>\n\n"
        for rule in rules:
            type_names = {"tp": "Take Profit", "sl": "Stop Loss", "ts": "Trailing Stop"}
            type_name = type_names.get(rule.rule_type, rule.rule_type.upper())
            pct = rule.target_percent or rule.stop_loss_percent or rule.take_profit_percent or rule.trailing_stop_percent
            message += (
                f"⚡ {type_name} on {rule.token_symbol}\n"
                f"   Trigger: {pct}%\n"
                f"   ID: {rule.id}\n\n"
            )
    
    keyboard = []
    for rule in rules:
        type_names = {"tp": "Take Profit", "sl": "Stop Loss", "ts": "Trailing Stop"}
        type_name = type_names.get(rule.rule_type, rule.rule_type.upper())
        pct = rule.target_percent or rule.stop_loss_percent or rule.take_profit_percent or rule.trailing_stop_percent
        keyboard.append([
            InlineKeyboardButton(
                f"⚡ {type_name} {rule.token_symbol} {pct}%",
                callback_data=f"autosell_detail_{rule.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_auto_sell")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def autosell_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await auto_sell_menu(update, context)


async def autosell_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    rule_id = int(query.data.replace("autosell_remove_", ""))
    db.delete_auto_sell_rule(rule_id)
    
    await query.edit_message_text(
        "✅ Auto sell rule removed",
        reply_markup=get_auto_sell_keyboard(),
        parse_mode="HTML"
    )