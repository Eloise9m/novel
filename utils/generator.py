"""AI生成模块 - 调用大模型API进行各项AI分析"""

import json
import logging
from typing import Any

import httpx
from openai import OpenAI

from .prompt import (
    CHARACTER_EXTRACT_PROMPT,
    SCENE_EXTRACT_PROMPT,
    DIALOGUE_ACTION_PROMPT,
    RELATION_EXTRACT_PROMPT,
    SUMMARY_PROMPT,
    SCRIPT_GENERATE_PROMPTS,
    SCENE_REGENERATE_PROMPT,
)
from .parser import safe_json_parse

logger = logging.getLogger(__name__)

DOUBAO_BASE = "https://ark.cn-beijing.volces.com/api/v3"
DOUBAO_MODEL = "ep-m-20260605150614-lq69r"


def _get_client(api_key: str) -> OpenAI:
    http_client = httpx.Client(proxy=None, timeout=60.0)
    return OpenAI(api_key=api_key, base_url=DOUBAO_BASE, http_client=http_client)


def _call_api(client: OpenAI, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """调用大模型API"""
    resp = client.chat.completions.create(
        model=DOUBAO_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


def extract_characters(api_key: str, text: str) -> dict[str, Any]:
    """从小说文本中提取人物"""
    client = _get_client(api_key)
    # 只取前8000字用于人物识别
    truncated = text[:8000] if len(text) > 8000 else text
    result = _call_api(
        client,
        "你是一个专业的小说人物分析助手。请严格按照JSON格式返回结果。",
        CHARACTER_EXTRACT_PROMPT.format(text=truncated),
        temperature=0.3,
    )
    return safe_json_parse(result)


def extract_scenes(api_key: str, chapter_text: str, chapter_title: str) -> dict[str, Any]:
    """从章节文本中提取场景"""
    client = _get_client(api_key)
    truncated = chapter_text[:6000] if len(chapter_text) > 6000 else chapter_text
    result = _call_api(
        client,
        "你是一个专业的影视场景分析助手。请严格按照JSON格式返回结果。",
        SCENE_EXTRACT_PROMPT.format(text=f"【{chapter_title}】\n{truncated}"),
        temperature=0.5,
    )
    return safe_json_parse(result)


def extract_dialogues_and_actions(api_key: str, scene_text: str, characters: list[str]) -> dict[str, Any]:
    """从场景文本中提取对白和动作"""
    client = _get_client(api_key)
    truncated = scene_text[:4000] if len(scene_text) > 4000 else scene_text
    result = _call_api(
        client,
        "你是一个专业的剧本分析助手。请严格按照JSON格式返回结果。",
        DIALOGUE_ACTION_PROMPT.format(text=truncated, characters=", ".join(characters)),
        temperature=0.4,
    )
    return safe_json_parse(result)


def extract_relations(api_key: str, text: str, characters: list[str]) -> dict[str, Any]:
    """分析人物关系"""
    client = _get_client(api_key)
    truncated = text[:8000] if len(text) > 8000 else text
    result = _call_api(
        client,
        "你是一个专业的人物关系分析助手。请严格按照JSON格式返回结果。",
        RELATION_EXTRACT_PROMPT.format(text=truncated, characters=json.dumps(characters, ensure_ascii=False)),
        temperature=0.3,
    )
    return safe_json_parse(result)


def generate_summary(api_key: str, text: str) -> str:
    """生成剧情摘要"""
    client = _get_client(api_key)
    truncated = text[:10000] if len(text) > 10000 else text
    result = _call_api(
        client,
        "你是一个专业的小说编辑。请简洁地总结小说剧情。",
        SUMMARY_PROMPT.format(text=truncated),
        temperature=0.5,
    )
    return result.strip()


def generate_script(api_key: str, chapter_text: str, chapter_title: str,
                    characters: list[str], mode: str = "faithful") -> dict[str, Any]:
    """根据章节内容生成剧本"""
    client = _get_client(api_key)
    prompt_template = SCRIPT_GENERATE_PROMPTS.get(mode, SCRIPT_GENERATE_PROMPTS["faithful"])
    truncated = chapter_text[:6000] if len(chapter_text) > 6000 else chapter_text
    result = _call_api(
        client,
        "你是一个专业的影视编剧。请严格按照JSON格式返回结果。",
        prompt_template.format(
            text=f"【{chapter_title}】\n{truncated}",
            characters=json.dumps(characters, ensure_ascii=False),
        ),
        temperature=0.7,
    )
    return safe_json_parse(result)


def regenerate_scene(api_key: str, original_scene: dict[str, Any], mode: str = "faithful") -> dict[str, Any]:
    """重新生成单个场景的对白和动作"""
    client = _get_client(api_key)
    prompt_tmpl = SCRIPT_GENERATE_PROMPTS.get(mode, SCRIPT_GENERATE_PROMPTS["faithful"])
    result = _call_api(
        client,
        "你是一个专业的影视编剧。请严格按照JSON格式返回结果。",
        SCENE_REGENERATE_PROMPT.format(
            original_scene=json.dumps(original_scene, ensure_ascii=False),
            mode=mode,
        ),
        temperature=0.9,
    )
    return safe_json_parse(result)
