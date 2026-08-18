# Phase 0 findings — capability probe against the live account

**Probed:** 2026-08-18T09:28:49Z · `@fupingryuguitar` · 1,676 followers · 552 media
**Route:** Instagram API with Instagram Login → `graph.instagram.com` **v26.0**
**Evidence:** [`data/capabilities.json`](../data/capabilities.json)

Every claim below cites the probe. Where the probe did not settle a question,
it says so rather than guessing — several of the operating plan's open
questions are **still open** after Phase 0, and pretending otherwise would
defeat the point of running it.

---

## Headline

| | |
|---|---|
| **Phase 1 path** | **API path.** `trial_params` was accepted. Not the assisted-manual fallback. |
| **Scorer** | **Broken as specified.** `profile_visits` is unavailable per-media. One of four inputs is gone. |
| **Gates** | Both pass — 1,676 followers (≥1,000), account type `MEDIA_CREATOR`. |
| **Token** | Expiry **not measurable** on this route without mutating the token. |

---

## The four questions from operating-plan.md §14

### Q1 — Does the Content Publishing API accept `trial_params` / `graduation_strategy`?

**ANSWERED: yes, with a caveat worth keeping.**

```json
"trial_params": {
  "supported": true,
  "confidence": "high",
  "note": "Container was created unexpectedly...",
  "container_id": "18619475482009797"
}
```

The probe posted `media_type=REELS` with `trial_params={"graduation_strategy":"MANUAL"}`
and a deliberately unreachable `video_url`. Graph did not reject `trial_params`
by name — it accepted the request and returned a container id. The container
references a video that cannot be fetched, so it will error and expire on its
own within 24h. **Nothing was published. Do not publish container
`18619475482009797`.**

**The caveat:** parameter *acceptance* is not proof the parameter is *honoured*.
Graph sometimes ignores unrecognised parameters rather than rejecting them, and
the container's trial status is not readable back. The evidence is strong —
this is the strongest signal obtainable without publishing — but the definitive
confirmation is the first real trial reel: publish one, then check in the app
that it is marked as a trial and is not on the grid. Treat that check as a
blocking step in Phase 1, not a formality.

The §7 assisted-manual fallback in `phase-1-repost-engine.md` should be kept in
the document, unbuilt, until that confirmation lands.

### Q2 — Publishing rate limit (25 / 50 / 100 per rolling 24h)?

**INCONCLUSIVE. The probe does not test this and nothing in
`capabilities.json` speaks to it.**

No request in the probe exercises a publishing quota, and Graph does not
advertise the limit on any endpoint the probe calls. The three figures in the
operating plan remain uncorroborated secondary-source numbers.

This is harmless at the planned volume of one trial per day, which is what the
plan already says. It becomes load-bearing only before a bulk operation. The
honest way to settle it is to read `X-App-Usage` / `X-Business-Use-Case-Usage`
response headers during real publishing in Phase 1 — the probe does not capture
headers today.

### Q3 — Do media insights expose a follower / non-follower reach breakdown?

**INCONCLUSIVE, leaning no — and the probe's limits here matter.**

No metric in the supported set carries a follower/non-follower split:

```
supported: reach, views, likes, comments, shares, saved,
           total_interactions, ig_reels_avg_watch_time,
           ig_reels_video_view_total_time
```

But the probe tests *metric names only*. It never sends a `breakdown`
parameter, which is the mechanism Meta uses for dimensional splits
(e.g. `breakdown=follow_type`). So the probe establishes that no *standalone
metric* returns the split; it does **not** establish that `reach` cannot be
broken down by follower type. That distinction was not tested and should not
be asserted either way.

Operationally this changes nothing, and the plan already anticipated it:
§6.2's argument stands — 100% of a trial reel's reach is non-follower reach by
definition, so trial reels measure stranger-acquisition cleanly regardless of
how the breakdown question resolves. Worth one probe extension later; not worth
blocking on.

### Q4 — Regional monetization eligibility (Subscriptions, Reels bonuses)?

**INCONCLUSIVE. Entirely unprobed.**

Nothing in the probe touches monetization surfaces, and `capabilities.json`
contains no evidence bearing on this. The operating plan's §8 ranking already
treats in-app monetization as tier 4–5 pocket money behind lessons and gigs, so
this does not gate anything. It is answered by looking in the Instagram app
under Professional dashboard → Monetization, not by the API.

---

## The finding the plan did not anticipate

### `profile_visits` and `follows` are unavailable on media insights for reels

```json
"unsupported": {
  "profile_visits": "The Media Insights API does not support the
                     profile_visits metric for this media product type.",
  "follows":        "The Media Insights API does not support the
                     follows metric for this media product type."
}
```

Both names are *recognised* by the API — they appear in the enumerated valid-metric
list Graph returned when rejecting `plays` — but neither is supported **for this
media product type**, and the probe's test media was a reel. Since the whole
repost engine operates on reels, that is the answer that matters.

