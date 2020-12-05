"""
Automated alert wrapper

Provides a wrapper that sends an alert if the wrapped process fails or completes.

Alert will be sent to the receiving email when either:
    a) all tests complete successfully
    b) A test encounters an exception
    c) The call to the test times out.
"""

import sys, datetime, subprocess, ssl, smtplib, os
from time import sleep
import keyring
import argparse


# set up variables
fmt = "%Y_%m_%d__%H_%M" # formatted as "YYYY_MM_DD__HH_MM"

MAX_RUNS = 3
MAX_FAILS = 1 # number of allowed failures in a row before notification
sleep_time = 30 # base delay time (seconds) before attempting to rerun test
TEST_TIMEOUT_MINUTES = 20 * 60

SMS_carriers = {
    "ATT": "txt.att.net",
    "Boost": "sms.myboostmobile.com",
    "Cricket": "mms.cricketwireless.net",
    "ProjectFi": "msg.fi.google.com",
    "RepublicWireless": "text.republicwireless.com",
    "Sprint": "messaging.sprintpcs.com",
    "StraightTalk": "vtext.com",
    "TMobile": "tmomail.net",
    "Ting": "message.ting.com",
    "USCellular": "email.uscc.net",
    "Verizon": "vtext.com",
    "VirginMobile": "vmobl.com",
}

email_server = {
    "yahoo": "smtp.mail.yahoo.com",
    "google": "smtp.google.com",
    "office365": "smtp.office365.com",
    "msn": "smtp-mail.outlook.com",
    "aol": "smtp.aol.com",
    "comcast": "smtp.comcast.net",
    "xfinity": "smtp.comcast.net",

}

class MailParameters(): #pylint: disable=too-few-public-methods
    """ storage object for messaging variables """
    keyring_svc: str
    mail_server: str
    port: int
    from_: str
    to_: str

    def __init__(self, program, host, port, sender, receiver):
        self.keyring_svc = program
        self.mail_server = host
        self.port = port
        self.from_ = sender
        self.to_ = receiver

def check_carrier(carrier: str) -> str:
    """ Checks whether the given service provider is supported """
    sms_carriers_lowercase = str(SMS_carriers.keys()).lower()
    if carrier.lower() not in sms_carriers_lowercase:
        mesg = (f"The service provider '{carrier}' is not supported. "
                f"Supported carriers are {', '.join(SMS_carriers)}.")
        raise argparse.ArgumentTypeError(mesg)
    return carrier

def lookup_smtp_server(email: str) -> str:
    """ Look up smtp server based on email address

    If the provider is not in the list (i.e. not common provider), then make a
    guess that the server follows a standard naming convention.
    """
    provider = email.split('@')[1].lower()
    try:
        return email_server[provider.split('.')[0]]
    except KeyError:
        return '.'.join(["smtp", provider]) # take a guess


def get_login_password(service, login_acct):
    # check keyring service for password, otherwise ask user
    passwd = keyring.get_password(service, login_acct)
    # if none, prompt user
    print(f"got {login_acct} password from keyring")
    if not passwd:
        passwd = input(f"provide your password for {login_acct}: ")
    return passwd

def store_login_password(service, login_acct, password):
    # store validated password in service
    print(f"Storing {login_acct} password in {service}")
    keyring.set_password(service, login_acct, password)

def validate_login(server:MailParameters, login, password=None):
    """ attempts login with password, if given. otherwise prompts for password """
    if not password:
        password = get_login_password(server.keyring_svc, login)

    with smtplib.SMTP(server.mail_server, server.port) as serv:
        # serv.set_debuglevel(1)
        ssl_context = ssl.create_default_context()
        serv.ehlo()
        serv.starttls(context=ssl_context)
        serv.ehlo()
        resp = serv.login(login, password) # code 235 = accepted, 535 = rejected

    print(resp)
    print("saving password...", end="")
    store_login_password(server.keyring_svc, login, password)

