# HealthLink

An Angular patient portal for browsing doctors, booking Chat/Video consultations and viewing appointment history. Doctor and admin workspaces manage appointments, availability and doctor visibility.

## Architecture

```text
Angular -> nginx /api -> NestJS -> Prisma -> PostgreSQL
```

The API checks account roles and ownership. Bookings claim an available slot and save the consultation in one transaction. Docker supplies the application runtimes and database.

## Setup and run

Requirements: Docker Desktop or Docker Engine with Compose v2 and Linux containers, a browser, and internet for the first build.

Open a terminal in the extracted `healthlink` folder, then run:

```bash
docker compose up -d --build
docker compose ps
```

Open **http://localhost:4200**. Defaults work without an `.env` file; `.env.example` contains the settings if needed. The API uses port 3000 and PostgreSQL uses host port 5433. Startup applies migrations and seeds fictional demo accounts, doctors, availability and two sample consultations.

## Demo accounts

Select the matching role on the login page. Credentials are prefilled and editable.

| Role | Email | Password |
|---|---|---|
| Patient | john@healthlink.local | healthlink-demo-2026 |
| Doctor | sarah.lim@healthlink.local | healthlink-demo-2026 |
| Admin | admin@healthlink.local | healthlink-demo-2026 |

## Use the app

1. Sign in as Patient and choose a doctor.
2. Select Chat or Video Call, a future available time, and a reason for the visit. Confirm the booking.
3. Check the saved consultation in Upcoming or Past and completed. Refresh to confirm it remains saved.
4. Sign in as Doctor to manage appointments and availability, or as Admin to view people and consultations and change doctor visibility.

Chat and Video Call are booking types; live messaging and video calls are outside this assessment build.

## Tests

With the app running:

```bash
docker compose exec -T backend npm test
```

The API tests cover booking, validation, saved details and role/session checks. They create demo test data.

## Stop

```bash
docker compose down
```

Database data remains saved for the next start. For startup errors, check `docker compose logs --tail 100`.
