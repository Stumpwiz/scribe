# Ensuring PyCharm Uses Python 3.x (Windows, PyCharm 2025.2.2)

Use this checklist if PyCharm shows Python 2.7 compatibility warnings while your project uses a Python 3 virtual environment.

## 1) Confirm the Interpreter for the Project and All Modules
- Open: File > Settings (Ctrl+Alt+S)
- Go to: Project: <your project> > Python Interpreter
  - Top dropdown: Select your virtualenv’s interpreter (e.g., .venv\Scripts\python.exe or your Python 3.13 path).
  - If missing, click the gear icon > Add… > Virtualenv Environment > Existing > point to <project>\.venv\Scripts\python.exe (or your chosen venv).
- Go to: Project: <your project> > Project Structure
  - Verify “Project SDK” shows your Python 3.13 interpreter.
  - Under Modules tab:
    - Ensure each module uses “Inherited from Project” or explicitly set the same Python SDK.
    - Content roots: your source folders (e.g., src) should be “Sources”; nothing critical should be “Excluded” unintentionally.
    - If some module shows a different SDK, set it to the same Python 3.13 SDK.

Tip: If you see multiple similar venvs, open the interpreter details (folder icon) and confirm the exact path points to your intended venv.

## 2) Set Python Language Level and Compatibility Inspections
- File > Settings > Editor > Code Style > Python
  - Language level: “Use recommended settings” or ensure it matches Python 3.x.
- File > Settings > Editor > Inspections > Python
  - Python compatibility: Ensure it targets “Project default” or explicitly Python 3.x.
  - Disable 2.7 checks unless you truly need cross-version compatibility.
- Check folder-level overrides:
  - Right-click a source folder in Project tool window > Mark Directory As
  - Ensure it’s “Sources Root” (not “Plain Text” or mis-marked) and no custom Python language level is applied.

## 3) Align Run/Debug Configurations
- Run > Edit Configurations…
  - For each configuration:
    - “Python interpreter”: set to “Project Default (Python 3.13 …)” or explicitly select your venv interpreter.
    - Make sure “Module name”/“Script path” configurations aren’t pulling a different interpreter template.
  - Apply/OK.

## 4) Remote/WSL Interpreters (if applicable)
- File > Settings > Build, Execution, Deployment > Python Interpreter
  - If a Remote/WSL interpreter appears selected, switch to the local Python 3.13 venv.
  - Remove stale remote interpreters if not used.

## 5) Refresh Caches and Skeletons
- File > Invalidate Caches / Restart…
  - Check “Clear file system cache and Local History”.
  - Click “Invalidate and Restart”.
- After restart, let indexing finish.

## 6) Verify Warnings Are Gone
- Open a file that previously showed Python 2.7 warnings.
- Confirm no “Python 2.7 does not support …” inspections appear.
- Re-run code inspections:
  - Code > Inspect Code… > Scope: Whole project > Run
  - Ensure compatibility findings reflect Python 3.x only.

## Known Quirks That Trigger 2.7 Fallback
- Opening the project without a configured interpreter: PyCharm may temporarily assume an older language level until an interpreter is set.
- Multiple content roots/modules: one module can silently use a different interpreter/SDK. Always check Project Structure > Modules.
- Mis-marked folders: marking src as Plain Text or leaving it unmarked can affect inspections.

## Quick Troubleshooting Flow
1. Settings > Project > Python Interpreter: select the correct venv.
2. Settings > Project Structure: set Project SDK; ensure all modules inherit it; mark src as Sources.
3. Settings > Editor > Inspections > Python: use Project default or Python 3.x.
4. Run > Edit Configurations…: set interpreter to Project Default or the venv.
5. File > Invalidate Caches / Restart…

If issues persist, remove and re-add the interpreter:
- Settings > Project > Python Interpreter > gear > Show All… > remove the stale interpreter > Add… > Existing environment > choose the correct venv python.exe.