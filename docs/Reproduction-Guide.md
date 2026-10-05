# Phishing Campaign Lab - Reproduction Guide

Abdellah Bayar | 5 October 2026

## Environment and execution context

A free local lab. No Microsoft 365 tenant or Exchange administrator access is required.

| Component | Reference setup / role |
| --- | --- |
| Windows / Hyper-V | Hosts a Generation 2 VM named SOC-Mail-Lab. |
| VM resources | 4 GB RAM, 2 vCPUs, 40 GB virtual disk; Default Switch. |
| Ubuntu Server 24.04.5 LTS | Hostname soc-mail-lab; administrator labadmin. |
| Postfix 3.8.6 | Local SMTP acceptance and Maildir delivery. |
| Swaks 20240103.0 | SMTP client and native transaction transcript. |
| rsyslog / Maildir | /var/log/mail.log and one file per received message. |
| Python 3 / SHA-256 | Runner validation, collection and evidence integrity. |
| OpenSSH / SCP | Remote terminal and evidence transfer from Windows. |

Use a dedicated VM with only lab data. Install the regular Ubuntu Server image and OpenSSH Server. For a Hyper-V Generation 2 Linux VM, choose the Microsoft UEFI Certificate Authority Secure Boot template. The reference disk uses ext4 for root and FAT32 for EFI. [11]

**Where commands run:** PowerShell commands run on Windows. Bash commands run inside Ubuntu, either in its console or an SSH session. A Windows terminal connected by SSH executes its commands on the VM.

The SMTP service listens only on 127.0.0.1 inside Ubuntu. Internet connectivity is needed to install packages, while test delivery remains local. This reproduces local recipient tracing, not the Exchange Message Trace interface.

## Configure the local mail server

Bash on the Ubuntu VM. Reuse the existing configuration when its checks already match.

**INSTALL PACKAGES**

```text
sudo apt update
sudo apt install postfix swaks rsyslog openssh-server
sudo systemctl enable --now rsyslog ssh
```

At the Postfix package prompt, choose **Local only** and enter **lab.test** as the system mail name. If Postfix is already installed, check its settings before changing them. Ubuntu documents Maildir delivery and Postfix logging. [9]

**LOCAL DELIVERY SETTINGS**

```text
sudo postconf -e 'inet_interfaces = loopback-only'
sudo postconf -e 'default_transport = error'
sudo postconf -e 'home_mailbox = Maildir/'
sudo postconf -e 'mailbox_command ='
sudo postconf -e 'mydestination = lab.test, $myhostname,
  soc-mail-lab, localhost.localdomain, localhost'
sudo systemctl restart postfix
```

The single-quoted mydestination value spans two Bash lines; keep both lines in the same quoted argument. Check that the hostname is soc-mail-lab. The runner intentionally stops on an unexpected host, account or configuration.

**VERIFY BEFORE SENDING**

```text
hostname
postconf inet_interfaces default_transport home_mailbox \
  mailbox_command mydestination
getent passwd alice bob carol edoardo vittorio
sudo ss -ltnp | grep ":25 "
```

If a recipient does not exist, create only that missing account with sudo useradd -m -s /usr/sbin/nologin USERNAME. Use alice, bob, carol, edoardo and vittorio. They do not need interactive login or passwords. Confirm that mail.log exists and SMTP listens on loopback.

## Inspect both message sources

Static analysis of the archive and inspection of the labelled simulation are separate steps.

### Archived phishing sample

Obtain sample-10.eml from the pinned Phishing Pot revision [1]. Open it as text in Notepad, rather than rendering its HTML. Compare From, Reply-To and the SMTP sender, inspect Authentication-Results and Received, then find href= and image src attributes. Do not open the recorded destinations.

**EXPECTED ARCHIVED SAMPLE SHA-256**

```text
4fbf4c3d80aba156c59004c12c83ff53dd64c9cf7b7a6029e98fe1da0760783a
```

Record the exact authentication values: SPF none, DKIM none and DMARC permerror. Separate mailto links from web links, the external image from an attachment, and the body IP from the sending SMTP peer. Consult existing domain reputation reports and record their capture dates. [2-5]

### Controlled source: lab/campaign-message.eml

