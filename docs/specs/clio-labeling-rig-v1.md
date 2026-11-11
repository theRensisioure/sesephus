# Clio Labeling Rig Contract v1

This document freezes a fair test rig for cluster-summary labeling. It is a
design contract, not an implementation claim. It does not implement Clio, and
it does not claim that Anthropic published this harness.

## Purpose

The rig grades the cluster summary a person is allowed to see. Privacy
aggregation runs before any routine label. The human task stays small: title
fit, membership, and anonymous side-by-side votes on the comparisons that
shrink uncertainty fastest. A short blinded expert pass audits those votes.
Screening stops on a recall test that was locked before the run.

## Frozen principles

1. **The summary is the visible unit.** A routine reviewer sees a cluster
   title and member summaries.
2. **Privacy runs before display.** Four layers produce that view. The facet
   step is instructed to omit private information. Clusters below the
   configured account floor and conversation floor are discarded. The summary
   step is instructed to omit private information. An auditor removes clusters
   whose summaries are still identifying.
3. **The size floor fails closed.** The published Clio work says a minimum
   number of unique accounts and of conversations exists, and it withholds
   that number. This contract sets no default. A blank floor shows no cards.
4. **The privacy line is 3.** On the published 1–5 scale, 3 means
   identification might narrow to a few thousand people, and 3 and above is
   the acceptable line. A summary scored below 3 is not shown. A summary
   scored 3 is shown and counted on its own scoreboard line.
5. **Votes that count are anonymous and side by side.** The person picks the
   better summary, a tie, or both bad. Names appear only after the vote.
   Votes cast after names are shown stay out of the official ranking. Text
   that names a model or its company stays out of the ranking sample.
6. **The sampler chooses the pair.** Pairs are drawn by how much they are
   expected to shrink the confidence interval. Each counted vote is
   reweighted by the inverse of its sampling probability. The voter does not
   set that probability.
7. **Experts audit a sample locked in advance.** Experts see the same card,
   with no names, and a fact-check is recorded separately. Crowd agreement
   and expert-with-expert agreement are both reported. The expert pass does
   not replace the crowd vote.
8. **Screening stops on a test locked in advance.** Stopping is allowed only
   when a hypergeometric test rejects the hypothesis that recall is below the
   locked target, at the locked significance level. A streak of irrelevant
   items is not a stop. A pile that looks finished is not a stop.
9. **A concern score does not punish an account.** Concern scores may sit
   beside an independent flag rate on the scoreboard. They do not change
   access, and they do not ban or restrict anyone. A cluster cannot prove
   that a pattern is absent.
10. **Borrowed measurements stay labeled.** Chatbot Arena sampling figures and
    the screening-review stop rule are method references. They are not Clio's
    label budget. Clio did not publish review time, throughput, or
    inter-rater disagreement.

## Run record

A run shows no cards until every required field is filled.

Required. No defaults except the privacy line.

- `min_unique_accounts` — integer
- `min_conversations` — integer
- `privacy_accept_minimum` — locked at `3` for v1
- `recall_target` — set before screening
- `significance_level` — set before screening
- `expert_sample_size` — set before the expert pass
- `title_miss` — a written definition of a title that does not match
- `membership_miss` — a written definition of a member that does not belong
- `pair_sampling` — must name uncertainty-reduction sampling and
  inverse-probability reweighting
- `raw_access` — must be `closed`

Optional. An empty field is not in force. These were not found as Clio
protocol gates, so v1 does not invent them as requirements.

- `labeler_demographic_note`
- `factual_versus_normative_rule`
- `false_positive_false_negative_asymmetry`

## Routine card

The card carries:

- a cluster id
- a cluster title
- member summaries
- a privacy score on the 1–5 scale
- one title judgment: yes or no
- one membership judgment per shown member: yes, no, or unsure
- an optional note when a title miss is "too generic"

The card carries no raw conversation, no account identifier, no model name,
and no company name.

## Pairwise ballot

The ballot carries two summaries and one choice: left, right, tie, or both
bad. Names and provenance stay hidden until the choice is stored. A ballot
cast after the reveal is stored as excluded. A summary that names a model or
a company is excluded from the ranking sample.

## Expert pass

