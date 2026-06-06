"""AI Novel To Script - AI小说转剧本工具"""

import os
import json
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from utils.parser import split_chapters, parse_chapter_list, parse_docx, parse_txt
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

MODE_LABELS = {
    "faithful": "忠实原著",
    "dramatic": "影视化改编",
    "dialogue_enhanced": "对话增强",
    "stage_play": "舞台剧模式",
}

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
    user_key = st.session_state.get("user_api_key", "")
    if user_key:
        return user_key
    if trials_remaining() > 0:
        return get_builtin_key()
    return ""

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
    st.session_state.novel_text = entry.get("novel_text", "")
    st.session_state.step = 3
    st.rerun()

# ── CSS ────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    .stApp { background: #fafafa; }
    section[data-testid="stSidebar"] { background: #1a1a2e; }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 { color: #fff !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: #6c63ff !important; color: #fff !important; border: none !important;
        border-radius: 8px !important; font-weight: 600 !important;
    }
    .hero-title {
        font-size: 2.5rem; font-weight: 800;
        background: linear-gradient(135deg, #6c63ff, #e94560); -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; margin-bottom: 0;
    }
    .stButton > button {
        border-radius: 10px !important; font-weight: 600 !important;
    }
    .dialogue-bubble {
        background: #fff; border-left: 4px solid #6c63ff; border-radius: 0 12px 12px 0;
        padding: 12px 18px; margin: 10px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .dialogue-bubble .speaker { font-weight: 700; color: #6c63ff; }
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

        # 导航放最上面
        menu = st.radio(
            "页面",
            ["🏠 首页", "🎬 剧本预览", "📥 下载"],
            key="_nav",
            label_visibility="collapsed",
        )
        st.markdown("---")

        remaining = trials_remaining()
        if remaining > 0:
            st.success(f"⚡ 免费试用剩余 **{remaining}/{MAX_FREE_TRIALS}** 次")
        else:
            st.warning("免费次数已用完")
        user_key = st.text_input(
            "输入你的 API Key（可选，优先使用）",
            type="password",
            value=st.session_state.user_api_key,
            placeholder="粘贴 API Key...",
        )
        if user_key != st.session_state.user_api_key:
            st.session_state.user_api_key = user_key

        st.markdown("---")

        # 生成模式
        st.caption("🎭 改编模式")
        prev_mode = st.session_state.mode
        mode = st.radio(
            "模式",
            options=list(MODE_LABELS.keys()),
            format_func=lambda x: MODE_LABELS[x],
            index=list(MODE_LABELS.keys()).index(st.session_state.mode),
            key="_mode_radio",
            label_visibility="collapsed",
        )
        st.session_state.mode = mode
        if mode != prev_mode and st.session_state.novel_text and not st.session_state.processing:
            st.session_state.trigger_generate = True

        st.markdown("---")

        # 核心操作
        if st.session_state.novel_text and not st.session_state.processing:
            if st.button("🚀 生成剧本", type="primary", use_container_width=True):
                active_key = get_active_key()
                if not active_key:
                    if trials_remaining() <= 0:
                        st.error("免费次数已用完，请在侧边栏输入你的 API Key")
                    else:
                        st.error("API Key 未配置，请联系管理员")
                else:
                    run_pipeline()
        elif st.session_state.processing:
            st.button("⏳ 生成中...", disabled=True, use_container_width=True)

        if st.button("🔄 重新开始", use_container_width=True):
            reset_all()
            st.rerun()

        st.markdown("---")

        # 历史记录
        st.caption("📜 历史记录")
        history = load_history()
        if not history:
            st.caption("暂无")
        else:
            for i, h in enumerate(history[:8]):
                title = h.get("title", "未命名")
                date_str = h.get("date", "")[:10]
                mode_name = MODE_LABELS.get(h.get("mode", ""), "")
                scene_count = h.get("scene_count", 0)
                with st.expander(f"{title}"):
                    st.caption(f"{date_str} · {mode_name} · {scene_count}场")
                    if st.button("📂 加载", key=f"load_{i}", use_container_width=True):
                        load_history_entry(h)

        st.markdown("---")
        st.caption("v1.1 · Powered by AI")

    # 返回选中的菜单
    return menu

# ── 首页 ───────────────────────────────────────────────
def page_home():
    st.markdown('<div class="hero-title">AI Novel To Script</div>', unsafe_allow_html=True)
    st.caption("上传小说 → 选择模式 → 一键生成标准剧本")

    # 自动触发
    if st.session_state.get("trigger_generate") and st.session_state.novel_text:
        st.session_state.trigger_generate = False
        active_key = get_active_key()
        if not active_key:
            if trials_remaining() <= 0:
                st.error("免费次数已用完，请在侧边栏输入你的 API Key")
            else:
                st.error("API Key 未配置，请联系管理员")
        else:
            run_pipeline()

    # 未加载小说
    if not st.session_state.novel_text:
        st.markdown("---")
        tab1, tab2 = st.tabs(["📤 上传文件", "📝 粘贴文本"])

        with tab1:
            uploaded_file = st.file_uploader(
                "选择 TXT 或 DOCX 小说文件",
                type=["txt", "docx"],
            )
            if uploaded_file:
                if st.button("📖 读取文件", type="primary", use_container_width=True):
                    with st.spinner("读取中..."):
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
                            st.rerun()
                        except Exception as e:
                            st.error(f"读取失败: {e}")

        with tab2:
            novel_title = st.text_input("小说标题（可选）", placeholder="输入标题")
            pasted_text = st.text_area(
                "粘贴小说正文",
                height=320,
                placeholder="在此粘贴小说全文...",
            )
            if st.button("✅ 提交", type="primary", use_container_width=True):
                if len(pasted_text.strip()) < 50:
                    st.warning("文本太短")
                else:
                    st.session_state.novel_text = pasted_text.strip()
                    st.session_state.novel_title = novel_title or "未命名小说"
                    st.rerun()
        return

    # 已加载小说
    chapters = parse_chapter_list(st.session_state.novel_text)
    st.markdown("---")

    c_left, c_right = st.columns([5, 1])
    with c_left:
        st.markdown(f"### 📖 《{st.session_state.novel_title}》")
        st.caption(f"{len(st.session_state.novel_text)} 字 · {len(chapters)} 个章节")
    with c_right:
        if st.button("更换", type="secondary"):
            st.session_state.novel_text = ""
            st.session_state.novel_title = ""
            st.session_state.step = 0
            st.rerun()

    with st.expander(f"📋 章节列表"):
        for ch in chapters:
            st.write(f"第{ch['chapter_index']}章: {ch['chapter_title']}")

    st.info("👈 在左侧边栏选择改编模式，点击「生成剧本」即可")

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
        status_area.info("步骤 1/3: 解析章节...")
        chapters = split_chapters(text)
        st.session_state.chapters = chapters
        progress_bar.progress(10)

        status_area.info("步骤 2/3: AI 分析中...")

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

        st.session_state.all_scenes.sort(
            key=lambda s: (s.get("_chapter_idx", 0), s.get("scene_id", 0))
        )

        progress_bar.progress(100)
        scene_count = len(st.session_state.all_scenes)
        status_area.success(f"完成！共 {scene_count} 个场景")

        save_history_entry({
            "title": st.session_state.novel_title,
            "date": datetime.now().isoformat(),
            "mode": mode,
            "scene_count": scene_count,
            "characters": st.session_state.characters,
            "relations": st.session_state.relations,
            "summary": st.session_state.summary,
            "all_scenes": st.session_state.all_scenes,
            "novel_text": st.session_state.novel_text,
        })

        st.session_state.step = 3
        st.session_state.just_finished = True
        st.session_state.processing = False
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        status_area.error(f"处理出错: {e}")
        logger.exception("Pipeline error")
        st.session_state.processing = False

# ── 剧本预览 ───────────────────────────────────────────
def page_results():
    st.title(f"📖 《{st.session_state.novel_title}》")

    if not st.session_state.all_scenes:
        st.info("暂无剧本，请先生成")
        return

    # 默认显示传统剧本格式
    script_text = scenes_to_script_text(st.session_state.novel_title, st.session_state.all_scenes)

    st.markdown("---")
    st.markdown("### 📝 剧本")
    st.text_area(
        "剧本内容", script_text, height=550,
        key="main_script_display",
        label_visibility="collapsed",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "⬇ 下载 TXT", script_text,
            file_name=f"{st.session_state.novel_title}.txt",
            mime="text/plain", use_container_width=True,
        )
    with c2:
        script = build_script_from_chapters(
            st.session_state.novel_title, st.session_state.summary,
            st.session_state.characters, st.session_state.relations,
            st.session_state.all_scenes,
        )
        st.download_button(
            "⬇ 下载 YAML", script.to_yaml(),
            file_name=f"{st.session_state.novel_title}.yaml",
            mime="application/x-yaml", use_container_width=True,
        )
    with c3:
        st.download_button(
            "⬇ 下载 JSON", script.to_json(),
            file_name=f"{st.session_state.novel_title}.json",
            mime="application/json", use_container_width=True,
        )

    # 详细信息折叠区
    st.markdown("---")
    with st.expander("📊 人物角色 & 关系"):
        t1, t2 = st.tabs(["人物", "关系"])
        with t1:
            characters = st.session_state.characters
            if characters:
                cols = st.columns(3)
                for i, char in enumerate(characters):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.markdown(f"**{char.get('name', '?')}**")
                            st.caption(char.get("description", ""))
            else:
                st.info("无数据")
        with t2:
            relations = st.session_state.relations
            if relations:
                for rel in relations:
                    st.markdown(
                        f"**{rel.get('source', '?')}** → "
                        f"{rel.get('relation', '?')} → "
                        f"**{rel.get('target', '?')}**"
                    )
            else:
                st.info("无数据")

    if st.session_state.summary:
        with st.expander("📖 剧情摘要"):
            st.write(st.session_state.summary)

    with st.expander("📄 YAML 源码"):
        st.code(script.to_yaml(), language="yaml", line_numbers=True)

    # 按场景浏览
    with st.expander("🎬 逐场景查看"):
        scenes = st.session_state.all_scenes
        scene_ids = [
            f"场景{s.get('scene_id', i + 1)}: {s.get('location', '?')}"
            for i, s in enumerate(scenes)
        ]
        selected = st.selectbox(
            "选择场景", range(len(scene_ids)),
            format_func=lambda i: scene_ids[i],
        )
        scene = scenes[selected]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("📍 地点", scene.get("location", "?"))
        with c2:
            st.metric("🕐 时间", scene.get("time", "?"))
        with c3:
            st.metric("🎭 情绪", scene.get("emotion", "?"))

        for a in scene.get("actions", []):
            st.caption(f"🎬 {a.get('actor', '?')} {a.get('content', '')}")
        for d in scene.get("dialogues", []):
            st.markdown(f"""
            <div class="dialogue-bubble">
                <span class="speaker">{d.get('speaker', '?')}</span>：{d.get('content', '')}
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 重写此场景", type="secondary"):
            active_key = get_active_key()
            if active_key:
                with st.spinner("重写中..."):
                    try:
                        new_content = regenerate_scene(active_key, scene, st.session_state.mode)
                        if new_content.get("actions"):
                            st.session_state.all_scenes[selected]["actions"] = new_content["actions"]
                        if new_content.get("dialogues"):
                            st.session_state.all_scenes[selected]["dialogues"] = new_content["dialogues"]
                        st.success("已更新")
                        st.rerun()
                    except Exception as e:
                        st.error(f"失败: {e}")

# ── 主入口 ─────────────────────────────────────────────
def main():
    inject_css()
    menu = render_sidebar()

    if st.session_state.get("just_finished"):
        st.session_state.just_finished = False
        page_results()
        return

    if "首页" in menu:
        page_home()
    elif "剧本预览" in menu:
        page_results()
    else:
        page_results()  # 下载页合并到预览页

if __name__ == "__main__":
    main()
