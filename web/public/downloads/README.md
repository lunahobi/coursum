# APK download asset

The public web page for installing the Android app is:

```text
https://coursum.online/download
```

Put the release Android package here before building or deploying the web app:

```text
web/public/downloads/coursum.apk
```

The page links to:

```text
/downloads/coursum.apk
```

Build the APK from the Flutter app:

```bash
cd mobile
flutter build apk --release
```

Then copy:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

to:

```text
web/public/downloads/coursum.apk
```
