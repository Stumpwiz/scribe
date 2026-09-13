# PyCharm interpreter and project setup

Use this sequence when imports or Python compatibility inspections disagree
with the configured Scribe environment. Settings labels vary by PyCharm version.

1. **Verify the interpreter.** In project Python Interpreter settings, choose
   the intended virtual environment, compatible with `pyproject.toml`. Check the
   actual executable path (`.venv/bin/python` on Unix or
   `.venv\Scripts\python.exe` on Windows). For remote development, select the
   interpreter on the development host; do not switch to a local interpreter
   merely because it is remote.
2. **Verify project structure.** Check content roots and source roots, including
   `src`. Ensure each module inherits the project SDK or uses the same intended
   interpreter. Do not exclude legitimate source directories.
3. **Verify the run environment.** Set run configurations to the project
   interpreter and repository-root working directory. Check environment variables
   privately and confirm Clerk/backend and local authentication prerequisites
   from the README. Align Python compatibility inspections with the interpreter.
4. **Allow indexing to finish.** Reopen an affected file and check whether the
   import/inspection problem remains. Missing dependencies need provisioning,
   not cache deletion.
5. **Consider cache repair only if needed.** Use the IDE's cache invalidation and
   restart facility after the settings above are correct. Preserve Local History;
   deleting it is not a routine troubleshooting step. If an interpreter entry
   is stale, reselect the existing environment without deleting the environment.

See [README](../README.md) and [Database setup](DATABASE_SETUP.md).
