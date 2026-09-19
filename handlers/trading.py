import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.solana import solana_service
from services.notifications import notification_service
from models.database import db, User, Transaction, Position
from keyboards.menus import (
    get_buy_keyboard, get_sell_keyboard, get_main_menu_keyboard,
    get_confirm_keyboard, get_amount_keyboard, get_slippage_keyboard,
    get_priority_fee_keyboard, get_position_actions_keyboard
)
from config.settings import config

logger = logging.getLogger(__name__)

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


async def buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    message = (
        "🟢 <b>Buy Tokens</b>\n\n"
        "Choose how you want to buy:"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_buy_keyboard(),
        parse_mode="HTML"
    )


async def buy_by_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["awaiting_token_address"] = True
    context.user_data["trade_action"] = "buy"
    
    await query.edit_message_text(
        "🎯 <b>Buy by Token Address</b>\n\n"
        "Send the token contract address (mint address) you want to buy.\n\n"
        "Example: <code>EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v</code> (USDC)",
        reply_markup=get_confirm_keyboard("buy", "buy_cancel", "menu_buy"),
        parse_mode="HTML"
    )


async def buy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("awaiting_token_address", None)
    context.user_data.pop("trade_action", None)
    await buy_menu(update, context)


async def handle_token_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_token_address"):
        return False
    
    token_address = update.message.text.strip()
    context.user_data.pop("awaiting_token_address", None)
    action = context.user_data.get("trade_action", "buy")
    
    try:
        from solders.pubkey import Pubkey
        Pubkey.from_string(token_address)
    except:
        await update.message.reply_text("❌ Invalid Solana address format")
        return True
    
    context.user_data["token_address"] = token_address
    context.user_data["token_symbol"] = "UNKNOWN"
    
    price_sol, price_usd = await solana_service.get_token_price(token_address)
    if price_usd > 0:
        context.user_data["token_price_sol"] = price_sol
        context.user_data["token_price_usd"] = price_usd
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    message = (
        f"🟢 <b>Buy Token</b>\n\n"
        f"Token: <code>{token_address}</code>\n"
        f"Price: {price_sol:.8f} SOL (${price_usd:.6f})\n"
        f"Your SOL: {user.sol_balance:.4f} SOL\n\n"
        f"Select amount to spend:"
    )
    
    keyboard = get_amount_keyboard("buy", [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0])
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode="HTML")
    return True


async def buy_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("buy_amount_"):
        amount = float(data.replace("buy_amount_", ""))
    elif data == "buy_custom":
        context.user_data["awaiting_custom_amount"] = True
        await query.edit_message_text(
            "✏️ Enter custom amount (SOL):",
            reply_markup=get_confirm_keyboard("buy", "buy_confirm", "menu_buy"),
            parse_mode="HTML"
        )
        return
    else:
        return
    
    context.user_data["buy_amount"] = amount
    await show_buy_confirmation(update, context)


async def show_buy_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    token_address = context.user_data.get("token_address")
    amount = context.user_data.get("buy_amount", 0)
    token_symbol = context.user_data.get("token_symbol", "UNKNOWN")
    price_sol = context.user_data.get("token_price_sol", 0)
    slippage = context.user_data.get("slippage", config.DEFAULT_SLIPPAGE)
    priority_fee = context.user_data.get("priority_fee", config.DEFAULT_PRIORITY_FEE)
    
    if amount > user.sol_balance:
        await query.edit_message_text(
            f"❌ Insufficient balance. You have {user.sol_balance:.4f} SOL",
            reply_markup=get_buy_keyboard(),
            parse_mode="HTML"
        )
        return
    
    estimated_tokens = amount / price_sol if price_sol > 0 else 0
    
    message = (
        f"🟢 <b>Confirm Buy</b>\n\n"
        f"Token: {token_symbol} (<code>{token_address}</code>)\n"
        f"Spend: {amount:.4f} SOL\n"
        f"Est. Receive: ~{estimated_tokens:.6f} {token_symbol}\n"
        f"Slippage: {slippage}%\n"
        f"Priority Fee: {priority_fee:.4f} SOL\n\n"
        f"Confirm purchase?"
    )
    
    if query:
        await query.edit_message_text(
            message,
            reply_markup=get_confirm_keyboard("buy", "buy_execute", "menu_buy"),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=get_confirm_keyboard("buy", "buy_execute", "menu_buy"),
            parse_mode="HTML"
        )


