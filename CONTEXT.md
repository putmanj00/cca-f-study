# CCA-F Study App

This context describes the language used by the local practice app for Claude Certified Architect - Foundations exam preparation.

## Language

**Practice Bank**:
The full set of scenario-based multiple-choice questions available to the study app.
_Avoid_: exam dump, real exam, question dump

**Blueprint-Aligned Practice Set**:
A **Practice Bank** whose domain coverage approximates the published CCA-F domain weights.
_Avoid_: official exam, exact exam replica

**Domain**:
The CCA-F knowledge area a question primarily assesses.
_Avoid_: category, section

**Scenario**:
The realistic work situation used as the setting for a question.
_Avoid_: story, prompt

**Principle**:
The architectural judgment or reliability pattern the question is designed to test.
_Avoid_: topic, tag

**Anti-Pattern**:
A tempting but unreliable design choice that a question is meant to train against.
_Avoid_: trick answer, gotcha

## Relationships

- A **Practice Bank** contains many questions.
- A question belongs to exactly one **Domain** and one **Scenario**.
- A question tests one primary **Principle**.
- A question may identify one **Anti-Pattern**.
- A **Blueprint-Aligned Practice Set** is balanced by **Domain**, not by **Scenario**.

## Example Dialogue

> **Dev:** "Are we trying to recreate the official exam exactly?"
> **Domain expert:** "No - we are building a **Blueprint-Aligned Practice Set**. It should train the same architectural judgment across the published **Domains**, without implying these are real exam questions."

## Flagged Ambiguities

- "exam" can mean the official proctored CCA-F exam or this local **Practice Bank** - resolved: call the local asset the **Practice Bank** or **Practice Set**.
