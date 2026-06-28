"""Prompt injection detection and sanitization utilities.

Provides defense-in-depth against prompt injection attacks by detecting
delimiter injection, instruction override, and abnormal characters before
user input reaches the LLM.
"""

import re
import unicodedata
from typing import Optional


# -- Delimiter / separator injection patterns ---------------------------------
_DELIMITER_PATTERNS: list[tuple[str, str]] = [
    (r"###\s*SYSTEM", "### SYSTEM delimiter injection"),
    (r"<\|im_start\|>", "<|im_start|> token injection"),
    (r"<\|im_end\|>", "<|im_end|> token injection"),
    (r"<\|endoftext\|>", "<|endoftext|> token injection"),
    (r"<\|end\|of\|prompt\|>", "<|end|of|prompt|> token injection"),
    (r"-{3,}\s*(system|user|assistant)", "--- role separator injection"),
    (r"\n{2,}(system|user|assistant|human|ai)\s*:", "role-switching prefix injection"),
    (r"^```\s*system\s*$", "code-fenced system role injection"),
    (r"^```\s*end\s*$", "code-fenced end tag"),
    (r"\n\s*END\s+INSTRUCTION", "END INSTRUCTION separator"),
    (r"<\|start_header\|>", "<|start_header|> injection"),
    (r"<\|end_header\|>", "<|end_header|> injection"),
    (r"<\|eot_id\|>", "<|eot_id|> injection"),
    (r"\[/INST\]", "[/INST] injection (Llama)"),
    (r"<\|begin_of_text\|>", "<|begin_of_text|> injection"),
    (r"<\|end_of_text\|>", "<|end_of_text|> injection"),
]


def contains_delimiter_injection(text: str) -> Optional[str]:
    """Check for delimiter/separator injection attempts.

    Returns the first matched description if found, or None if clean.
    """
    for pattern, description in _DELIMITER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return description
    return None


# -- Instruction override patterns --------------------------------------------
_INSTRUCTION_OVERRIDE_PATTERNS: list[tuple[str, str]] = [
    # English
    (r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
     "ignore previous instructions"),
    (r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
     "forget previous instructions"),
    (r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
     "disregard previous instructions"),
    (r"override\s+(all\s+)?(system\s+)?(instructions?|prompts?|rules?)",
     "override system instructions"),
    (r"you\s+are\s+now\s+(a\s+)?([A-Z]{2,}|an?\s+\w+\s+\w+)",
     "you are now role override"),
    (r"new\s+(system\s+)?(instructions?|prompts?|rules?)\s*(:|are|:)",
     "new instructions injection"),
    (r"your\s+(new\s+)?(system\s+)?prompt\s+(is|now|:)",
     "prompt redefinition"),
    (r"from\s+now\s+on\s+(you|your)\s+(are|must|will|should)",
     "behavioral override"),
    (r"act\s+as\s+(if\s+)?(you\s+are\s+)?(a\s+)?[A-Z]",
     "act as role injection"),
    (r"pretend\s+(you\s+are|to\s+be)",
     "pretend role injection"),
    (r"do\s+not\s+(follow|obey)\s+(the\s+)?(system\s+)?(instructions?|prompts?|rules?)",
     "do not follow instructions"),
    # Chinese
    (r"(忽略|忘掉|忘记|无视|别管|不要管)\s*(所有|之前|上面|前面|以上)?\s*(的?\s*)?(所有\s*)?(指令|提示|规则|要求|指示|说明)",
     "Chinese instruction override (忽略/忘掉)"),
    (r"你\s*(现在|从现在开始|接下来)\s*(是|扮演|作为|变成)\s*(一个|一名|一位)?",
     "Chinese role override (你现在是/扮演)"),
    (r"(不要|别再|禁止)\s*(遵守|遵循|按照|听从)\s*(系统\s*)?(指令|提示|规则)",
     "Chinese rule rejection"),
    (r"(重新|修改|更改)\s*(设定|定义|指定)\s*(你|你的)\s*(角色|身份|指令|规则)",
     "Chinese role redefinition"),
    (r"(把|将)\s*(你|你的)\s*(系统\s*)?(指令|提示|规则)\s*(改|换|替换)\s*(为|成)",
     "Chinese prompt replacement"),
]


