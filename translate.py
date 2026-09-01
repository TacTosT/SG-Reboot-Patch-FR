#!/usr/bin/env python
"""Batch-translate STEINS;GATE RE:BOOT dialogue to French via the Claude API.

Cost design — three multiplicative levers:

  1. Batch API           -50% on every token (asynchronous, up to 24h)
  2. Prompt caching      the system prompt + both glossaries are byte-identical
                         across every request, so they are written once and read
                         at ~0.1x thereafter instead of paying full price ~1200x

Effort is deliberately NOT a cost lever here. This text is judgment-dense —
register switching between Okabe and Hououin Kyouma, Luka's grammatical gender,
2chan slang into French net slang, semantic furigana, tag fidelity across a full
reword. `high` is the default; the gap to `low` is roughly $32 across the entire
game, which is not a trade worth making. Sweep downward only if an A/B on the
prologue shows quality actually holds.

Correctness design — the lesson from the NEKOPARA pipeline run: structured
outputs enforce SHAPE, never COMPLETENESS. A batch can report "succeeded",
return valid JSON, and still silently omit lines. Every returned chunk is
therefore diffed against the ids that were requested, and the gaps are retried
in smaller chunks. Never trust a batch status alone.

Usage:
    python translate.py estimate --chapter 00        # free, uses count_tokens
    python translate.py submit   --chapter 00        # costs money, asks first
    python translate.py poll                         # resume/collect a batch
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT_DIR = os.path.join(HERE, "prompt")
EXTRACTED = os.path.join(HERE, "extracted")
STATE = os.path.join(HERE, "batch_state.json")

DEFAULT_MODEL = "claude-opus-5"
LINES_PER_CHUNK = 20
RETRY_LINES_PER_CHUNK = 5
MAX_TOKENS = 16000

# Structured output: shape only. Array constraints (minItems) are not supported
# by the schema validator, so completeness is checked client-side below.
SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "fr": {"type": "string"},
                },
                "required": ["id", "fr"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["lines"],
    "additionalProperties": False,
}


def load_system_blocks():
    """System prompt + glossaries, as one cached prefix shared by every request.

    Order matters: this content is byte-identical across the whole batch, so it
    forms a stable cache prefix. Nothing volatile may appear before the
    cache_control breakpoint.
    """
    with open(os.path.join(PROMPT_DIR, "system_fr.md"), encoding="utf-8") as f:
        system = f.read()
    with open(os.path.join(PROMPT_DIR, "glossary_fr.md"), encoding="utf-8") as f:
        glossary = f.read()
    with open(os.path.join(PROMPT_DIR, "tips_glossary.tsv"), encoding="utf-8") as f:
        tips = f.read()

    text = (
        f"{system}\n\n---\n\n# glossary_fr.md\n\n{glossary}\n\n"
        f"---\n\n# tips_glossary.tsv\n\n```tsv\n{tips}```\n"
    )
    # 1h TTL: a large batch can spread over an hour, and a 5m entry would expire
    # mid-run and force re-writes. The 2x write premium is paid once.
    return [{"type": "text", "text": text,
             "cache_control": {"type": "ephemeral", "ttl": "1h"}}]


def render_chunk(rows):
    """The volatile part of the prompt — must come after the cached prefix."""
    parts = []
    for r in rows:
        speaker = r["speaker"] or "(narration — pensées d'Okabe)"
        block = [f"### {r['id']}", f"Locuteur : {speaker}"]
        if r.get("voice"):
            block.append(f"Voix : {r['voice']}")
        block.append(f"JA : {r['texts'].get('ja', '')}")
        if r["texts"].get("en"):
            block.append(f"EN (référence) : {r['texts']['en']}")
        parts.append("\n".join(block))

    ids = "\n".join(f"- {r['id']}" for r in rows)
    return (
        "Traduis en français les répliques ci-dessous.\n\n"
        + "\n\n".join(parts)
        + f"\n\n---\n\nRends un objet JSON avec une clé `lines` contenant "
        f"**exactement {len(rows)} entrées**, une par identifiant, dans cet ordre :\n{ids}"
    )


def load_rows(args):
    if args.chapter:
        path = os.path.join(EXTRACTED, f"chapter{args.chapter}.jsonl")
    elif args.file:
        path = os.path.join(EXTRACTED, f"{os.path.splitext(args.file)[0]}.jsonl")
    else:
        path = os.path.join(EXTRACTED, "all.jsonl")
    if not os.path.exists(path):
        sys.exit(f"missing {path} — run extract_dialogue.py for this selection first")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def chunks(rows, size):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def build_requests(rows, model, effort, size=LINES_PER_CHUNK):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    system = load_system_blocks()
    out, index = [], {}
    for n, group in enumerate(chunks(rows, size)):
        cid = f"chunk-{n:05d}"
        index[cid] = [r["id"] for r in group]
        out.append(Request(
            custom_id=cid,
            params=MessageCreateParamsNonStreaming(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                output_config={
                    "effort": effort,
                    "format": {"type": "json_schema", "schema": SCHEMA},
                },
                messages=[{"role": "user", "content": render_chunk(group)}],
            ),
        ))
    return out, index


def normalize(text: str) -> str:
    """Fix encoding-level mismatches the model reliably makes.

    The engine's line break is the two-character sequence backslash-n, but a
    model writing JSON naturally emits a real newline for the same intent. The
    translation is correct; only the encoding differs — so repair it rather than
    burning a retranslation. Same for NBSP (breaks the engine's word wrap) and
    three-dot ellipses.
    """
    return (text.replace("\r\n", "\n")
                .replace("\n", "\\n")
                .replace(" ", " ")
                .replace("...", "…"))


def client():
    import anthropic
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("note: no ANTHROPIC_API_KEY set — falling back to an `ant auth login` profile",
              file=sys.stderr)
    return anthropic.Anthropic()


# Batch API is half price. Output includes thinking tokens.
PRICES = {  # model: (input $/MTok, output $/MTok) at standard rates
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),   # introductory rate, ends 2026-08-31
    "claude-haiku-4-5": (1.00, 5.00),
}


def cmd_estimate(args):
    c = client()
    rows = load_rows(args)
    reqs, index = build_requests(rows, args.model, args.effort)
    system = load_system_blocks()

    # count_tokens is free. Measure the cached prefix once and one chunk body,
    # then extrapolate — counting all ~1200 chunks would be pointless traffic.
    prefix = c.messages.count_tokens(
        model=args.model, system=system,
        messages=[{"role": "user", "content": "x"}],
    ).input_tokens
    sample = reqs[len(reqs) // 2]
    full = c.messages.count_tokens(
        model=args.model, system=system,
        messages=sample["params"]["messages"],
    ).input_tokens
    body = max(full - prefix, 0)

    n = len(reqs)
    ja_chars = sum(r["ja_chars"] for r in rows)
    # French output runs roughly 1.5 tokens per JP source character, plus JSON
    # scaffolding; thinking at low effort is modest but real.
    est_out = int(ja_chars * 1.5) + n * 120

    in_price, out_price = PRICES.get(args.model, (5.00, 25.00))
    batch = 0.5
    cache_write = prefix * 2.0 * in_price / 1e6 * batch
    cache_read = prefix * 0.1 * in_price / 1e6 * n * batch
    fresh_in = body * in_price / 1e6 * n * batch
    out_cost = est_out * out_price / 1e6 * batch
    total = cache_write + cache_read + fresh_in + out_cost

    uncached = (prefix + body) * in_price / 1e6 * n * batch

    print(f"model            : {args.model}   effort={args.effort}")
    print(f"lines            : {len(rows):,}")
    print(f"requests         : {n:,}  ({LINES_PER_CHUNK} lines each)")
    print(f"cached prefix    : {prefix:,} tokens (system + both glossaries)")
    print(f"per-chunk body   : {body:,} tokens")
    print(f"est. output      : {est_out:,} tokens\n")
    print(f"  cache write    : ${cache_write:7.2f}   (once, 2x for the 1h TTL)")
    print(f"  cache reads    : ${cache_read:7.2f}   (0.1x x {n:,} requests)")
    print(f"  fresh input    : ${fresh_in:7.2f}")
    print(f"  output         : ${out_cost:7.2f}")
    print(f"  {'-' * 30}")
    print(f"  TOTAL          : ${total:7.2f}   (Batch API, 50% off)\n")
    print(f"without caching  : ${uncached + out_cost:7.2f}  -> caching saves "
          f"${uncached - cache_write - cache_read - fresh_in:,.2f}")


def cmd_submit(args):
    c = client()
    rows = load_rows(args)
    reqs, index = build_requests(rows, args.model, args.effort)

    print(f"{len(rows):,} lines -> {len(reqs):,} batch requests on {args.model}")
    if not args.yes:
        if input("This spends real money. Type 'go' to submit: ").strip() != "go":
            sys.exit("aborted")

    stem = (f"chapter{args.chapter}" if args.chapter
            else os.path.splitext(args.file)[0] if args.file else "all")
    batch = c.messages.batches.create(requests=reqs)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"batch_id": batch.id, "model": args.model,
                   "index": index, "stem": stem}, f)
    print(f"submitted {batch.id} ({batch.processing_status}) -> state in {STATE}")
    print("collect with:  python translate.py poll")


def cmd_poll(args):
    c = client()
    if not os.path.exists(STATE):
        sys.exit("no batch_state.json — nothing to poll")
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    batch_id, index = state["batch_id"], state["index"]

    while True:
        batch = c.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            break
        counts = batch.request_counts
        print(f"  {batch.processing_status}: {counts.succeeded} ok, "
              f"{counts.processing} running, {counts.errored} errored", flush=True)
        time.sleep(args.interval)

    got, errors = {}, []
    # Results arrive in arbitrary order — always key by custom_id, never position.
    for result in c.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            errors.append((result.custom_id, result.result.type))
            continue
        text = next((b.text for b in result.result.message.content if b.type == "text"), "")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            errors.append((result.custom_id, "unparseable_json"))
            continue
        for item in payload.get("lines", []):
            got[item["id"]] = normalize(item["fr"])

    # The completeness check that a "succeeded" status does not give you.
    wanted = {i for ids in index.values() for i in ids}
    missing = sorted(wanted - set(got))

    out = os.path.join(EXTRACTED, f"{state['stem']}_fr.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for i in sorted(got):
            f.write(json.dumps({"id": i, "fr": got[i]}, ensure_ascii=False) + "\n")

    print(f"\nreturned : {len(got):,} / {len(wanted):,} lines")
    print(f"errors   : {len(errors)}")
    print(f"missing  : {len(missing)}")
    print(f"wrote    : {out}")
    if missing:
        gap = os.path.join(EXTRACTED, f"{state['stem']}_missing.json")
        with open(gap, "w", encoding="utf-8") as f:
            json.dump(missing, f)
        print(f"\n{len(missing)} lines were silently omitted — this is expected and")
        print(f"is why we diff. Ids written to {gap}; resubmit them with")
        print(f"  python translate.py submit --retry (chunks of {RETRY_LINES_PER_CHUNK})")
    print(f"\nvalidate with:  python validate.py extracted/{state['stem']}.jsonl {out}")


def cmd_retry(args):
    """Fill gaps left by a previous run, merging straight into the main file.

    Smaller chunks than the main pass: whatever made the model drop these lines
    the first time is less likely to bite on 5 at a time.
    """
    gap_file = os.path.join(EXTRACTED, f"{args.stem}_missing.json")
    target = os.path.join(EXTRACTED, f"{args.stem}_fr.jsonl")
    if not os.path.exists(gap_file):
        sys.exit(f"no gap file at {gap_file} — nothing to retry")
    with open(gap_file, encoding="utf-8") as f:
        missing = set(json.load(f))
    with open(os.path.join(EXTRACTED, f"{args.stem}.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if json.loads(l)["id"] in missing]

    print(f"{len(rows)} missing lines -> chunks of {RETRY_LINES_PER_CHUNK}")
    if not rows:
        return
    c = client()
    reqs, index = build_requests(rows, args.model, args.effort, RETRY_LINES_PER_CHUNK)
    if not args.yes:
        if input(f"submit {len(reqs)} requests? type 'go': ").strip() != "go":
            sys.exit("aborted")

    batch = c.messages.batches.create(requests=reqs)
    print(f"submitted {batch.id}")
    while c.messages.batches.retrieve(batch.id).processing_status != "ended":
        time.sleep(15)

    got = {}
    for result in c.messages.batches.results(batch.id):
        if result.result.type != "succeeded":
            continue
        text = next((b.text for b in result.result.message.content if b.type == "text"), "")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        for item in payload.get("lines", []):
            got[item["id"]] = normalize(item["fr"])

    existing = {}
    if os.path.exists(target):
        with open(target, encoding="utf-8") as f:
            existing = {json.loads(l)["id"]: json.loads(l)["fr"] for l in f}
    existing.update(got)
    with open(target, "w", encoding="utf-8") as f:
        for i in sorted(existing):
            f.write(json.dumps({"id": i, "fr": existing[i]}, ensure_ascii=False) + "\n")

    still = sorted(missing - set(got))
    print(f"recovered {len(got)} / {len(missing)}   -> merged into {target}")
    if still:
        with open(gap_file, "w", encoding="utf-8") as f:
            json.dump(still, f)
        print(f"still missing: {len(still)} (gap file updated)")
    else:
        os.remove(gap_file)
        print("gap closed — all lines present")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("retry")
    p.add_argument("--stem", default="all")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--effort", default="high",
                   choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--yes", action="store_true")

    for name in ("estimate", "submit"):
        p = sub.add_parser(name)
        p.add_argument("--chapter", help="e.g. 00")
        p.add_argument("--file", help="e.g. resg00_01.ks")
        p.add_argument("--model", default=DEFAULT_MODEL)
        p.add_argument("--effort", default="high",
                       choices=["low", "medium", "high", "xhigh", "max"])
        if name == "submit":
            p.add_argument("--yes", action="store_true", help="skip the confirmation")

    p = sub.add_parser("poll")
    p.add_argument("--interval", type=int, default=60)

    args = ap.parse_args()
    {"estimate": cmd_estimate, "submit": cmd_submit,
     "poll": cmd_poll, "retry": cmd_retry}[args.cmd](args)


if __name__ == "__main__":
    main()
