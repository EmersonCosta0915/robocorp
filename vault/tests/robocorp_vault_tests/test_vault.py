import base64
import binascii
import copy
import json
import os

import mock
import pytest
import yaml
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_der_public_key

from robocorp.vault._errors import RobocorpVaultError
from robocorp.vault._secrets import SecretContainer
from robocorp.vault._vault import BaseSecretManager, FileSecrets, RobocorpVault, Vault


class InvalidBaseClass(object):
    def get_secret(self, secret_name):
        assert False, "Should not be called"


class MockAdapter(BaseSecretManager):
    args = None
    name = None
    value = None

    def __init__(self, *args, **kwargs):
        MockAdapter.args = (args, kwargs)

    def get_secret(self, secret_name):
        MockAdapter.name = secret_name
        return MockAdapter.value

    def set_secret(self, secret):
        MockAdapter.name = secret.name
        MockAdapter.value = dict(secret)


@pytest.fixture
def mock_env_default(monkeypatch):
    monkeypatch.delenv("RC_VAULT_SECRET_MANAGER", raising=False)


@pytest.fixture
def mock_env_vault(monkeypatch):
    monkeypatch.setenv("RC_API_SECRET_HOST", "mock-url")
    monkeypatch.setenv("RC_API_SECRET_TOKEN", "mock-token")
    monkeypatch.setenv("RC_WORKSPACE_ID", "mock-workspace")


@pytest.fixture(params=["secrets.json", "secrets.yaml"])
def secrets_file(request):
    return request.param


def test_secrets_vault_as_default(mock_env_default, mock_env_vault):
    library = Vault()
    assert isinstance(library.adapter, RobocorpVault)


def test_secrets_vault_missing_token(mock_env_default, mock_env_vault, monkeypatch):
    monkeypatch.delenv("RC_API_SECRET_TOKEN", raising=False)
    library = Vault()
    with pytest.raises(KeyError):
        _ = library.adapter


def test_secrets_custom_adapter_arguments(mock_env_default):
    library = Vault("pos-value", key="key-value", default_adapter=MockAdapter)
    library.get_secret("not-relevant")  # Adapter created on first request
    assert MockAdapter.args == (("pos-value",), {"key": "key-value"})


def test_secrets_custom_adapter_get_secret(mock_env_default):
    MockAdapter.value = "mock-secret"
    library = Vault(default_adapter=MockAdapter)
    assert library.get_secret("mock-name") == "mock-secret"
    assert MockAdapter.name == "mock-name"


def test_secrets_adapter_missing_import(monkeypatch):
    monkeypatch.setenv("RC_VAULT_SECRET_MANAGER", "RPA.AdapterNotExist")
    with pytest.raises(ValueError):
        Vault()


def test_secrets_adapter_invalid_baseclass(mock_env_default):
    with pytest.raises(ValueError):
        Vault(default_adapter=InvalidBaseClass)


def test_secret_properties():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={},
    )

    assert secret.name == "name-value"
    assert secret.description == "description-value"


def test_secret_get():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={"key_one": "value_one", "key_two": "value_two"},
    )

    assert secret["key_one"] == "value_one"
    assert secret["key_two"] == "value_two"
    with pytest.raises(KeyError):
        _ = secret["key_invalid"]


def test_secret_set():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={"key_one": "value_one", "key_two": "value_two"},
    )

    secret["key_one"] = "one"
    secret["key_two"] = "two"

    assert secret["key_one"] == "one"
    assert secret["key_two"] == "two"
    with pytest.raises(KeyError):
        _ = secret["key_invalid"]


def test_secret_update():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={"key_one": "value_one", "key_two": "value_two"},
    )

    secret.update({"key_three": "value_three"})
    expected = {
        "key_one": "value_one",
        "key_two": "value_two",
        "key_three": "value_three",
    }

    assert secret == expected


def test_secret_iterate():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={"key_one": "value_one", "key_two": "value_two"},
    )

    assert list(secret) == ["key_one", "key_two"]


def test_secret_contains():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={"key_one": "value_one", "key_two": "value_two"},
    )

    assert "key_two" in secret


def test_secret_print():
    secret = SecretContainer(
        name="name-value",
        description="description-value",
        values={"key_one": "value_one", "key_two": "value_two"},
    )

    repr_string = repr(secret)
    assert "value_one" not in repr_string
    assert "value_two" not in repr_string

    str_string = str(secret)
    assert "value_one" not in str_string
    assert "value_two" not in str_string


def test_adapter_filesecrets_from_arg(monkeypatch, secrets_file, datadir):
    monkeypatch.delenv("RC_VAULT_SECRETS_FILE", raising=False)

    adapter = FileSecrets(datadir / secrets_file)
    secret = adapter.get_secret("windows")
    assert isinstance(secret, SecretContainer)
    assert "password" in secret
    assert secret["password"] == "secret"


def test_adapter_filesecrets_from_env(monkeypatch, secrets_file, datadir):
    monkeypatch.setenv("RC_VAULT_SECRETS_FILE", str(datadir / secrets_file))

    adapter = FileSecrets()
    secret = adapter.get_secret("windows")
    assert isinstance(secret, SecretContainer)
    assert "password" in secret
    assert secret["password"] == "secret"


