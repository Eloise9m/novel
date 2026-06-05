# AI Novel To Script - AI小说转剧本工具

将小说自动转换为标准影视剧本（YAML格式），基于大语言模型，每日免费生成额度。

## 功能

- 支持 TXT / DOCX 小说上传，或直接粘贴文本
- 自动解析章节、识别人物、提取对白和动作
- 4种改编模式：忠实原著 / 影视化改编 / 对话增强 / 舞台剧模式
- 自动生成角色关系图和剧情摘要
- 场景情感分析
- 支持单场景重新生成
- 导出 YAML / JSON 剧本文件

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
streamlit run app.py
```

然后在浏览器中打开 http://localhost:8501

## 使用步骤

1. 首次使用无需配置，可直接免费试用
2. 选择改编模式
3. 上传小说文件或粘贴文本
4. 点击"开始生成剧本"
5. 在"剧本预览"页面查看结果
6. 在"下载中心"下载 YAML/JSON 剧本

## 项目结构

```
├── app.py              # 主程序 (Streamlit)
├── requirements.txt    # 依赖
├── utils/
│   ├── parser.py       # 小说解析
│   ├── generator.py    # AI生成
│   ├── yaml_export.py  # YAML导出
│   └── prompt.py       # AI提示词
├── outputs/            # 输出目录
└── uploads/            # 上传目录
```

## 获取 API Key

免费次数用完后，需自行配置 API Key 继续使用。

## YAML 剧本格式

```yaml
title: 小说标题
summary: 剧情摘要
characters:
  - name: 角色名
    description: 角色描述
scenes:
  - scene_id: 1
    location: 地点
    time: 时间
    emotion: 情绪
    characters: [出场人物]
    actions:
      - actor: 人物
        content: 动作
    dialogues:
      - speaker: 人物
        content: 对白
```
