# AI Novel To Script — YAML Schema 文档

## 概述

本工具将小说转换为结构化剧本，输出格式为 YAML。本文档定义输出数据的完整 Schema，并说明每项字段的设计原因。

---

## 顶层结构

```yaml
title: "小说标题"          # 剧本标题，取自小说文件名或用户输入
generated_at: "2026-06-05 14:30:00"  # 生成时间戳
summary: "剧情摘要..."      # 200 字以内的故事梗概
characters: [...]          # 人物列表
relations: [...]           # 人物关系列表
scenes: [...]              # 场景列表
```

### 设计原因

| 字段 | 理由 |
|------|------|
| `title` | 标识剧本来源，方便多部小说管理 |
| `generated_at` | 追踪生成时间，配合历史记录功能使用 |
| `summary` | 快速了解剧情全貌，无需通读所有场景 |
| `characters` | 与 scenes 分离，方便全局查看角色列表，避免每个场景重复存储完整人物信息 |
| `relations` | 人物关系独立存储，便于未来扩展可视化关系图 |
| `scenes` | 核心数据，按场景组织而非按章节，因为一个场景才是影视拍摄的最小单元 |

---

## characters（人物）

```yaml
characters:
  - name: "张三"            # 角色名（必填）
    role: "main"            # 角色类型（必填）
    description: "男大学生，性格开朗"  # 角色简介（必填）
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 人物名称，唯一标识 |
| `role` | enum | 是 | `main`（主角）/ `supporting`（配角）/ `npc`（龙套） |
| `description` | string | 是 | 简短的描述，不超过 30 字 |

### 设计原因

**三个角色等级**对应影视行业的分层体系：
- `main` — 推动主线剧情的核心人物，出场最多
- `supporting` — 辅助主线、制造冲突的关键配角
- `npc` — 一笔带过的路人角色

这种分类在剧组选角和排通告时非常实用——主配角需要演员表，龙套可以由群演担任。

`name` 不做全局唯一约束，因为实际小说中不同场景可能出现同名角色（如"小明"），由 AI 根据上下文自然区分。

---

## relations（人物关系）

```yaml
relations:
  - source: "张三"          # 关系起点人物
    target: "李四"          # 关系终点人物
    relation: "朋友"        # 关系类型
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | string | 是 | 关系起点，需与 characters 中的 name 对应 |
| `target` | string | 是 | 关系终点 |
| `relation` | string | 是 | 关系描述，如：朋友、师生、恋人、同事、家人、敌对 |

### 设计原因

**有向图模型**：每条关系是 source → target 的单向边。双向关系（如"两人互为朋友"）会生成两条记录，也可以只生成一条由解释方语义决定的有向边。这个设计天然支持：
- **非对称关系**："张三暗恋李四"不等于"李四暗恋张三"
- **未来扩展**：可以轻松转换为 D3.js / Graphviz 可视化

`relation` 使用**自然语言字符串**而非枚举，因为小说中的人物关系千变万化（如"杀父仇人"、"同门师兄兼情敌"），枚举无法覆盖。

---

## scenes（场景）

```yaml
scenes:
  - scene_id: 1             # 场景序号（全局唯一，从 1 开始）
    location: "教室"         # 场景地点
    time: "上午"             # 场景时间
    emotion: "愉快"          # 场景情绪基调
    characters:              # 本场景出场人物
      - "张三"
      - "李四"
    actions:                 # 人物动作列表
      - actor: "张三"
        content: "推门走进教室"
      - actor: "李四"
        content: "从座位上站起来"
    dialogues:               # 人物对白列表
      - speaker: "李四"
        content: "你终于来了。"
      - speaker: "张三"
        content: "抱歉，路上堵车。"
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scene_id` | integer | 是 | 全局唯一序号，从 1 递增 |
| `location` | string | 是 | 场景发生地点（如"教室""操场""客厅"） |
| `time` | string | 是 | 场景时间（如"上午""傍晚""深夜"） |
| `emotion` | string | 是 | 情绪基调（愉快/悲伤/紧张/平静/激动/压抑/浪漫/恐惧） |
| `characters` | string[] | 是 | 本场景出场的人物名称列表 |
| `actions` | object[] | 否 | 人物动作列表 |
| `dialogues` | object[] | 否 | 人物对白列表 |

### 设计原因

