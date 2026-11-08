# Deploying Society Manager (Netlify + Render)

Netlify serves **static websites only**, so it cannot run the Python (FastAPI) backend. The standard setup is:

| Part | Where | Cost |
|---|---|---|
| React frontend | **Netlify** | free |
| FastAPI backend (API) | **Render** web service | free tier |
| Database | **Render PostgreSQL** (or Neon) | free tier |

```
Browser  ->  Netlify (React site)  ->  Render (FastAPI API)  ->  PostgreSQL
```

Everything is already configured in this repo: `render.yaml`, `netlify.toml`, `frontend/public/_redirects`.
Do the steps in this order (the API address is needed by the frontend, the frontend address is needed by the API).

---------------------------------------------------------------------
## Step 1 - Put the project on GitHub
1. Create an empty repository on https://github.com (for example `society-manager`).
2. In the project folder (the one containing `backend`, `frontend`, `render.yaml`):
```
git init
git add .
git commit -m "Society Manager"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/society-manager.git
git push -u origin main
```
(`.gitignore` already keeps `node_modules`, `.venv` and database files out.)

---------------------------------------------------------------------
## Step 2 - Deploy the backend + database on Render
1. Sign up at https://render.com (use "Sign in with GitHub").
2. **New + -> Blueprint** -> choose your repository -> **Apply**. Render reads `render.yaml` and creates
   the API service `society-api` and the database `society-db`.
3. It asks for three values:
   - `ADMIN_EMAIL` - your login email, for example `you@gmail.com`
   - `ADMIN_PASSWORD` - a strong password (this becomes the first Admin user)
   - `CORS_ORIGINS` - type `https://temporary.example` for now (you fix it in Step 4)
4. Wait for the first deploy to finish ("Live"). Copy the service address, like
   `https://society-api-abcd.onrender.com`.
5. Test it in the browser: `https://society-api-abcd.onrender.com/api/health` must show `{"status":"ok"}`,
   and `.../docs` shows the API documentation.

**Want demo data first?** In Render -> society-api -> Environment, set `SEED` to `1` and redeploy. You get the 48 demo flats and the demo
accounts (with the demo passwords from the user guide). Switch back to `0` and use a fresh database for real use.

---------------------------------------------------------------------
## Step 3 - Deploy the frontend on Netlify
1. Sign up at https://netlify.com -> **Add new site -> Import an existing project** -> GitHub -> pick the repository.
2. Build settings are read from `netlify.toml` (base `frontend`, command `npm run build`, publish `dist`). Do not change them.
3. Before deploying, open **Site configuration -> Environment variables -> Add a variable**:
   - Key: `VITE_API_URL`
   - Value: `https://society-api-abcd.onrender.com/api`   (your Render address **plus `/api`**)
4. Click **Deploy**. When finished you get an address like `https://amazing-name-123.netlify.app`.
   (Rename it under **Site configuration -> Change site name**.)

> The variable is baked in at build time. If you change it later, use **Deploys -> Trigger deploy -> Clear cache and deploy site**.

---------------------------------------------------------------------
## Step 4 - Tell the API to trust your Netlify site (CORS)
1. Render -> `society-api` -> **Environment** -> edit `CORS_ORIGINS`:
   `https://amazing-name-123.netlify.app`  (exactly your Netlify address, **no slash at the end**).
   Several addresses can be separated by commas.
2. Save. Render redeploys by itself (1-2 minutes).

---------------------------------------------------------------------
## Step 5 - First login
1. Open your Netlify address and log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
2. With `SEED=0` the system is empty. Add, in this order: **Buildings -> Flats -> Users and Roles**
   (create the Secretary, Treasurer, Guard, then residents and link each resident to a flat).
3. Create vendors and maintenance tasks (water tank every 90 days, lift every 30 days...).

Optional - allow Netlify "deploy previews": set `CORS_ORIGIN_REGEX` to `https://.*--amazing-name-123\.netlify\.app`.

---------------------------------------------------------------------
## Alternative: drag-and-drop on Netlify (no GitHub for the frontend)
```
cd frontend
npm install
# Windows PowerShell:   $env:VITE_API_URL="https://society-api-abcd.onrender.com/api"; npm run build
# Mac/Linux:            VITE_API_URL=https://society-api-abcd.onrender.com/api npm run build
```
Then drag the `dist` folder onto https://app.netlify.com/drop. (`_redirects` is included, so page refresh works.)

## Alternative database: Neon (free PostgreSQL)
Create a project on https://neon.tech, copy the connection string, delete the `databases:` block and the
`DATABASE_URL` entry from `render.yaml` (or just edit the `DATABASE_URL` variable in the Render dashboard
and paste the Neon string).

---------------------------------------------------------------------
## Things to know about the free tiers
- **Render free web service sleeps after ~15 minutes without visitors.** The first request afterwards takes 30-60 seconds.
  The daily 8 AM reminder job cannot run while asleep; it catches up automatically when the service wakes (the checks run at every start).
  For a real society use a paid plan, or ping `/api/health` every 5 minutes with a free monitor such as UptimeRobot.
- **Render free PostgreSQL is time limited** (it expires after a period set by Render - check the current terms in the dashboard)
  and has no guaranteed backups. For real data use a paid database or Neon, and export backups regularly.
- Never use the SQLite file in production on Render free: the disk is wiped on every deploy.
- Change the demo passwords, keep `SECRET_KEY` secret, and keep `SEED=0` for real data.
- Payments are only recorded and alerts only appear in the app; SMS/WhatsApp/payment gateway are not connected.

## Troubleshooting
| Problem | Fix |
|---|---|
| Netlify site loads, login says "Failed to fetch" | `CORS_ORIGINS` on Render is wrong. It must equal the Netlify address exactly (https, no trailing slash). |
| Login calls `/api/...` on the Netlify address and fails | `VITE_API_URL` was missing at build time. Add it and **clear cache and deploy**. |
| Refreshing `/maintenance` shows "Page not found" | The redirect rule is missing. Check `netlify.toml` / `frontend/public/_redirects` were deployed. |
| First request is very slow | Render free service was asleep. Wait up to a minute. |
| Render build fails on `psycopg2` | Make sure `PYTHON_VERSION` is `3.12.7` (set in `render.yaml`). |
| "Invalid email or password" for the admin | `ADMIN_EMAIL`/`ADMIN_PASSWORD` are used only when the database has **no users**. Edit the user in the app, or reset the database. |
