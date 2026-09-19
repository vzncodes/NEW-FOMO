import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.solana import solana_service
from services.notifications import notification_service
from models.database import db, User, LimitOrder, Position
from keyboards.menus import (
    get_limit_orders_keyboard, get_main_menu_keyboard,
    get_confirm_keyboard, get_amount_keyboard
)
from config.settings import config

logger = logging.getLogger(__name__)

SOL_MINT = "So11111111111111111111111111111111111111112"


async def limit_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    message = "📊 <b>Limit Orders</b>\n\nSet buy/sell orders at specific prices."
    
    await query.edit_message_text(
        message,
        reply_markup=get_limit_orders_keyboard(),
        parse_mode="HTML"
    )


async def limit_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    positions = db.get_positions(user_id, active_only=True)
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("🎯 Buy Limit Order", callback_data="limit_buy_new")])
    if positions:
        keyboard.append([InlineKeyboardButton("🎯 Sell Limit Order (from positions)", callback_data="limit_sell_new")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_limit_orders")])
    
    await query.edit_message_text(
        "📊 <b>Create Limit Order</b>\n\nSelect order type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def limit_buy_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["awaiting_limit_token"] = True
    context.user_data["limit_side"] = "buy"
    
    await query.edit_message_text(
        "🎯 <b>Create Buy Limit Order</b>\n\n"
        "Send the token contract address:",
        reply_markup=get_confirm_keyboard("limit", "limit_cancel", "menu_limit_orders"),
        parse_mode="HTML"
    )


async def limit_sell_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    positions = db.get_positions(user_id, active_only=True)
    
    if not positions:
        await query.edit_message_text("❌ No positions to sell", reply_markup=get_limit_orders_keyboard(), parse_mode="HTML")
        return
    
    keyboard = []
    for pos in positions[:10]:
        keyboard.append([InlineKeyboardButton(f"{pos.token_symbol}", callback_data=f"limit_sell_pos_{pos.id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="limit_create")])
    
    await query.edit_message_text(
        "🎯 <b>Create Sell Limit Order</b>\n\nSelect position:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def limit_sell_pos_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    position_id = int(query.data.replace("limit_sell_pos_", ""))
    positions = db.get_positions(query.from_user.id)
    position = next((p for p in positions if p.id == position_id), None)
    
    if not position:
        await query.edit_message_text("❌ Position not found", reply_markup=get_limit_orders_keyboard(), parse_mode="HTML")
        return
    
    context.user_data["limit_position_id"] = position_id
    context.user_data["limit_token_address"] = position.token_mint
    context.user_data["limit_token_symbol"] = position.token_symbol
    context.user_data["limit_side"] = "sell"
    context.user_data["limit_max_amount"] = position.amount
    
    await query.edit_message_text(
        f"🎯 <b>Sell Limit Order - {position.token_symbol}</b>\n\n"
        f"Available: {position.amount:.6f}\n\n"
        f"Enter target price (SOL):",
        reply_markup=get_confirm_keyboard("limit", "limit_cancel", "menu_limit_orders"),
        parse_mode="HTML"
    )
    context.user_data["awaiting_limit_price"] = True


async def handle_limit_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_limit_token"):
        return False
    
    token_address = update.message.text.strip()
    context.user_data.pop("awaiting_limit_token", None)
    
    try:
        from solders.pubkey import Pubkey
        Pubkey.from_string(token_address)
    except:
        await update.message.reply_text("❌ Invalid Solana address format")
        return True
    
    context.user_data["limit_token_address"] = token_address
    context.user_data["awaiting_limit_price"] = True
    
    price_sol, price_usd = await solana_service.get_token_price(token_address)
    
    await update.message.reply_text(
        f"✅ Token: <code>{token_address}</code>\n"
        f"Current price: {price_sol:.8f} SOL (${price_usd:.6f})\n\n"
        f"Enter target price (SOL):",
        parse_mode="HTML"
    )
    return True


async def handle_limit_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_limit_price"):
        return False
    
    try:
        price = float(update.message.text.strip())
        context.user_data["limit_price_sol"] = price
        context.user_data.pop("awaiting_limit_price", None)
        context.user_data["awaiting_limit_amount"] = True
        
        side = context.user_data.get("limit_side", "buy")
        token_symbol = context.user_data.get("limit_token_symbol", "TOKEN")
        
        if side == "buy":
            await update.message.reply_text(
                f"Target price: {price:.8f} SOL\n\n"
                f"Enter amount to spend (SOL):",
                parse_mode="HTML"
            )
        else:
            max_amt = context.user_data.get("limit_max_amount", 0)
            await update.message.reply_text(
                f"Target price: {price:.8f} SOL\n"
                f"Max available: {max_amt:.6f} {token_symbol}\n\n"
                f"Enter amount to sell ({token_symbol}):",
                parse_mode="HTML"
            )
        return True
    except ValueError:
        await update.message.reply_text("❌ Invalid price")
        return True


async def handle_limit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_limit_amount"):
        return False
    
    try:
        amount = float(update.message.text.strip())
        context.user_data["limit_amount"] = amount
        context.user_data.pop("awaiting_limit_amount", None)
        
        await show_limit_confirmation(update, context)
        return True
    except ValueError:
        await update.message.reply_text("❌ Invalid amount")
        return True


async def show_limit_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    side = context.user_data.get("limit_side", "buy")
    token_address = context.user_data.get("limit_token_address")
    token_symbol = context.user_data.get("limit_token_symbol", "TOKEN")
    price_sol = context.user_data.get("limit_price_sol", 0)
    amount = context.user_data.get("limit_amount", 0)
    
    if side == "buy":
        if amount > user.sol_balance:
            await update.message.reply_text(f"❌ Insufficient SOL. You have {user.sol_balance:.4f} SOL")
            return
        estimated = amount / price_sol if price_sol > 0 else 0
        sol_amount = amount
    else:
        max_amt = context.user_data.get("limit_max_amount", 0)
        if amount > max_amt:
            await update.message.reply_text(f"❌ Insufficient tokens. Max: {max_amt:.6f}")
            return
        estimated = amount * price_sol
        sol_amount = estimated
    
    message = (
        f"📊 <b>Confirm Limit Order</b>\n\n"
        f"Type: {'BUY' if side == 'buy' else 'SELL'}\n"
        f"Token: {token_symbol} (<code>{token_address}</code>)\n"
        f"Target Price: {price_sol:.8f} SOL\n"
        f"Amount: {amount:.6f} {'SOL' if side == 'buy' else token_symbol}\n"
        f"Est. {'Receive' if side == 'buy' else 'Get'}: ~{estimated:.6f} {token_symbol if side == 'buy' else 'SOL'}\n\n"
        f"Confirm?"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=get_confirm_keyboard("limit", "limit_execute", "menu_limit_orders"),
        parse_mode="HTML"
    )


async def limit_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    side = context.user_data.get("limit_side", "buy")
    token_address = context.user_data.get("limit_token_address")
    token_symbol = context.user_data.get("limit_token_symbol", "TOKEN")
    price_sol = context.user_data.get("limit_price_sol", 0)
    amount = context.user_data.get("limit_amount", 0)
    position_id = context.user_data.get("limit_position_id")
    
    order = LimitOrder(
        user_id=user_id,
        token_mint=token_address,
        token_symbol=token_symbol,
        side=side,
        target_price_sol=price_sol,
        target_price_usd=price_sol * await solana_service.get_sol_price_usd(),
        amount=amount,
        sol_amount=amount if side == "buy" else amount * price_sol,
        is_active=True
    )
    db.add_limit_order(order)
    
    await notification_service.notify_limit_order(user_id, query.from_user.username or "Unknown", token_symbol, side.upper(), price_sol, amount)
    
    await query.edit_message_text(
        f"✅ Limit order created!\n\n"
        f"{side.upper()} {amount:.6f} {token_symbol if side == 'sell' else 'SOL'} @ {price_sol:.8f} SOL\n"
        f"Order ID: {order.id}",
        reply_markup=get_limit_orders_keyboard(),
        parse_mode="HTML"
    )
    
    context.user_data.clear()


async def limit_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    orders = db.get_limit_orders(user_id, active_only=True)
    
    if not orders:
        message = "📋 <b>My Limit Orders</b>\n\nNo active limit orders."
    else:
        message = "📋 <b>My Limit Orders</b>\n\n"
        for order in orders:
            price_usd = order.target_price_sol * await solana_service.get_sol_price_usd()
            side_emoji = "🟢" if order.side == "buy" else "🔴"
            message += (
                f"{side_emoji} {order.side.upper()} {order.token_symbol}\n"
                f"   Target: {order.target_price_sol:.8f} SOL (${price_usd:.6f})\n"
                f"   Amount: {order.amount:.6f} {'SOL' if order.side == 'buy' else order.token_symbol}\n"
                f"   ID: {order.id}\n\n"
            )
    
    keyboard = []
    for order in orders:
        keyboard.append([
            InlineKeyboardButton(
                f"{'🟢' if order.side == 'buy' else '🔴'} {order.side.upper()} {order.token_symbol}",
                callback_data=f"limit_detail_{order.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_limit_orders")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def limit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await limit_orders_menu(update, context)