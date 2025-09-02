#!/usr/bin/env python3
"""
Google Cloud Storage 連接測試腳本
用於測試 GCS 配置是否正確
"""
import os
import sys
from datetime import datetime
from google.cloud import storage

# 載入環境變數
if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

def test_gcs_connection():
    """測試 Google Cloud Storage 連接"""
    
    # 檢查環境變數
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    print("=== Google Cloud Storage 連接測試 ===")
    print(f"Bucket 名稱: {bucket_name}")
    print(f"認證檔案路徑: {credentials_path}")
    
    if not bucket_name:
        print("❌ 錯誤: 未設定 GCS_BUCKET_NAME 環境變數")
        return False
        
    if not credentials_path:
        print("❌ 錯誤: 未設定 GOOGLE_APPLICATION_CREDENTIALS 環境變數")
        return False
        
    if not os.path.exists(credentials_path):
        print(f"❌ 錯誤: 認證檔案不存在: {credentials_path}")
        return False
    
    try:
        # 初始化 Storage client
        print("\n📡 正在連接 Google Cloud Storage...")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # 檢查 bucket 是否存在
        if bucket.exists():
            print(f"✅ 成功連接到 bucket: {bucket_name}")
        else:
            print(f"❌ Bucket 不存在: {bucket_name}")
            return False
            
        # 測試上傳檔案
        print("\n📤 測試檔案上傳...")
        test_content = f"測試檔案 - {datetime.now()}"
        test_filename = f"test_uploads/test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        blob = bucket.blob(test_filename)
        blob.upload_from_string(test_content)
        print(f"✅ 成功上傳測試檔案: {test_filename}")
        
        # 設定為公開讀取
        blob.make_public()
        public_url = blob.public_url
        print(f"✅ 檔案公開 URL: {public_url}")
        
        # 檢查檔案是否存在
        if blob.exists():
            print("✅ 確認檔案已上傳並存在")
        else:
            print("❌ 檔案上傳後無法找到")
            return False
            
        # 列出最近的檔案
        print("\n📋 列出最近上傳的檔案:")
        blobs = bucket.list_blobs(prefix="linebot_images/", max_results=5)
        blob_count = 0
        for blob in blobs:
            blob_count += 1
            print(f"  - {blob.name} (大小: {blob.size} bytes)")
            
        if blob_count == 0:
            print("  (沒有找到 linebot_images/ 資料夾中的檔案)")
        else:
            print(f"  共找到 {blob_count} 個檔案")
        
        # 清理測試檔案
        print(f"\n🗑️ 刪除測試檔案: {test_filename}")
        blob.delete()
        print("✅ 測試檔案已刪除")
        
        print("\n🎉 所有測試都通過！GCS 配置正確。")
        return True
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        print(f"詳細錯誤: {traceback.format_exc()}")
        return False

def test_gemini_connection():
    """測試 Gemini API 連接"""
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    print("\n=== Gemini API 連接測試 ===")
    print(f"API Key: {gemini_key[:10]}...{gemini_key[-5:] if gemini_key else 'None'}")
    
    if not gemini_key:
        print("❌ 錯誤: 未設定 GEMINI_API_KEY 環境變數")
        return False
        
    try:
        from google import genai
        from google.genai import types
        
        print("📡 正在測試 Gemini API...")
        client = genai.Client(api_key=gemini_key)
        
        # 測試簡單的文字生成
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="請回答：測試成功"),
                ],
            ),
        ]
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        
        print(f"✅ Gemini API 回應: {response.text[:100]}...")
        print("🎉 Gemini API 連接正常！")
        return True
        
    except Exception as e:
        print(f"❌ Gemini API 錯誤: {e}")
        return False

if __name__ == "__main__":
    print("開始測試...")
    
    gcs_ok = test_gcs_connection()
    gemini_ok = test_gemini_connection()
    
    print(f"\n=== 測試結果 ===")
    print(f"Google Cloud Storage: {'✅ 正常' if gcs_ok else '❌ 異常'}")
    print(f"Gemini API: {'✅ 正常' if gemini_ok else '❌ 異常'}")
    
    if gcs_ok and gemini_ok:
        print("\n🎉 所有服務都正常！可以使用圖片生成功能。")
        sys.exit(0)
    else:
        print("\n⚠️ 請檢查並修正上述問題後再試。")
        sys.exit(1)
