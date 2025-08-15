#!/usr/bin/env python3
import os
from dotenv import load_dotenv

print("=== 環境變數檢查 ===")

# 檢查是否有 .env 檔案
if os.path.exists('.env'):
    print("✓ .env 檔案存在")
    load_dotenv()
else:
    print("✗ .env 檔案不存在")

# 檢查環境變數
required_vars = [
    'LINE_CHANNEL_SECRET',
    'LINE_CHANNEL_ACCESS_TOKEN', 
    'FIREBASE_URL',
    'GEMINI_API_KEY'
]

print("\n=== 環境變數狀態 ===")
for var in required_vars:
    value = os.getenv(var)
    if value:
        # 只顯示前幾個字符以保護隱私
        display_value = value[:8] + "..." if len(value) > 8 else value
        print(f"✓ {var}: {display_value}")
    else:
        print(f"✗ {var}: 未設定")

# 特別檢查 Channel Secret
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
if channel_secret:
    print(f"\n=== Channel Secret 詳細資訊 ===")
    print(f"長度: {len(channel_secret)}")
    print(f"內容: {channel_secret}")
    print(f"是否為32字符: {'✓' if len(channel_secret) == 32 else '✗'}")
else:
    print("\n✗ LINE_CHANNEL_SECRET 未設定")

print("\n=== API_ENV 設定 ===")
api_env = os.getenv('API_ENV', 'not_set')
print(f"API_ENV: {api_env}")