| Inspect | Expected simulation observation |
| --- | --- |
| Sender and reply | Microsoft display name; account-alerts.test From and account-review.test Reply-To. |
| Requested action | Review unusual sign-in activity within 24 hours. |
| Destination | http://account-review.test/verify; no web service is provided. |
| Recipients | Alice in To; Bob and Edoardo in Cc. |
| Lab marker | X-Lab-Simulation: true and an explicit disclaimer. |

The template has no Date or Message-ID. The runner assigns a fresh value for each run. It includes no Authentication-Results; do not add fabricated SPF, DKIM or DMARC verdicts. All external-looking destinations use reserved .test domains. [8]

## Run the controlled simulation

The included runner submits one message to the five named local accounts and saves native evidence.

Open PowerShell in the downloaded repository root. Replace VM_IP with the current address reported by hostname -I inside Ubuntu. Use the labadmin password only at the local terminal prompt.

**POWERSHELL: TRANSFER AND CONNECT**

```text
ssh labadmin@VM_IP "mkdir -p ~/phishing-campaign-lab"
scp lab/run_campaign.py lab/campaign-message.eml `
  labadmin@VM_IP:/home/labadmin/phishing-campaign-lab/
ssh labadmin@VM_IP
```

**BASH: START ONE RUN**

```text
cd /home/labadmin/phishing-campaign-lab
sudo /usr/bin/python3 -I run_campaign.py \
  --source campaign-message.eml
```

sudo is required to read the five users' mailbox files and the server log. The runner validates the host, recipient homes, labelled text source and Postfix configuration before submission. It connects Swaks to 127.0.0.1:25 and collects the server output. [10]

### Record the result

The output gives the Message-ID, queue ID and CAMPAIGN_RESULT directory. Each run uses new identifiers. Do not reuse the reference run's values to describe a later run. Stop on LAB ERROR and examine its cause before retrying; a later collection error can occur after submission, so avoid blind retries.

Successful reference run: **20261005T122642Z-08257e25**, queue **07C5A1E01FC**, five verified local deliveries. The actual output and native files are included under evidence/simulation/. Expected outcomes are not substitutes for your own run evidence.

run_campaign.py submits the controlled message and exports evidence. Reading Maildir files through the filesystem does not demonstrate that the mailbox owner opened or read the email.

## Trace from Alice's received message

Bash on Ubuntu. Use the CAMPAIGN_RESULT directory printed for your run.

**INSPECT THE RECEIVED COPY**

```text
cd /home/labadmin/phishing-campaign-runs/YOUR_RUN_ID
grep -iE '^(From|Reply-To|To|Cc|Subject|Message-ID):' \
  evidence/campaign-received-alice.eml
grep -A 3 '^Received:' evidence/campaign-received-alice.eml
```

Extract the Message-ID from the received message. In this template it is on one line. The following variable retains the full identifier while removing a possible carriage return:

**MAP MESSAGE-ID TO QUEUE ID**

```text
message_id=$(sed -n 's/^Message-ID: //p' \
  evidence/campaign-received-alice.eml | tr -d '\r')
test -n "$message_id"
sudo grep -F "message-id=$message_id" /var/log/mail.log
```

Find the queue ID on the matching cleanup record. Check its timestamp and host. Set YOUR_QUEUE_ID to that observed value; then inspect its delivery events.

**READ THE QUEUE EVENTS**

```text
queue_id='YOUR_QUEUE_ID'
sudo grep -F " $queue_id:" /var/log/mail.log
grep -F 'status=sent (delivered to maildir)' \
  evidence/campaign-delivery.log
```

Message-ID identifies the message; the Postfix queue ID identifies this server's processing instance. Message-ID alone is not a global trust verdict or a unique campaign identifier. Correlate sender, content, timestamps and server records for a wider campaign search. [6, 7]

## Verify delivery and preserve evidence

The SMTP transcript and the delivery log answer different questions.

1. **Check server acceptance.** In campaign-smtp.txt, verify five RCPT TO commands and the final queued as response. Acceptance means the server took responsibility for the message.

2. **Check final local outcomes.** In campaign-delivery.log, verify the Message-ID-to-queue mapping, nrcpt=5 and five distinct recipients with dsn=2.0.0 and status=sent (delivered to maildir).

3. **Check the received copies.** Inspect Delivered-To and Received in each of the five campaign-received files. Their Message-ID and queue ID must match this run.

**LIST DISTINCT CONFIRMED RECIPIENTS AND VERIFY HASHES**

```text
grep -F 'status=sent (delivered to maildir)' \
  evidence/campaign-delivery.log |
  sed -n 's/.*to=<\([^>]*\)>.*/\1/p' | sort -u
