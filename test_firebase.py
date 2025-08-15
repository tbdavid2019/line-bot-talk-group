#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from firebase import firebase

load_dotenv()

firebase_url = os.getenv('FIREBASE_URL')
print(f"Firebase URL: {firebase_url}")

# 建立 Firebase 連接
fdb = firebase.FirebaseApplication(firebase_url, None)

# 測試寫入 - 使用更具體的路徑
test_data = {'message': 'Hello Firebase!', 'timestamp': '2025-08-15'}

try:
    # 方法1：使用 post 方法（會自動生成 key）
    print("\n=== 測試 POST 方法 ===")
    result = fdb.post('/test/connection', test_data)
    print(f"POST result: {result}")
    
    # 方法2：使用 put 方法並指定具體的 key
    print("\n=== 測試 PUT 方法 ===")
    result = fdb.put('/test', 'connection_test', test_data)
    print(f"PUT result: {result}")
    
    # 測試讀取
    print("\n=== 測試讀取 ===")
    retrieved_data = fdb.get('/test', 'connection_test')
    print(f"Retrieved data: {retrieved_data}")
    
    # 測試讀取所有 test 資料
    all_test_data = fdb.get('/test', None)
    print(f"All test data: {all_test_data}")
    
    # 清理測試數據
    print("\n=== 清理測試數據 ===")
    fdb.delete('/test', 'connection_test')
    print("Test data cleaned up")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
