import pytest
from typing import List
from unittest.mock import patch
import keyring
import smtplib
from smtpdfix import smtpd
from argparse import Namespace

from completion_alert import (
    store_login_password,
    send_sms_message,
    get_login_password,
    validate_login,
    cli_parser,
    )

@patch('keyring.set_password')
def test_store_passwd(mock_keyring):
    """ Test the password was stored to the keyring properly """
    key_acct = "test_acct"
    login_name = "fake login"
    login_pass = "1234"

    store_login_password(key_acct, login_name, login_pass)
    mock_keyring.assert_called_once()
    assert [key_acct, login_name, login_pass] == list(mock_keyring.call_args[0])

@pytest.mark.xfail(reason="sender and receiver can't be mocked")
@patch('smtplib.SMTP', spec=smtplib.SMTP)
def test_send_sms_msg_basics(mock_smtp_context):
    """ test sending message via the SMTP server

    Check for correct interaction with SMTP server and verify message has
    correct sender, receiver and message fields.
    This test case assumes no errors are raised by the server (e.g. bad login, etc)
    This test case DOES NOT actually check the message matches a plain-text or
    MIME format. See the other test case with a 'real' SMTP server.
    """

    # Check tls session initiated by server
    # verify login
    # verify sender and receiver correct
    message = "This is a test"
    sender = "fake_sender@gmail.com"
    receiver = "fake_receiver@vtext.com"

    with patch('completion_alert.get_login_password', return_value="fake_pass") as lookup:
        send_sms_message(message)

    lookup.assert_called_once_with(sender)
    mock_smtp = mock_smtp_context.return_value.__enter__.return_value
    mock_smtp.ehlo.assert_called()
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with(sender, 'fake_pass')
    args, __ = mock_smtp.sendmail.call_args
    send, rcvr, msg = args
    assert send == sender
    assert rcvr == receiver
    assert message in msg


def test_get_password(capsys):
    """ test password retrieval from keyring """
    value = 'fk_pass'
    with patch('keyring.get_password', return_value=value) as mocker:
        result = get_login_password('key_srv', 'fake_account')

    assert result == value
    mocker.assert_called_once()
    captured = capsys.readouterr()
    assert len(captured.out.split('\n')) == 2


def test_get_password_failure(capsys):
    """ test behavior with failed password retrieval from keyring """
    value = 'fk_pass'
    key_svc = "fake_service"
    with patch('keyring.get_password', return_value=None) as mocker:
        with patch('builtins.input', return_value=value, side_effect=print('mock prompt')):
            result = get_login_password('key_srv', 'fake_account')

    assert result == value
    mocker.assert_called_once()
    captured = capsys.readouterr()
    assert len(captured.out.split('\n')) == 3

@pytest.mark.xfail
@patch('keyring.set_password')
def test_password_store_fail(mock_keyring):
    """ test failed password store """

    key_acct = "test_acct"
    login_name = "fake login"
    login_pass = "1234"

    mock_keyring.side_effect = keyring.errors.PasswordSetError

    store_login_password(key_acct, login_name, login_pass)
    mock_keyring.assert_called_once()
    assert [key_acct, login_name, login_pass] == list(mock_keyring.call_args[0])

@pytest.fixture
def mock_use_tls(monkeypatch):
    monkeypatch.setenv('SMTPD_USE_TLS', 'True')

@pytest.mark.skip(reason="firewall causes test to hang")
def test_validate_login(mock_use_tls, smtpd):
    """ test server login validation & storage w/ & w/o password """
    sender = "from@example.org"
    receiver = "to@example.org"

    with smtplib.SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        validate_login(client, sender)


@pytest.mark.skip
def test_validate_login_fail():
    """ Test for failed login & reprompt of password """



  # Test successful login & store password

# test (also) the whole thing (sending connection & sending) with an actual server
# test similar to ^^, check the plain/MIME-text is formatted properly

# test argument parsing
def test_cli_parser_help(capsys):
    test_input = ['-h']
    test_parser = cli_parser()

    with pytest.raises(SystemExit) as wrapped_e:
        result = test_parser.parse_args(test_input)

    assert wrapped_e.value.code == 0
    capture = capsys.readouterr()
    out, err = capture
    assert "show this help message and exit" in out
    assert len(err) == 0
    assert 0


class ParserArgs(Namespace):
    """ Stand-in for namespace object """
    sender: str = None
    email: bool = False
    sms: bool = False
    carrier: str = None
    receiver: str = None
    cmd: List[str] = []

    def __init__(self, sender: str = None, email: bool = False, sms: bool = False, #pylint: disable=too-many-arguments
                 carrier: str = None, receiver: str = None, cmd: List[str] = []):
        super().__init__()
        self.sender = sender
        self.email = email
        self.sms = sms
        self.receiver = receiver
        self.carrier = carrier
        self.cmd = cmd


@pytest.mark.parametrize("input_args, expected",
    [
        # acceptable email
        (['sender@fake_mail.com', '--email', 'receiver@fake_mail.com'],
            ParserArgs(sender='sender@fake_mail.com', email=True, receiver="receiver@fake_mail.com")
        ),
        # acceptable sms
        (['sender@mail.com', '--sms', '--carrier', 'verizon', '1234567890'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='verizon')
        ),
        # also acceptable sms: different order
        (['sender@mail.com', '--sms', '1234567890', '--carrier', 'verizon'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='verizon')
        ),
        # also acceptable sms : uppercase
        (['sender@mail.com', '--sms', '1234567890', '--carrier', 'VeriZon'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='VeriZon')
        ),
        # sms, no carrier
        (['sender@mail.com', '--sms', '1234567890'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890')
        ),
        # sms, unsupported carrier
        (['sender@mail.com', '--sms', '1234567890', '--carrier', 'oobleck'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='oobleck')
        ),
        # email to a number
        (['sender@mail.com', '--email', '1234567890', '--carrier', 'verizon'],
            ParserArgs(sender='sender@mail.com', email=True, receiver='1234567890', carrier='verizon')
        ),
        # no receiver info
        pytest.param(['sender@mail.com', '--sms', '--carrier', 'verizon'],
            ParserArgs(sender='sender@mail.com', sms=True, carrier='verizon'),
            marks=pytest.mark.raises(exception=SystemExit)
        ),
        # phone has special chars "()-"
        (['sender@mail.com', '--sms', '(123)456-7890', '--carrier', 'verizon'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='verizon')
        ),
        # no sender info
        (['--sms', '1234567890', '--carrier', 'verizon'],
            ParserArgs(sms=True, receiver='1234567890', carrier='verizon')
        ),
        # extra commands with --
        (['sender@mail.com', '--sms', '1234567890', '--carrier', 'verizon', '--', 'echo', '"with -- command"'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='verizon', cmd=['echo', '"with -- command"'])
        ),
        # extra commands without --
        (['sender@mail.com', '--sms', '1234567890', '--carrier', 'verizon', 'echo', '"no -- command"'],
            ParserArgs(sender='sender@mail.com', sms=True, receiver='1234567890', carrier='verizon', cmd=['echo', '"no -- command"'])
        ),
        # both email and sms
        pytest.param(['sender@mail.com', '--sms', '--email', '1234567890', '--carrier', 'verizon'],
            ParserArgs(),
            marks=pytest.mark.raises(exception=SystemExit)
        ),
    ],
    )
def test_cli_parser(input_args, expected):
    test_parser = cli_parser()
    print(f"input args: {input_args}")
    print(f"expected: {vars(expected)}")

    result = test_parser.parse_intermixed_args(input_args)
    assert vars(expected) == vars(result)
