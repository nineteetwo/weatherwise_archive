# Backend Model Pack

This directory contains the runtime model pack copied from `ml/trained_models`.

Included artifacts:
- `umbrella_model.pkl`
- `clothing_model.pkl`
- `suitability_model.pkl`
- `umbrella_feature_schema.json`
- `clothing_feature_schema.json`
- `suitability_feature_schema.json`

Notes:
- Model binaries (`*.pkl`) are ignored by git via root `.gitignore`.
- Schema JSON files are committed so backend normalization/inference contracts stay explicit.
- If models are retrained, recopy all six files from `ml/trained_models` to this folder.
