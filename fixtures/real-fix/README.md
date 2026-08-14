# real-fix

Base behavior fails `test_pending_is_ready`; head changes the implementation so the test passes. Expected result: `PROVEN`.

The fixture is intentionally documented as a scenario. The executable end-to-end fixture used by the release tests may materialize the same base/head pair in a temporary Git repository.