**场景是核心组织单元**：在影视制作中，"第 3 场 — 教室 — 日"是导演、摄影、灯光共同工作的基本调度单位。按场景组织便于：
- 导演分镜：按场景拆分拍摄通告
- 成本估算：按场景统计群演、道具、场地需求
- AI 重生成：单场景重写不影响其他场景

**actions 与 dialogues 分开**：影视剧本中动作和对话是两类本质不同的元素。
- `actions` 描述视觉呈现（镜头语言、走位、表情），面向导演和摄影
- `dialogues` 记录台词，面向演员和录音

分开存储使得两者可以独立编辑、独立统计字数、独立做正则搜索。

**characters 在场景内重复声明**：虽然顶层有全局 characters，但每个场景仍需声明出场人物，因为：
- 不是所有人物每个场景都出场
- 方便快速判断某场戏需要哪些演员到现场

---

## actions（动作）

```yaml
actions:
  - actor: "张三"            # 执行人
    content: "推开教室的门，环顾四周"  # 动作描述
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `actor` | string | 是 | 执行动作的人物 |
| `content` | string | 是 | 动作的具体描述 |

### 设计原因

两字段结构是最小完备表达：谁 + 做了什么。不做更细粒度的拆分（如动作类型、道具、走位方向）是因为：
- AI 从自由文本中精确提取这些维度的准确率不够高
- 过度结构化会让影视专业人员感到受限——他们需要的是一段可读的动作描述，而非数据库记录

---

## dialogues（对白）

```yaml
dialogues:
  - speaker: "李四"          # 说话人
    content: "你终于来了。"    # 台词内容
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `speaker` | string | 是 | 说话人 |
| `content` | string | 是 | 台词原文 |

### 设计原因

与 actions 一样采用最简结构——"谁说 + 说什么"。不做潜台词、语气、停顿等细粒度标记，因为：
- 这些属于导演和演员的二度创作范畴，由人去理解和演绎更合适
- 保持 Schema 简洁，降低 AI 输出的不一致风险
- 实际使用中，编剧需要的正是可读的纯文本对白

---

## 完整示例

```yaml
title: "校园往事"
generated_at: "2026-06-05 14:30:00"
summary: "讲述了大学生张三在校园中与恋人李四相遇、相知、分离的故事。"
characters:
  - name: "张三"
    role: "main"
    description: "大三学生，性格内向但执着"
  - name: "李四"
    role: "main"
    description: "张三的同班同学，文艺青年"
  - name: "王老师"
    role: "supporting"
    description: "班主任，严厉但善良"

relations:
  - source: "张三"
    target: "李四"
    relation: "恋人"
  - source: "张三"
    target: "王老师"
    relation: "师生"

scenes:
  - scene_id: 1
    location: "大学教室"
    time: "上午"
    emotion: "愉快"
    characters:
      - "张三"
      - "李四"
      - "王老师"
    actions:
      - actor: "张三"
        content: "匆匆跑进教室"
      - actor: "王老师"
        content: "推了推眼镜，看向张三"
    dialogues:
      - speaker: "王老师"
        content: "张三同学，又迟到了。"
      - speaker: "张三"
        content: "对不起老师，下次不会了。"
      - speaker: "李四"
        content: "（小声）每次都这么说。"

  - scene_id: 2
    location: "学校操场"
    time: "傍晚"
    emotion: "浪漫"
    characters:
      - "张三"
      - "李四"
    actions:
      - actor: "李四"
        content: "坐在长椅上，望着夕阳"
    dialogues:
      - speaker: "张三"
        content: "今天的晚霞很美。"
      - speaker: "李四"
        content: "嗯，和你一起看就更美了。"
```

---

## 扩展性说明

Schema 设计遵循以下原则：

1. **渐进增强**：所有数组字段允许为空，AI 无法识别时不报错
2. **向前兼容**：新增字段不会破坏旧版本输出，旧解析器忽略未知字段
3. **不做字段校验**：`emotion`、`role` 等不做严格枚举校验，AI 输出的细微变化不会导致解析失败

未来可扩展的方向：
- `scene` 下增加 `props`（道具列表）和 `extras`（群演数量），支持制片预算估算
- `relations` 下增加 `weight`（关系强度），支持关系图可视化
- `dialogues` 下增加 `subtext`（潜台词），支持高级剧本分析
