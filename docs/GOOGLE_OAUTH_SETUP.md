# Aura Google OAuth setup

This guide configures Google sign-in through Supabase Auth. Google redirects to Supabase Auth first; Supabase then redirects back to Aura.

## Required values

- Aura production origin: https://YOUR-AURA-DOMAIN
- Supabase project URL: https://YOUR-PROJECT-REF.supabase.co
- Google OAuth callback URI: https://YOUR-PROJECT-REF.supabase.co/auth/v1/callback

The DaMoA organization currently has two active free projects and has reached its two-project limit. A dedicated Aura project could not be provisioned. Do not use the unrelated Next-Up or Team Light projects for Aura authentication.

## 1. Create a Google Cloud project

1. Open https://console.cloud.google.com/
2. Sign in with the Google account that owns the Aura project.
3. Open the project selector near the top.
4. Choose New Project.
5. Project name: Aura AI.
6. Use the account's normal organization and location defaults.
7. Click Create and select the new Aura AI project.

## 2. Configure Google Auth Platform branding

1. Open https://console.cloud.google.com/auth/overview
2. Click Get started if shown.
3. App name: Aura AI.
4. User support email: an address you control.
5. Audience: choose External for users outside a Google Workspace.
6. During testing, choose Testing and add tester Google accounts.
7. Before public release, complete Google verification and publish the app.
8. Enter developer contact information and save.

## 3. Configure scopes

1. Open https://console.cloud.google.com/auth/scopes
2. Click Add or Remove Scopes.
3. Add only:
   - openid
   - https://www.googleapis.com/auth/userinfo.email
   - https://www.googleapis.com/auth/userinfo.profile
4. Save.

Basic Aura sign-in does not need Drive, Gmail, Calendar, or other Google permissions.

## 4. Create the OAuth web client

1. Open https://console.cloud.google.com/auth/clients
2. Click Create Client.
3. Application type: Web application.
4. Name: Aura AI Web.
5. Under Authorized JavaScript origins, add the exact production origin after Vercel assigns it:
   - https://YOUR-AURA-DOMAIN
6. For local development only, optionally add:
   - http://127.0.0.1:8000
   - http://localhost:8000
7. JavaScript origins contain only scheme and host. Do not include a path, callback path, query string, or trailing slash.
8. Under Authorized redirect URIs, add:
   - https://YOUR-PROJECT-REF.supabase.co/auth/v1/callback
9. Google must redirect to Supabase Auth, not directly to the Aura website.
10. Click Create.
11. Copy the Client ID and Client Secret into a password manager. Never commit the client secret to Git.

## 5. Configure Google inside Supabase

After a dedicated Aura Supabase project exists:

1. Open the Aura project dashboard.
2. Go to Authentication → Sign In / Providers → Google.
3. Enable Google.
4. Paste the Google Client ID and Client Secret.
5. Save.
6. Confirm the callback displayed by Supabase matches the URI registered in Google Cloud.

Callback format:
https://YOUR-PROJECT-REF.supabase.co/auth/v1/callback

Use the unique project reference of Aura. Do not substitute another application's project reference.

## 6. Configure Supabase redirect allow list

1. Open Authentication → URL Configuration.
2. Set Site URL to https://YOUR-AURA-DOMAIN
3. Add these redirect URLs:
   - https://YOUR-AURA-DOMAIN
   - https://YOUR-AURA-DOMAIN/**
   - http://127.0.0.1:8000
   - http://localhost:8000
4. Save.

Prefer the exact production domain over broad wildcards. Remove local URLs when no longer needed.

## 7. Configure Aura environment variables

On the Aura hosting service, set:

- SUPABASE_URL = https://YOUR-PROJECT-REF.supabase.co
- SUPABASE_PUBLISHABLE_KEY = the Aura project's sb_publishable_ key
- AURA_API_BASE_URL = the public API origin

The publishable key is designed for browser use. Never expose a Supabase secret key or service_role key in frontend JavaScript, HTML, public GitHub files, or NEXT_PUBLIC variables.

## 8. Test the complete sign-in flow

1. Open the production Aura website in a private window.
2. Click Google 계정으로 계속하기.
3. Select a Google account and review the consent screen.
4. Confirm the browser returns to the Aura production origin.
5. Confirm the Aura account control shows the signed-in account.
6. Test sign-out.
7. Separately test email registration, email verification, password sign-in, and password reset.

If Google returns redirect_uri_mismatch, compare the exact URI in Google Cloud with the Supabase callback. Scheme, host, and path must match.

If Supabase says a redirect URL is not allowed, add the Aura origin under Supabase Authentication → URL Configuration. This is a separate allow list from Google's OAuth redirect URI list.

## 9. Public launch checklist

- Publish the Google OAuth consent screen after verification.
- Configure Aura privacy policy and terms of service pages.
- Configure HTTPS and the production domain.
- Configure email SMTP and email verification.
- Enable row-level security on every exposed user-data table.
- Test that one account cannot read another account's conversations, devices, or model jobs.
- Keep provider secrets in hosting environment variables.
- Review requested OAuth scopes before public release.
