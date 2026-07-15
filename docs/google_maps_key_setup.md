# Google Maps API Key Restriction Setup

This guide explains how to restrict your `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` to
prevent unauthorized use and unexpected billing charges.

> **Why this matters**: The Maps JavaScript API key is sent to the browser and
> is visible to anyone who inspects your page source. Without restrictions, anyone
> can copy it and charge API calls to your quota.

---

## Step 1 — Open Google Cloud Console

1. Go to [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
2. Make sure the correct project is selected in the top project selector.

---

## Step 2 — Find Your Maps API Key

1. Under **API Keys**, locate the key used by this app.
2. Click the **pencil (Edit)** icon to open the key settings.

---

## Step 3 — Add HTTP Referrer Restriction

1. Under **Application restrictions**, select **HTTP referrers (web sites)**.
2. Click **Add an item** and enter your production domain(s):
   ```
   https://yourdomain.com/*
   https://www.yourdomain.com/*
   ```
3. For local development, optionally also add:
   ```
   http://localhost:3000/*
   ```
4. Click **Done**.

> **Important**: Once you save, any request from an origin NOT in this list will
> be rejected with a `403 REQUEST_DENIED` error.

---

## Step 4 — Restrict API Scope

1. Under **API restrictions**, select **Restrict key**.
2. In the dropdown, select only the APIs this app uses:
   - ✅ Maps JavaScript API
   - ✅ Geocoding API (if used server-side)
3. Click **Save**.

---

## Step 5 — Verify

1. Open your production site and check the browser console — no `REQUEST_DENIED` errors.
2. Try loading the map from a different domain (e.g. a VPN or browser extension
   that changes Origin headers) — it should be blocked.

---

## Additional Recommendations

| Action | Why |
|---|---|
| Enable **Cloud Billing Alerts** | Get notified before bill reaches a threshold |
| Enable **Maps API usage quotas** | Cap daily request count to limit blast radius |
| Separate keys per environment | Dev key unrestricted; prod key fully locked |
| Rotate the key if exposed | Even for minutes of exposure, rotate immediately |

---

## Code Reference

The key is loaded in the frontend via:
```typescript
// frontend/src/app/page.tsx
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
```

And passed to the Maps loader:
```typescript
// frontend/src/components/MapCanvas.tsx
const loader = new Loader({ apiKey: GOOGLE_MAPS_API_KEY, ... });
```

The restriction is enforced by Google's servers — no code change is needed here.
It is a **Google Cloud Console configuration action only**.
