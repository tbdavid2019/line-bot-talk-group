# 多群組處理機制說明

## 概述
這個 LINE Bot 可以同時在多個群組中運作，每個群組的對話記錄完全分離，不會相互混淆。

## 資料分離機制

### 1. 唯一識別碼
- **群組對話**：使用 LINE 提供的唯一 `group_id`
- **私人對話**：使用用戶的唯一 `user_id`  
- **聊天室對話**：使用 `room_id`

### 2. Firebase 資料結構
```
Firebase Realtime Database:
├── groups/
│   ├── {group_id_1}/
│   │   ├── messages/          # 群組1的對話記錄
│   │   └── info/             # 群組1的資訊（未來擴展）
│   ├── {group_id_2}/
│   │   ├── messages/          # 群組2的對話記錄
│   │   └── info/             # 群組2的資訊
│   └── ...
├── users/
│   ├── {user_id_1}/
│   │   └── messages/          # 用戶1的私人對話記錄
│   ├── {user_id_2}/
│   │   └── messages/          # 用戶2的私人對話記錄
│   └── ...
└── rooms/
    ├── {room_id_1}/
    │   └── messages/          # 聊天室1的對話記錄
    └── ...
```

### 3. 路徑範例
```python
# 群組A (group_id: "Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
path = "groups/Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/messages"

# 群組B (group_id: "Cyyyyyyyyyyyyyyyyyyyyyyyyyyy")  
path = "groups/Cyyyyyyyyyyyyyyyyyyyyyyyyyyy/messages"

# 私人對話 (user_id: "Uaaaaaaaaaaaaaaaaaaaaaaaaaaa")
path = "users/Uaaaaaaaaaaaaaaaaaaaaaaaaaaa/messages"
```

## 指令處理

### !摘要 指令
- 每個群組執行 `!摘要` 只會摘要該群組的對話記錄
- 私人對話執行 `!摘要` 只會摘要該用戶的私人對話記錄

### !清空 指令  
- 每個群組執行 `!清空` 只會清空該群組的對話記錄
- 不會影響其他群組或私人對話的記錄

## 日誌追蹤
程式會記錄每個操作的來源：
```
INFO: Processing GROUP message - Group ID: Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
INFO: Chat path: groups/Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/messages
```

這樣管理員可以清楚知道每個操作屬於哪個群組。

## 安全性
- 每個群組的 group_id 由 LINE 平台產生，保證唯一性
- 群組成員無法存取其他群組的對話記錄
- 私人對話記錄與群組記錄完全分離

## 擴展性
這個架構可以輕鬆支援：
- 無限數量的群組
- 群組資訊儲存（群組名稱、成員數等）
- 個別群組的設定（語言偏好、摘要風格等）
- 統計資訊（每個群組的使用量等）
