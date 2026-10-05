# Reproduce the Recipient Tracing Lab

Build a local mail server, deliver one harmless message to five test accounts, and reconstruct its recipients from a received copy and server logs.

The reference run is documented in [Recipient Tracing Lab](Recipient-Tracing.md). A new run will produce different Message-IDs, queue IDs, filenames and timestamps. Use those new values during your investigation.

## 1. Create the Ubuntu VM

Download Ubuntu Server 24.04 LTS from the [official release page](https://releases.ubuntu.com/24.04/). In Hyper-V Manager, create a VM with these lab settings:

| Setting | Value |
|---|---|
| Name | SOC-Mail-Lab |
| Generation | 2 |
| Memory | 4096 MB |
| Virtual processors | 2 |
| Virtual disk | 40 GB VHDX |
| Network | Default Switch |
| Secure Boot template | Microsoft UEFI Certificate Authority |

Attach the Ubuntu ISO and start the VM. Select the standard Ubuntu Server installation, use DHCP, leave the proxy blank, and confirm the archive mirror test. Use the VM's new 40 GB disk with a standard partition layout. Create user `labadmin` and hostname `soc-mail-lab`, skip Ubuntu Pro, and install OpenSSH Server with password authentication. Leave the featured server snaps unselected.

After installation, disconnect the ISO and reboot.

## 2. Connect from Windows

Log in to the VM and run:

```bash
hostname -I
```

Open PowerShell on the Windows host. Replace `YOUR_VM_IP` with the address shown by the VM:

```powershell
ssh labadmin@YOUR_VM_IP
```

Verify the host is your lab VM when establishing the first connection. Sign in with the password created during installation.

Run the remaining Linux commands in this SSH session. The prompt should identify `labadmin@soc-mail-lab`.

## 3. Install the mail tools

```bash
sudo apt update
sudo apt install postfix rsyslog swaks
```

In the Postfix installer, select **Local only** and set **System mail name** to `lab.test`.

Enable Maildir storage and verify the local configuration:

```bash
sudo postconf -e 'home_mailbox = Maildir/'
sudo systemctl restart postfix
postconf mydestination inet_interfaces default_transport home_mailbox mailbox_command
```

Confirm that `mydestination` includes `lab.test`, `inet_interfaces` is `loopback-only`, `default_transport` is `error`, `home_mailbox` is `Maildir/`, and `mailbox_command` is empty.

Check that mail logs are available:

```bash
sudo tail -n 10 /var/log/mail.log
```

## 4. Create five local recipients

On a fresh VM, create these accounts:

```bash
sudo useradd -m -s /usr/sbin/nologin alice
sudo useradd -m -s /usr/sbin/nologin bob
sudo useradd -m -s /usr/sbin/nologin carol
sudo useradd -m -s /usr/sbin/nologin edoardo
sudo useradd -m -s /usr/sbin/nologin vittorio
getent passwd alice bob carol edoardo vittorio
```

The `-m` option creates each home directory. The `nologin` shell disables interactive login while allowing the accounts to receive local mail. Maildir folders are created on first delivery.

If an account already exists, use the existing lab account rather than repeating its creation command.

## 5. Prepare a harmless message

Create a new working folder for this run. Choose a different folder name if the example already exists:

```bash
mkdir ~/recipient-tracing-run
cd ~/recipient-tracing-run
```

Generate the message without sending it:

```bash
swaks --server 127.0.0.1 --port 25 \
  --from labadmin@lab.test \
  --to alice@lab.test,bob@lab.test,carol@lab.test,edoardo@lab.test,vittorio@lab.test \
  --header 'To: alice@lab.test' \
  --header 'Cc: bob@lab.test, edoardo@lab.test' \
  --header 'Subject: [SOC-LAB] Recipient tracing test 02' \
  --body 'Controlled lab message for recipient tracing. No action is required.' \
  --dump-mail | tee message.eml
```

Verify that the generated message contains exactly one Message-ID:

```bash
grep -i '^Message-ID:' message.eml
```

Let Swaks generate this field automatically. Alice appears in `To`; Bob and Edoardo appear in `Cc`. Carol and Vittorio are included in the SMTP envelope but omitted from the visible recipient headers, reproducing blind-copy delivery.

## 6. Send the prepared file

```bash
swaks --server 127.0.0.1 --port 25 \
  --from labadmin@lab.test \
  --to alice@lab.test,bob@lab.test,carol@lab.test,edoardo@lab.test,vittorio@lab.test \
  --data @message.eml \
  2>&1 | tee smtp-session.txt
```

Record the response `250 2.0.0 Ok: queued as ...`. This is acceptance into the queue; delivery must be verified separately.

## 7. Investigate Alice's received copy

Replace `YOUR_MESSAGE_ID` with the full identifier from your new message, including its angle brackets:

```bash
sudo grep -rlF 'YOUR_MESSAGE_ID' /home/alice/Maildir/
```

Read the matching file, replacing `PATH_RETURNED_BY_SEARCH` with the returned path:

```bash
sudo cat 'PATH_RETURNED_BY_SEARCH'
```

Record `Delivered-To`, `To`, `Cc`, `Message-ID`, and the queue ID in `Received`. Count the distinct visible addresses and compare them with the server's delivery records.

## 8. Reconstruct all deliveries

Search the log for the received message's identifier:

```bash
sudo grep -F 'YOUR_MESSAGE_ID' /var/log/mail.log
```

The cleanup record associates that identifier with a queue ID. Replace `YOUR_QUEUE_ID` with this value:

```bash
sudo grep -F 'YOUR_QUEUE_ID:' /var/log/mail.log | tee delivery.log
```

Use the records to answer:

1. How many envelope recipients does `nrcpt` report?
2. Which distinct recipient addresses have `status=sent (delivered to maildir)`?
3. Which delivered addresses are absent from Alice's `To` and `Cc` headers?
4. Are there failures or deferred deliveries for this same queue?

A successful reproduction should show five distinct local deliveries, including Carol and Vittorio. Report what your own logs show if the outcomes differ.

## 9. Preserve and export the evidence

Copy the matching received file into the working folder, keeping the original mailbox file intact:

```bash
sudo install -o labadmin -g labadmin -m 600 'PATH_RETURNED_BY_SEARCH' alice-received.eml
sha256sum message.eml alice-received.eml smtp-session.txt delivery.log > evidence.sha256
```

In a new PowerShell tab on the Windows host, export the working folder. Replace `YOUR_VM_IP` with the current VM address and adjust the folder name if you used a different one:

```powershell
scp -r "labadmin@YOUR_VM_IP:/home/labadmin/recipient-tracing-run" "$env:USERPROFILE\Documents"
```

Keep the prepared message, received copy, SMTP transcript, delivery extract and checksum file together.

## 10. Write the conclusion

Report the visible recipients, confirmed delivered recipients, additional recipients identified through the logs, and the matching Message-ID and queue ID. Use server timestamps for the delivery timeline.

Distinguish delivery from opening, clicking or replying. This benign local exercise does not measure the recipient scope or impact of the historical phishing sample.

## References

- [Ubuntu Server installation](https://ubuntu.com/tutorials/install-ubuntu-server)
- [Microsoft: Hyper-V Secure Boot templates](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/generation-2-virtual-machine-security-features)
- [Ubuntu: Postfix](https://ubuntu.com/server/docs/how-to/mail-services/install-postfix/)
- [Swaks reference](https://www.jetmore.org/john/code/swaks/latest/doc/ref.txt)
