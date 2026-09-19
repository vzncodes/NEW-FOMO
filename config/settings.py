import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))
    
    SOLANA_RPC_URL: str = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    SOLANA_WS_URL: str = os.getenv("SOLANA_WS_URL", "wss://api.mainnet-beta.solana.com")
    
    JUPITER_API_URL: str = "https://quote-api.jup.ag/v6"
    JUPITER_SWAP_API_URL: str = "https://quote-api.jup.ag/v6/swap"
    
    CAPTCHA_LENGTH: int = 6
    CAPTCHA_TIMEOUT: int = 300
    
    MIN_DEPOSIT_SOL: float = 0.5
    MAX_DEPOSIT_SOL: float = 20.0
    
    DEFAULT_SLIPPAGE: float = 1.0
    DEFAULT_PRIORITY_FEE: float = 0.0005
    
    DATABASE_PATH: str = "bot_database.db"
    
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your-32-char-encryption-key-here!!")
    
    WELCOME_MEDIA_TYPE: str = os.getenv("WELCOME_MEDIA_TYPE", "none")  # none, photo, video
    WELCOME_MEDIA_URL: str = os.getenv("WELCOME_MEDIA_URL", "")  # URL or file path
    WELCOME_MEDIA_CAPTION: str = os.getenv("WELCOME_MEDIA_CAPTION", "")


config = Config()