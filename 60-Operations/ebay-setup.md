# eBay Connector Setup

## What you need
An eBay Developer Program application keyset with a Client ID (App ID) and Client Secret (Cert ID). Start in Sandbox. Production Browse API use depends on eBay granting the required production access.

## Windows PowerShell — temporary session
From `50-Code/`:

```powershell
$env:EBAY_CLIENT_ID="your-client-id"
$env:EBAY_CLIENT_SECRET="your-client-secret"
$env:EBAY_ENVIRONMENT="sandbox"
$env:EBAY_MARKETPLACE_ID="EBAY_CA"
$env:EBAY_CURRENCY="CAD"
$env:EBAY_COUNTRY_CODE="CA"
```

Do not paste real credentials into Git-tracked files.

## Smoke test
After credentials are configured, run Python from `50-Code/` and construct `EbayConfig.from_env()`. The connector will mint an Application access token with the client-credentials flow. The remaining Phase 3 acceptance check is one authenticated Browse API search using a generated watchlist `SearchJob`.

## CI
CI intentionally uses mocked eBay responses and does not require or expose eBay secrets.
