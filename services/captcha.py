import random
import string
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from config.settings import config
from models.database import db, User

class CaptchaService:
    def __init__(self):
        self.captcha_length = config.CAPTCHA_LENGTH
        self.timeout = config.CAPTCHA_TIMEOUT
    
    def generate_captcha(self) -> Tuple[str, bytes]:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=self.captcha_length))
        
        width = 280
        height = 100
        image = Image.new('RGB', (width, height), color=(25, 25, 35))
        draw = ImageDraw.Draw(image)
        
        for _ in range(50):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(random.randint(50, 100), random.randint(50, 100), random.randint(50, 100)), width=1)
        
        for _ in range(200):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(random.randint(80, 150), random.randint(80, 150), random.randint(80, 150)))
        
        try:
            font = ImageFont.truetype("arial.ttf", 42)
        except:
            font = ImageFont.load_default()
        
        char_width = width // self.captcha_length
        for i, char in enumerate(code):
            x = i * char_width + char_width // 4
            y = height // 4 + random.randint(-5, 5)
            color = (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))
            draw.text((x, y), char, font=font, fill=color)
        
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return code, buffer.getvalue()
    
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