def send_sms_message(acct: MailParameters, mesg: str=None):
    header = f"To: {acct.to_}\nFrom: {acct.from_}\n"
    # subj = "Subject: test rack failure\n"
    subj = 'Subject: \n'
    mesgbody = mesg or ""

    password = get_login_password(acct.keyring_svc, acct.to_)
    with smtplib.SMTP(acct.mail_server, acct.port) as server:
        # server.set_debuglevel(True)
        ssl_context = ssl.create_default_context()
        server.ehlo()
        server.starttls(context=ssl_context)
        server.ehlo()
        server.login(acct.to_, password)
        resp = server.sendmail(acct.to_, acct.from_, header + subj + mesgbody)
        print(resp)

def cli_parser():
    parser = argparse.ArgumentParser(
        description="Program completion utility",
        usage="%(prog)s [-h] sender (--email | --sms) [--carrier CARRIER] receiver [--] cmd ... ")
    tx_group = parser.add_argument_group(title="Sender arguments",
            description="Message sender details")
    tx_group.add_argument('sender', help="Sending email account")
    rx_group = parser.add_argument_group(
            title="Recipient arguments",
            description="Message recipient details")
    mutex_group = rx_group.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('--email', help="Send message as an email", action='store_true')
    mutex_group.add_argument('--sms', help="Send message as SMS (text) message",action='store_true')
    rx_group.add_argument('receiver', help="Email or phone number of recipient")
    rx_group.add_argument( '--carrier', type=check_carrier,
            help=("Mobile carrier for receiving number. Required with --sms option. "
                f"Supported carriers are {', '.join(SMS_carriers)}")
            )
    parser.add_argument('cmd', help="Command to run", nargs='*')
    return parser


def run(config: MailParameters):
    # Check email info upfront and save it to use later
    validate_login(config.from_, config.from_passwd)

    num_fails = 0
    for run in range(1, MAX_RUNS + 1):
        now = datetime.datetime.now()
        timestamp = now.strftime(fmt)

        print(f"executing run {run} of {MAX_RUNS}...")
        exec_cmd = [sys.executable, '-c', 'print("This is just a test")']
        try:
            subprocess.check_call(exec_cmd, timeout=TEST_TIMEOUT_MINUTES, text=True) # run and print output to console
        except subprocess.SubprocessError as err:
            num_fails += 1
            if isinstance(err, subprocess.TimeoutExpired):
                mes = datetime.datetime.now().strftime("%a %b %d %H%Mh")
                mes += " - TimeoutError - Program timed out after %s seconds" % err.timeout #pylint: disable=no-member
                print(mes)
                send_sms_message(config, mes)
                break
            if num_fails == MAX_FAILS:
                print(f"reached {MAX_FAILS} fails")
                # send an alert
                failure_time = datetime.datetime.now().strftime("%a %b %d %H%Mh")
                message = "Test rack error at %s." % failure_time
                send_sms_message(config, message)
                print(message)
                break
            failure_time = datetime.datetime.now().strftime("%a %b %d %H%Mh")
            message = "Test rack error at %s. Retrying." % failure_time
            send_sms_message(config, message)
            print(message)
            sleep(sleep_time * num_fails) # let retry period increase each time
        else:
            num_fails = 0 # reset counter
        finally:
            print(120 * '-')
    else:
        print("All tests completed")
        send_sms_message(config,
            "All tests completed @ %s" % datetime.datetime.now().strftime("%a %b %d %H%Mh")
            )


if __name__ == '__main__':
    cli_parser = cli_parser()
    args = cli_parser.parse_intermixed_args()

    if args.sms:
        if args.carrier is None:
            cli_parser.error("Text message requires --carrier.")
        args.receiver = '@'.join([args.receiver, SMS_carriers[args.carrier]])

    params = MailParameters(
        program="rack_alert",
        host=lookup_smtp_server(args.sender),
        port=587,
        sender=args.sender,
        receiver=args.receiver
    )
    run(params)