**Scope limit, stated plainly:** the probe tested one media item, the newest
reel. It did not test a `FEED` image or carousel. If those expose
`profile_visits`, this finding narrows to reels only. That was not tested.

**What this breaks, concretely:**

| Document | What assumed `profile_visits` per-post | Status |
|---|---|---|
| `operating-plan.md` §1 | "Profile conversion = `profile_visits ÷ reach`" | dead per-post |
| `operating-plan.md` §1 | "Follow efficiency = `follows ÷ profile_visits`" | dead per-post |
| `operating-plan.md` §2.1 | nightly pull lists both metrics | wrong, will error |
| `operating-plan.md` §6.3 | `+ 0.20 × normalized(profile_visits ÷ reach)` | uncomputable |
| `phase-1-repost-engine.md` §3 | `+ 0.20 × norm(profile_visits / reach)` | uncomputable |
| `phase-1-repost-engine.md` §6 | graduation gate on `profile_visits/reach` | uncomputable |

**What survives:** `profile_views` *is* available at the **account** level
(daily, `metric_type=total_value`). So profile conversion remains measurable
for the account as a whole, day by day. It is **not** attributable to an
individual post, which is precisely what the scorer and the 72h graduation
rule need. These are not substitutes and the amended documents should not
pretend otherwise.

---

## Amendments made to the plan documents

Per the instruction that probe results are primary evidence and outrank the
secondary sources the plan was written from:

1. **Scorer reweighted** in both documents. Dropping `profile_visits` and
   renormalising the remaining three preserves the author's relative intent
   (sends dominant, retention second, saves third):

   ```
   score =  0.4375 × norm(shares / reach)
          + 0.3125 × norm(avg_watch_s / duration_s)
          + 0.2500 × norm(saved / reach)
   ```

   This is a judgment call, flagged as such in the documents. The alternative —
   substituting `total_interactions / reach` into the vacated 0.20 slot — was
   rejected because it double-counts shares and saves, which are already
   weighted, and would quietly bias the scorer toward likes.

2. **Graduation criteria rewritten** in `phase-1-repost-engine.md` §6. The
   `GRADUATE` vs `HOOK_WON` split as specified cannot be computed per-trial.
   The amended version keeps the reach test, replaces the per-post profile
   test with `saved/reach` as an explicitly-labelled weaker proxy for "the
   body delivered", and records account-level `profile_views` alongside each
   trial as context rather than as a decision input.

3. **Host and route corrected throughout.** The documents assume
   `graph.facebook.com`. This account is on Instagram Login and answers on
   `graph.instagram.com` v26.0. `phase-0-setup.md`'s claim that "the probe
   script handles either" was false and cost a full setup session — an `IGAA`
   token sent to the Facebook host returns `Invalid OAuth access token -
   Cannot parse access token`, which is indistinguishable from a corrupt token.

4. **Dead metrics removed** from the §2.1 nightly pull list: `plays`,
   `impressions`, and `video_views` are not valid on v26.0. `views` replaces
   them.

5. **Request-shape note added.** Several account metrics only answer to
   `metric_type=total_value` (`views`, `profile_views`, `website_clicks`,
   `accounts_engaged`, `total_interactions`). Asking without it returns an
   error identical to "metric unsupported" — a trap that would have made a
   naive probe under-report capability. `capabilities.json` records the working
   shape per metric and `backfill.py` reuses it.

---

## Token lifetime — the one deliverable Phase 0 cannot produce

**Not measurable without changing state.**

`graph.instagram.com` has no `debug_token` endpoint; that is Facebook-host only.
For Instagram Login the only way to read expiry is:

```
GET /refresh_access_token?grant_type=ig_refresh_token&access_token=...
```

which **issues a new token** and is therefore a mutation. `probe.py` promises to
modify nothing, so it does not call it and reports the gap instead.

What can be said without measuring: Instagram long-lived tokens last **60 days
from issue** and are refreshable any time after the first 24 hours. This token
was generated during Part A on or about 2026-08-18, which puts expiry near
**2026-10-17** — an *inference from the issue date*, not a reading from the API.

To convert that into a fact, run the refresh call deliberately and record the
returned `expires_in`, then write the new token to `.env`. That call is also the
first half of the refresh automation the plan already flags as a single point of
failure (§13, "Token hygiene"). Building it is a Phase 1 task, not a Phase 0 one.

---

## Backfill

Results appended once `scripts/backfill.py --full` completes. Expect one
snapshot row per `(post, age_bucket)`; with 552 media all older than 30 days,
the expectation is 552 rows in the `30d` bucket and none in the younger
buckets — historical posts have already aged past every threshold, so a single
backfill cannot reconstruct the 6h/24h/72h/7d curve for them. **The curve only
exists for posts published from now on.** The plan's §2.1 claim that snapshots
capture the curve is true going forward and untrue retroactively; the amended
document says so.
