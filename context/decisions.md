# Decisions

## 2026-05-31: Bound Python support to 3.10-3.13

- Decision: Declare support for Python >=3.10,<3.14.
- Reason: The patched PyTorch 2.8 dependency line pulls Triton 3.4, which does not declare Python 3.14 support.
- Impact: Poetry can resolve the secure PyTorch lockfile, and README requirements now match packaging metadata.
- Revisit: When PyTorch/Triton support Python 3.14 in the selected dependency line.
