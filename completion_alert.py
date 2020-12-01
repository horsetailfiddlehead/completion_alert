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

# messaging variables
keyring_svc = "rack_alert"
smtp = "smtp.gmail.com"
port = 587
sending_addr = 'patrickm82694@gmail.com'
receiving_email = "2063009501@vtext.com"

# set up variables
fmt = "%Y_%m_%d__%H_%M" # formatted as "YYYY_MM_DD__HH_MM"

MAX_RUNS = 3
MAX_FAILS = 1 # number of allowed failures in a row before notification
sleep_time = 30 # base delay time (seconds) before attempting to rerun test
TEST_TIMEOUT_MINUTES = 20 * 60

def get_login_password(login_acct):
    # check keyring for password, otherwise ask user
    passwd = keyring.get_password(keyring_svc, login_acct)
    # if none, prompt user
    print(f"got {login_acct} password from keyring")
    if not passwd:
        passwd = input(f"provide your password for {login_acct}: ")
    return passwd

def store_login_password(service, login_acct, password):
    # store validated password
    print(f"Storing {login_acct} password in {service}")
    keyring.set_password(service, login_acct, password)

def validate_login(server, login, password=None):
    """ attempts login with password, if given. otherwise prompts for password """
    if not password:
        password = get_login_password(login)
    resp = server.login(login, password) # code 235 = accepted, 535 = rejected
    print(resp)
    print("saving password...", end="")
    store_login_password(keyring_svc, login, password)

def send_sms_message(mesg=None):
    header = f"To: {receiving_email}\nFrom: {sending_addr}\n"
    # subj = "Subject: test rack failure\n"
    subj = 'Subject: \n'
    mesgbody = mesg or ""

    password = get_login_password(sending_addr)
    with smtplib.SMTP(smtp, port) as server:
        # server.set_debuglevel(True)
        ssl_context = ssl.create_default_context()
        server.ehlo()
        server.starttls(context=ssl_context)
        server.ehlo()
        server.login(sending_addr, password)
        resp = server.sendmail(sending_addr, receiving_email, header + subj + mesgbody)
        print(resp)


def run():
    # Check email info upfront and save it to use later
    # with smtplib.SMTP(smtp, port) as serv:
    #     # serv.set_debuglevel(1)
    #     ssl_context = ssl.create_default_context()
    #     serv.ehlo()
    #     serv.starttls(context=ssl_context)
    #     serv.ehlo()
    #     validate_login(serv, sending_addr)

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
                send_sms_message(mes)
                break
            if num_fails == MAX_FAILS:
                print(f"reached {MAX_FAILS} fails")
                # send an alert
                failure_time = datetime.datetime.now().strftime("%a %b %d %H%Mh")
                message = "Test rack error at %s." % failure_time
                send_sms_message(message)
                print(message)
                break
            failure_time = datetime.datetime.now().strftime("%a %b %d %H%Mh")
            message = "Test rack error at %s. Retrying." % failure_time
            send_sms_message(message)
            print(message)
            sleep(sleep_time * num_fails) # let retry period increase each time
        else:
            num_fails = 0 # reset counter
        finally:
            print(120 * '-')
    else:
        print("All tests completed")
        send_sms_message("All tests completed @ %s" % datetime.datetime.now().strftime("%a %b %d %H%Mh"))


if __name__ == '__main__':
    run()
