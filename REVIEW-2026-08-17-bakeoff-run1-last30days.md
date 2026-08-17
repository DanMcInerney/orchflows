# Bakeoff run 1: `/last30days` on SpaceX stock sentiment

Part 1 of 3. Entry point and analysis: [REVIEW-2026-08-17-super-research-bakeoff.md](REVIEW-2026-08-17-super-research-bakeoff.md).
Run 2: [REVIEW-2026-08-17-bakeoff-run2-super-research.md](REVIEW-2026-08-17-bakeoff-run2-super-research.md).

- Date: 2026-08-17
- Question: "SpaceX sentiment - do people think it will go up or down?"
- Window: 2026-07-18 to 2026-08-17
- Tool: `last30days` v3.11.1 (plugin cache install), engine `scripts/last30days.py`
- Host: Windows 11, Git Bash, native Windows Python 3.14.6
- Reasoning model: Opus 5 (single context, no subagents)

## 1. What was run

### Pre-flight

`--diagnose` reported `available_sources`: `reddit`, `youtube`, `hackernews`, `polymarket`, `github`, `grounding`. No X (no auth), no TikTok/Instagram (no ScrapeCreators key). `LAST30DAYS_NATIVE_SEARCH=1` was exported because the host has its own WebSearch, so the engine skipped its keyless web floor and general web was supplied by the host model.

Query-quality pre-flight classed the topic as a named-entity sentiment/direction query. Material discovery during pre-research reshaped the whole run: **SpaceX IPO'd 2026-06-12 at $135/share as SPCX on Nasdaq**, so "up or down" is a live traded-equity question, not a private-valuation one. That moved finance communities into the targeting alongside the space ones.

### Resolution (Step 0.5 / 0.55), 6 host WebSearches

- Reddit dedicated: `SpaceX`, `spacexlounge`, `SpaceXMasterrace`, `Starlink`
- Reddit broad: `stocks`, `investing`, `wallstreetbets`, `StockMarket`, `space`, `spaceflight`
- X: `@SpaceX` (+ `@elonmusk`, `@Starlink`) - passed but X was unauthenticated
- Polymarket keywords: `spacex,spcx,starship`
- First-party positioning (spacex.com/mission): "designs, manufactures and launches advanced rockets and spacecraft... ultimate goal of enabling people to live on other planets"

### Plan (Step 0.75), authored by the host model and passed via `--plan`

`intent=prediction`, `freshness_mode=strict_recent`, `cluster_mode=market`, 4 subqueries:

| label | search_query | weight |
|---|---|---|
| primary | `SpaceX SPCX stock price` | 1.0 |
| bull_bear | `SPCX SpaceX overvalued buy the dip valuation` | 0.8 |
| earnings_lockup | `SpaceX Q2 earnings lockup expiration shares selloff` | 0.8 |
| starship_catalyst | `Starship Flight 14 Starlink V3 ship catch` | 0.6 |

### Invocation

```
python3.14 <SKILL_DIR>/scripts/last30days.py "SpaceX stock sentiment" \
  --emit=compact --save-dir="C:/Users/danhm/Documents/Last30Days" --save-suffix=v3 \
  --plan <plan.json> \
  --x-handle=SpaceX --x-related=elonmusk,Starlink \
  --dedicated-subreddits=SpaceX,spacexlounge,SpaceXMasterrace,Starlink \
  --subreddits=stocks,investing,wallstreetbets,StockMarket,space,spaceflight \
  --polymarket-keywords "spacex,spcx,starship"
```

Runtime **92.4 seconds**. Then 3 post-engine WebSearch supplements. Raw artifact saved to
`C:\Users\danhm\Documents\Last30Days\spacex-stock-sentiment-raw-v3.md`, with a
`## WebSearch Supplemental Results` appendix of 14 bullets appended per the skill's Step 2.5.

## 2. Yield

