import asyncio
import logging
from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from config.settings import config
from models.database import db, AdminNotification, User

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.admin_chat_id = config.ADMIN_CHAT_ID
        self._notification_queue = asyncio.Queue()
        self._running = False
    
    def set_bot(self, bot: Bot):
        self.bot = bot
    
    async def start(self):
        self._running = True
        asyncio.create_task(self._process_queue())
    
    async def stop(self):
        self._running = False
    
    async def _process_queue(self):
        while self._running:
            try:
                notification = await asyncio.wait_for(self._notification_queue.get(), timeout=1.0)
                await self._send_notification(notification)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}")
    
    async def _send_notification(self, notification: AdminNotification):
        if not self.bot or not self.admin_chat_id:
            return
        
        try:
            message = self._format_notification(notification)
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode="HTML"
            )
        except TelegramError as e:
            logger.error(f"Failed to send admin notification: {e}")
    
    def _format_notification(self, notification: AdminNotification) -> str:
        timestamp = notification.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"🔔 <b>New Activity</b>\n\n"
            f"👤 <b>User:</b> @{notification.username} (ID: {notification.user_id})\n"
            f"🎯 <b>Action:</b> {notification.action}\n"
            f"📝 <b>Details:</b> {notification.details}\n"
            f"🕒 <b>Time:</b> {timestamp}"
        )
    
    async def notify(self, user_id: int, username: str, action: str, details: str):
        notification = AdminNotification(
            user_id=user_id,
            username=username or "Unknown",
            action=action,
            details=details,
            created_at=datetime.now()
        )
        db.add_admin_notification(notification)
        await self._notification_queue.put(notification)
    
    async def notify_user_action(self, user_id: int, username: str, action: str, details: str = ""):
        await self.notify(user_id, username, action, details)
    
    async def notify_buy(self, user_id: int, username: str, token_symbol: str, amount_sol: float, token_amount: float, tx_signature: str):
        details = f"Bought {token_amount:.6f} {token_symbol} for {amount_sol:.4f} SOL\nTx: {tx_signature}"
        await self.notify(user_id, username, "🟢 BUY", details)
    
    async def notify_sell(self, user_id: int, username: str, token_symbol: str, amount_sol: float, token_amount: float, tx_signature: str):
        details = f"Sold {token_amount:.6f} {token_symbol} for {amount_sol:.4f} SOL\nTx: {tx_signature}"
        await self.notify(user_id, username, "🔴 SELL", details)
    
    async def notify_copy_trade(self, user_id: int, username: str, wallet_address: str, action: str, details: str):
        await self.notify(user_id, username, f"📋 COPY TRADE - {action}", f"Wallet: {wallet_address}\n{details}")
    
    async def notify_limit_order(self, user_id: int, username: str, token_symbol: str, side: str, target_price: float, amount: float):
        details = f"{side} {amount:.6f} {token_symbol} @ {target_price:.8f} SOL"
        await self.notify(user_id, username, "📊 LIMIT ORDER", details)
    
    async def notify_auto_sell(self, user_id: int, username: str, token_symbol: str, rule_type: str, details: str):
        await self.notify(user_id, username, f"⚡ AUTO SELL - {rule_type}", f"{token_symbol}: {details}")
    
    async def notify_wallet_deposit(self, user_id: int, username: str, amount_sol: float, tx_signature: str):
        details = f"Deposited {amount_sol:.4f} SOL\nTx: {tx_signature}"
        await self.notify(user_id, username, "💰 DEPOSIT", details)
    
    async def notify_wallet_withdraw(self, user_id: int, username: str, amount_sol: float, tx_signature: str):
        details = f"Withdrew {amount_sol:.4f} SOL\nTx: {tx_signature}"
        await self.notify(user_id, username, "📤 WITHDRAW", details)
    
    async def notify_wallet_import(self, user_id: int, username: str):
        await self.notify(user_id, username, "🔑 WALLET IMPORTED", "User imported a wallet")
    
    async def notify_wallet_connect(self, user_id: int, username: str, wallet_address: str):
        details = f"Connected wallet: {wallet_address}"
        await self.notify(user_id, username, "🔗 WALLET CONNECTED", details)
    
    async def notify_settings_change(self, user_id: int, username: str, setting: str, value: str):
        details = f"Changed {setting} to {value}"
        await self.notify(user_id, username, "⚙️ SETTINGS CHANGED", details)
    
    async def notify_new_user(self, user_id: int, username: str):
        await self.notify(user_id, username, "👋 NEW USER", "User started the bot")
    
    async def notify_verification(self, user_id: int, username: str):
        await self.notify(user_id, username, "✅ VERIFIED", "User passed CAPTCHA verification")


notification_service = NotificationService()