# Independent free scheduler: prepared, not activated

GitHub scheduled events were absent through 8:51 AM Pacific on October 24.
Yesterday's first recorded schedule event arrived at 11 AM. Manual dispatches
worked, including today's verified two-task recovery. These observations do not
identify GitHub's internal cause. Plain UTC triggers are being tested separately.

The fallback below replaces the scheduling dependency with cron-job.org while
keeping Python execution, Google OAuth secrets, and tests in private GitHub Actions.
It is not a ChatGPT reminder and does not run AI inference.

## Account authorization required

1. Create/sign in to a free account at https://console.cron-job.org/.
   No paid membership, payment method, or billing upgrade is required.
2. At https://github.com/settings/personal-access-tokens/new create a fine-grained
   token limited to **swapnilbotu/berkeley-meal-planner**, with **Actions: read and
   write**. Leave unrelated repository permissions unset. Choose an expiration
   you will renew before it expires; expiration stops the external trigger.
3. Enter the token directly into the cron-job.org authorization header below.
   Never paste it into chat, commit it, or reuse a broad account token. This
   authorizes cron-job.org to trigger/read Actions in this one repository. Google
   client credentials and the Google refresh token stay in GitHub Actions secrets.

## Exact job configuration

- Title: Berkeley meals
- URL: `https://api.github.com/repos/swapnilbotu/berkeley-meal-planner/actions/workflows/393303938/dispatches`
- Method: **POST**
- Timezone: **America/Los_Angeles**
- Custom schedule: every day, hour **7**, minutes **0 and 15**.
- Request timeout: 30 seconds; do not treat redirects as successful.
- Save responses: off.
- Headers:
  - `Authorization`: `Bearer YOUR_REPOSITORY_LIMITED_TOKEN` (enter only in the service)
  - `Accept`: `application/vnd.github+json`
  - `Content-Type`: `application/json`
  - `X-GitHub-Api-Version`: `2026-03-10`
- Request body:

```json
{"ref":"main","inputs":{"write_tasks":true,"recovery_only":true}}
```

The second dispatch reads and preserves an existing complete daily plan. It does
not duplicate tasks or change completed tasks. An HTTP success confirms only
dispatch acceptance, not successful menu retrieval or task writes.

## Verification before declaring migration complete

Run the service's test request. Check the new GitHub run, its test results and
read-back log, then independently verify exactly one lunch and one dinner task
for the current Pacific date. Observe a genuine scheduled request in the service
history and its corresponding successful GitHub run. After that, reduce native
GitHub cron to one later fallback (`17 16 * * *`) to limit runner consumption;
retain manual dispatch. Do not disable the workflow itself.

The account-wide $0 Actions stop-spending protection remains required. An external
scheduler avoids GitHub's cron dispatcher but cannot guarantee availability of
GitHub runners, Berkeley's website, or Google's API. This setup is not active until
the account authorization and live service test are completed.

Sources checked October 24, 2026:
- Free service/features: https://cron-job.org/en/
- Scheduling and HTTP request fields: https://docs.cron-job.org/rest-api.html
- GitHub dispatch permissions: https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
