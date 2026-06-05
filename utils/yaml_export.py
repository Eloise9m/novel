"""YAML剧本导出模块"""

import json
from typing import Any
from datetime import datetime

import yaml


class ScriptYAML:
    """剧本YAML数据结构"""

    def __init__(self, title: str = "未命名剧本"):
        self.data: dict[str, Any] = {
            "title": title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": "",
            "characters": [],
            "relations": [],
            "scenes": [],
        }

    def set_summary(self, summary: str):
        self.data["summary"] = summary

    def add_characters(self, characters: list[dict[str, Any]]):
        self.data["characters"] = characters

    def add_relations(self, relations: list[dict[str, Any]]):
        self.data["relations"] = relations

    def add_scenes(self, scenes: list[dict[str, Any]]):
        """添加场景列表"""
        for scene in scenes:
            entry = {
                "scene_id": scene.get("scene_id", 0),
                "location": scene.get("location", ""),
                "time": scene.get("time", ""),
                "emotion": scene.get("emotion", ""),
                "characters": scene.get("characters", []),
                "actions": scene.get("actions", []),
                "dialogues": scene.get("dialogues", []),
            }
            self.data["scenes"].append(entry)

    def add_scene(self, scene: dict[str, Any]):
        """添加单个场景"""
        entry = {
            "scene_id": scene.get("scene_id", len(self.data["scenes"]) + 1),
            "location": scene.get("location", ""),
            "time": scene.get("time", ""),
            "emotion": scene.get("emotion", ""),
            "characters": scene.get("characters", []),
            "actions": scene.get("actions", []),
            "dialogues": scene.get("dialogues", []),
        }
        self.data["scenes"].append(entry)

    def to_yaml(self) -> str:
        """输出为YAML字符串"""
        return yaml.dump(
            self.data,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
        )

    def to_json(self) -> str:
        """输出为JSON字符串"""
        return json.dumps(self.data, ensure_ascii=False, indent=2)

    def save_yaml(self, filepath: str):
        """保存为YAML文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_yaml())

    def save_json(self, filepath: str):
        """保存为JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


def scenes_to_script_text(title: str, scenes: list[dict[str, Any]]) -> str:
    """将场景列表转换为传统剧本格式文本"""
    lines = []
    lines.append(f"《{title}》")
    lines.append("=" * 40)
    lines.append("")

    for s in scenes:
        sid = s.get("scene_id", "?")
        loc = s.get("location", "未知")
        time_str = s.get("time", "")
        emotion = s.get("emotion", "")

        lines.append(f"第{sid}场 | {loc} | {time_str} | {emotion}")
        lines.append("-" * 36)

        for a in s.get("actions", []):
            actor = a.get("actor", "")
            content = a.get("content", "")
            lines.append(f"  【{actor} {content}】")

        for d in s.get("dialogues", []):
            speaker = d.get("speaker", "?")
            content = d.get("content", "")
            lines.append(f"  {speaker}：{content}")

        lines.append("")

    return "\n".join(lines)


def build_script_from_chapters(title: str, summary: str, characters: list[dict[str, Any]],
                                relations: list[dict[str, Any]],
                                all_scenes: list[dict[str, Any]]) -> ScriptYAML:
    """从已有数据构建剧本"""
    script = ScriptYAML(title)
    script.set_summary(summary)
    script.add_characters(characters)
    script.add_relations(relations)
    # 重新编号场景
    for i, scene in enumerate(all_scenes, 1):
        scene["scene_id"] = i
    script.add_scenes(all_scenes)
    return script
