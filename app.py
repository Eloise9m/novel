"""AI Novel To Script - AI小说转剧本工具"""

import os
import time
import logging

import streamlit as st

from utils.parser import split_chapters, parse_chapter_list, parse_docx, parse_txt, safe_json_parse
from utils.generator import (
    extract_characters,
    extract_scenes,
    extract_dialogues_and_actions,
    extract_relations,
    generate_summary,
    generate_script,
    regenerate_scene,
)
from utils.yaml_export import ScriptYAML, build_script_from_chapters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI Novel To Script",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 初始化 Session State ----
DEFAULTS = {
    "api_key": "",
    "novel_text": "",
    "novel_title": "",
    "chapters": [],
    "characters": [],
    "relations": [],
    "summary": "",
    "all_scenes": [],
    "current_scene_idx": 0,
    "mode": "faithful",
    "step": 0,            # 处理步骤: 0=未开始, 1=已解析章节, 2=已识别人物, 3=已生成剧本
    "processing": False,
    "progress": 0,
    "status_text": "",
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


def reset_all():
    """重置所有状态"""
    for key, val in DEFAULTS.items():
        st.session_state[key] = val


# ---- 侧边栏 ----
def render_sidebar():
    with st.sidebar:
        st.title("AI Novel To Script")
        st.markdown("---")

        st.markdown("### API 设置")
        api_key = st.text_input(
            "豆包 API Key",
            type="password",
            value=st.session_state.api_key,
            placeholder="sk-...",
            help="在 https://console.volcengine.com/ark 获取（每日免费50万token）",
        )
        if api_key != st.session_state.api_key:
            st.session_state.api_key = api_key

        st.markdown("---")

        st.markdown("### 生成模式")
        mode_labels = {
            "faithful": "忠实原著",
            "dramatic": "影视化改编",
            "dialogue_enhanced": "对话增强",
            "stage_play": "舞台剧模式",
        }
        mode = st.radio(
            "选择改编模式",
            options=list(mode_labels.keys()),
            format_func=lambda x: mode_labels[x],
            index=list(mode_labels.keys()).index(st.session_state.mode),
        )
        st.session_state.mode = mode

        st.markdown("---")
        mode_descriptions = {
            "faithful": "尽量保留原文内容和对白",
            "dramatic": "增加戏剧冲突和视觉张力",
            "dialogue_enhanced": "丰富人物对白，增加潜台词",
            "stage_play": "适合话剧舞台演出",
        }
        st.caption(f"当前模式: {mode_descriptions.get(mode, '')}")

        st.markdown("---")
        if st.button("重新开始", use_container_width=True):
            reset_all()
            st.rerun()


# ---- 页面1: 首页 ----
def page_home():
    st.title("AI Novel To Script")
    st.markdown("### 将小说一键转换为影视剧本")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("支持格式", "TXT / DOCX")
    with col2:
        st.metric("AI引擎", "豆包 (免费)")
    with col3:
        st.metric("输出格式", "YAML / JSON")

    st.markdown("---")

    tab1, tab2 = st.tabs(["上传文件", "粘贴文本"])

    with tab1:
        uploaded_file = st.file_uploader(
            "选择小说文件（至少包含3章）",
            type=["txt", "docx"],
            help="支持TXT和DOCX格式",
        )
        if uploaded_file is not None:
            file_size = uploaded_file.size
            if file_size > 2 * 1024 * 1024:
                st.warning("文件较大（>2MB），建议使用章节较少的小说以获得更好效果")

            if st.button("读取文件", type="primary", use_container_width=True):
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
                        st.success(f"成功读取: {uploaded_file.name} ({len(text)} 字)")
                    except Exception as e:
                        st.error(f"读取失败: {e}")

    with tab2:
        novel_title = st.text_input("小说标题", placeholder="输入小说标题")
        pasted_text = st.text_area(
            "粘贴小说内容",
            height=300,
            placeholder="请粘贴小说全文（至少包含3章内容）...",
        )
        if st.button("确认提交", type="primary", use_container_width=True):
            if len(pasted_text.strip()) < 500:
                st.warning("文本内容过短，请至少粘贴3章以上的内容")
            else:
                st.session_state.novel_text = pasted_text.strip()
                st.session_state.novel_title = novel_title or "未命名小说"
                st.success(f"文本已提交 ({len(pasted_text)} 字)")

    # 小说就绪后的操作
    if st.session_state.novel_text:
        st.markdown("---")
        st.subheader(f"《{st.session_state.novel_title}》")

        chapters = parse_chapter_list(st.session_state.novel_text)
        st.info(f"识别到 **{len(chapters)}** 个章节")

        if len(chapters) < 3:
            st.warning("系统要求至少3章内容，当前识别章节数不足，但仍可继续")

        with st.expander("查看章节列表"):
            for ch in chapters:
                st.write(f"第{ch['chapter_index']}章: {ch['chapter_title']}")

        if st.button("开始生成剧本", type="primary", use_container_width=True, disabled=st.session_state.processing):
            if not st.session_state.api_key:
                st.error("请先在侧边栏输入豆包 API Key")
            else:
                run_pipeline()


# ---- 处理流水线 ----
def run_pipeline():
    """执行完整的处理流水线"""
    st.session_state.processing = True
    st.session_state.all_scenes = []
    st.session_state.step = 0

    text = st.session_state.novel_text
    api_key = st.session_state.api_key
    mode = st.session_state.mode

    progress_bar = st.progress(0)
    status_area = st.empty()

    try:
        # 步骤1: 拆分章节
        status_area.info("步骤 1/5: 解析章节...")
        chapters = split_chapters(text)
        st.session_state.chapters = chapters
        progress_bar.progress(20)

        # 步骤2: 识别人物
        status_area.info("步骤 2/5: AI识别角色人物...")
        char_result = extract_characters(api_key, text)
        characters = char_result.get("characters", [])
        st.session_state.characters = characters
        progress_bar.progress(40)

        # 步骤3: 人物关系
        status_area.info("步骤 3/5: AI分析人物关系...")
        char_names = [c.get("name", "") for c in characters if c.get("name")]
        rel_result = extract_relations(api_key, text, char_names)
        st.session_state.relations = rel_result.get("relations", [])
        progress_bar.progress(55)

        # 步骤3.5: 生成摘要
        status_area.info("生成剧情摘要...")
        summary = generate_summary(api_key, text)
        st.session_state.summary = summary
        progress_bar.progress(65)

        # 步骤4: 逐章生成场景
        for i, ch in enumerate(chapters):
            status_area.info(f"步骤 4/5: 正在生成第{i + 1}/{len(chapters)}章剧本...")

            if mode == "faithful":
                # 忠实原著模式：分步提取场景+对白动作
                scene_result = extract_scenes(api_key, ch["content"], ch["chapter_title"])
                scenes = scene_result.get("scenes", [])

                for scene in scenes:
                    scene_chars = scene.get("characters", [])
                    dialogue_text = "\n".join([
                        f"{a.get('actor', '')}{a.get('content', '')}"
                        for a in scene.get("actions", [])
                    ])
                    if not dialogue_text.strip():
                        dialogue_text = ch["content"][:2000]

                    da_result = extract_dialogues_and_actions(api_key, dialogue_text, scene_chars)
                    scene["actions"] = da_result.get("actions", [])
                    scene["dialogues"] = da_result.get("dialogues", [])
                    scene["chapter"] = ch["chapter_title"]
                    st.session_state.all_scenes.append(scene)
            else:
                # 其他模式：直接生成剧本
                script_result = generate_script(
                    api_key, ch["content"], ch["chapter_title"],
                    char_names, mode,
                )
                scenes = script_result.get("scenes", [])
                for scene in scenes:
                    scene["chapter"] = ch["chapter_title"]
                    st.session_state.all_scenes.append(scene)

            progress_bar.progress(65 + int(30 * (i + 1) / len(chapters)))
            time.sleep(0.3)  # 避免API限流

        # 步骤5: 完成
        progress_bar.progress(100)
        status_area.success(f"剧本生成完成！共 {len(st.session_state.all_scenes)} 个场景")
        st.session_state.step = 3
        time.sleep(1)
        st.rerun()

    except Exception as e:
        status_area.error(f"处理出错: {e}")
        logger.exception("Pipeline error")
        st.session_state.processing = False
        return


# ---- 页面2: 生成结果 ----
def page_results():
    st.title("剧本预览")
    st.markdown(f"### 《{st.session_state.novel_title}》")

    if st.session_state.summary:
        with st.expander("剧情摘要", expanded=False):
            st.write(st.session_state.summary)

    tabs = st.tabs(["人物角色", "角色关系", "场景剧本", "YAML预览"])

    with tabs[0]:
        render_characters_tab()

    with tabs[1]:
        render_relations_tab()

    with tabs[2]:
        render_scenes_tab()

    with tabs[3]:
        render_yaml_preview_tab()


def render_characters_tab():
    """人物角色标签页"""
    characters = st.session_state.characters
    if not characters:
        st.info("暂无人物数据")
        return

    cols = st.columns(3)
    for i, char in enumerate(characters):
        role_labels = {"main": "主角", "supporting": "配角", "npc": "龙套"}
        role = role_labels.get(char.get("role", ""), char.get("role", ""))
        role_emoji = {"main": "", "supporting": "", "npc": ""}.get(char.get("role", ""), "")
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {role_emoji} {char.get('name', '未知')}")
                st.caption(f"角色类型: {role}")
                st.write(char.get("description", "暂无描述"))


def render_relations_tab():
    """人物关系标签页"""
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

    st.markdown("---")
    st.caption("提示：未来版本将支持可视化关系图")


def render_scenes_tab():
    """场景剧本标签页"""
    scenes = st.session_state.all_scenes
    if not scenes:
        st.info("暂无场景数据，请先生成剧本")
        return

    scene_ids = [f"场景 {s.get('scene_id', i + 1)}: {s.get('location', '未知')}" for i, s in enumerate(scenes)]
    selected = st.selectbox("选择场景", range(len(scene_ids)), format_func=lambda i: scene_ids[i])
    st.session_state.current_scene_idx = selected

    scene = scenes[selected]

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("场景ID", scene.get("scene_id", selected + 1))
    with col2:
        st.metric("地点", scene.get("location", "未知"))
    with col3:
        st.metric("时间", scene.get("time", "未知"))
    with col4:
        emotion = scene.get("emotion", "未知")
        st.metric("情绪", emotion)

    st.markdown(f"**所属章节:** {scene.get('chapter', '未知')}")

    st.markdown("---")

    # 角色
    scene_chars = scene.get("characters", [])
    if scene_chars:
        st.markdown("#### 出场人物")
        st.markdown(", ".join([f"**{c}**" for c in scene_chars]))

    # 动作
    actions = scene.get("actions", [])
    if actions:
        st.markdown("#### 动作")
        for a in actions:
            st.markdown(f"- {a.get('actor', '?')} **{a.get('content', '')}**")

    # 对白
    dialogues = scene.get("dialogues", [])
    if dialogues:
        st.markdown("#### 对白")
        for d in dialogues:
            speaker = d.get("speaker", "?")
            content = d.get("content", "")
            st.markdown(f"""
            <div style="background:#f0f2f6;border-radius:10px;padding:10px 15px;margin:8px 0;">
                <strong>{speaker}</strong>: {content}
            </div>
            """, unsafe_allow_html=True)

    # 重新生成按钮
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("重新生成当前场景", type="secondary", use_container_width=True):
            if st.session_state.api_key:
                with st.spinner("AI重新编写中..."):
                    try:
                        new_content = regenerate_scene(
                            st.session_state.api_key,
                            scene,
                            st.session_state.mode,
                        )
                        if new_content.get("actions"):
                            st.session_state.all_scenes[selected]["actions"] = new_content["actions"]
                        if new_content.get("dialogues"):
                            st.session_state.all_scenes[selected]["dialogues"] = new_content["dialogues"]
                        st.success("场景已重新生成！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"重新生成失败: {e}")


def render_yaml_preview_tab():
    """YAML预览标签页"""
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
    yaml_content = script.to_yaml()
    st.code(yaml_content, language="yaml", line_numbers=True)


# ---- 页面3: 下载中心 ----
def page_download():
    st.title("下载中心")

    if not st.session_state.all_scenes:
        st.info("请先生成剧本后再访问下载中心")
        return

    script = build_script_from_chapters(
        st.session_state.novel_title,
        st.session_state.summary,
        st.session_state.characters,
        st.session_state.relations,
        st.session_state.all_scenes,
    )

    st.markdown("### 剧本文件下载")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### YAML 格式")
        yaml_content = script.to_yaml()
        st.download_button(
            label="下载 YAML 剧本",
            data=yaml_content,
            file_name=f"{st.session_state.novel_title}.yaml",
            mime="application/x-yaml",
            type="primary",
            use_container_width=True,
        )
        with st.expander("预览 YAML"):
            st.code(yaml_content[:3000], language="yaml")

    with col2:
        st.markdown("#### JSON 格式")
        json_content = script.to_json()
        st.download_button(
            label="下载 JSON 剧本",
            data=json_content,
            file_name=f"{st.session_state.novel_title}.json",
            mime="application/json",
            type="primary",
            use_container_width=True,
        )
        with st.expander("预览 JSON"):
            st.code(json_content[:3000], language="json")

    st.markdown("---")
    st.markdown("### 剧本信息统计")

    scenes = st.session_state.all_scenes
    dialogues_total = sum(len(s.get("dialogues", [])) for s in scenes)
    actions_total = sum(len(s.get("actions", [])) for s in scenes)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("场景数", len(scenes))
    with col2:
        st.metric("人物数", len(st.session_state.characters))
    with col3:
        st.metric("对白数", dialogues_total)
    with col4:
        st.metric("动作数", actions_total)


# ---- 主入口 ----
def main():
    render_sidebar()

    st.sidebar.markdown("---")

    menu = st.sidebar.radio(
        "导航",
        ["首页", "剧本预览", "下载中心"],
    )

    if menu == "首页":
        if st.session_state.step >= 3 and st.session_state.all_scenes:
            st.sidebar.success("剧本已生成")
        page_home()
    elif menu == "剧本预览":
        page_results()
    elif menu == "下载中心":
        page_download()

    st.sidebar.markdown("---")
    st.sidebar.caption("AI Novel To Script v1.0")
    st.sidebar.caption("Powered by 豆包 (Doubao)")


if __name__ == "__main__":
    main()
