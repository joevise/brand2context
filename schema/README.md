# Brand2Context 品牌知识 Schema

## 设计原则

Schema 的设计以**消费者决策链路**为核心——消费者问 AI 关于一个品牌的问题，无非围绕以下几个阶段：

```
认知 → 了解 → 考虑 → 决策 → 购买 → 使用 → 推荐
"这是什么品牌？" → "它做什么？" → "跟XX比呢？" → "值不值得买？" → "去哪买？" → "怎么用？" → "好不好用？"
```

每个阶段对应不同的信息需求，Schema 覆盖所有阶段。

---

## Schema 总览

```
BrandKnowledge v0.3
├── identity          # 品牌身份 —— "你是谁"
├── offerings         # 产品/服务 —— "你卖什么"
├── differentiation   # 差异化 —— "你跟别人有什么不同"
├── trust             # 信任背书 —— "凭什么信你"
├── experience        # 用户体验 —— "用起来怎么样"
├── access            # 获取方式 —— "去哪买/怎么联系"
├── content           # 内容资产 —— "你说过什么"
├── perception        # 【新】品牌感知 —— "消费者心里你是什么样"
├── decision_factors  # 【新】决策因子 —— "买你要考虑什么"
├── vitality          # 【新】品牌活力 —— "你现在活得怎么样"
└── campaigns         # 【新】品牌活动 —— "你最近在做什么"
```

---

## 详细字段定义

### 1. identity（品牌身份）

消费者决策阶段：**认知**
CMO 关心：品牌定位是否被 AI 正确理解

```yaml
identity:
  name: "品牌名称"
  legal_name: "公司法律全称"
  founded: "成立年份"
  headquarters: "总部所在地"
  tagline: "品牌标语/Slogan"
  mission: "品牌使命"
  vision: "品牌愿景"
  values: ["核心价值观1", "核心价值观2"]
  positioning: "一句话定位（我们是做什么的，为谁服务）"
  category: "所属行业/品类"
  sub_categories: ["细分品类1", "细分品类2"]
  brand_story: "品牌故事（简述）"
  founder: "创始人信息"
  scale: "企业规模（员工数、营收量级等公开信息）"
```

**为什么这些最重要？** 当消费者问"XX 是什么品牌"时，AI 给出的第一句话决定了品牌的第一印象。positioning 和 tagline 是 CMO 花了最多钱去传播的东西，必须被 AI 准确引用。

---

### 2. offerings（产品/服务矩阵）

消费者决策阶段：**了解 → 考虑**
CMO 关心：核心产品是否被完整呈现、价格信息是否准确

```yaml
offerings:
  - name: "产品/服务名称"
    category: "产品线/品类"
    description: "一句话描述"
    key_features: ["特性1", "特性2", "特性3"]
    specs: # 关键参数（品类相关）
      - key: "参数名"
        value: "参数值"
    price_range: "价格区间"
    currency: "货币单位"
    target_audience: "目标人群"
    use_cases: ["使用场景1", "使用场景2"]
    is_flagship: true/false  # 是否主推产品
    launch_date: "上市时间"
    status: "在售/停产/即将上市"
```

**为什么这样设计？** 消费者问 AI "XX 品牌有什么产品"时，AI 需要按重要性排列。`is_flagship` 标记让 AI 知道该优先推荐什么。`target_audience` 和 `use_cases` 帮助 AI 做个性化推荐——"适合油皮的防晒霜有哪些品牌"。

---

### 3. differentiation（差异化定位）

消费者决策阶段：**考虑 → 决策**
CMO 关心：品牌的核心竞争优势是否被 AI 传达

```yaml
differentiation:
  unique_selling_points: ["USP1", "USP2", "USP3"]
  competitive_advantages: ["竞争优势1", "竞争优势2"]
  technology_highlights: ["技术亮点1", "技术亮点2"]
  patents_or_certifications: ["专利/认证1", "专利/认证2"]
  awards: 
    - name: "奖项名称"
      year: "获奖年份"
      issuer: "颁发机构"
  comparison_notes: "与竞品的关键差异点（品牌自述）"
```

