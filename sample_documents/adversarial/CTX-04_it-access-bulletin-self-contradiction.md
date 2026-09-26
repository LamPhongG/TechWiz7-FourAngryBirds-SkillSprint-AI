---
trap_id: CTX-04
title: IT Access Bulletin — MFA Rollout
category: Contradiction Test Case
status: Active
version: 1.0
effective_date: 2026-02-10
conflicts_with: itself (§2 vs §5) and DOC-06 §2 (Password & Authentication Standards)
contradiction_type: self_contradiction — same document disagrees with itself
---

# IT Access Bulletin — MFA Rollout

## 1. Background
This bulletin announces the rollout of multi-factor authentication (MFA) across company
systems.

## 2. MFA Requirement
Effective immediately, **MFA is mandatory for all systems**, with no exceptions, per
Information Security Policy DOC-06 §2.

## 3. Rollout Timeline
MFA will be enabled in phases over the next two weeks, department by department.

## 4. Support
Contact IT Support if you have trouble setting up MFA on your device.

## 5. Reducing Login Friction
To reduce login friction during the rollout, **MFA is optional for internal-only tools**
such as the intranet wiki and the shared calendar. Employees may enable it later once the
rollout stabilizes.

<!--
TEST NOTE: this is a same-document contradiction — §2 says MFA is mandatory
for ALL systems "with no exceptions", while §5 immediately carves out an
exception for internal tools. No comparison against another document is
needed to catch this one; it tests the checker's ability to detect
internal inconsistency within a single source, which is a prerequisite for
correctly resolving contradictions across documents. It's also useful as a
regression case: whichever rule wins, the checker must not silently ignore
the other line as if it doesn't exist.
-->
