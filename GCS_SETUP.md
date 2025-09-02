# Google Cloud Storage 設定指南

## 圖片生成功能需要 Google Cloud Storage 來儲存和提供圖片 URL

### 1. 建立 Google Cloud Project
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用 Cloud Storage API

### 2. 建立 Storage Bucket
1. 在 Google Cloud Console 中，前往 "Storage" > "Browser"
2. 點擊 "CREATE BUCKET"
3. 設定 bucket 名稱（例如：`your-linebot-images`）
4. 選擇地區（建議選擇亞洲地區以降低延遲）
5. 設定存取控制為 "Fine-grained"
6. 點擊 "CREATE"

### 3. 設定 Bucket 權限
1. 選擇剛建立的 bucket
2. 前往 "PERMISSIONS" 分頁
3. 點擊 "ADD PRINCIPAL"
4. 在 "New principals" 欄位輸入：`allUsers`
5. 在 "Role" 選擇 "Storage Object Viewer"
6. 點擊 "SAVE"

### 4. 建立服務帳戶
1. 前往 "IAM & Admin" > "Service Accounts"
2. 點擊 "CREATE SERVICE ACCOUNT"
3. 輸入服務帳戶名稱（例如：`linebot-storage`）
4. 點擊 "CREATE AND CONTINUE"
5. 在 "Grant this service account access to project" 中，選擇角色：
   - "Storage Admin" 或 "Storage Object Admin"
6. 點擊 "CONTINUE" 然後 "DONE"

### 5. 下載服務帳戶金鑰
1. 在服務帳戶列表中，點擊剛建立的服務帳戶
2. 前往 "KEYS" 分頁
3. 點擊 "ADD KEY" > "Create new key"
4. 選擇 "JSON" 格式
5. 點擊 "CREATE" 下載金鑰檔案
6. 將金鑰檔案放在安全的位置

### 6. 設定環境變數
在你的 `.env` 檔案中添加：
```bash
# 你的 bucket 名稱
GCS_BUCKET_NAME=your-linebot-images

# 服務帳戶金鑰檔案的路徑
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

### 7. 測試設定
啟動 LINE Bot 後，嘗試使用圖片生成指令：
```
!畫圖 可愛的貓咪在花園裡玩耍
```

### 注意事項
- 確保服務帳戶有足夠的權限存取 Storage bucket
- Bucket 必須設定為公開讀取，才能讓 LINE 存取圖片
- 建議設定 bucket 的生命週期規則，定期清理舊圖片以控制成本
- 圖片會儲存在 `linebot_images/` 資料夾下

### 費用估算
- Google Cloud Storage 的費用很低
- 每月前 5GB 免費
- 之後每 GB 約 $0.02 USD/月
- 網路傳輸費用約 $0.12 USD/GB

### 替代方案
如果不想使用 Google Cloud Storage，也可以考慮：
- AWS S3
- imgur API
- 其他免費圖片託管服務

但需要相應修改程式碼中的上傳邏輯。