cd evidence
sha256sum -c SHA256SUMS
cd ..
```

The runner preserves native SMTP output, queue log records and received mailbox bytes. It records each source path, byte size and hash in run-summary.json. It does not delete, quarantine or change the original Maildir files.

Reference comparison: To/Cc show three recipients; delivery evidence confirms five. Carol and Vittorio are envelope-only recipients in this controlled setup. No opening, click or credential capture was tested.

Record discrepancies as actual results. Investigate deferred or bounced outcomes instead of counting RCPT acceptance as delivery. Hashes verify the collected files remain unchanged; they do not prove that the mail is malicious.

## Export and prepare the repository

PowerShell on Windows. Keep native evidence and document results from the observed run.

Choose a local destination, then export your own run. Replace VM_IP and YOUR_RUN_ID with the current values. The example path is a portable lab location, not a requirement.

**POWERSHELL: EXPORT THE RUN**

```text
New-Item -ItemType Directory -Force 'C:\SOC-Labs'
$remoteRun = "labadmin@VM_IP:/home/labadmin/" +
  "phishing-campaign-runs/YOUR_RUN_ID"
scp -r $remoteRun C:\SOC-Labs\
```

Compare each exported evidence file's SHA-256 with the VM manifest. PowerShell Get-FileHash -Algorithm SHA256 computes a local hash. Keep the source file bytes intact when uploading or committing the evidence.

**REPOSITORY .gitattributes**

```text
.gitattributes text eol=lf
*.eml -text
*.log -text
*.pdf -text
*.png -text
campaign-smtp.txt -text
SHA256SUMS -text
run-summary.json -text
postfix-configuration.txt -text
*.py text eol=lf
*.md text eol=lf
```

The public package contains the report, reproduction guide, labelled template, runner, native simulation evidence and captured domain reports. Keep private access keys, local absolute paths and document-building utilities outside the repository.

## Troubleshooting and references

Resolve the specific failure before starting another run.

| Symptom | Check / next action |
| --- | --- |
| SSH connection fails | Confirm the VM is on and read its current IP with hostname -I. |
| Unexpected hostname or configuration | Use soc-mail-lab and compare postconf output with section 2. |
| Missing recipient account | Create the missing local account; confirm its home is /home/USERNAME. |
| Connection refused on port 25 | Check systemctl status postfix and loopback SMTP listening. |
| mail.log unavailable | Check rsyslog and Postfix logging; do not invent delivery records. |
| LAB ERROR after SMTP acceptance | Inspect the saved run and existing mailbox copies before retrying. |
| Checksum mismatch | Compare with the source files; preserve the mismatch and its cause. |

A real click investigation would require separate telemetry, such as secure email gateway or endpoint/proxy logs, correlated with message recipients and timestamps. This lab provides delivery evidence only.

[[1] Archived source: Phishing Pot, pinned revision](https://github.com/rf-peixoto/phishing_pot/blob/097878eab3043ced70fde2ce0fb3b660fb58717e/email/sample-10.eml)

[[2] Microsoft: unusual sign-in notifications](https://support.microsoft.com/en-us/accounts-billing/security/what-happens-if-there-s-an-unusual-sign-in-to-your-account)

[[3] Microsoft: email authentication results](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-troubleshoot)

[[4] RFC 7489: DMARC result definitions](https://www.rfc-editor.org/rfc/rfc7489.html#appendix-C)

[[5] VirusTotal: domain report fields](https://docs.virustotal.com/reference/domains-object)

[[6] RFC 5321: SMTP envelope and delivery](https://www.rfc-editor.org/rfc/rfc5321)

[[7] RFC 5322: message header fields](https://www.rfc-editor.org/rfc/rfc5322)

[[8] RFC 2606: reserved test domains](https://www.rfc-editor.org/rfc/rfc2606.html)

[[9] Ubuntu Server: Postfix and Maildir](https://documentation.ubuntu.com/server/how-to/mail-services/install-postfix/)

[[10] Swaks command reference](https://www.jetmore.org/john/code/swaks/latest/doc/ref.txt)

[[11] Hyper-V: Generation 2 security features](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/generation-2-virtual-machine-security-features)

[[12] Git attributes: preserving file bytes](https://git-scm.com/docs/gitattributes)
