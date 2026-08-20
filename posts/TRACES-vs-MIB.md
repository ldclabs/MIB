# TRACES and MIB: Two Benchmarks for AI That Can Discover — and Learn

[ English | [简体中文](TRACES-vs-MIB_cn.md) ]

For years, most AI benchmarks have asked a familiar kind of question:

> **Does the model know the answer?**

Sometimes the answer is hidden in a document. Sometimes it is buried across many web pages. Sometimes it requires several steps of reasoning. But the basic structure remains the same: somewhere, there is a correct answer, and the AI is judged by whether it can produce it.

Two new projects, **[TRACES](https://traces.apodex.com/)** from Apodex AI and **[MIB — Memory Intelligence Benchmark](https://github.com/ldclabs/MIB)**, challenge that framing from different directions.

TRACES asks:

> **Can an AI investigate a problem whose answer is not already sitting there waiting to be retrieved?**

MIB asks:

> **Can an AI use what happened in the past to behave better in the future?**

At first glance, one is about discovery and the other is about memory. But they are more closely related than that.

Both are part of a broader shift away from treating AI as a machine that answers isolated questions, and toward evaluating AI as a system that **acts, gathers evidence, changes its mind, learns from failure, and carries something forward through time**.

The simplest way to describe their relationship may be:

> **TRACES measures discovery. MIB measures accumulation.**

And together, they point toward a larger question:

> **Can artificial intelligence become cumulatively more capable through experience?**

---

## The Problem With “Does It Know the Answer?”

Traditional benchmarks are extremely useful. They measure knowledge, reasoning, retrieval, mathematics, coding, and many other capabilities.

But they tend to compress intelligence into something like this:

```text
Question
   ↓
Model
   ↓
Answer
   ↓
Correct / Incorrect
```

Real intellectual work rarely looks like that.

A scientist may begin without knowing the answer. An engineer may try something, observe a failure, change a hypothesis, use another tool, discover a hidden constraint, and only then reach a conclusion.

And even that is only half of intelligence.

If the same scientist encounters a related problem six months later, we would expect yesterday's experience to matter. The scientist should remember what failed, retain the important evidence, recognize similar conditions, and avoid repeating the same mistake.

That gives us a much longer loop:

```text
Problem
   ↓
Investigation
   ↓
Evidence
   ↓
Failure / Correction
   ↓
Discovery
   ↓
Experience
   ↓
Memory
   ↓
Future Problem
   ↓
Better Behavior
```

TRACES focuses largely on the first half.

MIB focuses largely on the second.

---

# What Is TRACES?

TRACES is part of Apodex's broader effort to evaluate what it calls **discoverative AI**: AI systems that do more than retrieve or synthesize existing answers.

The recent *Apodex Discovery* paper describes a framework built around extended, stateful and verifiable investigations. Instead of supplying only a question and checking the final answer, the environment can provide data, tools, constraints, feedback, intermediate artifacts and final-result verification. The initial work surveyed 561 industries across 16 sectors, collected 423 high-value real-world problems, and selected 20 for its initial release. ([arXiv][1])

In plain English:

> **TRACES wants to see whether an AI can conduct a serious investigation.**

Imagine asking an AI to investigate a biomedical hypothesis.

The interesting question is not merely:

> “Did it eventually output the right sentence?”

You also want to know:

* Did it choose useful tools?
* Did it understand the evidence returned by those tools?
* When an assumption failed, did it repair its approach?
* Did it consider competing explanations?
* Did it maintain consistency over a long investigation?
* Were its claims actually grounded in evidence?
* Did it understand the limits of its conclusion?

TRACES captures this through six dimensions, called **HDS6**:

| Dimension        | Plain-English meaning                                               |
| ---------------- | ------------------------------------------------------------------- |
| **Tools**        | Did the agent use the right tools correctly?                        |
| **Repair**       | Could it recognize and recover from errors?                         |
| **Alternatives** | Did it seriously consider competing explanations?                   |
| **Coherence**    | Did the investigation remain logically consistent over time?        |
| **Evidence**     | Were claims grounded in observations and sources?                   |
| **Scope**        | Did the agent understand where its conclusions do and do not apply? |

Importantly, these dimensions are evaluated separately from final task success. The Apodex paper also describes controlled ablations under a common TRACES episode interface to study which solver components actually improve performance. ([arXiv][1])

So TRACES is not simply asking experts whether a reasoning trace “looks good.”

It combines several things:

```text
realistic environment
        +
tool interaction
        +
trajectory recording
        +
artifact / outcome verification
        +
process evaluation
        +
system-component ablation
```

Apodex's own Deep Discover system illustrates the kind of workload it has in mind: long-running investigations involving parallel agents, hypothesis generation, verification and a shared evidence pool. Its public description says the architecture can orchestrate up to 150 agents and workflows exceeding 15,000 steps. ([Apodex][2])

TRACES therefore sits much closer to **scientific or engineering investigation** than to ordinary question answering.

---

# What Is MIB?

MIB starts from a different question.

Suppose an AI already went through a difficult experience yesterday.

It tried something.

It failed.

It discovered why.

It recovered.

Today, it encounters a related situation.

What should happen?

A capable system should not merely be able to quote yesterday's transcript.

Yesterday should change what it does today.

That leads to MIB's central idea:

> **Memory is the mechanism by which the past participates in future computation.**

And therefore:

> **A memory system should not be judged by how much of the past it can retrieve, but by whether the right parts of the past change the future in the right way.**

MIB grew out of an exploration of knowledge, experience and memory that can be summarized as:

```text
Experience
   ↓ compression
Knowledge

Experience
   ↓ compilation
Skill

Past
   ↓ participation in future computation
Memory
```

This thinking also influenced **KIP v2 — Knowledge Interaction Protocol**, which explores how durable cognition might represent things such as knowledge, experience, provenance, uncertainty, historical change and learned skills.

But KIP and MIB serve different purposes.

KIP asks:

> **How might durable cognition be represented and governed?**

MIB asks:

> **Does the memory system actually make the agent better?**

A system does **not** need to use KIP to participate in MIB.

It may use a vector database, raw history, summaries, a knowledge graph, episodic memory, procedural memory, or something completely different.

MIB judges observable behavior.

---

# MIB Measures More Than Recall

Consider a very simple example.

Yesterday:

> “I live in UTC+8.”

Later:

> “I moved. I now use UTC+1.”

A retrieval system might store both sentences.

But an intelligent memory system should understand their temporal relationship:

```text
current timezone     = UTC+1
historical timezone  = UTC+8
```

Now compare that with:

> “The serial number is AX-19.”

followed by:

> “Sorry, I misspoke. It is AX-91.”

That is a different kind of change.

The office move was a **real-world transition**.

The serial-number example was a **correction of a previously false belief**.

MIB wants systems to preserve those distinctions.

Its v0.1 benchmark therefore evaluates six major dimensions:

| MIB dimension                 | Question                                                         |
| ----------------------------- | ---------------------------------------------------------------- |
| **Retention & Retrieval**     | Can the system recover the relevant past?                        |
| **Temporal Memory**           | Can it distinguish what was true then from what is true now?     |
| **Epistemic Memory**          | Can it preserve sources, uncertainty, conflict and correction?   |
| **Experience Memory**         | Can it remember goals, actions, failures, feedback and outcomes? |
| **Skill Learning & Transfer** | Can experience become reusable behavior, with proper limits?     |
| **Causal Memory Impact**      | Can we demonstrate that memory actually changed later behavior?  |

The last dimension is particularly important.

---

# MIB's Distinctive Move: Remove the Memory and See What Changes

Suppose an agent succeeds at a task because it remembers an earlier failure.

How do we know the memory caused the improvement?

MIB uses paired interventions.

For example:

```text
Condition A

Full relevant memory
        ↓
Future task
        ↓
Success
```

Then replay the same situation:

```text
Condition B

Same model
Same tools
Same world
Same future task

but remove the relevant past experience
        ↓
Failure
```

The difference tells us something much stronger than:

> “The agent retrieved a relevant sentence.”

It suggests:

> **That past experience was causally involved in the later success.**

MIB also performs the inverse test.

Remove irrelevant memories:

```text
Full Memory
     vs
Irrelevant Memory Removed
```

Performance should remain stable.

And it can introduce stale or harmful memories:

```text
Current correct evidence
        +
old misleading memory
```

A strong system should resist being pulled back toward an obsolete answer.

This allows MIB to distinguish several phenomena that ordinary retrieval scores blur together:

```text
remembering
forgetting
updating
misremembering
negative transfer
stale-memory harm
learning from failure
causal benefit
```

---

# The First Major Similarity: Both Care About the Journey

This is where TRACES and MIB begin to look surprisingly similar.

Neither is satisfied by:

```text
AI outputs impressive final answer
→ give score
```

TRACES looks at the investigation.

MIB looks at the temporal trajectory.

Both care about things like:

```text
state
action
observation
feedback
revision
outcome
```

TRACES asks whether an investigation remains rigorous while it unfolds.

MIB asks whether earlier experience later changes cognition and behavior.

So both belong to a broader movement from:

> **answer evaluation**

toward:

> **process and behavior evaluation**

---

# But They Observe Different Time Scales

A useful distinction is:

## TRACES: intelligence *within* an investigation

Imagine one long scientific investigation:

```text
Hypothesis
   ↓
Search
   ↓
Experiment
   ↓
Evidence
   ↓
Contradiction
   ↓
New hypothesis
   ↓
Verification
   ↓
Conclusion
```

Even if that investigation lasts thousands of steps, it is still largely one continuous cognitive episode.

TRACES asks:

> **Can the agent remain competent throughout that investigation?**

---

## MIB: intelligence *across* experiences

MIB is particularly interested in this:

```text
Episode A
   ↓
something happens
   ↓
the agent learns something
   ↓
time passes

Episode B
   ↓
different but related situation
```

The question becomes:

> **Did Episode A change how the agent behaves in Episode B?**

This leads to a concise distinction:

> **TRACES evaluates continuity inside an investigation.
> MIB evaluates continuity of learning across investigations.**

The boundary is not absolute. Long TRACES investigations obviously require state and memory, and MIB scenarios can contain complex agent trajectories.

But the primary variable of interest is different.

---

# Memory-Dependent Does Not Mean Memory-Specific

This distinction matters when comparing TRACES's six dimensions with MIB.

Take **Coherence**.

An agent that forgets earlier constraints will become incoherent. So coherence clearly depends on memory.

But poor coherence might also come from:

* weak planning,
* poor reasoning,
* bad orchestration,
* context compression errors,
* attention failures,
* or a weak memory system.

A TRACES score can tell us:

> “This solver lost coherence.”

It does not necessarily tell us:

> “The memory system caused the loss of coherence.”

MIB attempts to isolate that question directly:

```text
keep everything else constant
        ↓
intervene on memory
        ↓
observe the behavioral delta
```

So a careful formulation is:

> **TRACES evaluates many behaviors that demand memory. MIB tries to isolate memory as the causal variable.**

---

# HDS6 and MIB Are Better Seen as Phenotypes and Mechanisms

It is tempting to map the six TRACES dimensions directly onto the six MIB dimensions.

There are real similarities, but the relationship is many-to-many.

For example:

| TRACES behavior  | Memory functions that may support it                   |
| ---------------- | ------------------------------------------------------ |
| **Tools**        | Experience memory, skill learning, temporal state      |
| **Repair**       | Remembered failures, correction, experience learning   |
| **Alternatives** | Epistemic memory, competing hypotheses, source memory  |
| **Coherence**    | Retention, temporal state, long-term constraint memory |
| **Evidence**     | Provenance, source distinction, evidence independence  |
| **Scope**        | Skill applicability, negative-transfer resistance      |

This suggests a useful conceptual distinction.

TRACES observes something like a **cognitive phenotype**:

> What competent investigation looks like from the outside.

MIB investigates one class of underlying mechanism:

> How memory supports behavior across time.

For example:

```text
          Memory mechanisms
             /    |    \
      Temporal Experience Skill
           \      |      /
            \     |     /
           observable behavior
       Coherence Repair Scope
```

That is why the two benchmarks overlap without being redundant.

---

# An Even Deeper Connection: Evidence

There is another connection that is easy to miss.

Apodex's Deep Discover architecture uses a structured **Shared Evidence Pool**, with separate verification agents checking claims, conflicts and sources. ([Apodex][2])

MIB's epistemic-memory work—and the KIP ideas behind it—care about similar distinctions:

```text
a claim
≠
the source of the claim

repetition
≠
independent evidence

confidence
≠
authority

old belief
≠
current belief

contradiction
≠
information that should simply be deleted
```

Consider this:

```text
Original report
      ↓
summary
      ↓
copied note
```

That is not three independent pieces of evidence.

It is one evidence chain repeated three times.

A discovery system needs to understand this **during investigation**.

A memory system needs to preserve this distinction **after the investigation is over**.

So the relationship can be extended:

```text
TRACES
    ↓
produce evidence and experience

KIP-like memory representation
    ↓
preserve provenance, belief,
history and relationships

MIB
    ↓
test whether that preserved past
improves future behavior
```

---

# Discovery Is Not the Same as Learning

Now consider an AI that performs brilliantly on a difficult investigation.

It generates hypotheses.

It chooses good tools.

It finds evidence.

It notices a mistake.

It repairs its reasoning.

It reaches an important conclusion.

Excellent.

Now give the same AI a closely related problem the next day.

It forgets the conclusion.

It repeats yesterday's failed experiment.

It makes the same wrong assumption.

It has to rediscover everything from scratch.

Was the first investigation intelligent?

Yes.

Did the system learn?

That is much less clear.

A useful definition is:

> **Learning occurs when experience causes a durable, context-appropriate change in future behavior.**

Under that definition, a successful discovery is not automatically learning.

It only becomes learning when the experience survives into future cognition.

That leads to one of the clearest ways to distinguish the projects:

> **TRACES asks: Was the investigation good?**
> **MIB asks: Did the investigation become learning?**

---

# The Reverse Is Also True: Memory Is Not Discovery

Of course, excellent memory is not enough either.

Imagine an AI that perfectly remembers:

* every paper it has read,
* every experiment it has run,
* every mistake it has made,
* every source and citation.

But when faced with a genuinely new problem, it cannot:

* formulate a novel hypothesis,
* choose an informative experiment,
* search for disconfirming evidence,
* compare plausible explanations.

That system may have impressive Memory Intelligence while still being weak at discovery.

So:

> **Memory is necessary for cumulative intelligence, but it is not sufficient for discovery.**

And conversely:

> **Discovery can happen without durable memory, but it cannot reliably compound without it.**

A compact way to say this is:

> **Memory without discovery preserves the known.
> Discovery without memory fails to compound.**

---

# Laboratory Precision vs Real-World Richness

TRACES and MIB also make different methodological tradeoffs.

MIB deliberately uses controlled scenarios, hidden ground truth, replay and memory ablations.

That gives it strong experimental control.

```text
MIB
→ controlled world
→ precise intervention
→ strong causal diagnosis
```

TRACES is moving toward realistic scientific and industrial environments where the path to success can be long, open-ended and messy. The Apodex framework explicitly emphasizes real-world problems, tools, feedback and verification rather than only predefined answer sets. ([arXiv][1])

That gives it greater ecological richness.

```text
TRACES
→ open investigation
→ realistic tools and evidence
→ stronger ecological validity
```

You can think of them as occupying different positions on a familiar scientific spectrum:

```text
Controlled Laboratory                           Open World
        │                                           │
       MIB  ------------------------------------  TRACES
        │                                           │
causal isolation                            ecological richness
```

Neither end is automatically better.

A laboratory can tell us **why** something works.

A realistic environment can tell us whether it still works when the world becomes complicated.

Strong science eventually needs both.

---

# TRACES Should Not Turn MIB Into a Discovery Benchmark

This distinction is important for MIB's future direction.

It would be easy to see TRACES and conclude:

> MIB should also become a huge scientific-agent benchmark.

That would probably be a mistake.

MIB has a distinctive experimental variable:

# **Memory**

Especially in its Track A design:

```text
same model
same prompt
same tools
same reasoning policy
same environment

only memory system changes
```

That makes it possible to compare memory systems themselves.

If MIB becomes a general measure of research ability, this advantage would disappear into all the other factors that determine agent performance.

The better direction is not to turn MIB into TRACES.

It is to bring MIB's memory interventions into richer environments.

---

# A Natural Future: Discovery Followed by Memory Ablation

Imagine a benchmark with two phases.

### Phase 1: Discovery

An agent investigates a difficult problem.

It generates:

```text
new evidence
failed experiments
corrections
a discovery
a learned procedure
```

Then some time passes.

### Phase 2: A related but different problem

The same agent encounters a new situation.

Now run several conditions:

```text
A — Full learned memory

B — Discovery removed

C — Failure experience removed

D — Learned skill removed

E — Stale conclusion injected
```

Then measure both:

```text
investigation quality
+
future behavioral change
```

Now we could ask questions that neither benchmark alone fully answers:

> Did the agent improve because it remembered the earlier discovery?

> Which part of the previous experience mattered?

> Did a failure become a transferable skill?

> Did the system overgeneralize an old lesson?

> Can discovery accumulate across multiple tasks?

This would connect discovery evaluation with memory causality.

---

# From Discovery Intelligence to Cumulative Intelligence

This is where the comparison becomes more interesting than a benchmark rivalry.

Consider the full loop:

```text
World
  ↓
Investigation
  ↓
Discovery
  ↓
Experience
  ↓
Memory
  ↓
Learning
  ↓
Future Investigation
  ↓
Better Discovery
  ↓
New Experience
  ↺
```

TRACES is primarily concerned with:

```text
World
→ Investigation
→ Discovery
```

MIB is primarily concerned with:

```text
Experience
→ Memory
→ Future Behavioral Change
```

Put them together and a larger concept appears:

# **Cumulative Intelligence**

One possible shorthand is:

> **Discovery × Memory = Cumulative Intelligence**

Not as a literal mathematical formula, but as a conceptual one.

An intelligent system that discovers but cannot retain is condemned to rediscovery.

An intelligent system that remembers but cannot discover is limited to preserving what it already knows.

A system capable of doing both can compound.

---

# Where KIP Fits

This also clarifies the role of KIP v2.

The three projects can be viewed as answering three different questions:

### TRACES

> **Can the agent earn new knowledge through rigorous interaction with the world?**

### KIP

> **How can knowledge, experience, evidence, provenance, uncertainty and learned structures persist as durable cognition?**

### MIB

> **Does that persisted past actually improve future cognition and behavior?**

Or visually:

```text
World
  ↓
TRACES
  ↓
Discovery / Experience
  ↓
Knowledge / Skill
  ↓
KIP
  ↓
Durable Memory
  ↓
MIB
  ↓
Future Behavior
  ↓
New Experience
  ↺
```

KIP is not required by either benchmark.

But conceptually, it occupies an interesting middle layer between discovering something and proving that the discovery became a durable part of intelligence.

---

# So, Are TRACES and MIB Competitors?

Not really.

They share a diagnosis:

> **Static answer benchmarks are not enough for increasingly agentic AI.**

But they focus on different failure modes.

TRACES worries that an AI may produce an answer without conducting a trustworthy investigation.

MIB worries that an AI may experience something important without being durably changed by it.

TRACES asks:

> **Can you explore the unknown rigorously?**

MIB asks:

> **Can your past become part of your future intelligence?**

One evaluates **discoverative agency**.

The other evaluates **cross-temporal learning**.

Their overlap is real—but complementary.

---

# A Simple Way to Remember the Difference

If you remember only four lines from this article, make them these:

> **TRACES measures whether an AI can conduct a rigorous investigation and earn new knowledge.**

> **MIB measures whether past knowledge and experience become a durable causal part of future behavior.**

> **TRACES is mainly about discovery. MIB is mainly about accumulation.**

> **The larger frontier is Cumulative Intelligence: systems that discover, remember, learn, and then discover differently next time.**

That may ultimately be more important than either benchmark individually.

Because the real goal is not an AI that can solve one extraordinary problem.

It is an AI that can say:

```text
I tried.
I observed.
I was wrong.
I learned why.
I changed.
And the next time,
I began from somewhere new.
```

That is when experience stops being history and starts becoming intelligence. ([arXiv][1])

[1]: https://arxiv.org/abs/2608.11341?utm_source=chatgpt.com "Apodex Discovery: Reality Benchmarks and Environments for Evaluating and Building Discoverative Artificial Intelligence"
[2]: https://www.apodex.com/discover?utm_source=chatgpt.com "Apodex | Self-Evolving Heavy-Duty Solver"
[3]: https://traces.apodex.com/ "TRACES Benchmark"
[4]: https://github.com/ldclabs/MIB "Memory Intelligence Benchmark (MIB)"
