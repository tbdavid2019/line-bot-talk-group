# Firebase 設定說明

## 問題
目前遇到 `401 Unauthorized` 錯誤，這是因為 Firebase Realtime Database 的安全規則限制了匿名存取。

## 解決方案

### 選項1：設定 Firebase 安全規則（開發/測試用）

在 Firebase Console 中：
1. 進入 Firebase Console (https://console.firebase.google.com/)
2. 選擇你的專案 `groupsummary-bb6ae`
3. 點擊左側選單的 "Realtime Database"
4. 點擊 "Rules" 標籤
5. 將規則改為（**僅供開發測試使用**）：

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

**⚠️ 警告：這個設定允許任何人讀寫你的資料庫，只適合開發測試！**

### 選項2：使用 Firebase Admin SDK（推薦生產環境）

1. 在 Firebase Console 中創建服務帳戶
2. 下載私鑰 JSON 檔案
3. 使用 Firebase Admin SDK 進行驗證

### 選項3：設定更安全的規則

```json
{
  "rules": {
    "groups": {
      "$groupId": {
        ".read": true,
        ".write": true
      }
    },
    "users": {
      "$userId": {
        ".read": true,
        ".write": true
      }
    },
    "test": {
      ".read": true,
      ".write": true
    }
  }
}
```

## 目前的建議

為了快速測試，建議先使用選項1，之後再考慮更安全的方案。

## 設定步驟

1. 登入 Firebase Console
2. 選擇專案 `groupsummary-bb6ae`
3. Realtime Database → Rules
4. 貼上規則並發布

設定完成後，重新測試 Firebase 連接。
