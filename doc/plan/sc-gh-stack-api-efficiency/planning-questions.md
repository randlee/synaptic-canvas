# Calibrated planning questions

Generated from the independent sealed question sets; this rendering does not change them. Production planning confidence remains 0.6. A tournament seal does not itself establish that the active plan passes. The actual planning-gate result is recorded separately.

## ANC-001 — Reduce GraphQL bursts

The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.

Independent result: [ANC-001](anchor-runs/0.5.0/plan-tuning/ANC-001/result.md).

### relevant

Would the work described in `item.text` fall within the scope of this anchor? Decide only applicability. Obligation: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.

- yes: The item changes or discusses work governed by this scope: Changes to API scheduling or status recommendations in sc-gh-stack scripts and the sc-gh-stack/sc-gh-stack-view skills.
- no: The item concerns unrelated work outside that scope.
- unclear: The item is too vague to determine scope overlap.

### addressed

Is the specific required behavior expressly planned in `item.text`, allowing equivalent wording? Generic topic mention and silence do not include it. Obligation: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.

- yes: The item explicitly commits to this specific obligation: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.
- no: The item omits this obligation, only mentions its topic, or explicitly chooses an incompatible approach. Silence is no.
- unclear: The wording leaves whether the specific obligation is included unresolved.

### contradicted

Is there an express plan in `item.text` that breaks the required behavior? A missing commitment alone does not break it. Obligation: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.

- yes: The item explicitly adopts an approach incompatible with this obligation: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.
- no: No incompatible decision is stated. Silence, topical discussion, and permitted necessary remote calls are not conflict.
- unclear: An explicit decision is ambiguous as to whether it conflicts.

## ANC-002 — Gather only needed information

Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.

Independent result: [ANC-002](anchor-runs/0.5.0/plan-tuning/ANC-002/invocation-03/result.md).

### relevant

Determine whether `item.text` concerns the script behavior or recommendation governed here. Ignore whether it obeys the requirement. Obligation: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.

- yes: The item changes or discusses work governed by this scope: Adds or changes information gathering in stack scripts or the two stack skills' recommendations.
- no: The item concerns unrelated work outside that scope.
- unclear: The item is too vague to determine scope overlap.

### addressed

Look for a concrete commitment in `item.text` to the required behavior below. Merely reviewing its subject is insufficient. Obligation: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.

- yes: The item explicitly commits to this specific obligation: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.
- no: The item omits this obligation, only mentions its topic, or explicitly chooses an incompatible approach. Silence is no.
- unclear: The wording leaves whether the specific obligation is included unresolved.

### contradicted

Identify whether `item.text` commits to an incompatible behavior below. Do not treat silence or an unspecified detail as an opposing commitment. Obligation: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.

- yes: The item explicitly adopts an approach incompatible with this obligation: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.
- no: No incompatible decision is stated. Silence, topical discussion, and permitted necessary remote calls are not conflict.
- unclear: An explicit decision is ambiguous as to whether it conflicts.

## ANC-003 — Determine local state first

The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.

Independent result: [ANC-003](anchor-runs/0.5.0/plan-tuning/ANC-003/result.md).

### relevant

Determine whether `item.text` concerns the script behavior or recommendation governed here. Ignore whether it obeys the requirement. Obligation: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.

- yes: The item changes or discusses work governed by this scope: Changes stack discovery, state derivation, or a GraphQL request path in the stack scripts.
- no: The item concerns unrelated work outside that scope.
- unclear: The item is too vague to determine scope overlap.

### addressed

Look for a concrete commitment in `item.text` to the required behavior below. Merely reviewing its subject is insufficient. Obligation: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.

- yes: The item explicitly commits to this specific obligation: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.
- no: The item omits this obligation, only mentions its topic, or explicitly chooses an incompatible approach. Silence is no.
- unclear: The wording leaves whether the specific obligation is included unresolved.

### contradicted

Identify whether `item.text` commits to an incompatible behavior below. Do not treat silence or an unspecified detail as an opposing commitment. Obligation: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.

- yes: The item explicitly adopts an approach incompatible with this obligation: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.
- no: No incompatible decision is stated. Silence, topical discussion, and permitted necessary remote calls are not conflict.
- unclear: An explicit decision is ambiguous as to whether it conflicts.

