# AI Novel To Script — AI小说转剧本工具

将小说自动转换为标准影视剧本，基于大语言模型，每日免费使用。

## 在线使用（推荐）

👉 **[点击这里打开](https://eloise9m-novel-app-bg234h.streamlit.app/)**

打开浏览器就能用，无需安装任何东西。

## 功能

- 上传 TXT / DOCX 小说，或直接粘贴文本
- 自动解析章节、识别人物、提取对白和动作
- 4 种改编模式：忠实原著 / 影视化改编 / 对话增强 / 舞台剧模式
- 输出传统剧本格式（人名：台词），可下载 TXT / YAML / JSON
- 自动生成角色关系图和剧情摘要
- 支持单场景重写

## 本地运行（开发者）

```bash
pip install -r requirements.txt
streamlit run app.py
# 浏览器打开 http://localhost:8501
```

## 输出格式

详见 [YAML Schema 文档](docs/SCHEMA.md)。

## 项目结构

```
├── app.py              # 主程序 (Streamlit)
├── requirements.txt    # 依赖
├── utils/
│   ├── parser.py       # 小说解析
│   ├── generator.py    # AI 生成
│   ├── yaml_export.py  # YAML / TXT 导出
│   └── prompt.py       # AI 提示词
├── docs/
│   └── SCHEMA.md       # YAML Schema 文档
├── outputs/            # 输出目录
└── uploads/            # 上传目录
```

## 部署到 Streamlit Cloud

1. Fork 本仓库
2. 打开 [share.streamlit.io](https://share.streamlit.io)，用 GitHub 登录
3. 点击 New app → 选择你的仓库 → Main file path: `app.py`
4. 在 Secrets 中添加你的 API Key
5. 部署完成，获得公开链接
