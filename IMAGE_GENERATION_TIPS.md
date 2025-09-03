# 圖片生成優化指南

## 問題分析

從日誌看到，Gemini API 成功回應（HTTP 200），但只返回文字而不是圖片：

```
Final text_response: 沒問題，這是您要的圖片：
Final image_url: None
```

這表示模型理解了請求，但選擇只提供文字描述而不生成實際圖片。

## 改進策略

### 1. 優化提示詞（已實作）

現在程式會嘗試不同的提示策略：

**第一次嘗試：**
```
Create a detailed image showing: {prompt}. Generate actual visual content, not just description.
```

**重試時：**
```
Generate a high-quality photograph of: {prompt}
Create visual artwork depicting: {prompt}
```

### 2. 具體描述建議

**❌ 不好的描述：**
- "做一個台灣太太上菜市場買菜的照片"
- "畫一隻貓"
- "美麗的風景"

**✅ 好的描述：**
- "A middle-aged Taiwanese woman carrying a basket, selecting fresh vegetables at a traditional market with colorful stalls"
- "A fluffy orange tabby cat sitting on a wooden fence in bright sunlight"
- "Mountain landscape at sunset with dramatic clouds and reflection in a lake"

### 3. 描述技巧

**包含具體元素：**
- 主題（人物、物件、場景）
- 環境背景
- 色彩、光線
- 風格（照片、繪畫、卡通等）
- 情緒或氛圍

**範例改寫：**

原始：`做一個台灣太太上菜市場買菜的照片`

優化：
```
!image A Taiwanese housewife in her 40s with short hair, wearing casual clothes, holding a shopping basket, selecting fresh vegetables at a vibrant traditional market with red lanterns and various colorful food stalls, warm natural lighting, realistic photography style
```

### 4. 語言選擇

**英文通常效果更好：**
- Gemini 的訓練資料中英文描述更豐富
- 英文描述更精確
- 藝術和攝影術語主要是英文

### 5. 提示詞範本

**人物照片：**
```
!image A [年齡] [性別] [外觀描述], [動作], [環境], [光線], [風格]
```

**風景照片：**
```
!image [地點] landscape with [特色], [天氣/時間], [色彩], [風格]
```

**物件照片：**
```
!image Close-up of [物件], [材質/顏色], [背景], [光線], [風格]
```

## 成功範例

### 人物類
```
!image A young woman with long black hair reading a book in a cozy café, warm golden lighting, realistic portrait photography
```

### 動物類
```
!image A golden retriever running through a field of sunflowers, blue sky background, vibrant colors, action photography
```

### 風景類
```
!image Japanese garden with cherry blossoms, stone bridge over a pond, morning mist, peaceful atmosphere, artistic photography
```

### 食物類
```
!image Traditional Taiwanese beef noodle soup in a white bowl, steaming hot, garnished with scallions, restaurant setting, food photography
```

## 故障排除

### 如果仍然只返回文字：

1. **簡化描述**：移除過於複雜的描述
2. **更換風格**：嘗試 "illustration", "painting", "artwork" 而不是 "photography"
3. **英文描述**：用英文重新描述
4. **等待重試**：系統有自動重試機制

### 檢查項目：

- ✅ 描述是否具體明確？
- ✅ 是否包含視覺元素？
- ✅ 語言是否清晰？
- ✅ 是否避免了敏感內容？

## 系統改進（已實作）

- ✅ 多重提示策略
- ✅ 自動重試機制
- ✅ 更好的錯誤訊息
- ✅ 英文提示詞優化
