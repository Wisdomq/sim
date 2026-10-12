# Google Play release preparation (X-13-03)

Step-by-step notes for shipping `simcards_app` (Flutter) to the Google Play
Store. The app itself (15-digit SIM scan, sales, recon) is ready; this covers
the packaging/signing/store-packaging checklist that lives outside the code.

## 1. Release signing (required before you can upload)

Play requires all uploads to be signed. Use **Play App Signing**: Google
keeps a copy of the app signing key; you upload with your **upload key**.

```bash
cd mobile/simcards_app

keytool -genkeypair -v \
  -keystore android/app/upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias upload

# Create android/key.properties (git-ignored):
#   storePassword=<password>
#   keyPassword=<password>
#   keyAlias=upload
#   storeFile=upload-keystore.jks
```

Wire the signing config into `android/app/build.gradle.kts` (release flavor)
referencing `key.properties`, then verify the flavor builds:

```bash
flutter build appbundle --dart-define=API_BASE_URL=https://<prod-api>/api/v1
# → build/app/outputs/bundle/release/app-release.aab
```

Keep the `.jks` + passwords in a secrets manager, NOT in the repo. Losing the
upload key requires a Play Console key-reset workflow with Google.

## 2. App identity

- Set `version`/`android.versionCode` in `pubspec.yaml` (currently `1.0.0+1`).
  Bump versionCode on every release; version bumps must be **increasing**.
- `applicationId` is set in `android/app/build.gradle.kts` — it must never
  change after the first upload.
- App icon + splash: replace launcher icons at all densities
  (`flutter_launcher_icons` package or manual `mipmap-*` PNGs).

## 3. Permissions audit (privacy-impacting)

The app uses the **camera** to scan SIM serials. No call/contacts/location
permissions are used. Confirm `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.CAMERA"/>
<uses-feature android:name="android.hardware.camera" android:required="true"/>
```

Camera access must be disclosed in the Play Console "Data safety" form.

## 4. Google Play Console checklist

1. **App content** — mobile app: it is a business/utility app; complete the
   questionnaire accurately.
2. **Data safety** — declare collected data: email/password credentials and
   device-captured SIM images (transient, used only for local OCR/barcode of
   serial numbers). No advertising or analytics SDKs are embedded.
3. **Privacy policy** — required because camera + account login are used.
   Publish a URL (e.g. `https://<host>/privacy`) and link it in the store
   listing.
4. **App signing** — finish Play App Signing enrollment.
5. **Store listing**:
   - Short description: "Activate, track and sell Safaricom SIM stock for
     your dealer network."
   - Full description: BA sales scanning, stock assignment, reconciliation,
     commissions, and HQ performance reports.
   - Screenshots: BA login, scan/sale, dashboard, recon (web dashboards are
     fine as supporting images).
6. **Release track** — internal testing first (upload the `.aab`, add seed
   HQ/branch/BA test accounts, run the X-13-02 E2E journey against the prod
   backend), then closed testing (50–100 invitees) → production.

## 5. Pre-flight smoke on the release build

Point a release build at the staging API and run the mobile leg of the
X-13-02 checks against the QA tenant:

```bash
flutter run --release --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Verify: login (HQ/branch/BA), stock list sync, scan→sale, return flows, and
offline queue (the app's local DB mirror).

## 6. Rollout monitoring

Once live, watch Store analytics and, in-app, monitor API errors via the
logging hooks in `docs/ops/` (X-13-04). Have a staged rollout (10% → 25% →
100%) rather than full release on day one.