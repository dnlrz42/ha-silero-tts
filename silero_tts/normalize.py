"""Make Russian text speakable for Silero.

Silero silently drops digits and Latin letters, so we spell numbers out,
expand common symbols, and transliterate Latin words.
"""
import re

from num2words import num2words

MAX_CHUNK = 800  # Silero fails on very long inputs

UNITS = {
    "%": ("процент", "процента", "процентов"),
    "°": ("градус", "градуса", "градусов"),
}

LATIN_DIGRAPHS = [
    ("shch", "щ"), ("sch", "ш"), ("sh", "ш"), ("ch", "ч"), ("zh", "ж"),
    ("kh", "х"), ("ts", "ц"), ("th", "т"), ("ph", "ф"), ("ya", "я"),
    ("yu", "ю"), ("yo", "ё"), ("ee", "и"), ("oo", "у"), ("ck", "к"),
    ("qu", "кв"), ("ea", "и"),
]
LATIN_CHARS = dict(zip(
    "abcdefghijklmnopqrstuvwxyz",
    ["а", "б", "к", "д", "е", "ф", "г", "х", "и", "дж", "к", "л", "м",
     "н", "о", "п", "к", "р", "с", "т", "у", "в", "в", "кс", "й", "з"],
))


def plural(n: int, forms: tuple[str, str, str]) -> str:
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]


def say_number(raw: str) -> str:
    raw = raw.replace(",", ".")
    if "." in raw:
        return num2words(float(raw), lang="ru")
    return num2words(int(raw), lang="ru")


def _time(m: re.Match) -> str:
    h, mm = int(m.group(1)), int(m.group(2))
    if h > 24 or mm > 59:
        return m.group(0)
    if mm == 0:
        minutes = "ноль ноль"
    elif mm < 10:
        minutes = "ноль " + num2words(mm, lang="ru")
    else:
        minutes = num2words(mm, lang="ru")
    return f"{num2words(h, lang='ru')} {minutes}"


def _number(m: re.Match) -> str:
    sign, raw, unit = m.group(1) or "", m.group(2), m.group(3)
    words = say_number(raw)
    if sign == "+":
        words = "плюс " + words
    elif sign:
        words = "минус " + words
    if unit:
        forms = UNITS["%" if "%" in unit else "°"]
        is_fraction = any(c in raw for c in ".,")
        words += " " + (forms[1] if is_fraction else plural(int(raw), forms))
    return words


def _latin(m: re.Match) -> str:
    word = m.group(0).lower()
    for src, dst in LATIN_DIGRAPHS:
        word = word.replace(src, dst)
    word = re.sub(r"y(?=[aeiou])", "й", word).replace("y", "и")
    return "".join(LATIN_CHARS.get(c, c) for c in word)


def normalize(text: str) -> str:
    text = re.sub(r"[*_#`>|~]", " ", text)  # markdown from LLM replies
    text = re.sub(r"\b(\d{1,2}):(\d{2})\b", _time, text)
    text = re.sub(
        r"(?<![\w.,])([+\-−](?=\d))?(\d+(?:[.,]\d+)?)(\s*(?:°\s*[CСcс]?(?![А-Яа-яA-Za-z])|%))?",
        _number,
        text,
    )
    text = re.sub(r"[A-Za-z]+", _latin, text)
    text = text.replace("&", " и ").replace("№", " номер ")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """Split into chunks short enough for Silero, on sentence borders."""
    chunks: list[str] = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        while len(sentence) > MAX_CHUNK:
            cut = sentence.rfind(",", 0, MAX_CHUNK)
            if cut < MAX_CHUNK // 2:
                cut = sentence.rfind(" ", 0, MAX_CHUNK)
            if cut <= 0:
                cut = MAX_CHUNK
            chunks.append(sentence[: cut + 1].strip())
            sentence = sentence[cut + 1 :]
        if sentence.strip():
            chunks.append(sentence.strip())
    return chunks