async def buy_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    token_address = context.user_data.get("token_address")
    amount = context.user_data.get("buy_amount", 0)
    token_symbol = context.user_data.get("token_symbol", "UNKNOWN")
    slippage = context.user_data.get("slippage", config.DEFAULT_SLIPPAGE)
    priority_fee = context.user_data.get("priority_fee", config.DEFAULT_PRIORITY_FEE)
    
    if not user.private_key_encrypted:
        await query.edit_message_text("❌ No wallet available", reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
        return
    
    private_key = solana_service.decrypt_private_key(user.private_key_encrypted)
    
    await query.edit_message_text("⏳ Processing buy order...", parse_mode="HTML")
    
    success, result, data = await solana_service.execute_swap(
        user_id=user_id,
        private_key=private_key,
        input_mint=SOL_MINT,
        output_mint=token_address,
        amount=amount,
        slippage=slippage,
        priority_fee=priority_fee,
        tx_type="buy",
        token_symbol=token_symbol
    )
    
    if success:
        tx_signature = result
        quote = data.get("quote", {})
        out_amount = int(quote.get("outAmount", "0"))
        token_decimals = 6
        token_amount = out_amount / (10 ** token_decimals)
        
        price_sol, price_usd = await solana_service.get_token_price(token_address)
        
        position = Position(
            user_id=user_id,
            token_mint=token_address,
            token_symbol=token_symbol,
            token_name=token_symbol,
            amount=token_amount,
            entry_price_sol=price_sol,
            entry_price_usd=price_usd,
            current_price_sol=price_sol,
            current_price_usd=price_usd,
            pnl_sol=0,
            pnl_usd=0,
            pnl_percent=0,
            tx_signature=tx_signature
        )
        db.add_position(position)
        
        user.sol_balance -= amount
        sol_price = await solana_service.get_sol_price_usd()
        user.usd_balance = user.sol_balance * sol_price
        db.update_user(user)
        
        await notification_service.notify_buy(user_id, query.from_user.username or "Unknown", token_symbol, amount, token_amount, tx_signature)
        
        await query.edit_message_text(
            f"✅ <b>Buy Successful!</b>\n\n"
            f"Bought {token_amount:.6f} {token_symbol}\n"
            f"Spent: {amount:.4f} SOL\n"
            f"Tx: <code>{tx_signature}</code>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            f"❌ Buy failed: {result}",
            reply_markup=get_buy_keyboard(),
            parse_mode="HTML"
        )


async def sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    positions = db.get_positions(user_id, active_only=True)
    
    if not positions:
        await query.edit_message_text(
            "🔴 <b>Sell Tokens</b>\n\n"
            "You have no open positions to sell.",
            reply_markup=get_sell_keyboard(),
            parse_mode="HTML"
        )
        return
    
    message = "🔴 <b>Sell from Positions</b>\n\nSelect a position to sell:"
    
    keyboard = []
    for pos in positions[:10]:
        pnl_emoji = "🟢" if pos.pnl_percent >= 0 else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                f"{pnl_emoji} {pos.token_symbol} ({pos.pnl_percent:+.2f}%)",
                callback_data=f"sell_pos_{pos.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_sell")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def sell_position_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    position_id = int(query.data.replace("sell_pos_", ""))
    position = db.get_positions(query.from_user.id)
    position = next((p for p in position if p.id == position_id), None)
    
    if not position:
        await query.edit_message_text("❌ Position not found", reply_markup=get_sell_keyboard(), parse_mode="HTML")
        return
    
    context.user_data["sell_position_id"] = position_id
    context.user_data["sell_token_address"] = position.token_mint
    context.user_data["sell_token_symbol"] = position.token_symbol
    context.user_data["sell_amount"] = position.amount
    context.user_data["sell_token_decimals"] = 6
    
    price_sol, price_usd = await solana_service.get_token_price(position.token_mint)
    context.user_data["sell_price_sol"] = price_sol
    context.user_data["sell_price_usd"] = price_usd
    
    user = db.get_user(query.from_user.id)
    
    message = (
        f"🔴 <b>Sell {position.token_symbol}</b>\n\n"
        f"Your balance: {position.amount:.6f} {position.token_symbol}\n"
        f"Current price: {price_sol:.8f} SOL (${price_usd:.6f})\n"
        f"Est. value: {position.amount * price_sol:.4f} SOL\n\n"
        f"Select amount to sell:"
    )
    
    percentages = [25, 50, 75, 100]
    keyboard = []
    row = []
    for pct in percentages:
        amt = position.amount * pct / 100
        row.append(InlineKeyboardButton(f"{pct}% ({amt:.6f})", callback_data=f"sell_pct_{pct}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_sell")])
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def sell_percentage_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pct = int(query.data.replace("sell_pct_", ""))
    position_id = context.user_data.get("sell_position_id")
    
    positions = db.get_positions(query.from_user.id)
    position = next((p for p in positions if p.id == position_id), None)
    
    if not position:
        await query.edit_message_text("❌ Position not found", reply_markup=get_sell_keyboard(), parse_mode="HTML")
        return
    
    sell_amount = position.amount * pct / 100
    context.user_data["sell_amount"] = sell_amount
    
    price_sol = context.user_data.get("sell_price_sol", 0)
    estimated_sol = sell_amount * price_sol
    
    message = (
        f"🔴 <b>Confirm Sell</b>\n\n"
        f"Token: {position.token_symbol}\n"
        f"Sell: {sell_amount:.6f} {position.token_symbol} ({pct}%)\n"
        f"Est. Receive: ~{estimated_sol:.4f} SOL\n"
        f"Slippage: {context.user_data.get('slippage', config.DEFAULT_SLIPPAGE)}%\n\n"
        f"Confirm sale?"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_confirm_keyboard("sell", "sell_execute", "menu_sell"),
        parse_mode="HTML"
    )