## ANC-004 — Choose economical REST reads

The sc-gh-stack redesign must prefer REST to GraphQL when REST supplies the required information at lower quota cost.

Independent result: [ANC-004](anchor-runs/0.5.0/plan-tuning/ANC-004/round-2/result.md).

### relevant

Would the item modify the component that remotely gathers stack information or the decisions that choose REST versus GraphQL? Implementation maintenance of that reader counts as subject overlap; silence about source preference does not remove relevance. Prefer REST over GraphQL only when it provides equivalent required stack information at lower quota cost without equivalent request fanout.

- yes: The item touches the governed activity or its clear prerequisite.
- no: The activity is unrelated.
- unclear: The activity cannot be identified.

### addressed

Does the item explicitly include the anchor obligation as a constraint or action? Silence is no; a topic mention with an unresolved policy is unclear. Prefer REST over GraphQL only when it provides equivalent required stack information at lower quota cost without equivalent request fanout.

- yes: The required commitment is explicitly present, including legitimate conditional boundaries.
- no: The commitment is absent or explicitly rejected.
- unclear: Only the topic is raised and the required commitment remains unresolved.

### contradicted

Does the item explicitly adopt behavior incompatible with the anchor? Silence and an unresolved choice alone are no. Prefer REST over GraphQL only when it provides equivalent required stack information at lower quota cost without equivalent request fanout.

- yes: An explicit decision conflicts with the requirement under its applicable conditions.
- no: No incompatible decision is present; silence and legitimate exceptions do not conflict.
- unclear: Described behavior is ambiguous between compatible and incompatible choices.

## ANC-005 — Preserve stack mergeability

The sc-gh-stack redesign must preserve reporting of stack mergeability.

Independent result: [ANC-005](anchor-runs/0.5.0/plan-tuning/ANC-005/result.md).

### relevant

Does the item concern the activity governed by this anchor? Judge subject overlap only. Preserve reporting of stack content-conflict mergeability, distinct from hosted checks, approvals and policy eligibility.

- yes: The item touches the governed activity or its clear prerequisite.
- no: The activity is unrelated.
- unclear: The activity cannot be identified.

### addressed

Does the item explicitly include the anchor obligation as a constraint or action? Silence is no; a topic mention with an unresolved policy is unclear. Preserve reporting of stack content-conflict mergeability, distinct from hosted checks, approvals and policy eligibility.

- yes: The required commitment is explicitly present, including legitimate conditional boundaries.
- no: The commitment is absent or explicitly rejected.
- unclear: Only the topic is raised and the required commitment remains unresolved.

### contradicted

Does the item explicitly adopt behavior incompatible with the anchor? Silence and an unresolved choice alone are no. Preserve reporting of stack content-conflict mergeability, distinct from hosted checks, approvals and policy eligibility.

- yes: An explicit decision conflicts with the requirement under its applicable conditions.
- no: No incompatible decision is present; silence and legitimate exceptions do not conflict.
- unclear: Described behavior is ambiguous between compatible and incompatible choices.

## ANC-006 — Prefer local whole-stack mergeability

The sc-gh-stack redesign must prefer local computation of whole-stack mergeability when the required state can be determined locally.

Independent result: [ANC-006](anchor-runs/0.5.0/plan-tuning/ANC-006/result.md).

### relevant

Is the work within the anchor scope, including a clear prerequisite? Decide overlap, using the concrete obligation as context. Prefer local computation of content-conflict mergeability across the whole stack when the necessary state is locally available; scoped refresh of missing refs is allowed.

- yes: The item touches the governed activity or its clear prerequisite.
- no: The activity is unrelated.
- unclear: The activity cannot be identified.

### addressed

Is the concrete requirement present in this item, in equivalent words? A step or constraint counts; topic-only deliberation is unclear and silence is no. Prefer local computation of content-conflict mergeability across the whole stack when the necessary state is locally available; scoped refresh of missing refs is allowed.

- yes: The required commitment is explicitly present, including legitimate conditional boundaries.
- no: The commitment is absent or explicitly rejected.
- unclear: Only the topic is raised and the required commitment remains unresolved.

