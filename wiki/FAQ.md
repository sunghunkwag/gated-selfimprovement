# FAQ

**Is this AGI / the singularity?** No. It is a controlled study of self-improvement
*dynamics* on research substrates, with counterfactual controls and honest nulls.
"Unbounded" improvement is not demonstrable in principle; experiments can only show
"kept improving for N steps, then stopped because X."

**Why LLM-free?** To buy rigor and reproducibility. The whole thing runs offline and
deterministically, so every claim can be re-derived exactly. The trade-off: blind
search does not scale to arbitrary real-world code the way LLM-based systems do.

**Is it a toy?** It moved well past toy list-arithmetic: a Turing-complete VM with
branches and loops, and a real-file `repo_repair` layer that patches actual Python and
grades by executing it. It remains a *controlled research domain* (bounded defect
space, small modules) — stated plainly, like any benchmark. That boundary is the next
frontier, and it collides with the LLM-free constraint.

**What is the single strongest result?** The cross-substrate transfer (p=0.0008 with a
random-capability control) and the SDT gate-integrity finding — both are
domain-independent and speak to generality and safety, not just one task family.
