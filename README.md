# Lantern

Lantern infers the shape of a web page from its accessibility tree. It probes a page in headless Chromium, records the role and state of each focusable element in tab order, and turns that sequence into a fingerprint that can be compared across sites. I built it as the upstream classifier for Foxworks Sherpa, a separate browser-agent project that is still private, behind one frozen call: `classify(url) -> LanternResult`.

## Status

Paused. The Lantern side is complete through the public-surface freeze, with 259 tests passing. The final utility phase needs a call site in Sherpa that does not exist yet, so the investigation stops at the L-12 pause note in `adrs/`.

## Run it

Needs Python 3.12 and uv.

```
uv sync
uv run playwright install chromium
uv run pytest
```

The unit tests finish in about 20 seconds. The probe and rescan tests start a local fixture server and drive real Chromium, so the full run takes a few minutes.

## The main decision

I read the accessibility tree instead of the DOM. The DOM is whatever a framework happened to emit, and it changes with every deploy. The accessibility tree is what a page has to expose to work at all, so it is the most stable description of a site's interaction surface. That choice fixed the method: a fingerprint is the ordered sequence of (role, state, landmark) tuples reached by tabbing through the page, and two pages have the same shape when those sequences are close under an edit distance. It also set the limit. Across 40 public sites the method found a library of only five shape clusters, and one catch-all cluster held half of the surviving sites, so the fingerprint under-discriminates on medium-complexity pages. I recorded that result in the L-07 report instead of tuning the method after seeing the data. Every phase was pre-registered in `LANTERN.md` and each verdict is written up in `adrs/`.
