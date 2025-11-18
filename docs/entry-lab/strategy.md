# Entry Lab Strategy Notes

Use this document as a living reference for your setups. We will iterate together: you add details, I’ll ask clarifying questions until we both can identify the setups accurately.

## 1. Instruments & Sessions
- **Primary market:** Topstep funded account, 5 primary pairs [MNQ, CL, MGC, SIL, 6E]
- **Structure/entry timeframe:** For documentation and backtests assume everything on the 5m chart (higher TF only for context, 1m only if noted during micro confirms).
- **Session focus:** All sessions, but London/Asia historically produce the cleanest statistics.
- **Volatility considerations:** No explicit filter—recent drawdown blamed on market conditions rather than a rule breach.

## 2. Core Concepts
My strategy is mostly structure/liquidity based, but its not the usual concept of liquidity you might usually know or understand. Structure as you know is mostly defined as bullish/bearish denoted by higher highs/lower lows in a bullish market, and the opposite in bearish scenarios.On a bullish structure, whenever price makes a higher high, breaking through the last identified higher high, this is called a BOS (break of structure). If we break below the last denoted higher low, this is called a change of character, which will denoted the change in orderflow from bullish to bearish (there are some special cases that will be mentioned later). All of this will also apply to bearish structure just opposite. Now going back to the higher highs/higher lows, another concept I take into account to even identify a steup is Trading Range/Fractals. Fractals are just the highs/lows that are important, meaning the higher higs/lows that denote structure. How the sequence would go is we have a current high, we make a higher low than the one before, this low makes a new higher high breaking structure, then the trading range would be from the higher low made, to the high that was broken. This trading range is where we ideally want to take trades. Look at structure_01 and Trading_range in the strat images to see visual representations of these concepts. 
Moving on from this now we can start talking about liquidity and what it means according to my strat and structure. Whenever a trading range is made (same thing as whenver a bos is made), usually price may come back as a retest, go up to where the bos was made, and move higher/lower depending on the structure. This is the liquidity which we expect has to be swept/taken if we want to continue in the intended direction. Liquidity is not only found where the bos/trading range was made, but also applies for POIs. Whenever a POI is made, there are things that denote its quality, and one of them is it has liquidity sitting on it. Will expand later when we touch on POIs. See structure_liquidity_01 and 02 in images to better understand this.
Now moving onto POIs which is essential for entries. When a trading range is formed (bos in a direction is made, we have structure), within the trading range, price leaves POIs, which are simple down/up moves in bullish scenarios and opposite for bearish. These down/up moves don't have to denote like a bos or something, they are simply combinations of candles that went down, made a low, broke higher, thus marking a higher high in micro structure, and this is whole move is marked as a POI. Opposite for bearish scenario. Important thing about POIs is that there are some better than others. 2 criteria for this: the first is if they have liquidity (same as structure liquidity mentioned before) and if they are mitigated more than 50%. This mitigation can happen as soon as they are made, meaning price made an up and down move, and came and mitigated it as soon as it was made, maybe making another POI on top. POis can be one candle meaning if the whole down/up move was made in one candle. See POIs for visual representation. 
Finally for entries/setups, What we look for to take a trade is of course a bos in any direction, a high quality POI, look for an entry withing a POI in the trading range. Expanding on this you would infer or understand that there will be tricky situations, like what if there are many pois in the trading range, what if price doesn't return to trading range just keeps going higher, other situations that you may think of. Mostly for this strat we would only look for trades if the already mentioned setps take place, price makes a bos (we have a trading range), this leaves a poi or many, we wait for price to retrace into that POI, and within our confluences we enter. Now for this confluences/entry methods, the one's that i've tried are not connected to each other, i just used these as i kept trading to see which ones gave better results. THe first one was simply putting limits at 50% of the POI that i was interested in. The stoploss would go at the low of that POI. This gave mixed results in terms of win rate but with a good rr/take profit, it would deliver and allowed me to pass my first combine. The second entry method was simply and ifvg formed within any poi in the trading range. Remember an ifvg (inverse fair value gap) forms when (in bullish scenario) a bearish fair value gap gets formed, an its immediately followed by a bullish fair value gap. I would entry as soon as it was formed, target the next higher high or where the new bos wuould be following structure. This gave probably the best and worst results, as i passed my second combine with this in 7 days with 60%+ win rate, but when i tried this on funded, have experienced worst results (this can also be because of indiscipline/just incorrect trades). The last entry method was just following micro structure after price hits our POI, this delivered okay results but not the best. ALso had to be looking at the charts a lot to see. 

### CHOCH Exceptions
- A wick sweep through the prior HL/LH does **not** flip bias unless the candle body closes beyond the level.
- If the active trading range sits above a previous range that has not been mitigated ≥50%, that older structure still “counts.” Only once the last two BOS ranges are respected/mitigated do we treat a break of the latest HL as a valid CHOCH.

### Liquidity & POI Ranking
- Liquidity at BOS highs/lows or on POIs is mainly a quality filter (not an extra entry confluence). We note whether stops were swept—either via wick or full body.
- When multiple POIs exist inside the range, rank them by (1) liquidity resting on top, (2) immediate mitigation ≥50%, (3) recency. If the freshest POIs fail, deeper POIs near the origin of the swing are still valid candidates.

### Entry Methods
1. **50% limit of POI**
   - Entry: limit order at midpoint of chosen POI (preferably ≥50% mitigated already).
   - Stop: extreme of the POI.
   - Target: next structural HH/LL (where the future BOS should print).
   - Notes: mixed win rate but great RR (passed Combine 1).
2. **IFVG inside POI**
   - Entry: as soon as a bearish FVG is immediately followed by a bullish FVG (inverse) inside the POI; ideally aligns with ≥50% mitigation mark.
   - Stop: POI extreme (same as limit approach).
   - Target: next structural HH/LL.
   - Notes: delivered Combine 2 quickly but struggled on funded—likely due to discipline/context.
3. **Micro-structure confirmation**
   - Entry: wait for a micro BOS/CHOCH inside the POI (often on 1m) and take the continuation.
   - Stop: depends on the micro swing used.
   - Notes: screen-time heavy; results mixed.

> Reference images: `docs/entry-lab/Strat_Images/Trading_range.png`, `docs/entry-lab/Strat_Images/POIs.png`, plus live trade screenshots in `server/data/Trading-Images/tradeexamples/`.


## 4. Risk Parameters
- Default risk per trade: around $150-$200
- Max daily drawdown or stop trading rules: $300 daily drawdown
- Scaling in/out rules (if any): none as of yet

## 5. Known Pain Points
Mostly stopped early and price went in direction. We can look at trades in our journal to see more of this

## 6. Examples
Add annotated chart references or IDs from `server/data/trading images/` once we align on format.

---

_As you fill sections, I’ll review and leave questions inline (in comments or next session) so we converge on a precise, testable strategy definition._
