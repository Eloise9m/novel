"""AI Novel To Script - AI小说转剧本工具"""

import os
import json
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from utils.parser import split_chapters, parse_chapter_list, parse_docx, parse_txt, safe_json_parse
from utils.generator import (
    extract_characters,
    extract_relations,
    generate_summary,
    generate_script,
    regenerate_scene,
)
from utils.yaml_export import ScriptYAML, build_script_from_chapters, scenes_to_script_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
TRIAL_FILE = os.path.join(BASE_DIR, "free_trials.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
MAX_FREE_TRIALS = 5
MAX_HISTORY = 20

# ── 试用次数 ───────────────────────────────────────────
def _read_trials():
    try:
        with open(TRIAL_FILE) as f:
            return json.load(f).get("used", 0)
    except Exception:
        return 0

def _write_trials(count):
    with open(TRIAL_FILE, "w") as f:
        json.dump({"used": count}, f)

def trials_remaining():
    return max(0, MAX_FREE_TRIALS - _read_trials())

def use_trial():
    _write_trials(_read_trials() + 1)

def get_builtin_key():
    try:
        return st.secrets["DOUBAO_API_KEY"]
    except Exception:
        return ""

def get_active_key():
    if trials_remaining() > 0:
        return get_builtin_key()
    return st.session_state.get("user_api_key", "")

# ── 历史记录 ───────────────────────────────────────────
def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history_entry(entry):
    history = load_history()
    history.insert(0, entry)
    if len(history) > MAX_HISTORY:
        history = history[:MAX_HISTORY]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history_entry(entry):
    st.session_state.novel_title = entry.get("title", "")
    st.session_state.mode = entry.get("mode", "faithful")
    st.session_state.characters = entry.get("characters", [])
    st.session_state.relations = entry.get("relations", [])
    st.session_state.summary = entry.get("summary", "")
    st.session_state.all_scenes = entry.get("all_scenes", [])
    st.session_state.step = 3
    st.rerun()

# ── 自定义 CSS ─────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    /* ── 全局 ── */
    .stApp { background: #f8f9fc; }
    section[data-testid="stSidebar"] { background: #1a1a2e; }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 { color: #fff !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: #6c63ff !important; color: #fff !important; border: none !important;
        border-radius: 8px !important; font-weight: 600 !important;
    }

    /* ── 主区域标题 ── */
    .hero-title {
        font-size: 3rem; font-weight: 800;
        background: linear-gradient(135deg, #6c63ff, #e94560); -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; margin-bottom: 0;
    }
    .hero-subtitle { color: #666; font-size: 1.15rem; margin-bottom: 2rem; }

    /* ── 卡片 ── */
    .metric-card {
        background: #fff; border-radius: 16px; padding: 20px 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); text-align: center;
        border: 1px solid #eee;
    }
    .metric-card .icon { font-size: 2rem; margin-bottom: 8px; }
    .metric-card .label { color: #888; font-size: 0.85rem; margin-bottom: 4px; }
    .metric-card .value { font-size: 1.3rem; font-weight: 700; color: #1a1a2e; }

    /* ── 按钮 ── */
    .stButton > button {
        border-radius: 10px !important; font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(108,99,255,0.3); }

    /* ── 对话气泡 ── */
    .dialogue-bubble {
        background: #fff; border-left: 4px solid #6c63ff; border-radius: 0 12px 12px 0;
        padding: 12px 18px; margin: 10px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .dialogue-bubble .speaker { font-weight: 700; color: #6c63ff; }
    .dialogue-bubble .content { color: #333; }

    /* ── 历史卡片 ── */
    .history-item {
        background: rgba(255,255,255,0.06); border-radius: 10px; padding: 10px 14px;
        margin: 6px 0; cursor: pointer; border: 1px solid rgba(255,255,255,0.08);
        transition: background 0.2s;
    }
    .history-item:hover { background: rgba(255,255,255,0.12); }
    .history-item .h-title { font-weight: 600; color: #fff !important; font-size: 0.9rem; }
    .history-item .h-meta { font-size: 0.7rem; color: #999 !important; margin-top: 2px; }

    /* ── 上传区域 ── */
    .upload-card {
        background: #fff; border-radius: 16px; padding: 28px; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

# ── 初始化 ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Novel To Script",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULTS = {
    "user_api_key": "",
    "novel_text": "",
    "novel_title": "",
    "chapters": [],
    "characters": [],
    "relations": [],
    "summary": "",
    "all_scenes": [],
    "current_scene_idx": 0,
    "mode": "faithful",
    "step": 0,
    "just_finished": False,
    "trigger_generate": False,
    "processing": False,
    "progress": 0,
    "status_text": "",
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

def reset_all():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

# ── 侧边栏 ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎬 Novel To Script")
        st.markdown("---")

        remaining = trials_remaining()
        if remaining > 0:
            st.markdown("### ⚡ 免费试用")
            st.success(f"剩余次数: **{remaining}/{MAX_FREE_TRIALS}**")
            st.caption("用完后需输入自己的 API Key")
        else:
            st.markdown("### 🔑 API 设置")
            st.warning("免费次数已用完")
            user_key = st.text_input(
                "API Key",
                type="password",
                value=st.session_state.user_api_key,
                placeholder="输入你的API Key...",
                help="在 https://console.volcengine.com/ark 获取",
            )
            if user_key != st.session_state.user_api_key:
                st.session_state.user_api_key = user_key

        st.markdown("---")
        st.markdown("### 🎭 生成模式")
        mode_labels = {
            "faithful": "忠实原著",
            "dramatic": "影视化改编",
            "dialogue_enhanced": "对话增强",
            "stage_play": "舞台剧模式",
        }
        prev_mode = st.session_state.mode
        mode = st.radio(
            "选择改编模式",
            options=list(mode_labels.keys()),
            format_func=lambda x: mode_labels[x],
            index=list(mode_labels.keys()).index(st.session_state.mode),
            key="_mode_radio",
        )
        st.session_state.mode = mode
        if mode != prev_mode and st.session_state.novel_text and not st.session_state.processing:
            st.session_state.trigger_generate = True
        st.caption(f"✨ {mode_labels.get(mode, '')}")

        st.markdown("---")
        if st.button("🔄 重新开始", use_container_width=True):
            reset_all()
            st.rerun()

        # ── 历史记录 ──
        st.markdown("---")
        st.markdown("### 📜 历史记录")
        history = load_history()
        if not history:
            st.caption("暂无记录，生成后自动保存")
        else:
            for i, h in enumerate(history[:10]):
                title = h.get("title", "未命名")
                date_str = h.get("date", "")[:16].replace("T", " ")
                mode_name = mode_labels.get(h.get("mode", ""), h.get("mode", ""))
                scene_count = h.get("scene_count", 0)
                with st.expander(f"📄 {title}"):
                    st.caption(f"🕒 {date_str}")
                    st.caption(f"🎭 {mode_name}  |  场景 ×{scene_count}")
                    if st.button("📂 加载此记录", key=f"load_{i}", use_container_width=True):
                        load_history_entry(h)

# ── 首页 ───────────────────────────────────────────────
def page_home():
    st.markdown('<div class="hero-title">AI Novel To Script</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">将小说一键转换为影视剧本</div>', unsafe_allow_html=True)

    # 功能卡片
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="metric-card">
            <div class="icon">📂</div>
            <div class="label">支持格式</div>
            <div class="value">TXT / DOCX</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-card">
            <div class="icon">🧠</div>
            <div class="label">AI引擎</div>
            <div class="value">大模型 (免费)</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
            <div class="icon">📥</div>
            <div class="label">输出格式</div>
            <div class="value">YAML / JSON</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 上传区域 / 已加载状态
    if st.session_state.novel_text:
        # 已加载小说，显示状态而非上传区
        st.success(f"📖 已加载：《{st.session_state.novel_title}》（{len(st.session_state.novel_text)} 字）")
        if st.button("🔄 更换小说", type="secondary"):
            st.session_state.novel_text = ""
            st.session_state.novel_title = ""
            st.session_state.step = 0
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["📤 上传文件", "📝 粘贴文本"])

        with tab1:
            uploaded_file = st.file_uploader(
                "选择小说文件",
                type=["txt", "docx"],
                help="支持TXT和DOCX格式",
            )
            if uploaded_file is not None:
                if uploaded_file.size > 2 * 1024 * 1024:
                    st.warning("文件较大（>2MB），建议使用章节较少的小说")

                if st.button("📖 读取文件", type="primary", use_container_width=True):
                    with st.spinner("读取文件中..."):
                        try:
                            temp_path = os.path.join("uploads", uploaded_file.name)
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            if uploaded_file.name.endswith(".docx"):
                                text = parse_docx(temp_path)
                            else:
                                text = parse_txt(temp_path)
                            st.session_state.novel_text = text
                            st.session_state.novel_title = os.path.splitext(uploaded_file.name)[0]
                            st.success(f"读取成功: {uploaded_file.name} ({len(text)} 字)")
                            st.rerun()
                        except Exception as e:
                            st.error(f"读取失败: {e}")

        with tab2:
            novel_title = st.text_input("小说标题", placeholder="输入小说标题")
            pasted_text = st.text_area(
                "粘贴小说内容",
                height=300,
                placeholder="请粘贴小说全文...",
            )
            if st.button("✅ 确认提交", type="primary", use_container_width=True):
                if len(pasted_text.strip()) < 100:
                    st.warning("文本内容过短")
                else:
                    st.session_state.novel_text = pasted_text.strip()
                    st.session_state.novel_title = novel_title or "未命名小说"
                    st.success(f"文本已提交 ({len(pasted_text)} 字)")
                    st.rerun()

    # 模式切换触发自动生成
    if st.session_state.get("trigger_generate") and st.session_state.novel_text:
        st.session_state.trigger_generate = False
        active_key = get_active_key()
        if active_key:
            run_pipeline()

    # 小说就绪
    if st.session_state.novel_text:
        st.markdown("---")
        st.subheader(f"📖 《{st.session_state.novel_title}》")
        chapters = parse_chapter_list(st.session_state.novel_text)
        st.info(f"识别到 **{len(chapters)}** 个章节")

        with st.expander("📋 查看章节列表"):
            for ch in chapters:
                st.write(f"第{ch['chapter_index']}章: {ch['chapter_title']}")

        if st.button("🚀 开始生成剧本", type="primary", use_container_width=True, disabled=st.session_state.processing):
            active_key = get_active_key()
            if not active_key:
                st.error("免费次数已用完，请在侧边栏输入你自己的 API Key")
            else:
                run_pipeline()

# ── 处理流水线 ─────────────────────────────────────────
def run_pipeline():
    st.session_state.processing = True
    st.session_state.all_scenes = []
    st.session_state.step = 0

    text = st.session_state.novel_text
    api_key = get_active_key()
    mode = st.session_state.mode

    if trials_remaining() > 0:
        use_trial()

    progress_bar = st.progress(0)
    status_area = st.empty()

    try:
        # 步骤1: 解析章节
        status_area.info("步骤 1/3: 解析章节...")
        chapters = split_chapters(text)
        st.session_state.chapters = chapters
        progress_bar.progress(10)

        # 步骤2: 并行执行人物提取 + 关系分析 + 摘要
        status_area.info(f"步骤 2/3: AI分析中（人物识别 + 关系分析 + 摘要）...")

        def do_characters():
            return extract_characters(api_key, text)
        def do_relations(char_names):
            return extract_relations(api_key, text, char_names)
        def do_summary():
            return generate_summary(api_key, text)

        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_chars = pool.submit(do_characters)
            fut_summary = pool.submit(do_summary)

            char_result = fut_chars.result()
            characters = char_result.get("characters", [])
            st.session_state.characters = characters
            char_names = [c.get("name", "") for c in characters if c.get("name")]

            fut_rels = pool.submit(do_relations, char_names)
            summary = fut_summary.result()
            st.session_state.summary = summary
            rel_result = fut_rels.result()
            st.session_state.relations = rel_result.get("relations", [])

        progress_bar.progress(30)

        # 步骤3: 并行生成所有章节剧本
        total = len(chapters)

        def process_chapter(idx_ch):
            i, ch = idx_ch
            script_result = generate_script(
                api_key, ch["content"], ch["chapter_title"],
                char_names, mode,
            )
            scenes = script_result.get("scenes", [])
            for scene in scenes:
                scene["chapter"] = ch["chapter_title"]
                scene["_chapter_idx"] = i
            return scenes

        with ThreadPoolExecutor(max_workers=min(4, total)) as pool:
            futures = {pool.submit(process_chapter, (i, ch)): i for i, ch in enumerate(chapters)}
            completed = 0
            for fut in as_completed(futures):
                scenes = fut.result()
                st.session_state.all_scenes.extend(scenes)
                completed += 1
                status_area.info(f"步骤 3/3: 生成剧本 {completed}/{total} 章")
                progress_bar.progress(30 + int(65 * completed / total))

        # 按章节顺序排列场景
        st.session_state.all_scenes.sort(key=lambda s: (s.get("_chapter_idx", 0), s.get("scene_id", 0)))

        progress_bar.progress(100)
        scene_count = len(st.session_state.all_scenes)
        status_area.success(f"剧本生成完成！共 {scene_count} 个场景")

        save_history_entry({
            "title": st.session_state.novel_title,
            "date": datetime.now().isoformat(),
            "mode": mode,
            "scene_count": scene_count,
            "characters": st.session_state.characters,
            "relations": st.session_state.relations,
            "summary": st.session_state.summary,
            "all_scenes": st.session_state.all_scenes,
        })

        st.session_state.step = 3
        st.session_state.just_finished = True
        time.sleep(1)
        st.rerun()

    except Exception as e:
        status_area.error(f"处理出错: {e}")
        logger.exception("Pipeline error")
        st.session_state.processing = False

# ── 剧本预览 ───────────────────────────────────────────
def page_results():
    st.title("🎬 剧本预览")
    st.markdown(f"### 《{st.session_state.novel_title}》")

    if st.session_state.summary:
        with st.expander("📖 剧情摘要", expanded=False):
            st.write(st.session_state.summary)

    tabs = st.tabs(["🎭 人物角色", "🕸️ 角色关系", "📜 场景剧本", "📝 传统剧本", "📄 YAML预览"])

    with tabs[0]:
        render_characters_tab()
    with tabs[1]:
        render_relations_tab()
    with tabs[2]:
        render_scenes_tab()
    with tabs[3]:
        render_script_text_tab()
    with tabs[4]:
        render_yaml_preview_tab()

def render_characters_tab():
    characters = st.session_state.characters
    if not characters:
        st.info("暂无人物数据")
        return
    cols = st.columns(3)
    for i, char in enumerate(characters):
        role_labels = {"main": "主角", "supporting": "配角", "npc": "龙套"}
        role = role_labels.get(char.get("role", ""), char.get("role", ""))
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {char.get('name', '未知')}")
                st.caption(f"角色: {role}")
                st.write(char.get("description", "暂无描述"))

def render_relations_tab():
    relations = st.session_state.relations
    if not relations:
        st.info("暂无关系数据")
        return
    st.markdown("#### 人物关系图")
    for rel in relations:
        source = rel.get("source", "?")
        target = rel.get("target", "?")
        relation = rel.get("relation", "?")
        st.markdown(f"**{source}** ──{relation}── **{target}**")
    st.caption("未来版本将支持可视化关系图")

def render_scenes_tab():
    scenes = st.session_state.all_scenes
    if not scenes:
        st.info("暂无场景数据，请先生成剧本")
        return

    scene_ids = [f"场景 {s.get('scene_id', i + 1)}: {s.get('location', '未知')}" for i, s in enumerate(scenes)]
    selected = st.selectbox("选择场景", range(len(scene_ids)), format_func=lambda i: scene_ids[i])
    st.session_state.current_scene_idx = selected
    scene = scenes[selected]

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("场景ID", scene.get("scene_id", selected + 1))
    with c2:
        st.metric("📍 地点", scene.get("location", "未知"))
    with c3:
        st.metric("🕐 时间", scene.get("time", "未知"))
    with c4:
        st.metric("🎭 情绪", scene.get("emotion", "未知"))

    st.markdown(f"**所属章节:** {scene.get('chapter', '未知')}")
    st.markdown("---")

    scene_chars = scene.get("characters", [])
    if scene_chars:
        st.markdown("#### 👥 出场人物")
        st.markdown(", ".join([f"**{c}**" for c in scene_chars]))

    actions = scene.get("actions", [])
    if actions:
        st.markdown("#### 🎬 动作")
        for a in actions:
            st.markdown(f"- {a.get('actor', '?')} **{a.get('content', '')}**")

    dialogues = scene.get("dialogues", [])
    if dialogues:
        st.markdown("#### 💬 对白")
        for d in dialogues:
            speaker = d.get("speaker", "?")
            content = d.get("content", "")
            st.markdown(f"""
            <div class="dialogue-bubble">
                <span class="speaker">{speaker}</span>：<span class="content">{content}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🔄 重新生成当前场景", type="secondary", use_container_width=True):
        active_key = get_active_key()
        if active_key:
            with st.spinner("AI重新编写中..."):
                try:
                    new_content = regenerate_scene(active_key, scene, st.session_state.mode)
                    if new_content.get("actions"):
                        st.session_state.all_scenes[selected]["actions"] = new_content["actions"]
                    if new_content.get("dialogues"):
                        st.session_state.all_scenes[selected]["dialogues"] = new_content["dialogues"]
                    st.success("场景已重新生成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"重新生成失败: {e}")

def render_script_text_tab():
    """传统剧本格式标签页"""
    if not st.session_state.all_scenes:
        st.info("暂无剧本数据")
        return
    script_text = scenes_to_script_text(st.session_state.novel_title, st.session_state.all_scenes)
    st.markdown("#### 传统剧本格式 (人名：台词)")
    st.text_area("剧本内容", script_text, height=500, key="script_text_area")
    st.download_button(
        label="⬇ 下载 TXT 剧本",
        data=script_text,
        file_name=f"{st.session_state.novel_title}.txt",
        mime="text/plain",
        type="primary",
    )

def render_yaml_preview_tab():
    if not st.session_state.all_scenes:
        st.info("暂无剧本数据")
        return
    script = build_script_from_chapters(
        st.session_state.novel_title,
        st.session_state.summary,
        st.session_state.characters,
        st.session_state.relations,
        st.session_state.all_scenes,
    )
    st.code(script.to_yaml(), language="yaml", line_numbers=True)

# ── 下载中心 ───────────────────────────────────────────
def page_download():
    st.title("📥 下载中心")

    if not st.session_state.all_scenes:
        st.info("请先生成剧本后再访问下载中心")
        return

    script = build_script_from_chapters(
        st.session_state.novel_title, st.session_state.summary,
        st.session_state.characters, st.session_state.relations,
        st.session_state.all_scenes,
    )

    st.markdown("### 剧本文件下载")
    c1, c2, c3 = st.columns(3)

    script_text = scenes_to_script_text(st.session_state.novel_title, st.session_state.all_scenes)

    with c1:
        st.markdown("#### 📝 TXT 剧本")
        st.download_button(
            label="⬇ 下载 TXT 剧本",
            data=script_text,
            file_name=f"{st.session_state.novel_title}.txt",
            mime="text/plain",
            type="primary",
            use_container_width=True,
        )
        st.caption("传统格式：人名：台词")

    with c2:
        st.markdown("#### 📄 YAML 格式")
        yaml_content = script.to_yaml()
        st.download_button(
            label="⬇ 下载 YAML 剧本",
            data=yaml_content,
            file_name=f"{st.session_state.novel_title}.yaml",
            mime="application/x-yaml",
            type="primary",
            use_container_width=True,
        )
        with st.expander("预览"):
            st.code(yaml_content[:3000], language="yaml")

    with c3:
        st.markdown("#### 📦 JSON 格式")
        json_content = script.to_json()
        st.download_button(
            label="⬇ 下载 JSON 剧本",
            data=json_content,
            file_name=f"{st.session_state.novel_title}.json",
            mime="application/json",
            type="primary",
            use_container_width=True,
        )
        with st.expander("预览"):
            st.code(json_content[:3000], language="json")

    st.markdown("---")
    st.markdown("### 📊 剧本统计")
    scenes = st.session_state.all_scenes
    dialogues_total = sum(len(s.get("dialogues", [])) for s in scenes)
    actions_total = sum(len(s.get("actions", [])) for s in scenes)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🎬 场景数", len(scenes))
    with c2:
        st.metric("🎭 人物数", len(st.session_state.characters))
    with c3:
        st.metric("💬 对白数", dialogues_total)
    with c4:
        st.metric("🎯 动作数", actions_total)

# ── 主入口 ─────────────────────────────────────────────
def main():
    inject_css()
    render_sidebar()

    st.sidebar.markdown("---")

    # 生成完成后自动跳到预览页
    if st.session_state.get("just_finished"):
        st.session_state.just_finished = False
        st.sidebar.success("✅ 剧本已生成")
        page_results()
        return

    menu = st.sidebar.radio(
        "📍 导航",
        ["🏠 首页", "🎬 剧本预览", "📥 下载中心"],
    )

    if "首页" in menu:
        if st.session_state.step >= 3 and st.session_state.all_scenes:
            st.sidebar.success("✅ 剧本已生成")
        page_home()
    elif "剧本预览" in menu:
        page_results()
    elif "下载中心" in menu:
        page_download()

    st.sidebar.markdown("---")
    st.sidebar.caption("v1.1 · Powered by AI")

if __name__ == "__main__":
    main()
