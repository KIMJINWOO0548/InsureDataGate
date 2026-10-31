# Security

InsureDataGate is an offline local dataset checker. It does not upload files, contact sources, authenticate declared approvers, or certify data rights. Treat its PASS result as a local consistency check only.

Use synthetic data only. Do not place customer records, credentials, access tokens, private keys, or other secrets in manifests, source files, cases, gold records, command output, or issue reports. Keep private datasets and generated exports out of public repositories.

The validator is designed to avoid printing case and gold contents in diagnostics. Reports can still reveal dataset identifiers, filenames, hashes, counts, and issue locations; review them before sharing. Filesystem races and hardlink attacks are outside the documented threat model; see `docs/CONTRACT.md`.

No security reporting contact is published in this repository. Do not invent or infer one. Avoid publicly disclosing secrets or sensitive dataset contents; use an established private channel with the project maintainers if one is available to you.
