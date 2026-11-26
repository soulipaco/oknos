# Security

Oknos runs on your own computer and listens on `127.0.0.1` only. It has no accounts and sends no learner data anywhere. The voice services it can use (each opt-in, with your own key in `learner/secrets.env`) receive only the Greek text of the content.

## Reporting a problem

Please report a security problem privately, not in a public issue: on the repository's **Security** tab, choose **Report a vulnerability** (or go straight to https://github.com/soulipaco/oknos/security/advisories/new). Only the maintainer sees the report.

Useful things to include: what an attacker could do, the steps to see it, and the version (the commit you are on). Never include a real learner's data or a real key.

Oknos is maintained by one person in their spare time, so there is no fixed response time, but a report is read and answered.

## What counts

For example: a way for a web page or another program to read or change a learner's data through the app, a way to reach the app from another machine, a key in `learner/secrets.env` reaching anything other than its own service, or private files ending up in a commit despite `oknos guard`.

Fixes go to `main`; there are no older versions kept up to date.
