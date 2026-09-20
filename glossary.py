"""게임 슬랭 사전 — 번역 품질을 가볍게 보정한다 (무료·오프라인·빠름 유지).

- SOURCE_SUB_EN/JA : 번역 '전' 원문에서 치환. 약어/슬랭을 일반 표현으로 풀어
  NLLB가 제대로 번역하게 한다. (예: gg → good game)
- TARGET_SUB       : 번역 '후' 한국어에서 치환. NLLB가 자주 틀리는 표현을 교정.

★ 게임하다가 어색한 번역을 보면 여기 딕셔너리에 한 줄씩 추가하면 끝.
  - 영어 약어/슬랭이면  SOURCE_SUB_EN 에  r"\\b단어\\b": "풀어쓴 표현"
  - 한국어 결과가 어색하면 TARGET_SUB 에  "틀린말": "고친말"
"""
import re

# 영어 약어/슬랭 → 풀어쓴 표현 (대소문자 무시, 단어 경계 \b)
SOURCE_SUB_EN = {
    r"\bgg\b": "good game",
    r"\bggwp\b": "good game well played",
    r"\bglhf\b": "good luck have fun",
    r"\bafk\b": "away from keyboard",
    r"\bbrb\b": "be right back",
    r"\bomw\b": "on my way",
    r"\binc\b": "incoming",
    r"\bmia\b": "missing",
    r"\bult\b": "ultimate",
    r"\bulti\b": "ultimate",
    r"\bnade\b": "grenade",
    r"\bnades\b": "grenades",
    r"\bdmg\b": "damage",
    r"\bhp\b": "health",
    r"\bcover me\b": "protect me",
    r"\bpush\b": "attack",
    r"\bpushing\b": "attacking",
    r"\bfall back\b": "retreat",
    r"\bback up\b": "retreat",
    r"\bgroup up\b": "gather together",
    r"\bregroup\b": "gather together",
    r"\brotate\b": "move to another lane",
    r"\bnerf\b": "weaken",
    r"\bbuff\b": "strengthen",
    r"\bnoob\b": "beginner",
    r"\bclutch\b": "win the round alone",
}

# 일본어 슬랭 → 일반 표현 (필요시 추가)
SOURCE_SUB_JA = {
    "ナイス": "良い",
}

# 한국어 출력 보정 — NLLB가 반복적으로 틀리는 것만 (과하면 오히려 망가지니 신중히)
TARGET_SUB = {
    # "잘못된 한국어": "고친 한국어",
}


def _apply_regex(text, table):
    for pat, rep in table.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    return text


def normalize_source(text, lang):
    """번역 전 원문 보정."""
    if lang == "en":
        return _apply_regex(text, SOURCE_SUB_EN)
    if lang == "ja":
        for a, b in SOURCE_SUB_JA.items():
            text = text.replace(a, b)
    return text


def fix_target(text):
    """번역 후 한국어 보정."""
    for a, b in TARGET_SUB.items():
        text = text.replace(a, b)
    return text
