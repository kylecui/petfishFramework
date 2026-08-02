# BDD Methodology: Discovery, Formulation, and Automation

This file documents the behavior-driven development lifecycle: how teams collaborate to discover requirements, formulate them as executable specifications, and implement them through disciplined TDD.

## The BDD Lifecycle

### Discovery Phase: Three Amigos

Before writing code or tests, Business/Product Owner, Developer, and Tester meet to discuss the feature. This is not a requirements handoff; it's a structured conversation to reach shared understanding.

- **Goal**: Establish what the system should do before deciding how it should do it.
- **Method**: Use Example Mapping — write concrete examples of user behavior on sticky notes, identify rules, and uncover edge cases collaboratively.
- **Output**: A set of agreed-upon examples that describe expected behavior in business terms.

### Formulation Phase: Gherkin Scenarios

Convert discovery examples into structured Gherkin scenarios (Given/When/Then). This creates executable specifications that serve as living documentation.

- **Goal**: Translate business intent into a testable contract.
- **Standard**: Scenarios must be declarative (what the user does) not imperative (how they do it).
- **Reference**: See [gherkin-reference.md](./gherkin-reference.md) for syntax rules and examples.

### Automation Phase: Red-Green-Refactor TDD

Implement scenarios using strict TDD cycles. Each scenario drives at least one complete cycle; complex scenarios may require multiple cycles to generalize the implementation.

- **RED**: Write a failing test that captures the scenario's expected behavior.
- **GREEN**: Write minimal production code to make the test pass.
- **REFACTOR**: Clean up code structure while tests remain green.
- **Reference**: See [tdd-three-laws.md](./tdd-three-laws.md) for the Three Laws of TDD discipline.

## BDD vs. TDD: Collaboration vs. Development

| Aspect | BDD | TDD |
|--------|-----|-----|
| Scope | Acceptance-level behavior (what to build) | Unit-level implementation (how to build) |
| Participants | Business + Dev + QA collaboration | Developer practice |
| Artifacts | Gherkin scenarios, executable specifications | Unit tests, production code |
| Timing | Before code: defines requirements | During code: guides implementation |

BDD and TDD work together: BDD defines the contract through collaboration; TDD ensures the implementation honors that contract through disciplined cycles.

## When BDD Is Overkill

Not all features need full BDD ceremony. Skip BDD for:
- Simple CRUD operations with clear requirements
- Throwaway prototypes and proof-of-concepts
- Internal utilities with no business stakeholder input
- Pure algorithmic work with well-defined mathematical contracts

For these cases, direct TDD without Gherkin formulation is sufficient.

## Example Mapping Technique

When the Three Amigos discuss a feature, use Example Mapping to structure the conversation:

1. **Write the user story** on a yellow sticky: "As a user I want..."
2. **Write concrete examples** on green stickies: "Given... When... Then..."
3. **Identify rules** on blue stickies extracted from examples: "Validate that..."
4. **Discover questions** on red stickies: "What happens when..."

This surfaces edge cases and ambiguity before any code is written, preventing rework and clarifying acceptance criteria.

## Outside-In vs Inside-Out

Two complementary styles of BDD-driven development:

**Outside-In (London school)**: Start from the outermost behaviour (HTTP
endpoint, CLI command, user action). The acceptance test comes first; work
inward through layers (controller → service → repository), discovering
collaborators as you go. Mocks define interfaces of not-yet-existing
collaborators.

**Inside-Out (Chicago / Classical school)**: Start from the innermost
domain logic. Build and test core entities first, then compose outward.
No mocks — use real collaborators.

BDD works with both, but outside-in aligns more naturally with Gherkin
scenarios: the scenario describes observable behaviour. If your `Then`
clause references internal state rather than observable output, you may be
writing inside-out tests in Gherkin clothing.

## Given-When-Then as Collaboration Tool

Gherkin is not just a test template — it is a **collaboration contract**.
During Discovery, the Three Amigos draft Given/When/Then together. The act
of writing Gherkin exposes three failure modes:

- **Missing context**: the Given can't be set up → the precondition is
  unclear or impossible.
- **Ambiguous action**: the When has multiple interpretations → the
  requirement is underspecified.
- **Unmeasurable outcome**: the Then can't be asserted → the acceptance
  criteria are subjective.

If a scenario can't be expressed in Given/When/Then, that is a signal the
requirement isn't ready for implementation — not a signal to relax the
format.

## Facilitating Example Mapping

Structure the Three Amigos conversation (Matt Wynne's technique):

1. **Time-box**: 25-30 minutes per feature. Longer = diminishing returns.
2. **Story** (yellow): one sentence, the user story under discussion.
3. **Rules** (blue): each a business rule extracted from the story
   ("password must be 8+ characters").
4. **Examples** (green): each a concrete instance attached to the rule it
   illustrates ("password `abc` → rejected", "password `abc123!@#` →
   accepted").
5. **Questions** (red): anything unresolved ("do we enforce special
   characters?"). These become follow-up items, not blockers.

Output: a visual map of rules → examples → open questions. This feeds
Gherkin formulation directly: each example becomes a Scenario, each rule
becomes a Feature or Background constraint.