# Phishing Email Investigation

A phishing investigation combining static analysis of an archived Microsoft impersonation email with a separate, controlled campaign delivered to five local mailboxes.

## Results

- **Archived sample:** phishing using Microsoft brand impersonation and reply redirection. All three action links are `mailto:` links to an unrelated Gmail mailbox; a hidden external image is consistent with tracking. No web sign-in page, password form or successful credential theft was observed.
- **Local simulation:** five confirmed Maildir deliveries. Alice, Bob and Edoardo appear in To/Cc; Carol and Vittorio are identified in the SMTP envelope and server records.
- **Limits:** the original campaign's recipients remain unknown. Opening, clicking, replies, credential entry and compromise were not measured in the local simulation.

## Reports

- [Investigation report](docs/Phishing-Campaign-Investigation-Abdellah-Bayar.pdf) - verdict, archived evidence, simulation findings, recipient scope and recommended response.
- [Reproduction guide](docs/Phishing-Campaign-Lab-Reproduction-Guide.pdf) - environment, technologies, commands, verification and evidence export.
- [Investigation in Markdown](docs/Investigation.md)
- [Reproduction guide in Markdown](docs/Reproduction-Guide.md)

## Actual local run

Run: `20261005T122642Z-08257e25`. Queue ID: `07C5A1E01FC`.

Message-ID:

```text
<179120320293.1674.8861293320127582421.phishing-lab-20261005T122642Z-08257e25@lab.test>
```

| Recipient | Visible header | Delivered 5 October 2026, UTC |
|---|---|---|
| alice@lab.test | To | 12:26:43.048235 |
| bob@lab.test | Cc | 12:26:43.050774 |
| carol@lab.test | Absent | 12:26:43.052262 |
| edoardo@lab.test | Cc | 12:26:43.054041 |
| vittorio@lab.test | Absent | 12:26:43.054089 |

Every delivery has `dsn=2.0.0` and `status=sent (delivered to maildir)`. Five matching received copies were preserved and their hashes verified after export. Nine native queue log records correlate the Message-ID with queue processing and final deliveries. Queue acceptance alone was not used as proof of mailbox delivery.

Carol and Vittorio have blind-copy-equivalent delivery in this deliberately configured simulation. No Bcc header is included. In production, forwarding or distribution lists can also result in recipients absent from To/Cc.

## Technologies

Windows Hyper-V; Ubuntu Server 24.04.5 LTS; Postfix 3.8.6; Swaks 20240103.0; rsyslog; Maildir; OpenSSH/SCP; Python 3; SHA-256; Notepad; existing VirusTotal domain reports.

The VM uses 4 GB RAM, 2 vCPUs and a 40 GB virtual disk. Postfix listens on loopback only with `lab.test` configured for local delivery and `default_transport=error`. The VM has installation connectivity through the Hyper-V Default Switch.

## Repository map

```text
docs/                 Investigation and reproduction reports
lab/                  Labelled template and local campaign runner
evidence/archive/     Captured VirusTotal reports
evidence/simulation/  Actual run summary, configuration and native evidence
SHA256SUMS            Package integrity manifest
```

`lab/run_campaign.py` validates the dedicated VM setup, submits one labelled message to five local test accounts and exports the real evidence. It requires sudo to read recipient Maildirs and mail.log. It stops on unexpected hosts, recipients, destinations or settings. It preserves the original mailbox files.

## Reproduce

Follow the [reproduction guide](docs/Reproduction-Guide.md). It includes Windows and Ubuntu commands and explains their execution context. Each new run produces a fresh Date, Message-ID, queue ID and result directory. Document those actual values rather than copying the reference run.

The simulation uses reserved `.test` domains. No live sign-in website, credential form or tracking service is provided. Authentication-Results are not inserted; the local simulation does not evaluate the archived email's SPF/DKIM/DMARC results.

From inside the native run's evidence directory on Ubuntu, verify the eight exported data files with `sha256sum -c SHA256SUMS`. From the repository root, `sha256sum -c SHA256SUMS` verifies the packaged files. Git attributes preserve native evidence bytes.

## Archived evidence and provenance

The original `sample-10.eml` is linked from the [Phishing Pot collection at a pinned revision](https://github.com/rf-peixoto/phishing_pot/blob/097878eab3043ced70fde2ce0fb3b660fb58717e/email/sample-10.eml); it is not redistributed here. It was not received in my own mailbox. The collection anonymises recipient information as `phishing@pot`; see the [upstream licence](https://github.com/rf-peixoto/phishing_pot/blob/097878eab3043ced70fde2ce0fb3b660fb58717e/LICENSE).

Original sample SHA-256:

```text
4fbf4c3d80aba156c59004c12c83ff53dd64c9cf7b7a6029e98fe1da0760783a
```

The archived gateway records SPF `none`, DKIM `none` and DMARC `permerror; action=none`. These are not `fail`; the exact DMARC error cause is unknown. DNS authentication was not re-evaluated.

VirusTotal results recorded on **5 October 2026**: visible sender domain 0/91, SMTP sender domain 0/91, hidden image domain 9/91. The nine red classifications comprise seven Phishing and two Malicious; ESET Suspicious is separate. A 0/91 score does not establish safety. The 2026 reports do not establish reputation at the time of the 2023 message.

Two captured reports are included under [evidence/archive](evidence/archive). The visible sender screenshot is cropped to the report area; the SMTP sender result was recorded from text and has no screenshot. The original sample and the new simulation have distinct message identifiers and evidence.

## Response

Preserve and report the message, investigate delivery scope, quarantine confirmed matches and validate targeted blocks. Use separate interaction and sign-in telemetry if account impact is suspected. In this exercise, delivery investigation and evidence preservation were completed; quarantine, blocking and account changes remain recommendations.

The earlier [Postfix Recipient Tracing Lab](https://github.com/abdellahbayar/postfix-recipient-tracing-lab) remains a separate foundational exercise.

Technical sources are linked in both reports.
