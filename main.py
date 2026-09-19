import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from config.settings import config
from services.notifications import notification_service
from handlers.welcome import (
    start_command, show_welcome, start_bot_callback,
    captcha_callback, show_main_menu, back_to_main
)
from handlers.wallet import (
    wallet_menu, wallet_deposit, wallet_deposit_done, wallet_withdraw,
    withdraw_amount, wallet_withdraw_confirm, wallet_import,
    wallet_import_cancel, wallet_refresh, wallet_history,
    connect_wallet_menu, handle_private_key_input,
    handle_withdraw_address_input
)
from handlers.trading import (
    buy_menu, buy_by_address, buy_cancel, handle_token_address_input,
    buy_amount_selected, buy_execute, sell_menu, sell_position_select,
    sell_percentage_selected, sell_execute, sell_by_address,
    positions_menu, positions_refresh, handle_custom_amount_input
)
from handlers.copy_trade import (
    copy_trade_menu, copy_add_wallet, copy_add_cancel,
    handle_copy_wallet_address, handle_copy_wallet_name,
    copy_list_wallets, copy_wallet_detail, copy_edit_wallet,
    copy_toggle_wallet, copy_remove_wallet, copy_settings, copy_history
)
from handlers.limit_orders import (
    limit_orders_menu, limit_create, limit_buy_new, limit_sell_new,
    limit_sell_pos_select, handle_limit_token_input,
    handle_limit_price_input, handle_limit_amount_input,
    limit_execute, limit_list, limit_cancel
)
from handlers.auto_sell import (
    auto_sell_menu, autosell_add, autosell_pos_select,
    autosell_type_select, handle_autosell_percent,
    autosell_execute, autosell_list, autosell_cancel, autosell_remove
)
from handlers.settings import (
    settings_menu, settings_slippage, slippage_selected,
    handle_slippage_input, settings_priority_fee, priority_fee_selected,
    handle_priority_fee_input, settings_notifications,
    settings_security, settings_export_key, settings_delete_account,
    settings_delete_confirm
)
from keyboards.menus import InlineKeyboardMarkup


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    await notification_service.start()
    notification_service.set_bot(application.bot)
    logger.info("Bot initialized and notification service started")


async def post_shutdown(application: Application):
    await notification_service.stop()
    from services.solana import solana_service
    await solana_service.close()
    logger.info("Bot shutdown complete")


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    
    handled = await handle_private_key_input(update, context)
    if handled:
        return
    
    handled = await handle_withdraw_address_input(update, context)
    if handled:
        return
    
    handled = await handle_token_address_input(update, context)
    if handled:
        return
    
    handled = await handle_copy_wallet_address(update, context)
    if handled:
        return
    
    handled = await handle_copy_wallet_name(update, context)
    if handled:
        return
    
    handled = await handle_limit_token_input(update, context)
    if handled:
        return
    
    handled = await handle_limit_price_input(update, context)
    if handled:
        return
    
    handled = await handle_limit_amount_input(update, context)
    if handled:
        return
    
    handled = await handle_autosell_percent(update, context)
    if handled:
        return
    
    handled = await handle_custom_amount_input(update, context)
    if handled:
        return
    
    handled = await handle_slippage_input(update, context)
    if handled:
        return
    
    handled = await handle_priority_fee_input(update, context)
    if handled:
        return


