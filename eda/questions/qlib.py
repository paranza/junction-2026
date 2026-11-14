"""Shared loading, language detection and template normalization for the questions EDA."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, re
import pandas as pd

DATASET = _DATA + "/"
WORK = _ROOT + "/eda/questions/"


def load():
    rows = [json.loads(l) for l in open(DATASET + "questions.jsonl", encoding="utf-8")]
    df = pd.DataFrame(rows)
    df["line"] = range(1, len(df) + 1)
    df["source"] = df.path.str.split("/").str[1]
    df["ext"] = df.path.str.rsplit(".", n=1).str[-1].str.lower()
    df["lang"] = df.question.map(detect_lang)
    return df


# Distinctive function words per language; scored by whole-word hits. Verified by reading samples.
CUES = {
    "en": r"\b(how|many|what|which|the|is|are|of|on|in|this|there|drawn|shown|labelled|floor)\b",
    "fi": r"\b(kuinka|monta|pohjapiirustuksessa|pohjapiirustukseen|on|piirretty|yhteensä|lasketaan)\b",
    "de": r"\b(wie|viele|gross|groß|sind|ist|auf|diesem|dieses|gibt|es|im|der|die|das|mit|enthält|von|aller)\b",
    "fr": r"\b(combien|quelle|est|de|la|le|sur|ce|cet|sont|portant|dessinées|dessinés|figurent|pièces|y|a-t-il)\b",
    "it": r"\b(quanti|quante|qual|è|sono|in|questa|questo|piano|pianta|ci|del|della|dei|locali|disegnate|disegnati)\b",
    "et": r"\b(mitu|on|kui|suur|mudelis|korruse|korrusel|plaanil|ruumi|näidatud)\b",
    "da": r"\b(hvor|mange|er|der|hvad|på|vist|plantegningen|modellen|i|af|det|den)\b",
}
CUE_RE = {k: re.compile(v, re.I) for k, v in CUES.items()}
# Words that are strong single-hit signals.
STRONG = {
    "fi": re.compile(r"\b(kuinka|monta)\b", re.I),
    "de": re.compile(r"\b(wie viele|wie gross|wie groß|wie lang)\b", re.I),
    "fr": re.compile(r"\b(combien|quelle est|quel est)\b", re.I),
    "it": re.compile(r"\b(quanti|quante|qual è|quale)\b", re.I),
    "et": re.compile(r"\b(mitu|kui suur)\b", re.I),
    "da": re.compile(r"\b(hvor mange|hvad er)\b", re.I),
    "en": re.compile(r"^(how|what|which|could|can|is|are|give|on sheet|does|do)\b", re.I),
}


def detect_lang(q):
    # Strip quoted names so labels in the drawing language do not vote.
    s = re.sub(r"«[^»]*»|„[^“”]*[“”]|“[^”]*”|(?<![A-Za-z])'[^']*'(?=[\s,?.)]|$)", " ", q)
    for lang, rx in STRONG.items():
        if rx.search(s):
            return lang
    scores = {k: len(rx.findall(s)) for k, rx in CUE_RE.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


# Template normalization: ordered substitutions, each to a typed placeholder.
QUOTED = re.compile(r"«\s*([^»]+?)\s*»|„([^“”]+)[“”]|“([^”]+)”|(?<![A-Za-z])'(.+?)'(?=[\s,?.)]|$)")
SUBS = [
    (re.compile(r"\b(sheet) [A-Z]-?\d{3}\b"), r"\1 <SHEET>"),
    (re.compile(r"\d+'-\d+(?: \d+/\d+)?\"?(?: x \d+'-\d+(?: \d+/\d+)?\"?)?"), "<DIM>"),
    (re.compile(r"\b\d{3}\.[A-Z]\d?(?:-\d{3}\.[A-Z]\d?)?\b"), "<DOOR_ID>"),
    (re.compile(r"\b[A-Z]?\d+\.\d{2}\b"), "<ROOM_ID>"),
    (re.compile(r"\b(apartment|Wohnung|appartamento|l'appartement|dell'appartamento) [A-Z]\b"), r"\1 <APT>"),
    (re.compile(r"\b(room|rooms) \d+\b"), r"\1 <ROOM_NO>"),
    (re.compile(r"\b(Level|level) [A-Z]\d{2}_\w+"), r"\1 <LEVEL>"),
    (re.compile(r"\b\d+(?:[.,]\d+)?\b"), "<NUM>"),
]


def normalize(q):
    """Return (template, list of quoted slot values)."""
    slots = []

    def qrep(m):
        val = next(g for g in m.groups() if g is not None)
        slots.append(val)
        return "<Q>"

    t = QUOTED.sub(qrep, q)
    for rx, rep in SUBS:
        t = rx.sub(rep, t)
    return t.strip(), slots