def test_adapter_filesecrets_from_env_backward_compatibility(
    monkeypatch, secrets_file, datadir
):
    monkeypatch.setenv("RPA_SECRET_MANAGER", "RPA.Robocorp.Vault.FileSecrets")
    monkeypatch.setenv("RPA_SECRET_FILE", str(datadir / secrets_file))

    vault = Vault()
    secret = vault.get_secret("windows")
    assert isinstance(secret, SecretContainer)
    assert "password" in secret
    assert secret["password"] == "secret"


def test_adapter_filesecrets_invalid_file(monkeypatch, datadir):
    monkeypatch.setenv("RC_VAULT_SECRETS_FILE", str(datadir / "not-a-file.json"))

    # Should not raise
    adapter = FileSecrets()
    assert adapter._load() == {}


def test_adapter_filesecrets_invalid_file_extension(monkeypatch, datadir):
    # Note the invalid ".yamla" extension not recognized by the serializers.
    monkeypatch.setenv("RC_VAULT_SECRETS_FILE", str(datadir / "secrets.yamla"))

    # Should raise immediately, because this is invalid straight from the
    # configuration. Only certain extensions (formats) are accepted.
    with pytest.raises(ValueError):
        FileSecrets()


def test_adapter_filesecrets_unknown_secret(monkeypatch, secrets_file, datadir):
    monkeypatch.setenv("RC_VAULT_SECRETS_FILE", str(datadir / secrets_file))

    adapter = FileSecrets()
    with pytest.raises(KeyError):
        adapter.get_secret("not-exist")


def test_adapter_filesecrets_saving(monkeypatch, tmp_path, secrets_file, datadir):
    tmp_file = tmp_path / secrets_file
    tmp_file.write_text((datadir / secrets_file).read_text())
    monkeypatch.setenv("RC_VAULT_SECRETS_FILE", str(tmp_file))

    adapter = FileSecrets()
    secret = adapter.get_secret("credentials")
    secret["sap"]["password"] = "my-different-secret"
    adapter.set_secret(secret)

    assert tmp_file.suffix in (".json", ".yaml")
    if tmp_file.suffix == ".json":
        loader = json.load
    else:
        loader = yaml.full_load
    secret_dict = loader(tmp_file.open())
    assert secret_dict["credentials"]["sap"]["password"] == "my-different-secret"


@mock.patch("robocorp.vault._vault.requests")
def test_adapter_vault_request(mock_requests, mock_env_default, mock_env_vault):
    mock_requests.get.return_value.json.return_value = {
        "name": "mock-name",
        "description": "mock-desc",
        "value": {"mock-key": "mock-value"},
        "encryption": {},
    }

    def mock_decrypt(payload):
        # Decrypt tested separately
        payload = copy.deepcopy(payload)
        payload["values"] = payload.pop("value")
        return payload

    adapter = RobocorpVault()
    adapter._decrypt_payload = mock_decrypt

    secret = adapter.get_secret("mock-name")
    assert secret.name == "mock-name"
    assert secret.description == "mock-desc"
    assert secret["mock-key"] == "mock-value"

    mock_requests.get.assert_called_once_with(
        "mock-url/secrets-v1/workspaces/mock-workspace/secrets/mock-name",
        headers={"Authorization": "Bearer mock-token"},
        params={
            "encryptionScheme": "robocloud-vault-transit-v2",
            "publicKey": adapter._public_bytes,
        },
    )


@mock.patch("robocorp.vault._vault.requests")
def test_adapter_vault_error(mock_requests, mock_env_vault):
    mock_requests.get.side_effect = RuntimeError("Some request error")

    adapter = RobocorpVault()
    with pytest.raises(RobocorpVaultError):
        adapter.get_secret("mock-name")


def test_adapter_vault_encryption(mock_env_vault):
    data = json.dumps({"mock-key": "mock-value"}).encode("utf-8")

    # Cloud encrypts secret with symmetric encryption
    key = AESGCM.generate_key(bit_length=128)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct_data = aesgcm.encrypt(binascii.hexlify(nonce), data, b"")

    # Cloud uses client-supplied public key to encrypt symmetric key
    adapter = RobocorpVault()
    public_key = load_der_public_key(
        base64.b64decode(adapter._public_bytes), default_backend()
    )

    ct_key = public_key.encrypt(
        key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    ct_data, auth_tag = ct_data[:-16], ct_data[-16:]

    # Binary fields are base64 encoded, except nonce/iv (will possibly change)
    payload = {
        "name": "mock-name",
        "description": "mock-desc",
        "value": base64.b64encode(ct_data).decode("utf-8"),
        "encryption": {
            "encryptionScheme": adapter.ENCRYPTION_SCHEME,
            "encryptedAES": base64.b64encode(ct_key).decode("utf-8"),
            "authTag": base64.b64encode(auth_tag).decode("utf-8"),
            "iv": base64.b64encode(nonce).decode("utf-8"),
        },
    }

    response = adapter._decrypt_payload(payload)
    assert response["name"] == "mock-name"
    assert response["values"]["mock-key"] == "mock-value"