def contains_instruction_override(text: str) -> Optional[str]:
    """Check for instruction-override / role-switching injection attempts.

    Returns the first matched description if found, or None if clean.
    """
    for pattern, description in _INSTRUCTION_OVERRIDE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return description
    return None


# -- Abnormal character detection ---------------------------------------------
# Zero-width characters
_ZERO_WIDTH_CHARS: set[str] = {
    "​",  # ZERO WIDTH SPACE
    "‌",  # ZERO WIDTH NON-JOINER
    "‍",  # ZERO WIDTH JOINER
    "‎",  # LEFT-TO-RIGHT MARK
    "‏",  # RIGHT-TO-LEFT MARK
    "﻿",  # ZERO WIDTH NO-BREAK SPACE (BOM)
    "⁠",  # WORD JOINER
    "⁡",  # FUNCTION APPLICATION
    "⁢",  # INVISIBLE TIMES
    "⁣",  # INVISIBLE SEPARATOR
    "⁤",  # INVISIBLE PLUS
    "­",  # SOFT HYPHEN
}

# Bidi override characters (Unicode bidi control)
_BIDI_OVERRIDE_CHARS: set[str] = {
    "‪",  # LEFT-TO-RIGHT EMBEDDING
    "‫",  # RIGHT-TO-LEFT EMBEDDING
    "‬",  # POP DIRECTIONAL FORMATTING
    "‭",  # LEFT-TO-RIGHT OVERRIDE
    "‮",  # RIGHT-TO-LEFT OVERRIDE
    "⁦",  # LEFT-TO-RIGHT ISOLATE
    "⁧",  # RIGHT-TO-LEFT ISOLATE
    "⁨",  # FIRST STRONG ISOLATE
    "⁩",  # POP DIRECTIONAL ISOLATE
}


def contains_abnormal_chars(text: str) -> Optional[str]:
    """Check for zero-width characters and bidi override characters.

    Returns a description if abnormal chars are found, or None if clean.
    """
    for ch in text:
        if ch in _ZERO_WIDTH_CHARS:
            return f"zero-width character U+{ord(ch):04X}"
        if ch in _BIDI_OVERRIDE_CHARS:
            return f"bidi override character U+{ord(ch):04X}"
    return None


# -- Sanitization ------------------------------------------------------------
def sanitize_for_prompt(text: str) -> str:
    """Sanitize user input for prompt use.

    Removes zero-width characters, bidi override characters, and normalizes
    Unicode. Does NOT strip legitimate punctuation or CJK characters.
    """
    # Remove zero-width and bidi override characters
    all_dangerous = _ZERO_WIDTH_CHARS | _BIDI_OVERRIDE_CHARS
    cleaned = "".join(ch for ch in text if ch not in all_dangerous)

    # Normalize Unicode (NFKC to catch homoglyph tricks)
    cleaned = unicodedata.normalize("NFKC", cleaned)

    # Replace excessive whitespace with single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


# -- Main check function -----------------------------------------------------
def check_injection(text: str) -> Optional[str]:
    """Run all injection detection checks on user input.

    Returns None if the text passes all checks, or an error message
    describing the first detected injection pattern.
    """
    # Check delimiter injection
    result = contains_delimiter_injection(text)
    if result:
        return f"检测到违规输入模式 (分隔符注入): {result}"

    # Check instruction override
    result = contains_instruction_override(text)
    if result:
        return f"检测到违规输入模式 (指令覆盖): {result}"

    # Check abnormal characters
    result = contains_abnormal_chars(text)
    if result:
        return f"检测到违规输入模式 (异常字符): {result}"

    return None
