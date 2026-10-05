# Phishing Email Investigation

A manual investigation of a Microsoft account alert using email headers, HTML link inspection and VirusTotal domain reports, followed by a controlled recipient-tracing exercise on a local Postfix server.

## Project contents

| Exercise | Result | Documentation |
|---|---|---|
| Archived phishing email | Microsoft brand impersonation; action links prepare drafts to an unrelated mailbox | [Phishing investigation report](Phishing-Email-Investigation-Abdellah-Bayar.pdf) |
| Local recipient tracing | Five confirmed mailbox deliveries, including two recipients absent from the visible headers | [Tracing findings](Recipient-Tracing.md) · [Reproduction guide](Recipient-Tracing-Reproduction-Guide.md) |

## Verdict

**Phishing with Microsoft brand impersonation.** The message presents itself as a Microsoft security notification, but replies and all three embedded action links point to an unrelated Gmail mailbox. A hidden external image is consistent with a tracking pixel.

No sign-in page, password request or successful credential theft was observed in this sample.

## Investigation

Sample: `sample-10.eml` from the public [Phishing Pot collection](https://github.com/rf-peixoto/phishing_pot/blob/097878eab3043ced70fde2ce0fb3b660fb58717e/email/sample-10.eml). Tools: Notepad and VirusTotal. The email was inspected as text; its links and external image were not opened.

| Evidence | Recorded value | Interpretation |
|---|---|---|
| Display name | Microsoft account team | Claims to represent Microsoft |
| From address | `no-reply@access-accsecurity[.]com` | Differs from Microsoft's documented account alert sender |
| Reply-To | `sotrecognizd@gmail[.]com` | Replies go to a separate Gmail mailbox |
| SMTP MAIL FROM domain | `thcultarfdes[.]co.uk` | Distinct from the visible From domain |
| Sending server IP | `89.144.44.2` | Recorded in the receiving gateway's headers |
| Three `href` links | `mailto:` to the Reply-To mailbox, also in CC | Prepare email drafts; no web login destination observed |
| Hidden image | `thebandalisty[.]com/track/...`, 1 x 1, `visibility:hidden` | Consistent with possible email tracking |
| Body claim | Russia/Moscow, `103.225.77.255` | Unverified sign-in details supplied by the message |

The receiving gateway recorded the external SMTP handoff on **8 September 2023 at 05:47:04 UTC**. The body IP is distinct from the sending server IP; neither identifies a person or proves account compromise.

### Email authentication

| Check | Result in the archived headers | Interpretation |
|---|---|---|
| SPF | `none` | No SPF policy was found for the SMTP sender domain |
| DKIM | `none` | No DKIM signature was found |
| DMARC | `permerror`, `action=none` | Permanent evaluation error; the exact cause is unknown |

These recorded results are different from `fail`. They add context to the investigation and do not, on their own, establish phishing. DNS authentication was not re-evaluated.

### Domain reputation

Existing VirusTotal reports consulted during the lab, recorded on **5 October 2026**:

| Domain | Role | Malicious detections | Last analysis, as displayed |
|---|---|---|---|
| `access-accsecurity[.]com` | Visible sender | 0/91 | 2 months ago |
| `thcultarfdes[.]co.uk` | SMTP sender | 0/91 | 26 days ago |
| `thebandalisty[.]com` | Hidden image host | **9/91** | 4 days ago |

The nine red classifications comprise seven **Phishing** and two **Malicious** results. ESET reports **Suspicious** separately. A 0/91 result does not establish safety, and the 2026 reports do not establish the domains' reputation when the email was sent in 2023.

## Recommended response

1. Avoid replying, clicking links or loading external images. Preserve the original email and report it through the organisation's phishing reporting process.
2. Have the security team quarantine or remove confirmed matching messages and apply targeted blocks after checking the indicators. Blocking all Gmail traffic would be too broad.
3. Search mail-flow records for related messages and establish who received or interacted with them. If sensitive information was disclosed or account compromise is suspected, investigate sign-in activity and secure the affected account.

For the archived phishing sample, these are proposed actions. Mailbox searches, blocking and remediation were not performed against its original environment. Its recipient scope, user interaction and account impact remain unknown.

## Recipient tracing extension

A separate benign test on a local Postfix server established **five successful deliveries**. Alice's received copy lists three visible recipients; the mail logs identify two additional blind-copy recipients in the controlled setup.

- [Recipient tracing findings and evidence](Recipient-Tracing.md)
- [Step-by-step reproduction guide](Recipient-Tracing-Reproduction-Guide.md)
- [SHA-256 checksums of the four exported evidence files](Recipient-Tracing-Checksums.sha256)

The repository includes the prepared message, Alice's received copy, the SMTP transcript and the delivery log extract. Git attributes preserve their original line endings when the repository is cloned.

This extension demonstrates delivery tracing with local server logs. The recipient scope and user interaction for the archived phishing sample remain unknown.

## Documentation

- [Investigation report](Phishing-Email-Investigation-Abdellah-Bayar.pdf)
- [VirusTotal evidence: visible sender](01-virustotal-access-accsecurity.png)
- [VirusTotal evidence: hidden image domain](03-virustotal-thebandalisty.png)

The visible-sender screenshot is cropped to the report area, preserving the displayed security results. The SMTP domain result was recorded from the report text; no screenshot was captured for that lookup.

## Reproduce the investigation

Use the pinned [source sample](https://github.com/rf-peixoto/phishing_pot/blob/097878eab3043ced70fde2ce0fb3b660fb58717e/email/sample-10.eml) and open it in a text editor. Compare `From` and `Reply-To`, inspect `Authentication-Results` and `Received`, then search the HTML for `href=` and `<img`. Record each destination and its role before checking existing domain reports. Keep observations separate from assumptions in the verdict.

Original sample SHA-256:

```text
4fbf4c3d80aba156c59004c12c83ff53dd64c9cf7b7a6029e98fe1da0760783a
```

## Sources

The sample comes from **rf-peixoto/Phishing Pot**, revision `097878eab3043ced70fde2ce0fb3b660fb58717e`; see the [upstream licence](https://github.com/rf-peixoto/phishing_pot/blob/097878eab3043ced70fde2ce0fb3b660fb58717e/LICENSE). The collection anonymises recipient information as `phishing@pot`. That placeholder is not evidence of the sender's original wording, and the sample was not received in my own mailbox.

- [Microsoft: unusual sign-in notifications](https://support.microsoft.com/en-us/accounts-billing/security/what-happens-if-there-s-an-unusual-sign-in-to-your-account)
- [Microsoft: email authentication results](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-troubleshoot)
- [RFC 7489: DMARC result meanings](https://www.rfc-editor.org/rfc/rfc7489.html#appendix-C)
- [VirusTotal: domain report fields](https://docs.virustotal.com/reference/domains-object)
