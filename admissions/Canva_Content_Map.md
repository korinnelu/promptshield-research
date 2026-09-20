# PromptShield — Canva Content Map

目標：把 Research Brief 壓成 **3 頁教授可快速掃完的研究型作品**。

---

## Page 1 — Research Question & Architecture

### 視覺主旨

教授在 20–30 秒內必須知道：

1. 你研究的不是「做一個聊天機器人」；
2. 你區分 detection 與 actual security outcome；
3. 你有明確 RQ 與實驗流程。

### 建議版面

**上方 20%**
- 主標題
- 一句 thesis statement

建議主句：

> Detection performance 不等於 downstream security outcome；規避偵測，也不一定代表攻擊成功。

**中間 30%**
三個 Research Questions，橫向三格。

- RQ1 Obfuscation
- RQ2 Adaptive Evasion
- RQ3 Detection vs Leakage

每格最多 2 行中文。

**下方 50%**
放主架構圖：

```text
                    ┌→ Detector ─────→ Detection Outcome
Test Input ─────────┤
                    └→ Victim LLM ───→ Leakage Outcome
                                      ↓
                                  Evaluation

Adaptive only:
Seed → Detector Feedback → Red-Team Rewrite → Next Round
```

旁邊只列技術標籤：
- Gemini
- Llama 3.3 70B
- Python
- Streamlit
- quantitative evaluation

不要放大段技術棧。

---

## Page 2 — Experimental Design & Evidence

### 視覺主旨

教授要看到：

> 她知道如何設計比較，而不是只有跑模型。

### 左側 35%

放 Experimental Design 表：

- 60 fixed cases
- 20 benign（10 easy + 10 hard negatives）
- 20 overt direct attacks
- 20 covert/contextual direct attacks（10 medium + 10 hard）
- 2 detector conditions
- 3 repeated runs

下方小字：

**Primary metrics:** Precision, Recall, F1, FNR, Evasion Rate, Leakage Rate.

### 右側 65%

Research V2 跑完後放兩張圖：

**Figure A**
Recall by Attack Category

**Figure B**
Detection × Leakage matrix

目前 Canva 初稿可以先放灰色 placeholder：

> Research V2 experiment in progress

### 頁面底部

放一條很重要的 preliminary observation：

> Original 15-case PoC produced F1 = 1.0 for both detector prompts — revealing that the original benchmark was too small to discriminate between methods.

這句很重要，因為它把「舊實驗太簡單」轉化成研究反思能力。

---

## Page 3 — Failure Analysis & Research Reflection

### 視覺主旨

這頁不是展示成功，而是展示你會分析「為什麼方法不夠好」。

### 上半部：Failure Case

畫三階段：

```text
Explicit malicious request
        ↓
Business / compliance pretext
        ↓
Natural insider-style request
```

右邊：

```text
Detected
   ↓
Detected
   ↓
EVADED
```

但在 EVADED 旁放問號：

> Was the malicious objective still preserved?

這就是整頁的亮點。

### 中間：重新定義 attack success

大字：

> **Evasion ≠ Successful Attack**

下面：

```text
True Attack Success =
Evasion
AND Objective Preservation
AND Actual Leakage
```

### 下方左側：Methodological Improvement

- synthetic canary secrets
- fixed benchmark before testing
- category-level error analysis
- separate detection from leakage
- disclose that covert cases are still direct user-input attacks

### 下方右側：Limitations

只放四點：

- simulated victim
- limited benchmark size
- English-focused
- model dependence

### 最底一句

> 從完成一個系統，到重新質疑「我用什麼證據證明它有效」，是這個專案最重要的研究轉折。

---

## 全文件不要放的內容

- 大量 JSON dump
- 逐行程式碼
- 59 頁原作業式說明
- 未實作的 API / CI-CD 當作已完成成果
- 未校準的 confidence 當作機率
- “MITRE accuracy” 作為主結果
- “world-aware = 最新即時研究” 類型的過度宣稱

## 最終閱讀層級

### 30 秒
看到：
- Research Question
- Architecture
- Result headline

### 3 分鐘
理解：
- experiment design
- failure analysis
- limitations

### 有興趣才點 GitHub
看到：
- code
- fixed benchmark
- raw results
- experiment config
- reproducibility files
