import pytest
from unittest.mock import patch
import keyring

from completion_alert import store_login_password

@patch('keyring.set_password')
def test_store_passwd(mock_keyring):
    """ Test the password was stored to the keyring properly """
    key_acct = "test_acct"
    login_name = "fake login"
    login_pass = "1234"

    store_login_password(key_acct, login_name, login_pass)
    mock_keyring.assert_called_once()
    assert [key_acct, login_name, login_pass] == list(mock_keyring.call_args[0])

# test sending message function
# test password retrieval and retrieval failure
# test failed password store
# test server login validation & storage
  # Test for failed login & reprompt of password
  # Test successful login & store password

# test argument parsing