**核心洞察：** 消费者决策的关键时刻是对比。"XX 和 YY 哪个好？" 是 AI 收到最多的品牌相关问题之一。如果你的差异化信息不在 AI 的知识里，AI 就只能瞎编或者偏向有数据的竞品。

---

### 4. trust（信任背书）

消费者决策阶段：**决策**
CMO 关心：社会证明和权威背书是否被 AI 知道

```yaml
trust:
  certifications: ["ISO认证", "有机认证", "FDA认证"]
  partnerships: ["合作伙伴1", "合作伙伴2"]
  media_coverage:
    - outlet: "媒体名称"
      title: "报道标题"
      date: "报道日期"
      url: "链接"
  investor_backed: "投资方信息（如有公开）"
  user_stats: # 用户数据（公开的）
    - metric: "注册用户"
      value: "1000万+"
    - metric: "服务客户"
      value: "500+"
  testimonials:
    - source: "来源（用户/媒体/KOL）"
      quote: "评价内容"
      verified: true/false
```

**传播学视角：** 信任的建立靠"第三方背书"而非品牌自说自话。AI 在回答"XX 品牌靠谱吗"时，如果能引用认证、媒体报道、用户数据，说服力远强于品牌官网的自我描述。这部分信息是 CMO 在 PR 上投入最多预算的地方。

---

### 5. experience（用户体验）

消费者决策阶段：**决策 → 使用**
CMO 关心：售后体验和用户口碑是否被 AI 正确反映

```yaml
experience:
  warranty: "保修政策"
  return_policy: "退换货政策"
  customer_service:
    channels: ["400电话", "在线客服", "微信"]
    hours: "服务时间"
  faq:
    - question: "常见问题"
      answer: "官方回答"
  onboarding: "新用户引导/上手说明"
  community: "用户社区链接"
```

**消费者行为洞察：** 售后体验是消费者"推荐 vs 不推荐"的分水岭。AI 被问"XX 品牌售后怎么样"时，如果没有结构化数据，就会去抓用户的负面评价。品牌主动提供 FAQ 和服务政策，是对叙事的主动控制。

---

### 6. access（获取方式）

消费者决策阶段：**购买**
CMO 关心：购买转化路径是否通畅

```yaml
access:
  official_website: "官网URL"
  online_stores:
    - platform: "天猫/京东/官网商城"
      url: "链接"
  offline_presence: "线下门店/柜台信息"
  contact:
    phone: "400电话"
    email: "客服邮箱"
    address: "公司地址"
  social_media:
    - platform: "微信公众号/抖音/小红书/微博"
      handle: "账号名"
      url: "链接"
  app: "App下载链接"
```

**广告学视角：** 再好的品牌认知，如果消费者不知道去哪买，就是漏斗断裂。AI 回答"在哪买 XX"时，必须能给出准确的购买渠道。这是最直接的转化信息。

---

### 7. content（内容资产）

消费者决策阶段：**全链路**
CMO 关心：品牌的内容资产被 AI 索引和引用

```yaml
content:
  latest_news:
    - title: "新闻标题"
      date: "日期"
      summary: "摘要"
      url: "链接"
  blog_posts:
    - title: "文章标题"
      date: "日期"
      summary: "摘要"
      url: "链接"
  key_announcements:
    - title: "重要公告"
      date: "日期"
      content: "内容"
  brand_guidelines_public: "品牌使用规范（如有公开）"
```

---

### 8. perception（品牌感知坐标）

消费者决策阶段：**考虑**
CMO 关心：品牌在消费者心智中的位置

```yaml
perception:
  personality_traits: ["真诚", "刺激", "能力", "精致", "粗犷"]  # Aaker品牌个性模型
  brand_tone: "沟通调性描述"
  price_positioning: "大众/中端/轻奢/高端/超高端"
  price_benchmark: "对标品牌或品类均价"
  primary_audience:
    demographics: "25-35岁，一二线城市，女性为主"
    psychographics: "追求品质但不盲目追奢"
    lifestyle: "生活方式描述"
  anti_audience: "明确不适合的人群"
  category_association: "品类心智占位强度"
  usage_occasions: ["使用场景1", "使用场景2"]
```

