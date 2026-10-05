"""Run one local campaign simulation and preserve native delivery evidence."""
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import format_datetime, make_msgid
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import pwd
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid

RECIPIENTS = ['alice', 'bob', 'carol', 'edoardo', 'vittorio']


def command(args, timeout=25):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=timeout, check=True).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo to read mailbox files and mail.log.')
    if socket.gethostname().split('.')[0] != 'soc-mail-lab':
        raise RuntimeError('This runner is restricted to the soc-mail-lab VM.')
    owner = pwd.getpwnam('labadmin')
    if Path(owner.pw_dir).resolve() != Path('/home/labadmin'):
        raise RuntimeError('Unexpected labadmin home directory.')
    source = args.source.resolve()
    raw_template = source.read_bytes()
    template = BytesParser(policy=policy.default).parsebytes(raw_template)
    if template.defects or template['X-Lab-Simulation'] != 'true':
        raise RuntimeError('Expected the labelled laboratory message template.')
    if template.get_all('Message-ID') or template.get_all('Date'):
        raise RuntimeError('Template must not contain pre-existing Date or Message-ID fields.')
    if template.get_all('Authentication-Results'):
        raise RuntimeError('Template must not include synthetic authentication verdicts.')
    if template['From'].addresses[0].domain != 'account-alerts.test':
        raise RuntimeError('Unexpected simulation sender.')
    if template.get_content_type() != 'text/plain':
        raise RuntimeError('The simulation template must be plain text.')
    if re.findall(r'https?://[^\s]+', template.get_content()) != ['http://account-review.test/verify']:
        raise RuntimeError('Unexpected destination in the simulation message.')
    for name in RECIPIENTS:
        account = pwd.getpwnam(name)
        if Path(account.pw_dir).resolve() != Path('/home') / name:
            raise RuntimeError('Unexpected recipient home directory: ' + name)
    required = {'inet_interfaces': 'loopback-only', 'default_transport': 'error',
                'home_mailbox': 'Maildir/', 'mailbox_command': ''}
    config = {}
    for name, value in required.items():
        actual = command(['postconf', '-h', name]).decode().strip()
        config[name] = actual
        if actual != value:
            raise RuntimeError('Postfix setting mismatch: ' + name + ' = ' + actual)
    destination = command(['postconf', '-h', 'mydestination']).decode().strip()
    if 'lab.test' not in re.split(r'[\s,]+', destination):
        raise RuntimeError('lab.test is not configured for local delivery.')
    config['mydestination'] = destination
    log_path = Path('/var/log/mail.log')
    if not log_path.is_file():
        raise RuntimeError('Postfix mail.log is unavailable.')
    for executable in ['swaks', 'postconf']:
        if not shutil.which(executable):
            raise RuntimeError('Missing tool: ' + executable)
    now = datetime.now(timezone.utc)
    run_id = now.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    base = Path('/home/labadmin/phishing-campaign-runs')
    base.mkdir(mode=0o750, exist_ok=True)
    if not base.resolve().is_relative_to(Path('/home/labadmin')):
        raise RuntimeError('Run directory is outside the expected lab home.')
    run = base / run_id
    run.mkdir(mode=0o750, exist_ok=False)
    evidence = run / 'evidence'
    evidence.mkdir(mode=0o750)
    os.chown(base, owner.pw_uid, owner.pw_gid)
    os.chown(run, owner.pw_uid, owner.pw_gid)
    os.chown(evidence, owner.pw_uid, owner.pw_gid)
    message_id = make_msgid(idstring='phishing-lab-' + run_id, domain='lab.test')
    template['Date'] = format_datetime(now)
    template['Message-ID'] = message_id
    prepared = evidence / 'campaign-prepared.eml'
    prepared.write_bytes(template.as_bytes(policy=policy.SMTP))
    print('Submitting one labelled simulation to five local test recipients.', flush=True)
    smtp_args = ['swaks', '--server', '127.0.0.1', '--port', '25',
                 '--from', 'security@account-alerts.test',
                 '--to', ','.join(name + '@lab.test' for name in RECIPIENTS),
                 '--data', '@' + str(prepared)]
    smtp = command(smtp_args)
    (evidence / 'campaign-smtp.txt').write_bytes(smtp)
    match = re.search(rb'queued as ([A-Z0-9]+)', smtp)
    if not match:
        raise RuntimeError('The SMTP transcript did not confirm queue acceptance.')
    queue_id = match.group(1).decode()
    marker = (' ' + queue_id + ':').encode()
    deadline = time.monotonic() + 12
    queue_lines = []
    while time.monotonic() < deadline:
        queue_lines = [line for line in log_path.read_bytes().splitlines(keepends=True) if marker in line]
        joined = b''.join(queue_lines)
        successful = re.findall(rb'to=<([^>]+)>.*status=sent \(delivered to maildir\)', joined)
        if len(set(successful)) == len(RECIPIENTS) and re.search(rb'postfix/qmgr.*: removed', joined):
            break
        time.sleep(0.2)
    native_log = b''.join(queue_lines)
    (evidence / 'campaign-delivery.log').write_bytes(native_log)
    successful_addresses = sorted(set(value.decode() for value in successful))
    expected_addresses = sorted(name + '@lab.test' for name in RECIPIENTS)
    if successful_addresses != expected_addresses:
        raise RuntimeError('Expected five confirmed local deliveries; inspect the saved evidence.')
    if ('message-id=' + message_id).encode() not in native_log:
        raise RuntimeError('Missing Message-ID to queue correlation.')
    if b'nrcpt=5' not in native_log:
        raise RuntimeError('Unexpected queue recipient count.')
    mailbox_records = []
    for name in RECIPIENTS:
        matches = []
        for folder_name in ['new', 'cur']:
            folder = Path('/home') / name / 'Maildir' / folder_name
            if not folder.exists():
                continue
            for path in folder.iterdir():
                if path.is_file():
                    data = path.read_bytes()
                    msg = BytesParser(policy=policy.default).parsebytes(data)
                    if msg.get('Message-ID') == message_id:
                        matches.append((path, data, msg))
        if len(matches) != 1:
            raise RuntimeError('Expected one matching mailbox copy for ' + name)
        original, data, received = matches[0]
        if received.get('Delivered-To') != name + '@lab.test':
            raise RuntimeError('Unexpected Delivered-To value for ' + name)
        if not any(queue_id in header for header in received.get_all('Received', [])):
            raise RuntimeError('Queue ID missing from received copy for ' + name)
        exported = 'campaign-received-' + name + '.eml'
        (evidence / exported).write_bytes(data)
        mailbox_records.append({'recipient': name + '@lab.test', 'source': str(original),
                                'export': 'evidence/' + exported, 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest(),
                                'authentication_results': received.get_all('Authentication-Results', [])})
    delivery_records = []
    for line in native_log.decode().splitlines():
        found = re.search(r'^(\S+).*to=<([^>]+)>.*dsn=([^,]+), status=sent \(delivered to maildir\)', line)
        if found:
            delivery_records.append({'timestamp': found.group(1), 'recipient': found.group(2),
                                     'dsn': found.group(3), 'status': 'sent (delivered to maildir)'})
    run_data = {
        'scenario': 'Controlled Microsoft impersonation simulation',
        'run_id': run_id, 'started_utc': now.isoformat(), 'message_id': message_id,
        'queue_id': queue_id, 'hostname': socket.gethostname(),
        'os_release': Path('/etc/os-release').read_text(),
        'postfix_version': command(['postconf', '-h', 'mail_version']).decode().strip(),
        'swaks_version_output': command(['swaks', '--version']).decode().strip(),
        'configuration': config, 'sender': str(template['From']),
        'reply_to': str(template['Reply-To']), 'subject': str(template['Subject']),
        'visible_to': str(template['To']), 'visible_cc': str(template['Cc']),
        'successful_recipients': successful_addresses, 'delivery_records': delivery_records,
        'mailbox_copies': mailbox_records, 'queue_log_record_count': len(queue_lines),
        'template_sha256': hashlib.sha256(raw_template).hexdigest(),
        'interaction_measurement': 'Opening, clicking, replies and credential entry were not measured.',
        'authentication_scope': 'No authentication verdicts were injected; local messages do not reproduce archived gateway evaluations.',
    }
    (run / 'run-summary.json').write_text(json.dumps(run_data, indent=2) + '\n')
    (run / 'postfix-configuration.txt').write_text(''.join(name + ' = ' + value + '\n' for name, value in config.items()))
    checksums = []
    for file in sorted(evidence.iterdir()):
        checksums.append(hashlib.sha256(file.read_bytes()).hexdigest() + '  ' + file.name)
    (evidence / 'SHA256SUMS').write_text('\n'.join(checksums) + '\n')
    for directory in [run, evidence]:
        for file in directory.iterdir():
            if file.is_file():
                os.chown(file, owner.pw_uid, owner.pw_gid)
                os.chmod(file, 0o640)
    print('Message-ID: ' + message_id, flush=True)
    print('Queue ID: ' + queue_id, flush=True)
    print('Verified local deliveries: ' + ', '.join(successful_addresses), flush=True)
    print('Evidence directory: ' + str(run), flush=True)
    print('CAMPAIGN_RESULT=' + str(run), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('LAB ERROR: ' + str(error), file=sys.stderr, flush=True)
        sys.exit(1)
