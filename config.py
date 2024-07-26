# config.py
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')
    TPV_URL = os.getenv('TPV_URL', 'https://sis.redsys.es:25443/sis/realizarPago')  # URL de pruebas correcta
    TPV_MERCHANT_CODE = os.getenv('TPV_MERCHANT_CODE', '175780451')
    TPV_TERMINAL = os.getenv('TPV_TERMINAL', '1')
    TPV_SECRET_KEY = os.getenv('TPV_SECRET_KEY', 'nIkuxMD5qp50WnxxpyUvT+59xs/f2FUz')
    TPV_CURRENCY = '978'  # Euro
    TPV_TRANSACTION_TYPE = '0'  # Autorización
    TPV_CALLBACK_URL = os.getenv('TPV_CALLBACK_URL', 'https://www.salasax.com/callback')
