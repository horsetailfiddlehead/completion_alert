import pytest
from unittest.mock import patch
import keyring
import smtplib
from smtpdfix import smtpd

from completion_alert import (
    store_login_password,
    send_sms_message,
    get_login_password,
    validate_login,
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
        result = get_login_password('fake_account')

    assert result == value
    mocker.assert_called_once()
    captured = capsys.readouterr()
    assert len(captured.out.split('\n')) == 2


def test_get_password_failure(capsys):
    """ test behavior with failed password retrieval from keyring """
    value = 'fk_pass'
    with patch('keyring.get_password', return_value=None) as mocker:
        with patch('builtins.input', return_value=value, side_effect=print('mock prompt')):
            result = get_login_password('fake_account')

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
