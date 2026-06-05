"""小说解析模块 - 章节拆分、人物识别、场景分析"""

import re
import json
import logging
from typing import Any

from .prompt import CHAPTER_PATTERNS

logger = logging.getLogger(__name__)


def split_chapters(text: str) -> list[dict[str, Any]]:
    """根据章节标题将文本拆分为章节列表"""
    lines = text.split('\n')
    chapter_starts: list[tuple[int, str, int]] = []  # (line_index, title, chapter_num)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in CHAPTER_PATTERNS:
            if re.match(pattern, stripped):
                chapter_num = len(chapter_starts) + 1
                chapter_starts.append((i, stripped, chapter_num))
                break

    if not chapter_starts:
        return [{"chapter_index": 1, "chapter_title": "全文", "content": text}]

    chapters = []
    for idx, (line_idx, title, num) in enumerate(chapter_starts):
        start = line_idx
        end = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(lines)
        content = '\n'.join(lines[start:end]).strip()
        chapters.append({
            "chapter_index": num,
            "chapter_title": title,
            "content": content,
        })

    return chapters


def parse_chapter_list(text: str) -> list[dict[str, Any]]:
    """返回章节标题列表（不含正文）"""
    chapters = split_chapters(text)
    return [{"chapter_index": c["chapter_index"], "chapter_title": c["chapter_title"]} for c in chapters]


def safe_json_parse(response: str) -> dict[str, Any]:
    """安全解析AI返回的JSON"""
    response = response.strip()
    # 移除markdown代码块标记
    if response.startswith("```"):
        lines = response.split('\n')
        response = '\n'.join(lines[1:])
        if response.endswith("```"):
            response = response[:-3]
    response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # 尝试提取JSON对象
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # 尝试提取JSON数组
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from response: %s", response[:200])
        return {}


def parse_docx(file_path: str) -> str:
    """解析DOCX文件，返回纯文本"""
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return '\n'.join(paragraphs)


def parse_txt(file_path: str) -> str:
    """读取TXT文件，自动检测编码"""
    for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()
