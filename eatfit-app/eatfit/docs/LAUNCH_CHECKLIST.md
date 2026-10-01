# Launch checklist

Tick all of these before opening the app to the public. Laws and store rules change, so confirm the current versions of each when you get here.

## Product and data
- [ ] Every official food row verified (`source` is not `estimate`); see NUTRITION_DATA.md
- [ ] A qualified nutritionist / dietitian has reviewed the targets (`targets.py`) and the food table
- [ ] Permission or licence to use any third-party nutrition data commercially (e.g. IFCT 2017 from ICMR-NIN)
- [ ] The 100–150 dishes your first target messes actually serve are covered, with good aliases
- [ ] Plans checked by hand for at least two weeks of real menus (`scripts/demo.py`)

## Legal and privacy (India)
- [ ] Privacy policy that says what you collect (email, body measurements, food logs, menu photos), why, where it's stored (Supabase region), who processes it (Supabase, your host, Google for menu scans), how long you keep it, and how to delete it
- [ ] Terms of use with the medical disclaimer ("general guidance, not medical advice")
- [ ] Consent captured at sign-up/onboarding (the app has a checkbox; make the wording match your policy)
- [ ] Comply with the **Digital Personal Data Protection Act 2023** and its Rules: consent, purpose limitation, deletion, breach notification, a grievance contact
- [ ] Adults only (18+), enforced in app, API and database. Supporting minors later needs verifiable parental consent
- [ ] Gemini (or other AI) terms checked: use a paid tier if the free tier may use submitted images for training
- [ ] Company set up (e.g. private limited / LLP) before taking payments or signing mess partnerships

## Security
- [ ] `ENV=production`, `AUTH_MODE=supabase` on the server
- [ ] Supabase: asymmetric JWT signing keys on, email confirmation **on**, a strong DB password, backups on
- [ ] Separate Supabase projects for dev and prod
- [ ] Secret/service-role key only on the server; never in the app or git
- [ ] `002_auth.supabase.sql` applied (RLS on). Check in Supabase → Database → Tables: "RLS enabled"
- [ ] HTTPS only for the API (release builds don't allow `http://`)
- [ ] Add rate limiting before marketing pushes (e.g. Render/Cloudflare, or `slowapi` in FastAPI)

## Reliability
- [ ] Paid (non-sleeping) backend instance
- [ ] Uptime monitor on `/health` (e.g. UptimeRobot, free)
- [ ] Error tracking (e.g. Sentry for FastAPI and Flutter)
- [ ] Database backup restore tested once

## Google Play
- [ ] Developer account (one-time fee) and final app id (`--org`) chosen
- [ ] Signing key created **and backed up in two places**
- [ ] Store listing: name, description, screenshots, icon, feature graphic
- [ ] Privacy policy URL, Data safety form, Health apps declaration, target audience 18+, content rating
- [ ] In-app account deletion works (Profile → Delete my account) and a web page explains how to request deletion
- [ ] Closed testing period completed if your account type requires it (check current tester/day minimums)
- [ ] Release built with `env.prod.json` (production API URL)

## After launch
- [ ] Watch logs and errors daily for the first two weeks
- [ ] Collect "this plan was weird" feedback in-app or via a form, and turn each case into a test
- [ ] Track: daily active users, % of planned meals logged, nutrients most often short
