# Lantern

Probe-based schema inference for undocumented web surfaces. Lantern infers the shape of a website by reading its accessibility tree — the least-hidden, most-honest representation of any site's real interaction surface.

Lantern plugs into [Foxworks Sherpa](https://github.com/) as an upstream classifier via a single frozen contract (`classify(url) -> LanternResult`). Integration is soft-fallthrough: any Lantern failure leaves Sherpa's blind execution path untouched.

- **Methodology:** see [`LANTERN.md`](./LANTERN.md) — the frozen investigation spec.
- **Build contract:** see [`BUILD.md`](./BUILD.md) — Tier 3 cairn-explicit build, tickets R0 through L-14.

Lantern is a separate project from Sherpa and develops asynchronously.
