"""AI提示词模板"""

# 章节解析提示词
CHAPTER_PARSE_PROMPT = """你是一个小说分析专家。请分析以下小说文本，识别所有章节标题和对应的起始位置。

要求：
1. 识别中文章节格式（如：第一章、第二章、第1章、Chapter 1等）
2. 返回JSON数组，每个元素包含 chapter_title 和 chapter_index（从1开始）
3. 只返回JSON，不要其他内容

小说文本：
{text}

请返回如下格式的JSON：
[{{"chapter_index": 1, "chapter_title": "第一章 初入校园"}}, ...]
"""

# 人物识别提示词
CHARACTER_EXTRACT_PROMPT = """你是一个小说分析专家。请从以下小说文本中提取所有人物角色。

要求：
1. 识别所有有名字的角色
2. 区分主角(main)、配角(supporting)、龙套(npc)
3. 为每个角色写一句简短描述（不超过20字）
4. 只返回JSON，不要其他内容

小说文本：
{text}

请返回如下格式的JSON：
{{
  "characters": [
    {{"name": "张三", "role": "main", "description": "男大学生，性格开朗"}},
    {{"name": "李四", "role": "supporting", "description": "张三的室友"}}
  ]
}}
"""

# 场景识别提示词
SCENE_EXTRACT_PROMPT = """你是一个影视剧本分析专家。请将以下小说章节分解为场景。

要求：
1. 识别场景切换（地点变化）
2. 为每个场景标注地点(location)、时间(time)、出场人物(characters)、情绪(emotion)
3. 情绪可选：愉快、悲伤、紧张、平静、激动、压抑、浪漫、恐惧
4. 只返回JSON，不要其他内容

小说章节文本：
{text}

请返回如下格式的JSON：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "location": "教室",
      "time": "上午",
      "characters": ["张三", "李四"],
      "emotion": "愉快",
      "summary": "张三和李四在教室聊天"
    }}
  ]
}}
"""

# 对白和动作提取提示词
DIALOGUE_ACTION_PROMPT = """你是一个影视剧本分析专家。请从以下小说场景中提取所有对白和动作。

要求：
1. 提取所有人物对话，识别说话人和对话内容
2. 提取所有人物动作，识别执行人和动作内容
3. 按原文顺序排列
4. 只返回JSON，不要其他内容

小说场景文本：
{text}

出场人物：{characters}

请返回如下格式的JSON：
{{
  "actions": [
    {{"actor": "张三", "content": "走进教室"}},
    {{"actor": "李四", "content": "站起身"}}
  ],
  "dialogues": [
    {{"speaker": "李四", "content": "你来了？"}},
    {{"speaker": "张三", "content": "是的。"}}
  ]
}}
"""

# 关系图谱提示词
RELATION_EXTRACT_PROMPT = """你是一个小说分析专家。请分析以下小说文本中的人物关系。

要求：
1. 识别人物之间的关系（朋友、师生、恋人、同事、家人、敌对等）
2. 只返回JSON，不要其他内容

小说文本：
{text}

人物列表：{characters}

请返回如下格式的JSON：
{{
  "relations": [
    {{"source": "张三", "target": "李四", "relation": "朋友"}},
    {{"source": "张三", "target": "王老师", "relation": "师生"}}
  ]
}}
"""

# 剧情摘要提示词
SUMMARY_PROMPT = """你是一个小说分析专家。请为以下小说生成简洁的剧情摘要。

要求：
1. 200字以内
2. 涵盖主要情节
3. 语言流畅

小说文本：
{text}

请直接返回摘要文本，不要加任何前缀说明。
"""

# 剧本生成提示词模板
SCRIPT_GENERATE_PROMPTS = {
    "faithful": """你是一个专业影视编剧。请根据以下小说内容，忠实原著的风格和内容，生成标准影视剧本格式。

要求：
1. 严格按照原著的剧情和对白
2. 使用标准剧本格式
3. 标注场景地点、时间、人物
4. 每句对白标明说话人
5. 标注人物动作
6. 只返回JSON，不要其他内容

小说内容：
{text}

人物列表：
{characters}

请返回如下格式的JSON：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "location": "场景地点",
      "time": "时间",
      "emotion": "情绪",
      "characters": ["出场人物"],
      "actions": [{{"actor": "人物", "content": "动作描述"}}],
      "dialogues": [{{"speaker": "人物", "content": "对白内容"}}]
    }}
  ]
}}""",

    "dramatic": """你是一个专业影视编剧。请根据以下小说内容，进行影视化改编，增加戏剧冲突和视觉表现力。

要求：
1. 在原著基础上增加戏剧张力
2. 丰富场景氛围描写
3. 适当调整对白使其更具表现力
4. 增强人物性格的鲜明度
5. 只返回JSON，不要其他内容

小说内容：
{text}

人物列表：
{characters}

请返回如下格式的JSON：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "location": "场景地点",
      "time": "时间",
      "emotion": "情绪",
      "characters": ["出场人物"],
      "actions": [{{"actor": "人物", "content": "动作描述"}}],
      "dialogues": [{{"speaker": "人物", "content": "对白内容"}}]
    }}
  ]
}}""",

    "dialogue_enhanced": """你是一个专业影视编剧。请根据以下小说内容，重点增强人物对白。

要求：
1. 丰富人物对话内容
2. 使对白更符合人物性格
3. 增加潜台词和情感层次
4. 保持原著剧情走向
5. 只返回JSON，不要其他内容

小说内容：
{text}

人物列表：
{characters}

请返回如下格式的JSON：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "location": "场景地点",
      "time": "时间",
      "emotion": "情绪",
      "characters": ["出场人物"],
      "actions": [{{"actor": "人物", "content": "动作描述"}}],
      "dialogues": [{{"speaker": "人物", "content": "对白内容"}}]
    }}
  ]
}}""",

    "stage_play": """你是一个专业舞台剧编剧。请根据以下小说内容，改编为舞台剧剧本。

要求：
1. 适合舞台演出
2. 场景集中，不宜过多
3. 对白富有戏剧性
4. 增加舞台提示
5. 只返回JSON，不要其他内容

小说内容：
{text}

人物列表：
{characters}

请返回如下格式的JSON：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "location": "场景地点",
      "time": "时间",
      "emotion": "情绪",
      "characters": ["出场人物"],
      "actions": [{{"actor": "人物", "content": "动作描述"}}],
      "dialogues": [{{"speaker": "人物", "content": "对白内容"}}]
    }}
  ]
}}"""
}

# 场景重新生成提示词
SCENE_REGENERATE_PROMPT = """你是一个专业影视编剧。请重新编写以下场景的剧本内容。

要求：
1. 保持原有人物和场景设定
2. 改写对白，使其更加生动
3. 可以调整动作描写
4. 只返回JSON，不要其他内容

原始场景：
{original_scene}

模式：{mode}

请返回如下格式的JSON：
{{
  "actions": [{{"actor": "人物", "content": "动作描述"}}],
  "dialogues": [{{"speaker": "人物", "content": "对白内容"}}]
}}
"""

# 章节拆分函数（本地处理，无需API）
CHAPTER_PATTERNS = [
    r'^第[一二三四五六七八九十百千\d]+章',
    r'^第[一二三四五六七八九十百千\d]+节',
    r'^Chapter\s+\d+',
    r'^CH\s*\d+',
    r'^Part\s+\d+',
    r'^第[一二三四五六七八九十百千\d]+卷',
]