```
Reddit:  20 threads | 14,432 upvotes | 3,462 comments
YouTube:  7 videos  | 240,603 views  | 7,074 likes | 1,613 comments | 2/7 with transcripts
HN:      13 stories | 571 points     | 592 comments
GitHub:  18 items   | 86 reactions   | 67 comments
Polymarket: 0 markets (59/47/54/28 events found across queries, all filtered as noise)
X:        0 (unauthenticated)
```

58 evidence items across 4 sources, clustered into 8 ranked clusters. Research quality self-reported
as 4/5 core sources, missing X.

Notable: the relevance floor **dropped 84, 124, 147 and 21 off-topic Reddit posts** across the four
subqueries. Those drops are invisible in the output. See run 3's defect analysis - this is both why
run 1 is clean and its one unauditable step.

## 3. Ranked evidence clusters (engine output)

1. **"SpaceX Just Crushed Earnings. Why Is the Stock Falling? SPCX"** (score 73, 6 items, HN + YouTube)
   - `ggdyD2Un5zo`, UNRIVALED INVESTING, 2026-08-05, 21,075 views / 413 likes / 230 comments
   - "SpaceX just posted exceptionally strong 2Q'26 earnings, yet the stock is falling as investors confront a staggering level of cash burn and what may be a much shorter funding runway than expected."
   - Ars Technica "SpaceX spooks investors with debut earnings report" (HN, 8pts)
   - Dissent "The SpaceX Sham" (HN, 39pts / 47cmt)
2. **"3 Reasons Why SpaceX Stock Is Finally A Buy"** (score 72, single-source)
   - `Huv4D-yTwlg`, Hedged Stock Income, 2026-08-08, 8,325 views / 149 likes / 39 comments
   - "Three weeks ago, I posted a YouTube video warning that SpaceX (SPCX) had substantial downside risk. After the stock fell 25%, I am now bullish."
3. **"SpaceX Stock: $225 to $140 - Buy the Dip or Wait?"** (score 67, single-source)
   - `gVrZrXbZXdA`, World Trends, 2026-08-16. Records the price path: $135 IPO, $225.64 post-IPO high, $104.83 early August, ~$140 by Aug 14, still ~38% below the high.
4. **"SpaceX Stock Is Falling. Here's Why It Could Get Worse."** (score 67, single-source)
   - `in8B14t2MdQ`, Renaissance Capital IPO, 2026-08-06. Lockup-calendar thesis.
5. **"Elon Musk PANIC Grows Over SpaceX Stock Nightmare As Lockup Ending Looms"** (score 65)
   - `wWwHSaImg8U`, The Damage Report, 2026-08-04, 114,521 views / 3,753 likes / 905 comments
   - Transcript highlights: "912 million shares will become available more than double the current supply"; "Nearly 25 billion dollars worth of their tradeable stock, or 34% of its float, is held by short sellers"; "SpaceX is the eighth most shorted stock in the US, and the most shorted stock over the last 30 days, based on S3 data"; "he calculated the company was worth $300 a share, but noted there was a current disconnect and increasingly bearish investor sentiment"
6. **"SpaceX beat earnings and still sold off. Tomorrow 911.5M shares unlock."** (score 62)
   - r/stocks, 2026-08-05, **1,265 points / 590 comments**
7. **"The SpaceX IPO... It's Worse Than You Think"** (score 60, 3 items, HN + Reddit + YouTube)
   - `Yx9huiJH33g`, Finance Bureau, 2026-08-11, 86,283 views / 2,224 likes / 382 comments
   - "The largest IPO in history went on to destroy about 1.3 trillion dollars of market value in under eight weeks." "$135 a share on the 11th of June, raised 85.7 billion dollars, closed its first session up 19% at $160." "a price set by 4.9% of the shares is only a real price until the other 95% turns up on the market."
   - r/stocks "SpaceX revenue jumps 92% in first earnings report since IPO", 2026-08-04, 1,044pts / 570cmt
   - CNBC via HN: "SpaceX stock has cratered nearly 23% since the company joined the Nasdaq-100"
