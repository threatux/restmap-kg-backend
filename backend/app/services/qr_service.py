"""
QR-код генератор для booking checkin/checkout
"""
import qrcode
import base64
from io import BytesIO
import json
from datetime import datetime


class QRService:
    
    @staticmethod
    def generate_booking_qr(booking_code: str, rest_point_id: int, tourist_id: int) -> str:
        """
        Генерирует QR-код для брони.
        Возвращает base64 PNG.
        """
        data = {
            "type": "tamgaflow_booking",
            "booking_code": booking_code,
            "rest_point_id": rest_point_id,
            "tourist_id": tourist_id,
            "issued_at": datetime.utcnow().isoformat(),
        }
        qr_content = json.dumps(data)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        
        base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"
    
    @staticmethod
    def parse_qr_data(qr_content: str) -> dict:
        """Парсит QR-данные"""
        try:
            return json.loads(qr_content)
        except json.JSONDecodeError:
            return {}