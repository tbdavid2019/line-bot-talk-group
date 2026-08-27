#!/usr/bin/env python3
import os
from dotenv import load_dotenv
try:
    from firebase import firebase
except ImportError:
    firebase = None

load_dotenv()

firebase_url = os.getenv('FIREBASE_URL')
print(f"Firebase URL: {firebase_url}")

# 嘗試載入認證憑證
cred_path = os.getenv('FIREBASE_CREDENTIALS') or os.getenv('FIREBASE_KEY_PATH')
if not cred_path or not os.path.exists(cred_path):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    key_dir = os.path.join(base_dir, 'key')
    if os.path.exists(key_dir):
        json_files = [os.path.join(key_dir, f) for f in os.listdir(key_dir) if f.endswith('.json')]
        if json_files:
            cred_path = json_files[0]

auth_obj = None
if cred_path and os.path.exists(cred_path):
    from google.oauth2 import service_account
    import google.auth.transport.requests

    class FirebaseServiceAccountAuth:
        def __init__(self, path):
            self.credentials = service_account.Credentials.from_service_account_file(
                path,
                scopes=[
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/firebase.database'
                ]
            )
        def get_access_token(self):
            if not self.credentials.valid:
                req = google.auth.transport.requests.Request()
                self.credentials.refresh(req)
            return self.credentials.token

    auth_obj = FirebaseServiceAccountAuth(cred_path)
    print(f"Using Firebase Service Account key: {cred_path}")
elif os.getenv('FIREBASE_SECRET'):
    auth_obj = os.getenv('FIREBASE_SECRET')
    print("Using FIREBASE_SECRET")

if __name__ == "__main__":
    if not firebase:
        print("Firebase module not installed, skipping.")
        exit(0)

    # 建立 Firebase 連接
    fdb = firebase.FirebaseApplication(firebase_url, auth_obj)

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
