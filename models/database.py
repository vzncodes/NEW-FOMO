import sqlite3
import json
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime
from config.settings import config
import threading


@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: bool = False
    captcha_code: Optional[str] = None
    captcha_expires: Optional[datetime] = None
    wallet_address: Optional[str] = None
    private_key_encrypted: Optional[str] = None
    sol_balance: float = 0.0
    usd_balance: float = 0.0
    settings: str = "{}"
    created_at: datetime = None
    updated_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def get_settings(self) -> dict:
        return json.loads(self.settings) if self.settings else {}
    
    def set_settings(self, settings: dict):
        self.settings = json.dumps(settings)
        self.updated_at = datetime.now()


@dataclass
class Position:
    id: Optional[int] = None
    user_id: int = 0
    token_mint: str = ""
    token_symbol: str = ""
    token_name: str = ""
    amount: float = 0.0
    entry_price_sol: float = 0.0
    entry_price_usd: float = 0.0
    current_price_sol: float = 0.0
    current_price_usd: float = 0.0
    pnl_sol: float = 0.0
    pnl_usd: float = 0.0
    pnl_percent: float = 0.0
    tx_signature: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    is_closed: bool = False
    closed_at: Optional[datetime] = None
    exit_price_sol: float = 0.0
    exit_price_usd: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class Transaction:
    id: Optional[int] = None
    user_id: int = 0
    tx_type: str = ""
    token_mint: str = ""
    token_symbol: str = ""
    amount: float = 0.0
    price_sol: float = 0.0
    price_usd: float = 0.0
    sol_amount: float = 0.0
    tx_signature: str = ""
    status: str = "pending"
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class CopyTradeWallet:
    id: Optional[int] = None
    user_id: int = 0
    wallet_address: str = ""
    wallet_name: str = ""
    is_active: bool = True
    buy_percentage: float = 100.0
    sell_percentage: float = 100.0
    max_buy_sol: float = 1.0
    min_buy_sol: float = 0.01
    created_at: datetime = None
    last_trade_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class LimitOrder:
    id: Optional[int] = None
    user_id: int = 0
    token_mint: str = ""
    token_symbol: str = ""
    side: str = ""
    target_price_sol: float = 0.0
    target_price_usd: float = 0.0
    amount: float = 0.0
    sol_amount: float = 0.0
    is_active: bool = True
    is_triggered: bool = False
    created_at: datetime = None
    triggered_at: Optional[datetime] = None
    tx_signature: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AutoSellRule:
    id: Optional[int] = None
    user_id: int = 0
    token_mint: str = ""
    token_symbol: str = ""
    rule_type: str = ""
    target_percent: float = 0.0
    stop_loss_percent: float = 0.0
    take_profit_percent: float = 0.0
    trailing_stop_percent: float = 0.0
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AdminNotification:
    id: Optional[int] = None
    user_id: int = 0
    username: str = ""
    action: str = ""
    details: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_verified BOOLEAN DEFAULT 0,
                captcha_code TEXT,
                captcha_expires TIMESTAMP,
                wallet_address TEXT,
                private_key_encrypted TEXT,
                sol_balance REAL DEFAULT 0,
                usd_balance REAL DEFAULT 0,
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token_mint TEXT,
                token_symbol TEXT,
                token_name TEXT,
                amount REAL,
                entry_price_sol REAL,
                entry_price_usd REAL,
                current_price_sol REAL,
                current_price_usd REAL,
                pnl_sol REAL,
                pnl_usd REAL,
                pnl_percent REAL,
                tx_signature TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_closed BOOLEAN DEFAULT 0,
                closed_at TIMESTAMP,
                exit_price_sol REAL,
                exit_price_usd REAL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tx_type TEXT,
                token_mint TEXT,
                token_symbol TEXT,
                amount REAL,
                price_sol REAL,
                price_usd REAL,
                sol_amount REAL,
                tx_signature TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS copy_trade_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                wallet_address TEXT,
                wallet_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                buy_percentage REAL DEFAULT 100,
                sell_percentage REAL DEFAULT 100,
                max_buy_sol REAL DEFAULT 1,
                min_buy_sol REAL DEFAULT 0.01,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_trade_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS limit_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token_mint TEXT,
                token_symbol TEXT,
                side TEXT,
                target_price_sol REAL,
                target_price_usd REAL,
                amount REAL,
                sol_amount REAL,
                is_active BOOLEAN DEFAULT 1,
                is_triggered BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                tx_signature TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_sell_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token_mint TEXT,
                token_symbol TEXT,
                rule_type TEXT,
                target_percent REAL,
                stop_loss_percent REAL,
                take_profit_percent REAL,
                trailing_stop_percent REAL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def get_user(self, user_id: int) -> Optional[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return User(**dict(row))
        return None
    
    def create_user(self, user: User) -> User:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, is_verified, 
                              captcha_code, captcha_expires, wallet_address, private_key_encrypted,
                              sol_balance, usd_balance, settings, created_at, updated_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user.user_id, user.username, user.first_name, user.last_name, user.is_verified,
              user.captcha_code, user.captcha_expires, user.wallet_address, user.private_key_encrypted,
              user.sol_balance, user.usd_balance, user.settings, user.created_at, user.updated_at, user.last_activity))
        self.conn.commit()
        return user
    
    def update_user(self, user: User):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET username=?, first_name=?, last_name=?, is_verified=?,
                            captcha_code=?, captcha_expires=?, wallet_address=?, private_key_encrypted=?,
                            sol_balance=?, usd_balance=?, settings=?, updated_at=?, last_activity=?
            WHERE user_id=?
        """, (user.username, user.first_name, user.last_name, user.is_verified,
              user.captcha_code, user.captcha_expires, user.wallet_address, user.private_key_encrypted,
              user.sol_balance, user.usd_balance, user.settings, user.updated_at, user.last_activity, user.user_id))
        self.conn.commit()
    
    def add_position(self, position: Position) -> Position:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO positions (user_id, token_mint, token_symbol, token_name, amount,
                                  entry_price_sol, entry_price_usd, current_price_sol, current_price_usd,
                                  pnl_sol, pnl_usd, pnl_percent, tx_signature, created_at, updated_at,
                                  is_closed, closed_at, exit_price_sol, exit_price_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (position.user_id, position.token_mint, position.token_symbol, position.token_name, position.amount,
              position.entry_price_sol, position.entry_price_usd, position.current_price_sol, position.current_price_usd,
              position.pnl_sol, position.pnl_usd, position.pnl_percent, position.tx_signature, 
              position.created_at, position.updated_at, position.is_closed, position.closed_at,
              position.exit_price_sol, position.exit_price_usd))
        position.id = cursor.lastrowid
        self.conn.commit()
        return position
    
    def get_positions(self, user_id: int, active_only: bool = True) -> List[Position]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM positions WHERE user_id = ?"
        if active_only:
            query += " AND is_closed = 0"
        query += " ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        return [Position(**dict(row)) for row in cursor.fetchall()]
    
    def update_position(self, position: Position):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE positions SET amount=?, current_price_sol=?, current_price_usd=?,
                                pnl_sol=?, pnl_usd=?, pnl_percent=?, updated_at=?,
                                is_closed=?, closed_at=?, exit_price_sol=?, exit_price_usd=?
            WHERE id=?
        """, (position.amount, position.current_price_sol, position.current_price_usd,
              position.pnl_sol, position.pnl_usd, position.pnl_percent, position.updated_at,
              position.is_closed, position.closed_at, position.exit_price_sol, position.exit_price_usd, position.id))
        self.conn.commit()
    
    def add_transaction(self, tx: Transaction) -> Transaction:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, tx_type, token_mint, token_symbol, amount,
                                     price_sol, price_usd, sol_amount, tx_signature, status, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx.user_id, tx.tx_type, tx.token_mint, tx.token_symbol, tx.amount,
              tx.price_sol, tx.price_usd, tx.sol_amount, tx.tx_signature, tx.status, tx.created_at, tx.completed_at))
        tx.id = cursor.lastrowid
        self.conn.commit()
        return tx
    
    def update_transaction(self, tx: Transaction):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE transactions SET status=?, completed_at=?, tx_signature=?
            WHERE id=?
        """, (tx.status, tx.completed_at, tx.tx_signature, tx.id))
        self.conn.commit()
    
    def get_transactions(self, user_id: int, limit: int = 50) -> List[Transaction]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
        return [Transaction(**dict(row)) for row in cursor.fetchall()]
    
    def add_copy_trade_wallet(self, wallet: CopyTradeWallet) -> CopyTradeWallet:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO copy_trade_wallets (user_id, wallet_address, wallet_name, is_active,
                                           buy_percentage, sell_percentage, max_buy_sol, min_buy_sol, created_at, last_trade_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (wallet.user_id, wallet.wallet_address, wallet.wallet_name, wallet.is_active,
              wallet.buy_percentage, wallet.sell_percentage, wallet.max_buy_sol, wallet.min_buy_sol,
              wallet.created_at, wallet.last_trade_at))
        wallet.id = cursor.lastrowid
        self.conn.commit()
        return wallet
    
    def get_copy_trade_wallets(self, user_id: int) -> List[CopyTradeWallet]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM copy_trade_wallets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [CopyTradeWallet(**dict(row)) for row in cursor.fetchall()]
    
    def update_copy_trade_wallet(self, wallet: CopyTradeWallet):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE copy_trade_wallets SET wallet_name=?, is_active=?, buy_percentage=?,
                                         sell_percentage=?, max_buy_sol=?, min_buy_sol=?, last_trade_at=?
            WHERE id=?
        """, (wallet.wallet_name, wallet.is_active, wallet.buy_percentage, wallet.sell_percentage,
              wallet.max_buy_sol, wallet.min_buy_sol, wallet.last_trade_at, wallet.id))
        self.conn.commit()
    
    def delete_copy_trade_wallet(self, wallet_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM copy_trade_wallets WHERE id = ?", (wallet_id,))
        self.conn.commit()
    
    def add_limit_order(self, order: LimitOrder) -> LimitOrder:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO limit_orders (user_id, token_mint, token_symbol, side, target_price_sol,
                                     target_price_usd, amount, sol_amount, is_active, is_triggered,
                                     created_at, triggered_at, tx_signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order.user_id, order.token_mint, order.token_symbol, order.side, order.target_price_sol,
              order.target_price_usd, order.amount, order.sol_amount, order.is_active, order.is_triggered,
              order.created_at, order.triggered_at, order.tx_signature))
        order.id = cursor.lastrowid
        self.conn.commit()
        return order
    
    def get_limit_orders(self, user_id: int, active_only: bool = True) -> List[LimitOrder]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM limit_orders WHERE user_id = ?"
        if active_only:
            query += " AND is_active = 1 AND is_triggered = 0"
        query += " ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        return [LimitOrder(**dict(row)) for row in cursor.fetchall()]
    
    def update_limit_order(self, order: LimitOrder):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE limit_orders SET is_active=?, is_triggered=?, triggered_at=?, tx_signature=?
            WHERE id=?
        """, (order.is_active, order.is_triggered, order.triggered_at, order.tx_signature, order.id))
        self.conn.commit()
    
    def add_auto_sell_rule(self, rule: AutoSellRule) -> AutoSellRule:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO auto_sell_rules (user_id, token_mint, token_symbol, rule_type,
                                        target_percent, stop_loss_percent, take_profit_percent,
                                        trailing_stop_percent, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule.user_id, rule.token_mint, rule.token_symbol, rule.rule_type,
              rule.target_percent, rule.stop_loss_percent, rule.take_profit_percent,
              rule.trailing_stop_percent, rule.is_active, rule.created_at))
        rule.id = cursor.lastrowid
        self.conn.commit()
        return rule
    
    def get_auto_sell_rules(self, user_id: int) -> List[AutoSellRule]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM auto_sell_rules WHERE user_id = ? AND is_active = 1", (user_id,))
        return [AutoSellRule(**dict(row)) for row in cursor.fetchall()]
    
    def delete_auto_sell_rule(self, rule_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE auto_sell_rules SET is_active = 0 WHERE id = ?", (rule_id,))
        self.conn.commit()
    
    def add_admin_notification(self, notification: AdminNotification):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO admin_notifications (user_id, username, action, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (notification.user_id, notification.username, notification.action, notification.details, notification.created_at))
        self.conn.commit()
    
    def get_all_users(self) -> List[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [User(**dict(row)) for row in cursor.fetchall()]


db = Database()