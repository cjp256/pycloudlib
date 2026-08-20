"""Tests related to pycloudlib.azure.util module."""

import mock
import pytest

from pycloudlib.azure import util
from pycloudlib.errors import CloudSetupError

SERVICE_PRINCIPAL_CONFIG = {
    "clientId": "client-id",
    "clientSecret": "client-secret",
    "tenantId": "tenant-id",
    "subscriptionId": "subscription-id",
}


class TestGetClient:
    """Tests covering pycloudlib.azure.util.get_client."""

    @mock.patch("pycloudlib.azure.util.AzureCliCredential")
    @mock.patch("pycloudlib.azure.util.ClientSecretCredential")
    def test_service_principal_credentials(self, m_sp_credential, m_cli_credential):
        """A full service principal authenticates via ClientSecretCredential."""
        resource = mock.MagicMock()

        client = util.get_client(resource, dict(SERVICE_PRINCIPAL_CONFIG))

        m_sp_credential.assert_called_once_with(
            tenant_id="tenant-id",
            client_id="client-id",
            client_secret="client-secret",
        )
        m_cli_credential.assert_not_called()
        resource.assert_called_once_with(
            m_sp_credential.return_value, subscription_id="subscription-id"
        )
        assert client == resource.return_value

    @mock.patch("pycloudlib.azure.util.AzureCliCredential")
    @mock.patch("pycloudlib.azure.util.ClientSecretCredential")
    def test_azure_cli_credentials(self, m_sp_credential, m_cli_credential):
        """Azure CLI credentials require an explicit opt-in."""
        resource = mock.MagicMock()

        client = util.get_client(
            resource,
            {"subscriptionId": "subscription-id"},
            use_azure_cli_credential=True,
        )

        m_sp_credential.assert_not_called()
        m_cli_credential.assert_called_once_with()
        resource.assert_called_once_with(
            m_cli_credential.return_value, subscription_id="subscription-id"
        )
        assert client == resource.return_value

    @pytest.mark.parametrize(
        ("config_dict", "use_azure_cli_credential", "missing_keys"),
        (
            (
                {"subscriptionId": "subscription-id"},
                False,
                "clientId, clientSecret, tenantId",
            ),
            (
                dict(SERVICE_PRINCIPAL_CONFIG, clientSecret=""),
                False,
                "clientSecret",
            ),
            ({}, True, "subscriptionId"),
        ),
    )
    @mock.patch("pycloudlib.azure.util.AzureCliCredential")
    @mock.patch("pycloudlib.azure.util.ClientSecretCredential")
    def test_missing_configuration_raises(
        self,
        m_sp_credential,
        m_cli_credential,
        config_dict,
        use_azure_cli_credential,
        missing_keys,
    ):
        """Validate all configuration required by the selected auth method."""
        with pytest.raises(CloudSetupError) as exc_info:
            util.get_client(
                mock.MagicMock(),
                config_dict,
                use_azure_cli_credential=use_azure_cli_credential,
            )

        assert str(exc_info.value) == (f"Missing required Azure configuration: {missing_keys}")
        m_sp_credential.assert_not_called()
        m_cli_credential.assert_not_called()
