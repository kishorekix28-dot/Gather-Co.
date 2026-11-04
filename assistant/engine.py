"""Retrieval-first assistant.

1. Look for an HTTP error code (or error title) in the question -> ErrorCode table.
2. Score FAQs and help articles with IDF-weighted keyword coverage.
3. If the best match is confident, answer from the database (optionally
   rephrased by an LLM that is only given the retrieved text).
4. Otherwise do NOT guess: create (or reuse) a support ticket.
"""
import hashlib
import math
import re
from dataclasses import dataclass, field

from . import llm
from .models import FAQ, ErrorCode, HelpArticle

STOPWORDS = set("""
a an the i me my we our you your is are was were be been am do does did doing to of in on for with at by from
and or but if then so how what why when where which who whom can could should would will shall may might must
it its this that these those there here please tell explain show give about into up out as just get got any some
not no want need know like im i'm hi
""".split())

SYNONYMS = {
    "items": "product", "item": "product", "goods": "product", "products": "product",
    "inventory": "stock", "quantity": "stock", "qty": "stock", "units": "stock",
    "remove": "delete", "erase": "delete", "modify": "edit", "change": "edit", "update": "edit",
    "csv": "export", "download": "export", "excel": "export", "vendor": "supplier", "vendors": "supplier",
    "suppliers": "supplier", "receive": "stockin", "received": "stockin", "restock": "stockin",
    "sell": "stockout", "sold": "stockout", "dispatch": "stockout", "issue": "stockout",
    "log": "history", "logs": "history", "movement": "history", "pwd": "password",
    "missing": "appear", "appearing": "appear", "visible": "appear", "showing": "appear", "find": "appear",
}

ERROR_CODE_RE = re.compile(r"\b([1-5]\d{2})\b")
GREETINGS = {"hi", "hello", "hey", "thanks", "thank", "good morning", "good evening"}
CONFIDENCE_THRESHOLD = 0.5


def _stem(token):
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def tokenize(text):
    text = (text or "").lower()
    text = re.sub(r"\bstock[\s\-]+in\b", "stockin", text)
    text = re.sub(r"\bstock[\s\-]+out\b", "stockout", text)
    raw = re.findall(r"[a-z0-9]+", text)
    tokens = []
    for tok in raw:
        if tok in STOPWORDS:
            continue
        tok = SYNONYMS.get(tok, tok)
        tokens.append(_stem(tok))
    return tokens


def normalize_question(text):
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def question_hash(text):
    return hashlib.sha256(normalize_question(text).encode()).hexdigest()


@dataclass
class Candidate:
    kind: str
    obj: object
    text_tokens: set = field(default_factory=set)
    title_tokens: set = field(default_factory=set)
    question_tokens: set = field(default_factory=set)


@dataclass
class AssistantResult:
    answer: str
    source: str  # faq | error_database | help_docs | ai_fallback | system
    confidence: float = 0.0
    matched: dict | None = None
    needs_ticket: bool = False
    used_llm: bool = False


def _candidates():
    items = []
    for faq in FAQ.objects.filter(is_active=True):
        question = set(tokenize(faq.question))
        title = question | set(tokenize(faq.keywords.replace(",", " ")))
        items.append(Candidate("faq", faq, title | set(tokenize(faq.answer)), title, question))
    for art in HelpArticle.objects.filter(is_active=True):
        question = set(tokenize(art.title))
        title = question | set(tokenize(art.keywords.replace(",", " ")))
        items.append(Candidate("help", art, title | set(tokenize(art.content)), title, question))
    return items


def _score(query_tokens, candidates):
    n = len(candidates) or 1
    df = {}
    for c in candidates:
        for t in c.text_tokens:
            df[t] = df.get(t, 0) + 1
    unknown_idf = math.log(n + 1) + 1.5

    def idf(t):
        return math.log((n + 1) / (df[t] + 0.5)) + 1 if t in df else unknown_idf

    query = set(query_tokens)
    total = sum(idf(t) for t in query) or 1.0
    best, best_key = None, (0.0, 0.0)
    for c in candidates:
        title_hit = sum(idf(t) for t in query if t in c.title_tokens)
        body_hit = sum(idf(t) for t in query if t in c.text_tokens and t not in c.title_tokens)
        coverage = (title_hit + 0.6 * body_hit) / total
        # Tie-break: how much of the stored question itself the user's words cover.
        precision = len(query & c.question_tokens) / (len(c.question_tokens) or 1)
        key = (round(coverage, 3), precision)
        if key > best_key:
            best, best_key = c, key
    return best, round(min(best_key[0], 1.0), 3)


def format_error(err):
    return (
        f"**Error {err.code} – {err.title}**\n\n{err.description}\n\n"
        f"**Possible causes:** {err.possible_causes}\n\n**Recommended solution:** {err.recommended_solution}"
    )


def find_error_code(message, tokens):
    match = ERROR_CODE_RE.search(message or "")
    if match:
        return ErrorCode.objects.filter(code=int(match.group(1))).first(), True
    if {"error", "mean", "code", "status"} & set(tokens) or "error" in (message or "").lower():
        for err in ErrorCode.objects.all():
            title_tokens = set(tokenize(err.title))
            if title_tokens and title_tokens <= set(tokens):
                return err, True
    return None, False


def answer(message):
    message = (message or "").strip()
    tokens = tokenize(message)
    lowered = normalize_question(message)

    if lowered in GREETINGS or (not tokens and lowered):
        return AssistantResult(
            "Hi! I'm the StockPilot assistant. Ask me how to add products, record stock, export reports, "
            "manage suppliers or what an error code means.", "system", 1.0)

    err, mentioned_error = find_error_code(message, tokens)
    if err:
        text = format_error(err)
        rephrased = llm.rephrase(message, text)
        return AssistantResult(rephrased or text, "error_database", 1.0,
                               {"type": "error_code", "code": err.code, "title": err.title}, used_llm=bool(rephrased))

    if tokens and not mentioned_error:
        best, score = _score(tokens, _candidates())
        if best and score >= CONFIDENCE_THRESHOLD:
            if best.kind == "faq":
                text, source = best.obj.answer, "faq"
                matched = {"type": "faq", "id": best.obj.pk, "question": best.obj.question}
            else:
                text, source = best.obj.content, "help_docs"
                matched = {"type": "help_article", "id": best.obj.pk, "title": best.obj.title}
            rephrased = llm.rephrase(message, text)
            return AssistantResult(rephrased or text, source, score, matched, used_llm=bool(rephrased))

    return AssistantResult(
        "I couldn't find a reliable answer to that in our knowledge base, so I won't guess. "
        "This question needs further assistance from our support team.",
        "ai_fallback", 0.0, None, needs_ticket=True)
