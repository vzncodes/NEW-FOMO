import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.captcha import captcha_service
from services.notifications import notification_service
from models.database import db, User
from keyboards.menus import get_welcome_keyboard, get_captcha_keyboard, get_main_menu_keyboard
from config.settings import config

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """What can this bot do?

Launch Bot by FOMO - your fastest and most secure way to access trusted tokens on Solana and EVM chain before the crowd. It can also mirror other wallets with copy trading.

Tap /start to enjoy."""


async def send_welcome_media(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, keyboard):
    """Send welcome message with optional photo/video"""
    media_type = config.WELCOME_MEDIA_TYPE.lower()
    media_url = config.WELCOME_MEDIA_URL
    caption = config.WELCOME_MEDIA_CAPTION or message
    
    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
        message_obj = update.callback_query.message
    else:
        chat_id = update.message.chat_id
        message_obj = update.message
    
    try:
        if media_type == "photo" and media_url:
            if media_url.startswith("http"):
                await context.bot.send_photo(chat_id=chat_id, photo=media_url, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
            else:
                # Local file
                with open(media_url, "rb") as f:
                    await context.bot.send_photo(chat_id=chat_id, photo=f, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
        elif media_type == "video" and media_url:
            if media_url.startswith("http"):
                await context.bot.send_video(chat_id=chat_id, video=media_url, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
            else:
                with open(media_url, "rb") as f:
                    await context.bot.send_video(chat_id=chat_id, video=f, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
        else:
            # No media, just text
            if update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to send welcome media: {e}")
        # Fallback to text only
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    existing_user = db.get_user(user_id)
    if not existing_user:
        new_user = User(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        db.create_user(new_user)
        await notification_service.notify_new_user(user_id, user.username or "Unknown")
    
    if captcha_service.is_verified(user_id):
        await show_main_menu(update, context)
    else:
        await show_welcome(update, context)


async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_welcome_keyboard()
    await send_welcome_media(update, context, WELCOME_MESSAGE, keyboard)


async def start_bot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if captcha_service.is_verified(user_id):
        await show_main_menu(update, context)
        return
    
    code, display_text = captcha_service.generate_captcha()
    captcha_service.set_captcha(user_id, code)
    
    await query.edit_message_text(
        "🔐 <b>Verification Required</b>\n\n"
        "Please enter the CAPTCHA code shown below to continue.\n\n"
        f"{display_text}",
        parse_mode="HTML",
        reply_markup=get_captcha_keyboard(code)
    )


async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "captcha_refresh":
        code, display_text = captcha_service.generate_captcha()
        captcha_service.set_captcha(user_id, code)
        
        await query.edit_message_text(
            "🔐 <b>Verification Required</b>\n\n"
            "Please enter the CAPTCHA code shown below to continue.\n\n"
            f"{display_text}",
            parse_mode="HTML",
            reply_markup=get_captcha_keyboard(code)
        )
        return
    
    if data == "captcha_verify":
        user = db.get_user(user_id)
        if user and user.captcha_code:
            await query.edit_message_text(
                "✅ <b>Verification Successful!</b>\n\n"
                "Welcome to Launch Bot by FOMO!\n"
                "You can now start trading.",
                parse_mode="HTML"
            )
            await notification_service.notify_verification(user_id, query.from_user.username or "Unknown")
            await show_main_menu(update, context)
        else:
            await query.edit_message_text(
                "❌ No active CAPTCHA. Please start over with /start",
                parse_mode="HTML"
            )
        return
    
    if data.startswith("captcha_"):
        char = data.replace("captcha_", "")
        user = db.get_user(user_id)
        if not user:
            return
        
        current_input = context.user_data.get("captcha_input", "")
        current_input += char
        context.user_data["captcha_input"] = current_input
        
        await query.edit_message_text(
            "🔐 <b>Verification Required</b>\n\n"
            "Please enter the CAPTCHA code shown in the image below to continue.\n\n"
            f"<code>{current_input}</code>",
            parse_mode="HTML",
            reply_markup=get_captcha_keyboard(user.captcha_code or "")
        )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await start_command(update, context)
        return
    
    if not user.wallet_address:
        from services.solana import solana_service
        wallet_address, private_key = solana_service.generate_wallet()
        encrypted_key = solana_service.encrypt_private_key(private_key)
        user.wallet_address = wallet_address
        user.private_key_encrypted = encrypted_key
        db.update_user(user)
    
    sol_balance = user.sol_balance
    usd_balance = user.usd_balance
    
    if sol_balance == 0 and user.wallet_address:
        from services.solana import solana_service
        sol_balance = await solana_service.get_sol_balance(user.wallet_address)
        sol_price = await solana_service.get_sol_price_usd()
        usd_balance = sol_balance * sol_price
        user.sol_balance = sol_balance
        user.usd_balance = usd_balance
        db.update_user(user)
    
    wallet_short = f"{user.wallet_address[:6]}...{user.wallet_address[-4:]}" if user.wallet_address else "Not connected"
    
    message = (
        f"A Solana Wallet address:\n"
        f"  <code>{user.wallet_address}</code> (Tap to copy)\n\n"
        f"SOL Balance: {sol_balance:.4f} SOL (${usd_balance:.2f})\n\n"
        f"You can send {config.MIN_DEPOSIT_SOL} to {config.MAX_DEPOSIT_SOL} SOL to the bot Or import your existing wallet.\n\n"
        f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    keyboard = get_main_menu_keyboard()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)