from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any


def rule_summary(payload: dict[str, Any]) -> str:
    states = payload.get("candidate_macro_states") or ["数据分化、暂难判断"]
    dimensions = payload.get("dimension_scores") or []
    eligible = [item for item in dimensions if item.get("can_enter_summary")]
    positives = [item["dimension_name"] for item in eligible if item.get("score") is not None and item["score"] >= 0.5]
    negatives = [item["dimension_name"] for item in eligible if item.get("score") is not None and item["score"] <= -0.5]
    if not positives and not negatives:
        return "多数关键维度证据不足或处于中性区间，当前暂难形成高置信度主判断。"
    parts = [f"当前更接近“{'、'.join(states)}”"]
    if positives:
        parts.append(f"主要支撑来自{'、'.join(positives[:2])}")
    if negatives:
        parts.append(f"主要约束来自{'、'.join(negatives[:2])}")
    return "；".join(parts) + "。"


def _weak_evidence_risks(payload: dict[str, Any]) -> list[str]:
    return [f"{item['dimension_name']}虽出现方向性信号，但证据质量较弱，不进入主判断。" for item in payload.get("dimension_scores", []) if item.get("score") is not None and abs(item["score"]) >= 0.5 and not item.get("can_enter_summary")]


def fallback_judgement(payload: dict[str, Any], reason: str = "not_configured") -> dict[str, Any]:
    confidence_counts = {level: sum(1 for item in payload.get("dimension_scores", []) if item.get("confidence") == level) for level in ("高", "中", "低")}
    data_confidence = "高" if confidence_counts["高"] >= 5 else "中" if confidence_counts["高"] + confidence_counts["中"] >= 4 else "低"
    return {
        "one_sentence_summary": rule_summary(payload),
        "macro_state_labels": payload.get("candidate_macro_states", []),
        "overall_tone": "中性",
        "dimension_interpretations": [],
        "key_relation_interpretations": [],
        "top_divergences": [],
        "main_judgement": "未启用 GPT 解读，当前显示规则引擎分析结果。" if reason == "not_configured" else "GPT 调用失败，当前显示规则引擎分析结果。",
        "next_watchlist": _rule_watchlist(payload),
        "risk_notes": ["当前报告未包含 GPT 自然语言解读。", *_weak_evidence_risks(payload), "规则得分不构成投资建议。"],
        "data_confidence": data_confidence,
        "learning_note": "先观察信号是否跨频率共振，再判断单项变化是否代表趋势。",
        "gpt_enabled": False,
        "gpt_status": reason,
    }


def _rule_watchlist(payload: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for divergence in payload.get("detected_divergences", [])[:3]:
        items.extend(divergence.get("what_to_watch_next", []))
    if not items:
        for dimension in payload.get("dimension_scores", []):
            items.extend(dimension.get("stale_indicators", [])[:1])
    return list(dict.fromkeys(items))[:6]


def generate_gpt_judgement(payload: dict[str, Any], prompts_root: Path) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback_judgement(payload)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    system_prompt = (prompts_root / "macro_analysis_system.txt").read_text(encoding="utf-8")
    template = (prompts_root / "macro_analysis_user_template.txt").read_text(encoding="utf-8")
    user_prompt = template.replace("{{DAILY_MACRO_PAYLOAD_JSON}}", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        judgement = json.loads(content)
        valid_states = set(payload.get("candidate_macro_states", []))
        judgement["one_sentence_summary"] = rule_summary(payload)
        judgement["macro_state_labels"] = [item for item in judgement.get("macro_state_labels", []) if item in valid_states]
        judgement["risk_notes"] = list(dict.fromkeys([*judgement.get("risk_notes", []), *_weak_evidence_risks(payload)]))
        judgement["gpt_enabled"] = True
        judgement["gpt_status"] = "ok"
        judgement["model"] = model
        return judgement
    except Exception:  # The dashboard must remain usable even when the optional API fails.
        return fallback_judgement(payload, "api_failed")


def render_markdown(payload: dict[str, Any], judgement: dict[str, Any]) -> str:
    dimensions = "\n".join(f"- **{item['dimension_name']}**：{item.get('score')}｜{item['label']}｜置信度{item['confidence']}" for item in payload.get("dimension_scores", []))
    relations = "\n".join(f"- **{item['relation_name']}**：{item['conclusion']}（置信度{item['confidence']}）" for item in payload.get("relation_diagnostics", []))
    divergences = "\n".join(f"- **{item['title']}**（{item['severity']}）：{item['interpretation']}" for item in payload.get("detected_divergences", [])[:3]) or "- 暂未检测到达到阈值的重要背离。"
    states = "、".join(judgement.get("macro_state_labels") or payload.get("candidate_macro_states") or ["数据不足"])
    watchlist = "\n".join(f"- {item}" for item in judgement.get("next_watchlist", [])) or "- 等待下一批关键数据更新。"
    risks = "\n".join(f"- {item}" for item in judgement.get("risk_notes", []))
    return f"""# 每日宏观分析判断

> 生成时间：{payload.get('generated_at', '')}
> 用于宏观学习和研究观察，不构成投资建议。

## 一句话总判断

{judgement.get('one_sentence_summary', '')}

## 宏观状态标签

{states}

## 8 个维度打分

{dimensions}

## 关键组合关系

{relations}

## 今日重要背离

{divergences}

## 主体分析

{judgement.get('main_judgement', '')}

## 后续观察指标

{watchlist}

## 数据质量与风险提示

数据置信度：{judgement.get('data_confidence', '未知')}

{risks}

## 今日宏观学习笔记

{judgement.get('learning_note', '')}
"""