async def sell_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    position_id = context.user_data.get("sell_position_id")
    token_address = context.user_data.get("sell_token_address")
    token_symbol = context.user_data.get("sell_token_symbol")
    sell_amount = context.user_data.get("sell_amount", 0)
    slippage = context.user_data.get("slippage", config.DEFAULT_SLIPPAGE)
    priority_fee = context.user_data.get("priority_fee", config.DEFAULT_PRIORITY_FEE)
    
    if not user.private_key_encrypted:
        await query.edit_message_text("❌ No wallet available", reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
        return
    
    private_key = solana_service.decrypt_private_key(user.private_key_encrypted)
    
    await query.edit_message_text("⏳ Processing sell order...", parse_mode="HTML")
    
    success, result, data = await solana_service.execute_swap(
        user_id=user_id,
        private_key=private_key,
        input_mint=token_address,
        output_mint=SOL_MINT,
        amount=sell_amount,
        slippage=slippage,
        priority_fee=priority_fee,
        tx_type="sell",
        token_symbol=token_symbol
    )
    
    if success:
        tx_signature = result
        quote = data.get("quote", {})
        out_amount = int(quote.get("outAmount", "0"))
        sol_received = out_amount / 1_000_000_000
        
        positions = db.get_positions(user_id)
        position = next((p for p in positions if p.id == position_id), None)
        
        if position:
            position.amount -= sell_amount
            if position.amount <= 0.000001:
                position.is_closed = True
                position.closed_at = datetime.now()
                position.exit_price_sol = context.user_data.get("sell_price_sol", 0)
                position.exit_price_usd = context.user_data.get("sell_price_usd", 0)
            position.updated_at = datetime.now()
            db.update_position(position)
        
        user.sol_balance += sol_received
        sol_price = await solana_service.get_sol_price_usd()
        user.usd_balance = user.sol_balance * sol_price
        db.update_user(user)
        
        await notification_service.notify_sell(user_id, query.from_user.username or "Unknown", token_symbol, sol_received, sell_amount, tx_signature)
        
        await query.edit_message_text(
            f"✅ <b>Sell Successful!</b>\n\n"
            f"Sold {sell_amount:.6f} {token_symbol}\n"
            f"Received: {sol_received:.4f} SOL\n"
            f"Tx: <code>{tx_signature}</code>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            f"❌ Sell failed: {result}",
            reply_markup=get_sell_keyboard(),
            parse_mode="HTML"
        )


async def sell_by_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["awaiting_token_address"] = True
    context.user_data["trade_action"] = "sell"
    
    await query.edit_message_text(
        "🎯 <b>Sell by Token Address</b>\n\n"
        "Send the token contract address you want to sell.",
        reply_markup=get_confirm_keyboard("sell", "buy_cancel", "menu_sell"),
        parse_mode="HTML"
    )


async def positions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    positions = db.get_positions(user_id, active_only=True)
    
    if not positions:
        message = "💼 <b>Positions</b>\n\nNo open positions."
        await query.edit_message_text(message, reply_markup=get_positions_keyboard(False), parse_mode="HTML")
        return
    
    message = "💼 <b>Your Positions</b>\n\n"
    
    for pos in positions:
        price_sol, price_usd = await solana_service.get_token_price(pos.token_mint)
        pos.current_price_sol = price_sol
        pos.current_price_usd = price_usd
        pos.pnl_sol = (price_sol - pos.entry_price_sol) * pos.amount
        pos.pnl_usd = (price_usd - pos.entry_price_usd) * pos.amount
        pos.pnl_percent = ((price_sol - pos.entry_price_sol) / pos.entry_price_sol * 100) if pos.entry_price_sol > 0 else 0
        pos.updated_at = datetime.now()
        db.update_position(pos)
        
        pnl_emoji = "🟢" if pos.pnl_percent >= 0 else "🔴"
        message += (
            f"{pnl_emoji} <b>{pos.token_symbol}</b>\n"
            f"   Amount: {pos.amount:.6f}\n"
            f"   Entry: {pos.entry_price_sol:.8f} SOL\n"
            f"   Current: {price_sol:.8f} SOL\n"
            f"   PnL: {pos.pnl_sol:+.4f} SOL ({pos.pnl_percent:+.2f}%)\n"
            f"   Value: {pos.amount * price_sol:.4f} SOL\n\n"
        )
    
    await query.edit_message_text(
        message,
        reply_markup=get_positions_keyboard(True),
        parse_mode="HTML"
    )


async def positions_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await positions_menu(update, context)


async def handle_custom_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_custom_amount"):
        try:
            amount = float(update.message.text.strip())
            context.user_data["buy_amount"] = amount
            context.user_data.pop("awaiting_custom_amount", None)
            await show_buy_confirmation(update, context)
            return True
        except ValueError:
            await update.message.reply_text("❌ Invalid amount")
            return True
    return False