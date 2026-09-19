import random
import string
from datetime import datetime, timedelta
from typing import Tuple
from config.settings import config
from models.database import db, User


class CaptchaService:
    def __init__(self):
        self.captcha_length = config.CAPTCHA_LENGTH
        self.timeout = config.CAPTCHA_TIMEOUT
    
    def generate_captcha(self) -> Tuple[str, str]:
        """Generate CAPTCHA code and return (code, display_text)"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=self.captcha_length))
        
        # Create a visual text representation using Unicode box drawing
        display = self._create_text_display(code)
        return code, display
    
    def _create_text_display(self, code: str) -> str:
        """Create a text-based visual CAPTCHA"""
        # Style 1: Boxed characters
        top = "┌" + "─" * (len(code) * 4 - 1) + "┐"
        middle = "│ " + " │ ".join(code) + " │"
        bottom = "└" + "─" * (len(code) * 4 - 1) + "┘"
        
        # Add some noise characters
        noise_chars = "░▒▓█▄▀▌▐▙▛▜▟▞▚▘▝▖▗"
        noise_line = "".join(random.choices(noise_chars, k=len(code) * 2))
        
        return (
            f"<pre>{top}</pre>\n"
            f"<pre>{middle}</pre>\n"
            f"<pre>{bottom}</pre>\n\n"
            f"<pre>{noise_line}</pre>\n\n"
            f"Enter the <b>{self.captcha_length} characters</b> above by tapping buttons below."
        )
    
    def set_captcha(self, user_id: int, code: str):
        user = db.get_user(user_id)
        if not user:
            user = User(user_id=user_id)
            db.create_user(user)
        
        user.captcha_code = code
        user.captcha_expires = datetime.now() + timedelta(seconds=self.timeout)
        db.update_user(user)
    
    def verify_captcha(self, user_id: int, input_code: str) -> bool:
        user = db.get_user(user_id)
        if not user or not user.captcha_code:
            return False
        
        if user.captcha_expires and datetime.now() > user.captcha_expires:
            return False
        
        if user.captcha_code.upper() == input_code.upper():
            user.is_verified = True
            user.captcha_code = None
            user.captcha_expires = None
            db.update_user(user)
            return True
        
        return False
    
    def is_verified(self, user_id: int) -> bool:
        user = db.get_user(user_id)
        return user and user.is_verified


captcha_service = CaptchaService()