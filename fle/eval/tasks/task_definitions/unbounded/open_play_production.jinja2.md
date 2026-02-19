Build the biggest automated factory possible.

Your goal is to maximize your automated production score income by:
- Establishing efficient automatic resource extraction (iron, copper, coal, stone)
- Building self-fueling power generation infrastructure
- Creating automated production chains for increasingly complex items with assemblers
- Scaling up production capacity over time
- Optimizing factory layout and logistics

The production score reflects the total economic value of everything your factory produces.
More complex items (circuits, science packs, etc.) are worth more than raw materials.
Ticks represent the wall-time of the environment.

# Tips for getting started
---

## Writing Policies for Maximum Information Extraction

Each policy execution is a **sampling opportunity** against a stochastic environment. Maximize bits extracted per sample.

**Shallow scripts waste samples.** A procedural 100-line script fails at line 74 because of environmental drift. Use logical branching to deal with expected future conditions.

Adaptive policies extract information continuously:

Every if/else is a bit extracted and used
Every status check that changes behavior is information captured
Every assertion is an early exit that preserves budget for the next sample
Nested branches cover combinatorial space — A linear script tests one path. n nested binary branches cover 2^n world-states in a single policy. The structure itself is a exploration strategy.

**Principles:**

1. **Observe → Branch → Act** — Never act without observing. Never observe without branching on the result.

2. **Fail fast at gates** — Assert preconditions early. A failed assertion at line 10 lets you re-sample; failure at line 90 is wasted compute.

3. **Diff state, don't assume it** — `inventory.get()` before crafting, `entity.status` before depending on it. The environment changed since your last sample.

4. **Small action quanta** — Each block: observe, decide, act, observe result. The tighter this loop, the more adaptive the policy.

5. **Recovery is information too** — `try/except` with fallback isn't defensive coding—it's branching on implicit observations (collision detected, resource missing).

---

Focus on building sustainable, scalable automation rather than manual crafting to maximise your production score rate.