The expert sees the routine card and the pairwise ballot with names hidden.
The fact-check is a separate record from the vote. The report states
agreement with the crowd and agreement among experts.

## Stop rule

The hypothesis under test is that recall is below `recall_target`. Screening
may stop only when the hypergeometric test rejects that hypothesis at
`significance_level`. Both numbers come from the run record, written before
any card is shown.

## Scoreboard

Report these lines separately. They do not collapse into one grade.

- share of clusters at privacy 5, at 4, at 3, and below 3
- title accuracy for random clusters and for flagged clusters, apart
- membership-miss rate
- summary fidelity on a held-out slice
- expert agreement with the crowd
- expert agreement with each other
- ballots excluded because a name was visible, or because the text named a
  model or a company
- a concern score beside an independent flag rate, when both exist

Published reference points. They are not defaults for a new run.

- Privacy audit of 5,000 conversations: about 10% of raw conversations scored
  1 or 2, about 1.5% did after summarization, and cluster summaries were
  almost all 5, a few 4, and none below 3. The rater was 98% accurate on
  1,237 hand-built examples (630 not privacy-preserving, 607
  privacy-preserving).
- Titles on 183 base clusters and 5,904 assignments: 99% on random clusters
  and 96% on flagged clusters. Hierarchical assignments, 1,094 of them: 95%
  random and 99% flagged. Combined accuracy was 97% for both clusterers.
  About 3% of members did not clearly belong. Harm titles tended to go too
  generic.
- Conversation summaries: 200 checked, 96% accurate (93% on a random slice,
  98% on concerning ones).
- Synthetic reconstruction: 19,476 general chats at 94%, against 5% for a
  guess, across 20 top-level categories and 15 languages, above 92% in every
  tested language on the non-concerning set. A second set holds 19,488
  concerning conversations across 18 high-level topics.
- Concern against an independent flag rate: Pearson r = 0.71 on cluster
  means. On 200 conversations, model and human concern scores correlated at
  Spearman 0.84.
- Arena sampling reference: precision 0.2 at 4,400 uncertainty-sampled votes,
  against 6,800 random votes, on a Bradley-Terry fit to 213,576 holdout
  votes.
- Arena expert reference: 160 blinded battles. Agreement with the crowd was
  72.8% and 77.8% on one pair, with experts agreeing at 89.8%. On the other
  pair it was 73.8% and 83.1%, with experts agreeing at 79.4%.
- Screening stop-rule reference: about 17% less work on that paper's test
  sets. Clio did not publish this saving.

## Safety path

Account-level safety review is outside this contract. Any path that turns
aggregation off, ties a result to an account, or shows a raw conversation to
designated staff needs its own contract. Privacy numbers from the aggregated
audit describe the aggregated path only. This contract gives that path no
fields and no actions.

## Explicit non-goals for v1

- No labeling UI, API, database, queue, or watcher
- No default cluster-size floor, recall target, significance level, or
  expert sample size
- No raw-conversation viewer
- No account ban, rate limit, or access change
- No claim that a concern score proves a violation
- No claim of review-time savings for Clio
- No vendor of an external clustering pipeline, its prompts, or its withheld
  hyperparameters, including k for k-means
- No rename of Method Cards, and no use of this contract as a methods
  database
- No claim that the audio PR-review contract specifies this labeling design
- No copy of this contract into the private Sesefus tree as shared runtime
- No claim that the current Sesephus runtime labels clusters

## Sesephus relationship

The contract lives in this public lineage repository as documentation. A
future implementation must decide separately whether the rig lives here, in
an external sibling, or in a new repository. Until that decision, this tree
holds the contract only.

The supported Voice boundary remains external Clippers at
`C:\dev\journal-clippers\audio-journal-system`. This contract does not change
that boundary.

## Sources

Figures in the reference list were recorded from Tamkin et al., Clio,
arXiv:2412.13678; Chiang et al., Chatbot Arena, arXiv:2403.04132; the Arena
FAQ; and "Statistical stopping criteria for automated screening in systematic
reviews" (https://link.springer.com/article/10.1186/s13643-020-01521-4). The
local research writeup that gathered them is partial. Exact minimum
unique-user counts, k for k-means, and an official public evaluation
repository for these checks stay unresolved there, so they stay unresolved
here.