**为什么这些重要？** AI 做推荐时不只是对比参数，更在做"人 - 品牌匹配"。`personality_traits` 基于 Aaker 品牌个性模型，让 AI 理解品牌的"性格"；`anti_audience` 帮助 AI 做排除推荐（"这个品牌不太适合你"）；`price_positioning` 让 AI 在预算匹配时更精准。这些字段对应 Keller 品牌共鸣金字塔的右侧——品牌意象层。

---

### 9. decision_factors（决策因子权重）

消费者决策阶段：**决策**
CMO 关心：品牌在关键购买因子上的表现

```yaml
decision_factors:
  category_key_factors:
    - factor: "安全性"
      brand_score: "行业领先/优秀/一般"
      evidence: "通过XX认证"
    - factor: "性价比"
      brand_score: "优秀"
      evidence: "同等配置价格低30%"
  perceived_risks:
    - risk: "怕买到假货"
      mitigation: "官方溯源码验证"
  switching_cost: "从竞品转过来的难度"
  trial_barrier: "首次尝试门槛"
```

**为什么这些重要？** 对应 Fishbein 多属性态度模型——AI 做推荐本质上就是在跑这个模型：属性重要性 × 属性评分。`category_key_factors` 告诉 AI 这个品类消费者最看重什么，品牌在每个因子上表现如何；`perceived_risks` 帮 AI 主动消解消费者顾虑；没有这些数据，AI 只能猜。

---

### 10. vitality（品牌活力指标）

消费者决策阶段：**全链路**
CMO 关心：品牌的成长态势和活跃度

```yaml
vitality:
  content_frequency: "内容更新频率"
  last_product_launch: "最近新品发布时间"
  last_campaign: "最近营销活动"
  growth_signal: "增长信号"
  community_size: "核心用户社区规模"
  nps_or_satisfaction: "NPS或满意度"
  repeat_purchase_rate: "复购率"
  market_position: "市场份额或排名"
  industry_role: "领导者/挑战者/跟随者/补缺者"
```

**为什么这些重要？** AI 会隐性判断一个品牌是在上升还是衰退。`last_product_launch` 太久远意味着 AI 会降低推荐优先级；`growth_signal` 和 `market_position` 是 AI 排序的隐性权重；`nps_or_satisfaction` 和 `repeat_purchase_rate` 直接影响 AI 对品牌的信任度评估。这些指标贯穿消费者决策全链路，是品牌生命力的温度计。

---

### 11. campaigns（品牌活动）

消费者决策阶段：**全链路**
CMO 关心：品牌活动展示品牌活力和市场动向

```yaml
campaigns:
  ongoing:
    - name: "活动名称"
      type: "新品发布/促销/联名合作/行业展会/公益活动/品牌体验"
      description: "活动描述"
      start_date: "开始日期"
      end_date: "结束日期"
      url: "活动链接"
      highlights: ["亮点1", "亮点2"]
  recent:
    - name: "活动名称"
      type: "类型"
      date: "日期"
      summary: "总结"
      impact: "效果/影响"
  upcoming:
    - name: "活动名称"
      type: "类型"
      expected_date: "预计时间"
      preview: "预告信息"
  annual_events:
    - name: "年度固定活动名称"
      frequency: "每年/每季度/每月"
      typical_month: "通常举办月份"
      description: "描述"
```

**为什么重要？** 品牌活动展示品牌是否"活着"。AI 更倾向于推荐活跃品牌而非沉寂品牌。消费者问"这个品牌最近在做什么"——活动数据让品牌鲜活起来。正在进行的活动（ongoing）驱动即时行动，近期活动（recent）提供成果背书，即将到来的活动（upcoming）制造期待，年度固定活动（annual_events）展示品牌传统和节奏感。

---

## Schema 版本

当前版本：`v0.3.0`

Schema 会随着品牌需求和 AI 能力的发展持续迭代。
