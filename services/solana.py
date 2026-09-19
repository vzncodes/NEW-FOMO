import base64
import json
import os
import asyncio
import aiohttp
from typing import Optional, Dict, List, Tuple
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.hash import Hash
from solders.system_program import transfer, TransferParams
from solders.instruction import Instruction, AccountMeta
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit
from config.settings import config
from models.database import db, Transaction, Position
from cryptography.fernet import Fernet
import logging
from mnemonic import Mnemonic

logger = logging.getLogger(__name__)

ENCRYPTION_KEY = config.ENCRYPTION_KEY.encode() if isinstance(config.ENCRYPTION_KEY, str) else config.ENCRYPTION_KEY
cipher = Fernet(base64.urlsafe_b64encode(ENCRYPTION_KEY[:32].ljust(32, b'=')))

mnemo = Mnemonic("english")

# SPL Token constants
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")


def get_associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """Derive associated token address (ATA) for owner/mint"""
    seeds = [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
    ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
    return ata


def create_associated_token_account_instruction(
    payer: Pubkey, owner: Pubkey, mint: Pubkey
) -> Instruction:
    """Create instruction to create associated token account"""
    ata = get_associated_token_address(owner, mint)
    keys = [
        AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
        AccountMeta(pubkey=ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
        AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=Pubkey.from_string("11111111111111111111111111111111"), is_signer=False, is_writable=False),  # System Program
    ]
    # ATA create instruction: discriminator + no data
    data = bytes([1])  # Create instruction discriminator
    return Instruction(
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
        accounts=keys,
        data=data
    )


class SolanaService:
    def __init__(self):
        self.rpc_url = config.SOLANA_RPC_URL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def rpc_call(self, method: str, params: list = None) -> dict:
        session = await self.get_session()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        async with session.post(self.rpc_url, json=payload) as resp:
            return await resp.json()
    
    def generate_wallet(self) -> Tuple[str, str]:
        keypair = Keypair()
        pubkey = str(keypair.pubkey())
        private_key = base64.b64encode(bytes(keypair)).decode()
        return pubkey, private_key
    
    def encrypt_private_key(self, private_key: str) -> str:
        return cipher.encrypt(private_key.encode()).decode()
    
    def decrypt_private_key(self, encrypted_key: str) -> str:
        return cipher.decrypt(encrypted_key.encode()).decode()
    
    def get_keypair_from_private_key(self, private_key: str) -> Keypair:
        key_bytes = base64.b64decode(private_key)
        return Keypair.from_bytes(key_bytes)
    
    def get_keypair_from_seed_phrase(self, seed_phrase: str) -> Keypair:
        seed = mnemo.to_seed(seed_phrase, passphrase="")
        return Keypair.from_seed(seed[:32])
    
    async def get_sol_balance(self, address: str) -> float:
        try:
            result = await self.rpc_call("getBalance", [address, {"commitment": "confirmed"}])
            lamports = result.get("result", {}).get("value", 0)
            return lamports / 1_000_000_000
        except Exception as e:
            logger.error(f"Error getting SOL balance: {e}")
            return 0.0
    
    async def get_token_accounts(self, address: str) -> List[dict]:
        try:
            result = await self.rpc_call("getTokenAccountsByOwner", [
                address,
                {"programId": str(TOKEN_PROGRAM_ID)},
                {"encoding": "jsonParsed", "commitment": "confirmed"}
            ])
            accounts = []
            for acc in result.get("result", {}).get("value", []):
                parsed = acc.get("account", {}).get("data", {}).get("parsed", {})
                info = parsed.get("info", {})
                mint = info.get("mint", "")
                amount = int(info.get("tokenAmount", {}).get("amount", "0"))
                decimals = info.get("tokenAmount", {}).get("decimals", 0)
                if amount > 0:
                    accounts.append({
                        "mint": mint,
                        "amount": amount / (10 ** decimals),
                        "raw_amount": amount,
                        "decimals": decimals
                    })
            return accounts
        except Exception as e:
            logger.error(f"Error getting token accounts: {e}")
            return []
    
    async def get_token_price(self, token_mint: str) -> Tuple[float, float]:
        try:
            session = await self.get_session()
            url = f"{config.JUPITER_API_URL}/price?ids={token_mint}"
            async with session.get(url) as resp:
                data = await resp.json()
                price_data = data.get("data", {}).get(token_mint, {})
                price_usd = price_data.get("price", 0)
                price_sol = price_data.get("priceSol", 0)
                return price_sol, price_usd
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return 0.0, 0.0
    
    async def get_sol_price_usd(self) -> float:
        try:
            session = await self.get_session()
            url = f"{config.JUPITER_API_URL}/price?ids=So11111111111111111111111111111111111111112"
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("data", {}).get("So11111111111111111111111111111111111111112", {}).get("price", 0)
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return 0.0
    
    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int, slippage: float = 1.0) -> Optional[dict]:
        try:
            session = await self.get_session()
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": int(slippage * 100),
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "true"
            }
            url = f"{config.JUPITER_API_URL}/quote"
            async with session.get(url, params=params) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return None
    
    async def get_jupiter_swap_transaction(self, quote: dict, user_public_key: str, priority_fee: float = 0.0005) -> Optional[str]:
        try:
            session = await self.get_session()
            payload = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": int(priority_fee * 1_000_000_000),
                "asLegacyTransaction": True
            }
            url = f"{config.JUPITER_SWAP_API_URL}"
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                return data.get("swapTransaction")
        except Exception as e:
            logger.error(f"Error getting Jupiter swap transaction: {e}")
            return None
    
    async def send_transaction(self, signed_tx: VersionedTransaction) -> Optional[str]:
        try:
            tx_bytes = bytes(signed_tx)
            tx_b64 = base64.b64encode(tx_bytes).decode()
            result = await self.rpc_call("sendTransaction", [tx_b64, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}])
            return result.get("result")
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            return None
    
    async def confirm_transaction(self, signature: str) -> bool:
        try:
            result = await self.rpc_call("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])
            status = result.get("result", {}).get("value", [None])[0]
            if status and status.get("confirmationStatus") in ["confirmed", "finalized"]:
                return True
            return False
        except Exception as e:
            logger.error(f"Error confirming transaction: {e}")
            return False
    
    async def execute_swap(self, user_id: int, private_key: str, input_mint: str, output_mint: str, 
                          amount: float, slippage: float, priority_fee: float, 
                          tx_type: str, token_symbol: str) -> Tuple[bool, str, dict]:
        try:
            keypair = self.get_keypair_from_private_key(private_key)
            user_pubkey = str(keypair.pubkey())
            
            input_decimals = 9 if input_mint == "So11111111111111111111111111111111111111112" else 6
            amount_lamports = int(amount * (10 ** input_decimals))
            
            quote = await self.get_jupiter_quote(input_mint, output_mint, amount_lamports, slippage)
            if not quote:
                return False, "Failed to get quote", {}
            
            swap_tx_b64 = await self.get_jupiter_swap_transaction(quote, user_pubkey, priority_fee)
            if not swap_tx_b64:
                return False, "Failed to get swap transaction", {}
            
            tx_bytes = base64.b64decode(swap_tx_b64)
            transaction = VersionedTransaction.from_bytes(tx_bytes)
            
            message_bytes = bytes(transaction.message)
            signature = keypair.sign_message(message_bytes)
            signed_tx = VersionedTransaction(transaction.message, [signature])
            
            tx_signature = await self.send_transaction(signed_tx)
            if not tx_signature:
                return False, "Failed to send transaction", {}
            
            confirmed = await self.confirm_transaction(tx_signature)
            if not confirmed:
                return False, "Transaction not confirmed", {"signature": tx_signature}
            
            tx = Transaction(
                user_id=user_id,
                tx_type=tx_type,
                token_mint=output_mint if tx_type == "buy" else input_mint,
                token_symbol=token_symbol,
                amount=amount,
                price_sol=0,
                price_usd=0,
                sol_amount=amount if input_mint == "So11111111111111111111111111111111111111112" else 0,
                tx_signature=tx_signature,
                status="confirmed" if confirmed else "pending"
            )
            db.add_transaction(tx)
            
            return True, tx_signature, {"quote": quote}
            
        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            return False, str(e), {}


solana_service = SolanaService()
