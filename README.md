# Gather support assistant

Live site: [https://gatherinventory.onrender.com](https://gatherinventory.onrender.com)

Gather is a responsive event-rental and booking site with an FAQ-grounded support assistant. The assistant looks up SQL FAQ and error-code records, and creates a SQL support ticket when it cannot find a confident answer. Chat transcripts and answer feedback are stored in MongoDB.

## Features

- Rental browsing, sign-in, bookings, owner dashboard, and simulated payment flows.
- Responsive FAQ, error-code, health, and ticket pages; shared assistant widget across pages.
- Fourteen seeded FAQs and eight seeded error codes, including `GAT-001` for a reservation conflict.
- The assistant answers common reservation, inventory, account, and payment questions from FAQ data and the live inventory catalog. If a website question is vague or could mean several things, it asks for clarification and offers clickable suggested questions before creating a support ticket.
- Custom 404 and 500 pages with an option to ask the assistant.
- SQL-backed support tickets and FAQs/error codes; MongoDB-backed chat logs and feedback.
- Request method/path/status/duration logging and `/health/` dependency checks.
- Open-Meteo weather lookup with a 2.5-second server-side timeout and a user-visible fallback.

## Run locally

From the `myproject` directory:

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set a private `DJANGO_SECRET_KEY` and `MONGODB_URI`. Do not commit `.env` or paste credentials into source files. The app reads configuration directly from environment variables.
4. Run `python manage.py migrate`, then `python manage.py runserver`.
5. Visit `http://127.0.0.1:8000/`. Use `/faqs/`, `/error-codes/`, and `/health/` for the support pages.

`MONGODB_URI` must point to a reachable MongoDB instance for chat history and feedback persistence. The seeded FAQ and error-code records are installed by the initial Django migration. `DJANGO_DEBUG` should be `false` in production, and `DJANGO_ALLOWED_HOSTS` should contain the deployed host names.

## Deploy on Render

Set the service root directory to `myproject`, then use this build command so new and existing deployments apply database migrations:

```sh
pip install -r requirements.txt && python manage.py migrate --noinput
```

Use `gunicorn myproject.wsgi:application` as the start command. Set `DJANGO_SECRET_KEY` to a private value and `DJANGO_ALLOWED_HOSTS` to include `gatherinventory.onrender.com`. `DJANGO_DEBUG` defaults to `false`. After changing the build command, deploy the latest commit; migrations run during the build before the service starts.

## Proposed improvement

Add a staff support inbox with assignment, ticket replies, and email notifications so the team can resolve assistant-created tickets without relying on manual database inspection.