### contradicted

Does the item require an approach ruled out by this obligation? Missing coverage is no; unresolved possible conflict is unclear only when the described behavior itself is ambiguous. Prefer local computation of content-conflict mergeability across the whole stack when the necessary state is locally available; scoped refresh of missing refs is allowed.

- yes: An explicit decision conflicts with the requirement under its applicable conditions.
- no: No incompatible decision is present; silence and legitimate exceptions do not conflict.
- unclear: Described behavior is ambiguous between compatible and incompatible choices.

## ANC-007 — Preserve recipe strategies and outcomes

The sc-gh-stack redesign must preserve the stacking strategies and intended outcomes of established recipes when changing their git calls.

Independent result: [ANC-007](anchor-runs/0.5.0/plan-tuning/ANC-007/result.md).

### relevant

Does item.text discuss, optimize, or change established stacking recipes? This is subject overlap: information-gathering optimization inside an established recipe touches the recipe even when its exact git substitutions are not specified. Unrelated wallpaper changes are outside scope. Judge only applicability. Use the work area named in the item.

- yes: The item plans, changes, or depends on the thing the anchor statement is about, directly or as a clear prerequisite.
- no: The item is about a different part of the system or a different activity, and completing it would neither follow nor break the anchor.
- unclear: The item text is too vague to tell what part of the system it touches.

### addressed

Does item.text explicitly include preserving established recipe stacking strategies and intended outcomes under challenging conditions; equivalent git-call substitutions are permitted? Judge presence of the obligation only. A positive plan or concrete preservation qualifies. Silence is no; explicitly undecided inclusion is unclear. A proposal that rejects the obligation without including it is no.

- yes: The item text contains the directive's specific content, in its own words or the user's, as a step, constraint, or stated starting point.
- no: The item text is silent about the directive: it neither includes the directive's specific content nor references it.
- unclear: The item text alludes to the directive's topic but it is not possible to tell whether the directive itself is included.

### contradicted

Does item.text affirmatively choose to discard or alter an established recipe stacking strategy or intended outcome? Equivalent git substitutions are allowed. An unresolved future choice is not an adopted conflicting decision. Silence or discussion without an adopted incompatible behavior is no. Choose unclear only when an actual adopted decision has ambiguous compatibility.

- yes: The item text states a plan, approach, or decision that cannot be reconciled with the directive in the anchor statement.
- no: Nothing in the item text conflicts with the directive, whether or not the directive is mentioned.
- unclear: The item text is ambiguous enough that it might or might not conflict with the directive.

The prohibition verdict uses relevance and conflict; affirmative preservation prose is not required merely to avoid a conflict.

## ANC-008 — Design for 100-plus layers

The sc-gh-stack redesign must support stacks with more than 100 layers.

Independent result: [ANC-008](anchor-runs/0.5.0/plan-tuning/ANC-008/result.md).

### relevant

Does item.text concern the work governed by anchor.scope and anchor.statement, specifically supporting stacks with more than 100 layers; finite pagination and batching are allowed and unlimited capacity is not required? Judge subject overlap only, including implementation choices that could affect this duty.

- yes: The item plans, changes, or depends on the thing the anchor statement is about, directly or as a clear prerequisite.
- no: The item is about a different part of the system or a different activity, and completing it would neither follow nor break the anchor.
- unclear: The item text is too vague to tell what part of the system it touches.

### addressed

Does item.text explicitly include supporting stacks with more than 100 layers; finite pagination and batching are allowed and unlimited capacity is not required? Judge presence of the obligation only. A positive plan or concrete preservation qualifies. Silence is no; explicitly undecided inclusion is unclear. A proposal that rejects the obligation without including it is no.

- yes: The item text contains the directive's specific content, in its own words or the user's, as a step, constraint, or stated starting point.
- no: The item text is silent about the directive: it neither includes the directive's specific content nor references it.
- unclear: The item text alludes to the directive's topic but it is not possible to tell whether the directive itself is included.

### contradicted

