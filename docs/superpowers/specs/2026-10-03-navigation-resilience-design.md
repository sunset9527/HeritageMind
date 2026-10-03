# Navigation resilience design

## Goal

Make top-level navigation feel immediate and recoverable when the API is slow,
unavailable, or a user navigates away before a request finishes.

## Scope

- Keep Vue Router navigation independent from page data loading.
- Give API-backed list pages an explicit loading, error, and retry state.
- Bound ordinary page-data requests to 15 seconds.
- Cancel in-flight page-data requests on component disposal.
- Reload a craft or inheritor detail record when its route parameter changes.
- Add regression tests for loading/retry and parameter changes.

## Non-goals

- No backend API contract changes.
- No global cache/store migration.
- No changes to chat streaming timeout behavior.

## Design

Introduce a small composable, `usePageRequest`, for regular page reads. It
owns `data`, `loading`, `error`, `load`, and an `AbortController`. Calling
`load` aborts the prior call, clears stale state, and starts a new request.
The composable aborts its active request when the component unmounts. Its error
copy is actionable and the caller exposes a retry button.

The API client receives a named `PAGE_REQUEST_TIMEOUT_MS` of 15 seconds. Page
read functions accept an optional Axios request config so the composable can
pass the abort signal without changing backend endpoints. Chat streaming keeps
its existing long-running behavior and does not use this composable.

List views replace their implicit empty-before-loaded state with three explicit
states: loading, request failed with retry, and loaded-empty. Craft and
inheritor detail views use the same lifecycle and watch the slug route
parameter so a link between two records refreshes the content.

## Error handling

- Cancellation is silent: it is expected during navigation.
- Timeouts and connection failures show a short unavailable message and a
  retry action.
- A successful retry replaces the error state.
- Empty successful responses retain the current "暂未发布" copy.

## Verification

1. A failing view test asserts the loading state appears before a deferred API
   response and that retry invokes the read again after failure.
2. A failing detail test changes the reactive route slug and asserts that the
   second record is fetched and rendered.
3. The focused tests, full frontend test suite, type check, and production
   build pass.