def main():
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Please set BOT_TOKEN in config/settings.py or environment variable")
        return
    
    if config.ADMIN_CHAT_ID == 0:
        logger.warning("ADMIN_CHAT_ID not set - admin notifications will not work")
    
    application = Application.builder().token(config.BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    
    application.add_handler(CommandHandler("start", start_command))
    
    application.add_handler(CallbackQueryHandler(start_bot_callback, pattern="^start_bot$"))
    application.add_handler(CallbackQueryHandler(captcha_callback, pattern="^captcha_"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    
    application.add_handler(CallbackQueryHandler(wallet_menu, pattern="^menu_wallet$"))
    application.add_handler(CallbackQueryHandler(wallet_deposit, pattern="^wallet_deposit$"))
    application.add_handler(CallbackQueryHandler(wallet_deposit_done, pattern="^wallet_deposit_done$"))
    application.add_handler(CallbackQueryHandler(wallet_withdraw, pattern="^wallet_withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_amount, pattern="^withdraw_(amount_|custom)"))
    application.add_handler(CallbackQueryHandler(wallet_withdraw_confirm, pattern="^wallet_withdraw_confirm$"))
    application.add_handler(CallbackQueryHandler(wallet_import, pattern="^wallet_import$"))
    application.add_handler(CallbackQueryHandler(wallet_import_cancel, pattern="^wallet_import_cancel$"))
    application.add_handler(CallbackQueryHandler(wallet_refresh, pattern="^wallet_refresh$"))
    application.add_handler(CallbackQueryHandler(wallet_history, pattern="^wallet_history$"))
    application.add_handler(CallbackQueryHandler(connect_wallet_menu, pattern="^menu_connect_wallet$"))
    
    application.add_handler(CallbackQueryHandler(buy_menu, pattern="^menu_buy$"))
    application.add_handler(CallbackQueryHandler(buy_by_address, pattern="^buy_by_address$"))
    application.add_handler(CallbackQueryHandler(buy_cancel, pattern="^buy_cancel$"))
    application.add_handler(CallbackQueryHandler(buy_amount_selected, pattern="^buy_(amount_|custom)"))
    application.add_handler(CallbackQueryHandler(buy_execute, pattern="^buy_execute$"))
    application.add_handler(CallbackQueryHandler(sell_menu, pattern="^menu_sell$"))
    application.add_handler(CallbackQueryHandler(sell_position_select, pattern="^sell_pos_"))
    application.add_handler(CallbackQueryHandler(sell_percentage_selected, pattern="^sell_pct_"))
    application.add_handler(CallbackQueryHandler(sell_execute, pattern="^sell_execute$"))
    application.add_handler(CallbackQueryHandler(sell_by_address, pattern="^sell_by_address$"))
    application.add_handler(CallbackQueryHandler(positions_menu, pattern="^menu_positions$"))
    application.add_handler(CallbackQueryHandler(positions_refresh, pattern="^positions_refresh$"))
    
    application.add_handler(CallbackQueryHandler(copy_trade_menu, pattern="^menu_copy_trade$"))
    application.add_handler(CallbackQueryHandler(copy_add_wallet, pattern="^copy_add_wallet$"))
    application.add_handler(CallbackQueryHandler(copy_add_cancel, pattern="^copy_add_cancel$"))
    application.add_handler(CallbackQueryHandler(copy_list_wallets, pattern="^copy_list_wallets$"))
    application.add_handler(CallbackQueryHandler(copy_wallet_detail, pattern="^copy_wallet_"))
    application.add_handler(CallbackQueryHandler(copy_edit_wallet, pattern="^copy_edit_"))
    application.add_handler(CallbackQueryHandler(copy_toggle_wallet, pattern="^copy_toggle_"))
    application.add_handler(CallbackQueryHandler(copy_remove_wallet, pattern="^copy_remove_"))
    application.add_handler(CallbackQueryHandler(copy_settings, pattern="^copy_settings$"))
    application.add_handler(CallbackQueryHandler(copy_history, pattern="^copy_history$"))
    
    application.add_handler(CallbackQueryHandler(limit_orders_menu, pattern="^menu_limit_orders$"))
    application.add_handler(CallbackQueryHandler(limit_create, pattern="^limit_create$"))
    application.add_handler(CallbackQueryHandler(limit_buy_new, pattern="^limit_buy_new$"))
    application.add_handler(CallbackQueryHandler(limit_sell_new, pattern="^limit_sell_new$"))
    application.add_handler(CallbackQueryHandler(limit_sell_pos_select, pattern="^limit_sell_pos_"))
    application.add_handler(CallbackQueryHandler(limit_execute, pattern="^limit_execute$"))
    application.add_handler(CallbackQueryHandler(limit_list, pattern="^limit_list$"))
    application.add_handler(CallbackQueryHandler(limit_cancel, pattern="^limit_cancel$"))
    
    application.add_handler(CallbackQueryHandler(auto_sell_menu, pattern="^menu_auto_sell$"))
    application.add_handler(CallbackQueryHandler(autosell_add, pattern="^autosell_add$"))
    application.add_handler(CallbackQueryHandler(autosell_pos_select, pattern="^autosell_pos_"))
    application.add_handler(CallbackQueryHandler(autosell_type_select, pattern="^autosell_type_"))
    application.add_handler(CallbackQueryHandler(autosell_execute, pattern="^autosell_execute$"))
    application.add_handler(CallbackQueryHandler(autosell_list, pattern="^autosell_list$"))
    application.add_handler(CallbackQueryHandler(autosell_cancel, pattern="^autosell_cancel$"))
    application.add_handler(CallbackQueryHandler(autosell_remove, pattern="^autosell_remove_"))
    
    application.add_handler(CallbackQueryHandler(settings_menu, pattern="^menu_settings$"))
    application.add_handler(CallbackQueryHandler(settings_slippage, pattern="^settings_slippage$"))
    application.add_handler(CallbackQueryHandler(slippage_selected, pattern="^slippage_"))
    application.add_handler(CallbackQueryHandler(settings_priority_fee, pattern="^settings_priority_fee$"))
    application.add_handler(CallbackQueryHandler(priority_fee_selected, pattern="^priority_"))
    application.add_handler(CallbackQueryHandler(settings_notifications, pattern="^settings_notifications$"))
    application.add_handler(CallbackQueryHandler(settings_security, pattern="^settings_security$"))
    application.add_handler(CallbackQueryHandler(settings_export_key, pattern="^settings_export_key$"))
    application.add_handler(CallbackQueryHandler(settings_delete_account, pattern="^settings_delete_account$"))
    application.add_handler(CallbackQueryHandler(settings_delete_confirm, pattern="^settings_delete_confirm$"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()