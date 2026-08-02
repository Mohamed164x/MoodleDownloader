# KFU Moodle Downloader — Android APK build kit

A complete Capacitor + Android project that packages a **standalone phone app**
which talks to Moodle directly (via the native Capacitor HTTP plugin, no PC
server needed, no CORS issues).

## Build it in the cloud (recommended)

1. Create a GitHub repo and push this `web/` folder (or the whole kit).
2. Go to the repo → **Actions** → **Build Android APK** → **Run workflow**.
3. When it finishes, download the uploaded artifact
   `KFU_Moodle_Downloader-apk`, which contains `app-debug.apk`.
4. Install `app-debug.apk` on your Android phone (ARM64 or any 64-bit device).

The workflow uses GitHub's hosted runner, which has the Android SDK + JDK 21
preinstalled, so no local SDK setup is needed.

## Build it locally (optional)

You need installed/available:
- JDK 21  (Temurin: https://adoptium.net)
- Android command-line tools + `platforms;android-3x` + `build-tools` via sdkmanager
- Node.js (Node 20+)

```
cd web
npm install
npx cap sync android
cd android
gradlew.bat assembleDebug     # (on Windows) or ./gradlew on mac/linux
```

APK output: `web/android/app/build/outputs/apk/debug/app-debug.apk`

## Installing on the phone
- Copy the `.apk` to the phone and tap it (allow "install unknown apps").
- If the app needs to reach Moodle over plain http, `usesCleartextTraffic` is
  already enabled in the config.

## Note about "install from phone only"
If you want downloads to save/visible on the phone, the app currently downloads
via the browser's native save flow. On Android the file lands in **Downloads**.