# Python Standards

## Purpose

This repo uses small amounts of Python for two cases:

- endpoint-side helpers that talk to local device APIs
- narrow custom Ansible modules for Intersight behaviors not covered cleanly by the official collection

The goal is to keep Python code minimal, readable, and tightly scoped.

## Preferred design

- keep orchestration, batching, and aggregation in Ansible
- use Python only for focused API behavior or custom module logic
- prefer the official `cisco.intersight` collection where it already works
- add custom Python only for unsupported or clearly broken gaps
- avoid building a parallel full Intersight framework in this repo

## Module vs helper rules

Use a custom Ansible module when:

- the logic is Intersight-side and should fit naturally into an Ansible task
- the code needs to return structured module results
- the behavior should reuse Cisco collection signing or module utilities

Use a standalone helper script when:

- the logic is endpoint-side and session-oriented
- the workflow is awkward to express as a module
- the script is tightly coupled to a local device API interaction

## Coding standards

- target Python 3
- follow PEP 8 style unless Ansible module conventions require a different layout
- use descriptive function names and keep functions small
- prefer explicit return values over hidden side effects
- avoid large monolithic scripts when a few focused functions will do
- keep imports standard-library-first, third-party next, local imports last
- use type hints when they improve readability
- use docstrings for modules and non-trivial functions
- keep comments sparse and useful

## Error handling

- return JSON-safe errors from helpers
- in custom modules, fail through module result handling instead of raw tracebacks
- include enough detail to diagnose API failures without dumping secrets
- prefer deterministic error messages over generic catch-all text

## Security rules

- never print API keys, private keys, claim codes, passwords, cookies, or tokens
- ensure secret-bearing module arguments are marked `no_log=True`
- let Ansible tasks use `no_log` when helper or module output may contain secrets
- avoid writing debug artifacts unless explicitly gated by `debug_enabled`

## Intersight-specific rules

- prefer reusing `ansible_collections.cisco.intersight.plugins.module_utils.intersight`
  in custom modules for signing and REST calls
- do not duplicate signing code across multiple custom modules unless there is a strong reason
- keep custom Intersight code narrowly focused on the missing workflow gap
- if the implementation requires hidden Resource Group or reservation plumbing, keep that detail out of the user input contract unless the product explicitly wants to expose it

## Testing and validation

- run `python3 -m py_compile` for every new helper or custom module
- syntax-check the affected playbook after wiring a new helper or module
- validate one real endpoint flow when changing claim or connector behavior
- document any live-tested assumptions in the relevant README or architecture notes

## Documentation expectations

For each custom Python component, document:

- why it exists
- what official module or collection gap it fills
- what inputs it expects
- what outputs it returns
- whether it is intended to remain temporary or strategic
