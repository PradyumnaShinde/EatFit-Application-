# EatFit

**Eat right from the menu you actually have.** EatFit reads a hostel mess or canteen menu and tells each user exactly how much of each dish to eat to hit their daily nutrition targets, in rotis and bowls rather than grams. When they skip a meal, it re-plans the rest of the day.

| Part | State |
|---|---|
| Backend API (Python/FastAPI + Postgres) | ✅ Built and tested: 22 automated tests, including user isolation and login-token checks |
| Planning engine (optimizer) | ✅ Built and tested |
| Database migrations + Supabase security rules | ✅ Built and tested on Postgres 16 (with a simulated Supabase auth schema) |
| Flutter app (Android/iOS) | ⚠️ Written and reviewed, **not yet compiled**. First `flutter run` may need small fixes |
| Menu photo scanning (Gemini) | ⚠️ Written; needs your API key to test |
| Food database | ⚠️ 45 dishes with **estimated** values; must be verified before public launch ([docs/NUTRITION_DATA.md](docs/NUTRITION_DATA.md)) |

---

## Contents

1. [What the app does](#1-what-the-app-does)
2. [How it is built](#2-how-it-is-built)
3. [Repository map](#3-repository-map)
4. [Step 1: Install the tools](#step-1-install-the-tools)
5. [Step 2: Put the code on GitHub](#step-2-put-the-code-on-github)
6. [Step 3: Run the backend on your laptop](#step-3-run-the-backend-on-your-laptop)
7. [Step 4: Create the Supabase project](#step-4-create-the-supabase-project)
8. [Step 5: Connect the backend to Supabase](#step-5-connect-the-backend-to-supabase)
9. [Step 6: Run the Flutter app](#step-6-run-the-flutter-app)
10. [Step 7: Turn on menu photo scanning](#step-7-turn-on-menu-photo-scanning)
11. [Step 8: Deploy the backend](#step-8-deploy-the-backend)
12. [Step 9: Release the Android app](#step-9-release-the-android-app)
13. [Step 10: Continuous integration](#step-10-continuous-integration)
14. [Configuration reference](#configuration-reference)
15. [Troubleshooting](#troubleshooting)
16. [Before public launch](#before-public-launch)
17. [Further docs](#further-docs)

---

## 1. What the app does

1. **Sign up**, then fill in a profile: age, sex, height, weight, activity, goal, diet type, allergies, which meals you eat, and optionally "max rotis per day".
2. EatFit computes **daily targets** for 8 nutrients: calories, protein, carbs, fat, fibre, iron, calcium and vitamin C.
3. **Add today's menu** by snapping a photo or typing it. Menus can cover a date range (e.g. the mess's weekly menu).
4. The **planner** builds a meal-by-meal plan from that menu, e.g. "3 rotis, ½ bowl dal, 1 bowl curd". It can also suggest small add-ons (a guava, sprouts) when the menu alone can't cover a nutrient.
5. Through the day, the user **ticks what they ate** or taps **Skip**. The remaining meals are re-planned instantly. On a skip, the user chooses whether to make up for it.
6. The **Nutrients** tab shows progress bars and "Quick Suggest" ideas for whatever is still short.

## 2. How it is built

```
 ┌──────────────────────┐   login (email/password)  ┌─────────────────────────────┐
 │  Flutter app         │ ────────────────────────▶ │  Supabase                   │
 │  (Android / iOS)     │ ◀──── access token ────── │   • Auth (users, logins)    │
 └──────────┬───────────┘                           │   • Postgres database       │
            │ HTTPS + "Authorization: Bearer <token>"└──────────────▲──────────────┘
            ▼                                                       │ SQL
 ┌──────────────────────────────────────────────────────────────────┴──────────────┐
 │  EatFit API (Python, FastAPI)  — runs on Render/Railway/any Docker host         │
 │   auth.py      verify the token → user id                                      │
 │   repo.py      all database queries (always filtered by user id)               │
 │   targets.py   profile → daily nutrient targets                                │
 │   optimizer.py menu + targets → how much of each dish (integer linear program) │
 │   planner.py   a user's day: eaten + skipped → re-plan + tips                  │
 │   menu_parser  menu photo → dish names (Google Gemini)                         │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

**Why these choices**

- **Supabase** gives a managed Postgres database and user login in one service, with a free tier to start. The app only talks to Supabase for logging in. All data goes through *our* API, so the business logic lives in one place.
- **FastAPI (Python)**: the planner, the nutrition maths and any future ML are all Python, so the API is too. It also gives free interactive docs at `/docs`.
- **The planner is optimization, not a trained AI model.** A nutrition plan must be exact, explainable, and never suggest a starvation diet. A linear program guarantees all three, needs no training data, and solves in under a second. AI is used where it genuinely helps: reading menu photos. Details are in [docs/OPTIMIZER.md](docs/OPTIMIZER.md).
- **Flutter**: one codebase for Android and iOS.

## 3. Repository map

```
eatfit/
├── README.md                    ← you are here
├── docs/
│   ├── API.md                   every endpoint, with real example requests/responses
│   ├── OPTIMIZER.md             how the planner works and how to tune it
│   ├── NUTRITION_DATA.md        the food database: format, sourcing, verifying
│   ├── DEVELOPMENT.md           everyday tasks: add a food, endpoint, migration...
│   └── LAUNCH_CHECKLIST.md      legal, data, store and ops checklist
├── docker-compose.yml           local Postgres + API in one command
├── .github/workflows/backend-ci.yml   runs the tests on every push
├── backend/
│   ├── app/
│   │   ├── main.py              API routes
│   │   ├── config.py            settings from environment variables
│   │   ├── auth.py              login-token verification, account deletion
│   │   ├── db.py                database connection pool
│   │   ├── repo.py              every SQL query
│   │   ├── schemas.py           request validation
│   │   ├── foods.py             per-user food catalog, name matching, diet filters
│   │   ├── targets.py           daily nutrient targets
│   │   ├── optimizer.py         the planning engine
│   │   ├── planner.py           builds a user's day
│   │   ├── menu_parser.py       menu photo → dish names
│   │   └── dbtools.py           migrations + food seeding
│   ├── data/foods.csv           the official food list (source of truth)
│   ├── migrations/              database schema, applied in order
│   ├── scripts/                 migrate.py, seed_foods.py, demo.py
│   ├── tests/test_api.py        22 tests
│   ├── Dockerfile, start.sh     production container
│   ├── requirements.txt         pinned Python dependencies
│   └── .env.example             template for your settings
└── app/                         Flutter app
    ├── pubspec.yaml
    ├── env.example.json         template for app settings
    └── lib/
        ├── main.dart            start-up, login gate, onboarding gate
        ├── config.dart          build-time settings
        ├── api.dart             all calls to the backend
        ├── widgets.dart         shared bits (error view, disclaimer)
        └── screens/             auth, home tabs, today, nutrients, menu, profile
```

---

## Step 1: Install the tools

| Tool | Version | Needed for | Get it |
|---|---|---|---|
| Git | any recent | version control | git-scm.com |
| Python | 3.11 or 3.12 | backend | python.org |
| Docker Desktop | any recent | easiest way to run Postgres locally (optional but recommended) | docker.com |
| Flutter SDK | 3.22 or newer | the app | docs.flutter.dev/get-started/install |
| Android Studio | latest | Android emulator + build tools | developer.android.com/studio |
| VS Code | latest | editor (install the Python + Flutter extensions) | code.visualstudio.com |

Check everything:

```bash
git --version
python --version        # 3.11+ (on some systems: python3 --version)
docker --version
flutter doctor          # fix anything it marks with ✗ (accept Android licenses etc.)
```

## Step 2: Put the code on GitHub

Do this first, so nothing gets lost and the team can work together.

```bash
cd eatfit
git init
git add .
git commit -m "EatFit v1"
```

1. On github.com, click **New repository**, name it `eatfit`, and set it to **Private**. Don't add a README.
2. Connect and push:
   ```bash
   git remote add origin https://github.com/<you>/eatfit.git
   git branch -M main
   git push -u origin main
   ```

`.gitignore` already keeps secrets out of git: `.env`, `env.json`, signing keys. **Never commit those files.** If you do by accident, rotate (regenerate) the keys immediately.

## Step 3: Run the backend on your laptop

Pick **Option A** (Docker, easiest) or **Option B** (no Docker).

### Option A: Docker

```bash
cd eatfit
docker compose up --build
```

This starts Postgres plus the API. On start-up the API creates the tables (migrations) and loads the food list (seeding) automatically.

Open **http://localhost:8000/docs**. You'll see every endpoint and can try them from the browser.

### Option B: without Docker

1. Install PostgreSQL 16 (postgresql.org/download). Remember the password you set for the `postgres` user.
2. Create the databases:
   ```bash
   createdb -U postgres eatfit
   createdb -U postgres eatfit_test     # used by the tests
   ```
3. Set up Python:
   ```bash
   cd eatfit/backend
   python -m venv .venv
   # Windows:  .venv\Scripts\activate        Mac/Linux:  source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
4. Create your settings file:
   ```bash
   cp .env.example .env          # Windows: copy .env.example .env
   ```
   Open `.env` and make `DATABASE_URL` match your Postgres password. Keep `AUTH_MODE=dev` for now.
5. Create the tables, load the foods, and start the server:
   ```bash
   python scripts/migrate.py         # prints "apply 001_init.sql"
   python scripts/seed_foods.py      # prints "seeded 45 official foods"
   uvicorn app.main:app --reload
   ```
6. Open **http://127.0.0.1:8000/docs**.

### Check that it works

With the server's virtual environment active, in `backend/`:

```bash
python scripts/demo.py     # plans a full day, skips breakfast, logs lunch, prints everything
pytest -q                  # expect: 22 passed
```

**What "dev" auth mode means:** instead of a real login, you send the header `X-User-Id: <any UUID>`, and each UUID acts as a separate user. To try it in `/docs`, click an endpoint → **Try it out** → put a UUID like `11111111-1111-1111-1111-111111111111` in the `x-user-id` box. The server **refuses to start** with dev mode when `ENV=production`.

## Step 4: Create the Supabase project

1. Go to supabase.com, sign up, and click **New project**.
   - **Name:** `eatfit-prod`. Tip: create a second project, `eatfit-dev`, later for testing.
   - **Database password:** generate a strong one and save it in a password manager.
   - **Region:** pick the one closest to your users. For India that's **Mumbai (ap-south-1)**.
2. Wait about 2 minutes for it to finish setting up.
3. **Collect four values.** The dashboard layout changes from time to time; use its search bar if a menu has moved.

   | Value | Where | Used by |
   |---|---|---|
   | Project URL `https://<ref>.supabase.co` | **Project Settings → API** (or the **Connect** button) | backend + app |
   | Publishable (or *anon*) key | **Project Settings → API Keys** | **app only** (safe to ship in the app) |
   | Secret (or *service_role*) key | **Project Settings → API Keys** | **backend only**, never in the app |
   | Database connection string | **Connect** button (top of the dashboard) → **Session pooler** | backend `DATABASE_URL` |

   For the connection string, use the **Session pooler** one, not "Direct connection". The direct connection is IPv6-only, and many hosts (and home networks) can't reach it. Replace `[YOUR-PASSWORD]` in the string with your database password.
4. **Signing keys (recommended):** in **Project Settings → JWT Keys**, if the project still uses the "Legacy JWT secret", migrate to the new asymmetric **JWT signing keys**. Then the backend verifies logins with Supabase's public keys and needs no shared secret. The backend supports both, so either way works.
5. **Auth settings:** in **Authentication → Sign In / Providers**, make sure **Email** is enabled.
   - During development you can turn off **Confirm email**, so new accounts can sign in immediately.
   - Turn it back **on** before launch.
   - Under **Authentication → URL Configuration**, set the Site URL to your website (used in confirmation and password-reset emails).

## Step 5: Connect the backend to Supabase

1. Edit `backend/.env`:
   ```ini
   ENV=development
   DATABASE_URL=postgresql://postgres.<ref>:<db-password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
   AUTH_MODE=supabase
   SUPABASE_URL=https://<ref>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<secret key>
   # SUPABASE_JWT_SECRET=<only if you stayed on the legacy JWT secret>
   ```
   Copy `DATABASE_URL` exactly from the dashboard. The host above is only an example.
2. Create the tables in Supabase:
   ```bash
   python scripts/migrate.py
   ```
   You should see **both** files applied. `002_auth.supabase.sql` only runs on Supabase. It does two things:
   - links every table to Supabase's users, so deleting a user deletes their data
   - turns on **Row Level Security**, so even someone holding the public key can only ever read their own rows
3. Load the foods with `python scripts/seed_foods.py`. In Supabase → **Table Editor** → `foods` you should now see 45 rows.
4. Start the server with `uvicorn app.main:app --reload`.
5. **Test with a real login:**
   - Create a user in Supabase → **Authentication → Users → Add user** (email + password, tick "auto confirm").
   - Get a token for that user:
     ```bash
     curl -s -X POST "https://<ref>.supabase.co/auth/v1/token?grant_type=password" \
       -H "apikey: <publishable/anon key>" -H "Content-Type: application/json" \
       -d '{"email":"test@example.com","password":"<password>"}'
     ```
   - Copy `access_token` from the reply and call the API:
     ```bash
     curl -s http://127.0.0.1:8000/v1/me -H "Authorization: Bearer <access_token>"
     ```
     `{"detail":"Profile not set up yet"}` means **login works**. The user just has no profile yet.

## Step 6: Run the Flutter app

1. **Generate the Android/iOS project folders** around the code. `flutter create .` only adds missing files; it keeps our `lib/` and `pubspec.yaml`.
   ```bash
   cd eatfit/app
   flutter create . --org com.yourcompany --project-name eatfit --platforms android,ios
   rm test/widget_test.dart       # the generated sample test refers to a widget we don't have
   flutter pub get
   ```
   `--org` fixes the app's permanent ID, e.g. `com.yourcompany.eatfit`. Choose it now, because it can't change after the app is published.

2. **App settings:**
   ```bash
   cp env.example.json env.json
   ```
   Fill in `SUPABASE_URL` and `SUPABASE_ANON_KEY` (the **publishable/anon** key, never the secret one). Then set `API_URL`:
   - **Android emulator:** `http://10.0.2.2:8000` (the emulator's name for your laptop).
   - **Real phone on the same Wi-Fi:** `http://<your laptop's IP>:8000`. Find the IP with `ipconfig` (Windows) or `ifconfig` (Mac/Linux), and start the backend with `uvicorn app.main:app --reload --host 0.0.0.0`.
   - **Production:** your deployed `https://` URL (Step 8).

3. **Android permissions.**
   - In `android/app/src/main/AndroidManifest.xml`, add this line just above `<application`:
     ```xml
     <uses-permission android:name="android.permission.INTERNET"/>
     ```
   - Allow plain `http://` **only in debug builds**, so release builds stay HTTPS-only. Replace the contents of `android/app/src/debug/AndroidManifest.xml` with:
     ```xml
     <manifest xmlns:android="http://schemas.android.com/apk/res/android">
         <uses-permission android:name="android.permission.INTERNET"/>
         <application android:usesCleartextTraffic="true"/>
     </manifest>
     ```

4. **iOS permissions** (only if building for iPhone; needs a Mac). Add to `ios/Runner/Info.plist` inside `<dict>`:
   ```xml
   <key>NSCameraUsageDescription</key><string>To scan your mess menu</string>
   <key>NSPhotoLibraryUsageDescription</key><string>To read a menu photo you choose</string>
   ```

5. **Run it.** Start an emulator from Android Studio (Device Manager) or plug in a phone with USB debugging on, then:
   ```bash
   flutter run --dart-define-from-file=env.json
   ```

6. **Walk through the app:**
   1. **Create account**. If "Confirm email" is on, click the link in the email first.
   2. **Onboarding:** fill in the profile, tick the note, then **Continue**.
   3. **Menu** tab: type `roti, dal, rice, curd` for lunch, then **Save**. Try `curd rice` to see the "did you mean" chips and **Add as my own food**.
   4. **Today** tab: tick items → **I ate this**, or **Skip** → choose whether to make up for it. Use the arrows to switch days.
   5. **Nutrients** tab: progress bars and Quick Suggest.
   6. **Profile** tab: edit details, sign out, delete account.

> The Dart code hasn't been compiled yet. If `flutter run` reports errors, they will be small (a renamed parameter in a package update, say). Read the message: it names the file and line.

## Step 7: Turn on menu photo scanning

1. Get an API key at **aistudio.google.com** → **Get API key**.
2. Put it in `backend/.env`:
   ```ini
   GEMINI_API_KEY=<key>
   GEMINI_MODEL=gemini-2.5-flash
   ```
   Model names change over time. If you get a "model not found" error, set `GEMINI_MODEL` to the current Flash model listed in AI Studio.
3. Restart the backend, then try **Menu → Snap menu** in the app.

The scan only *fills in* the text boxes; the user checks them and taps Save. That confirmation step is deliberate, because handwriting OCR makes mistakes.

**Cost and privacy:** check Google's current pricing and data terms for the API tier you use before launch. Free tiers may use submitted data to improve their models, and menu photos can contain people or hostel details.

## Step 8: Deploy the backend

Any host that runs a Docker container works. These steps use **Render** (render.com).

1. Push your code to GitHub (Step 2).
2. Render → **New → Web Service** → connect the `eatfit` repo.
3. Settings:
   - **Root directory:** `backend`
   - **Runtime:** Docker (Render finds `backend/Dockerfile`)
   - **Region:** Singapore (closest to India)
   - **Instance:** the free tier sleeps when idle, so the first request after a pause takes 30–60 s. Use a paid instance for real users.
   - **Health check path:** `/health`
4. **Environment variables:** add every line from your `.env`, and change:
   ```ini
   ENV=production
   AUTH_MODE=supabase
   CORS_ORIGINS=https://your-website.com      # or leave *; mobile apps don't use CORS
   ```
   Render sets `PORT` itself.
5. Click **Deploy**. On every start the container:
   - applies new migrations
   - re-syncs `foods.csv` into the database
   - starts the server
6. Check `https://<your-service>.onrender.com/health`. It should return `{"ok": true}`.
7. Point the app at it:
   - Create `app/env.prod.json` with `API_URL` set to that `https://` URL.
   - Build the app with that file (Step 9).

**Production hygiene:**
- Use a **separate** Supabase project for development and production.
- Turn on Supabase backups.
- Never reuse the production database for testing.

## Step 9: Release the Android app

1. **Icon and name:**
   - Put the app name in `android/app/src/main/AndroidManifest.xml` (`android:label="EatFit"`).
   - Generate icons, e.g. with the `flutter_launcher_icons` package.
2. **Create a signing key, once.** Back it up; if you lose it you can't update the app.
   ```bash
   keytool -genkey -v -keystore ~/eatfit-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
3. **Tell Gradle about the key:** follow Flutter's official guide, **docs.flutter.dev → Deployment → Android → "Sign the app"**. It walks through creating `android/key.properties` (already git-ignored) and editing the Gradle file.
4. **Build:**
   ```bash
   flutter build appbundle --dart-define-from-file=env.prod.json
   ```
   The output is `build/app/outputs/bundle/release/app-release.aab`.
5. **Google Play Console** (play.google.com/console): one-time registration fee, currently US$25.
   1. Create the app and upload the `.aab` to **Testing → Internal testing** first.
   2. Complete **App content**:
      - privacy policy URL (required)
      - **Data safety**: we collect email, health and fitness info (profile, food logs) and photos (menu scans, not stored). Data is encrypted in transit, and users can delete it in-app.
      - target audience: **18+**
      - **Health apps** declaration
      - ads: none
   3. New *personal* developer accounts must run a **closed test** with a minimum number of testers for a minimum period before production access. At the time of writing that's 12 testers for 14 days; check the current rule in Play Console. A hostel full of friends is perfect for this.
   4. Promote to **Production**.
6. **iOS:** needs a Mac with Xcode and an Apple Developer account ($99/year). Run `flutter build ipa`, then upload through Xcode or Transporter. Do Android first.

## Step 10: Continuous integration

`.github/workflows/backend-ci.yml` runs all backend tests against a fresh Postgres on every push that touches `backend/`. Results appear on GitHub under **Actions**.

On GitHub → **Settings → Branches → Add rule** for `main`: tick **Require status checks to pass**. Now broken code can't be merged.

---

## Configuration reference

**Backend** (`backend/.env` locally; environment variables on the host):

| Variable | Example | Meaning |
|---|---|---|
| `ENV` | `development` / `production` | production refuses `AUTH_MODE=dev` |
| `DATABASE_URL` | `postgresql://...` | Postgres connection string (Supabase: Session pooler) |
| `AUTH_MODE` | `dev` / `supabase` | `dev` = `X-User-Id` header (local only); `supabase` = real login tokens |
| `SUPABASE_URL` | `https://abc.supabase.co` | used to fetch public signing keys and check the token issuer |
| `SUPABASE_JWT_SECRET` | | only for projects still on the legacy JWT secret |
| `SUPABASE_SERVICE_ROLE_KEY` | | lets the server delete a user's login on account deletion. **Secret** |
| `GEMINI_API_KEY` | | enables menu photo scanning |
| `GEMINI_MODEL` | `gemini-2.5-flash` | which Gemini model reads menus |
| `CORS_ORIGINS` | `*` | comma-separated allowed web origins |
| `MAX_UPLOAD_MB` | `6` | largest menu photo accepted |

**App** (`app/env.json`, passed with `--dart-define-from-file`):

| Key | Meaning |
|---|---|
| `API_URL` | backend base URL (no trailing slash) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | publishable/anon key (public by design; **never** the secret key) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` on port 5432 | Postgres isn't running. Start Docker (`docker compose up db`) or the Postgres service |
| `password authentication failed` | `DATABASE_URL` password is wrong (Supabase: the *database* password, not your account password) |
| Can't reach Supabase DB from the host | Use the **Session pooler** connection string, not Direct |
| API returns 401 "Invalid or expired login" | Wrong `SUPABASE_URL`; project on legacy secret but `SUPABASE_JWT_SECRET` unset; or the phone's clock is wrong |
| API returns 401 "Dev mode: send header X-User-Id" | You're in dev mode; send the header, or set `AUTH_MODE=supabase` |
| App shows "Cannot reach the server" | Wrong `API_URL`: emulator needs `10.0.2.2`; real phone needs laptop IP + `--host 0.0.0.0` + same Wi-Fi; release builds need `https://` |
| App shows "App not configured" | Run with `--dart-define-from-file=env.json` |
| Sign-up says "check your email" and never signs in | "Confirm email" is on in Supabase; click the email link, or turn it off for development |
| Menu scan: "not configured on the server" | Set `GEMINI_API_KEY` and restart the backend |
| Menu scan: model not found | Update `GEMINI_MODEL` |
| Plan looks odd (e.g. too much curd) | Tune the weights; see [docs/OPTIMIZER.md](docs/OPTIMIZER.md) |
| A dish isn't recognised | Add it or an alias to `foods.csv`; see [docs/NUTRITION_DATA.md](docs/NUTRITION_DATA.md) |

## Before public launch

Read [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md). The four items that can sink a health startup:

1. **Nutrition data accuracy and licensing.** The current 45 values are estimates. Verify every dish, and get permission for any database you copy values from. IFCT 2017 is published by ICMR-NIN; check its terms for commercial use.
2. **Privacy law.** Food logs and body measurements are personal data under India's **DPDP Act 2023** and its Rules. You need:
   - a privacy policy
   - clear consent
   - in-app deletion (already built)
   - a plan for breaches
3. **Minors.** v1 is **18+ only** (enforced in the app, the API and the database). Children's data needs verifiable parental consent under the DPDP Act, and the adult RDAs don't apply to teenagers.
4. **Medical claims.** Keep the app's wording to "general nutrition guidance". The disclaimer is already shown at sign-up, onboarding and in the app. Never claim to diagnose or treat anything.

## Further docs

- [docs/API.md](docs/API.md): every endpoint, with real examples
- [docs/OPTIMIZER.md](docs/OPTIMIZER.md): how the planner decides, and how to tune it
- [docs/NUTRITION_DATA.md](docs/NUTRITION_DATA.md): building a trustworthy food database
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): adding foods, endpoints, migrations, screens
- [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md): everything to tick before going public
