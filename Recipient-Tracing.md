# Recipient Tracing Lab

A controlled mail-flow investigation using Postfix logs to identify every recipient of a benign test message.

**Abdellah Bayar · 5 October 2026**

## Result

**Five local mailboxes received the message.** Alice's copy lists three recipients in `To` and `Cc`. The delivery logs identify two additional recipients, Carol and Vittorio, who were included as blind-copy recipients in this controlled test.

| Recipient | Visible header in Alice's copy | Delivery time, UTC | Recorded outcome |
|---|---|---|---|
| `alice@lab.test` | To | 09:20:34.148495 | Delivered to Maildir |
| `bob@lab.test` | Cc | 09:20:34.150859 | Delivered to Maildir |
| `carol@lab.test` | Not listed | 09:20:34.152450 | Delivered to Maildir |
| `edoardo@lab.test` | Cc | 09:20:34.153637 | Delivered to Maildir |
| `vittorio@lab.test` | Not listed | 09:20:34.153883 | Delivered to Maildir |

All timestamps are from 5 October 2026. The delivery time corresponds to 11:20:34 in Italy (UTC+02:00).

## Environment

Windows Hyper-V · Ubuntu Server 24.04.5 LTS · Postfix 3.8.6 · Swaks 20240103.0 · rsyslog

- Sender: `labadmin@lab.test`.
- Five local recipient accounts with Maildir storage and login disabled.
- Postfix configuration: `mydestination` includes `lab.test`, `inet_interfaces = loopback-only`, `default_transport = error`, `home_mailbox = Maildir/`, and an empty `mailbox_command`.
- Plain-text message sent over SMTP to `127.0.0.1:25` within the VM.

## Investigation

### 1. Start from the received message

Alice's received copy contains:

```text
Delivered-To: alice@lab.test
To: alice@lab.test
Cc: bob@lab.test, edoardo@lab.test
Subject: [SOC-LAB] Recipient tracing test 02
Message-Id: <20261005091903.003053@soc-mail-lab>
```

The visible headers identify three recipients. They do not establish the full delivery scope.

### 2. Correlate the Message-ID with the queue

The Postfix cleanup record associates the Message-ID with queue ID `20B261E01F8`:

```text
2026-10-05T09:20:34.137417+00:00 soc-mail-lab postfix/cleanup[3067]: 20B261E01F8: message-id=<20261005091903.003053@soc-mail-lab>
```

The same queue ID appears in the received message's `Received` header and in the SMTP acceptance response.

### 3. Read the delivery outcomes

The queue manager records `nrcpt=5`. Five distinct recipient addresses then appear in local delivery records, each with:

```text
relay=local, dsn=2.0.0, status=sent (delivered to maildir)
```

The SMTP response `250 ... queued as ...` establishes acceptance into the queue. The local delivery records establish successful delivery to the five Maildir mailboxes.

The final `removed` record means that the processed message was removed from the delivery queue. It does not mean that the mailbox copies were deleted.

## Evidence

| File | What it establishes |
|---|---|
| [Received copy from Alice](soc-trace-alice-02.eml) | The actual received headers, body and transport queue ID |
| [Prepared test message](soc-trace-message-02.eml) | The plain-text content and visible recipient headers before transmission |
| [SMTP transcript](soc-trace-smtp-02.txt) | Five envelope recipients and acceptance into queue `20B261E01F8` |
| [Postfix delivery records](soc-trace-delivery-02.log) | Message-ID correlation and five successful local deliveries |
| [SHA-256 checksums](Recipient-Tracing-Checksums.sha256) | Checksums of the four exported evidence files |

The four evidence files were exported from the VM. Their contents have been preserved without editing. The log file is an extract of the records for this queue, rather than the complete server log.

## Scope and limitations

This experiment measures local delivery of a benign test message. It does not establish who opened, clicked or replied to it.

The message's `Date` header is 09:19:03 UTC, when the prepared message was created. The server records transmission and delivery at 09:20:34 UTC. The declared header date is not the delivery timestamp.

Recipient roles are known from the controlled setup. In a production investigation, an address absent from `To` and `Cc` could also result from distribution lists or forwarding, so that absence alone would not prove blind-copy delivery.

This is a separate exercise from the archived 2023 phishing sample in the parent project. The recipient scope of that original sample remains unknown.

## Reproduce

[Step-by-step reproduction guide](Recipient-Tracing-Reproduction-Guide.md)

## References

- [Ubuntu: Postfix configuration and mail logs](https://ubuntu.com/server/docs/how-to/mail-services/install-postfix/)
- [Swaks: SMTP envelope and message headers](https://www.jetmore.org/john/code/swaks/latest/doc/ref.txt)
- [Microsoft: related mail-flow records, forwarding and group expansion](https://learn.microsoft.com/en-us/exchange/monitoring/trace-an-email-message/message-trace-modern-eac)
