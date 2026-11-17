# Contributing

Thanks for helping improve EDBio.

## Report a bug

Open an issue and include:

- Your Windows version
- Your Elite Dangerous game mode
- What you expected
- What happened
- Steps to reproduce it
- Relevant journal or app errors, but remove personal details

Do not upload complete journal files or SQLite databases. They can contain
commander and location history.

## Suggest a feature

Open an issue with a short use case, the behavior you want, and why it helps.

## Submit code

1. Fork the repository.
2. Create a branch for your change.
3. Keep changes focused.
4. Run the tests.
5. Open a pull request.

Run tests with:

```powershell
python -m pytest tests -q
```

Do not add copied GPL or PolyForm licensed code or data. EDBio is MIT licensed
and uses its own independently maintained reference data.