Does item.text explicitly choose behavior incompatible with supporting stacks with more than 100 layers; finite pagination and batching are allowed and unlimited capacity is not required? Silence or undecided implementation is no conflict. Equivalent permitted alternatives do not conflict. Judge conflict only.

- yes: The item text states a plan, approach, or decision that cannot be reconciled with the directive in the anchor statement.
- no: Nothing in the item text conflicts with the directive, whether or not the directive is mentioned.
- unclear: The item text is ambiguous enough that it might or might not conflict with the directive.

## ANC-009 — Account for stale local state

The sc-gh-stack design must document how to obtain the required information when local repository state is out of date.

Independent result: [ANC-009](anchor-runs/0.5.0/plan-tuning/ANC-009/result.md).

### relevant

Does item.text concern the work governed by anchor.scope and anchor.statement, specifically documenting how required information is obtained when local repository state is out of date; targeted refresh and necessary remote reads are permitted? Judge subject overlap only, including implementation choices that could affect this duty.

- yes: The item plans, changes, or depends on the thing the anchor statement is about, directly or as a clear prerequisite.
- no: The item is about a different part of the system or a different activity, and completing it would neither follow nor break the anchor.
- unclear: The item text is too vague to tell what part of the system it touches.

### addressed

Does item.text explicitly include documenting how required information is obtained when local repository state is out of date; targeted refresh and necessary remote reads are permitted? Judge presence of the obligation only. A positive plan or concrete preservation qualifies. Silence is no; explicitly undecided inclusion is unclear. A proposal that rejects the obligation without including it is no.

- yes: The item text contains the directive's specific content, in its own words or the user's, as a step, constraint, or stated starting point.
- no: The item text is silent about the directive: it neither includes the directive's specific content nor references it.
- unclear: The item text alludes to the directive's topic but it is not possible to tell whether the directive itself is included.

### contradicted

Does item.text explicitly choose behavior incompatible with documenting how required information is obtained when local repository state is out of date; targeted refresh and necessary remote reads are permitted? Silence or undecided implementation is no conflict. Equivalent permitted alternatives do not conflict. Judge conflict only.

- yes: The item text states a plan, approach, or decision that cannot be reconciled with the directive in the anchor statement.
- no: Nothing in the item text conflicts with the directive, whether or not the directive is mentioned.
- unclear: The item text is ambiguous enough that it might or might not conflict with the directive.

## ANC-010 — Include tests despite live quota constraints

The sc-gh-stack redesign must include automated tests.

Independent result: [ANC-010](anchor-runs/0.5.0/plan-tuning/ANC-010/result.md).

### relevant

Does item.text concern the work governed by anchor.scope and anchor.statement, specifically including automated tests for the redesign; local fixtures and mocked API tests qualify and live GraphQL tests are not mandatory? Judge subject overlap only, including implementation choices that could affect this duty.

- yes: The item plans, changes, or depends on the thing the anchor statement is about, directly or as a clear prerequisite.
- no: The item is about a different part of the system or a different activity, and completing it would neither follow nor break the anchor.
- unclear: The item text is too vague to tell what part of the system it touches.

### addressed

Does item.text explicitly include including automated tests for the redesign; local fixtures and mocked API tests qualify and live GraphQL tests are not mandatory? Judge presence of the obligation only. A positive plan or concrete preservation qualifies. Silence is no; explicitly undecided inclusion is unclear. A proposal that rejects the obligation without including it is no.

- yes: The item text contains the directive's specific content, in its own words or the user's, as a step, constraint, or stated starting point.
- no: The item text is silent about the directive: it neither includes the directive's specific content nor references it.
- unclear: The item text alludes to the directive's topic but it is not possible to tell whether the directive itself is included.

### contradicted

Does item.text explicitly choose behavior incompatible with including automated tests for the redesign; local fixtures and mocked API tests qualify and live GraphQL tests are not mandatory? Silence or undecided implementation is no conflict. Equivalent permitted alternatives do not conflict. Judge conflict only.

- yes: The item text states a plan, approach, or decision that cannot be reconciled with the directive in the anchor statement.
- no: Nothing in the item text conflicts with the directive, whether or not the directive is mentioned.
- unclear: The item text is ambiguous enough that it might or might not conflict with the directive.