8. **`report(stock): SPCX 종목분석 2026-08-08 - 56.5/100 Reduce`** (score 49, GitHub, `kimsl12/stock-analyst` PR #29)

## 4. Top community comments (vote-ranked, engine-surfaced)

| votes | author | text | source |
|---|---|---|---|
| 305 | u/rustybeancake | "These two firing their Hall effect thrusters is right up there with the most sci-fi photos of the year so far." | r/spacex |
| 252 | u/H-K_47 | "Musk replied: Unfortunately, ship recovery is not looking good right now. Nonetheless, we were able to obtain close-up photos of critical regions of the heat shield and engines for future upgrades." | r/spacex |
| 130 | u/rustybeancake | "Everything achieved except proper booster landing burn. Great result! Hope they can still attempt a booster catch next flight. The launch cadence can't pick up much until they start reusing boosters." | r/spacex |
| 122 | u/H-K_47 | "Musk confirmed they got good data. We got all the heat shield data we needed and then some! The shots of the Ship just floating there are INSANE." | r/spacex |

Four `vercel[bot]` / base64-payload entries were also surfaced from GitHub and are junk.

**The signal in this table is that it contains no stock content at all.** The highest-engagement
community comments in the window are hardware. r/spacex grades engineering; r/stocks grades a share
price; the two rooms barely reference each other.

## 5. WebSearch supplements (3 post-engine, plus 6 pre-research)

Key facts added that the social engine did not carry:

- Analyst consensus "Buy", average 12-month target ~$228-231 across 35 analysts, **range $62 to $800**
- Short interest fell **34% -> 11% of float** during the August rally; squeeze speculation at ~$1.9T cap
- Lockup is **staged**: 911.5M shares Aug 6, eight further tranches through 2026 into 2027, Musk and select investors locked until mid-2027; analysts call it a headwind until summer 2027
- Q2 cash burn ~$16B; FCF -$13.8B (2025), -$9.1B (Q1 2026); $29.1B long-term debt; ~$25B borrowed weeks after the $86B raise; cash depletable in ~6 quarters at that pace
- Aug 6 lockup fear trade failed: **+21%, closing $138.74** the following week
- FinanceFeeds framed the unlock as **$190 bull vs $76 bear**
- Dissent's "The SpaceX Sham": IPO as "a mass delusion event of astronomical proportions"; argues valuation rests on **xAI**, merged into SpaceX pre-IPO
- Starship Flight 14 targeted end of August with operational Starlink V3 and a ship-catch attempt (Musk, first earnings call since IPO)
- Operational cadence: record **38.5 minutes** between two Falcon 9 launches on Aug 15; 93-launch year to date

## 6. The delivered answer

Sentiment is **bimodal and calendar-driven, not directional**. Every serious take in the window is a
take on unlock tranches rather than on the business. Fundamentals and price decoupled (92% revenue
growth plus a sell-off in the same session). The Aug 6 unlock failing to crash the stock converted a
large bloc of bears into buyers. The bear thesis is a liquidity and AI-spending thesis, not a space
thesis, and the most-discussed critique reframes the equity as an xAI vehicle. Analyst dispersion
($62-$800) is the most honest sentiment reading available: high conviction that it moves, no
consensus on direction.

## 7. What run 1 could not do

- **X was unauthenticated**, so zero real-time retail posts - the most expensive gap for a
  heavily-shorted-ticker sentiment question. On Windows only Firefox cookies are supported.
- **Polymarket returned 0 markets** after filtering 59/47/54/28 events as noise across the four
  queries, despite `--polymarket-keywords`. For a literal "up or down" question this is the single
  most relevant absent source, and the filter's rejection is not itemized.
- **No provenance labelling.** The 14,432 Reddit upvotes carry no indication of which route or
  operator reported them, no access class, no time-confidence, and no distinction between "the
  platform said this" and "an archive said this".
- **The relevance floor is unauditable.** 376 Reddit posts were dropped across four subqueries with
  no record of which or why.
- **GitHub contributed noise.** 18 of 58 items, including base64 `vercel[bot]` payloads surfaced into
  the top-comments block.
