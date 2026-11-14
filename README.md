# Salesforce Synthetic Data Generator

Generate thousands of coherent, fictional Salesforce-style records locally with Python. Version 0.2 can create either one object or a relational Sales Cloud bundle containing linked Users, Accounts, Contacts, and Opportunities.

Use it when a free sample is limited to 1,000 rows but you need 2,000, 5,000, 15,000, or more rows to test an app, dashboard, data pipeline, or territory-planning workflow.

## Highlights

- Relational bundles with valid Account, Owner, Contact, and Opportunity links
- Exact counts for Users, Accounts, Contacts, and Opportunities
- Standard-object presets for Account, Opportunity, Contact, Lead, Case, and User
- Configurable sales regions, districts, opportunity stages, win/loss rates, and picklists
- Reproducible output from a seed and explicit as-of date
- CSV and JSONL single-object output, plus multi-file CSV bundles with a manifest
- Salesforce-style 18-character synthetic IDs
- Optional Groq enrichment for single-object text fields
- No required runtime dependencies outside the Python standard library

## Requirements and installation

Python 3.10 or newer.

Run the script directly, or install the command locally:

```bash
python -m pip install .
sf-synthetic-data --help
```

## Relational bundle quick start

Generate an internally linked dataset:

```bash
sf-synthetic-data \
  --bundle-dir output/sales_scenario \
  --users 50 \
  --accounts 2000 \
  --contacts 5000 \
  --opportunities 15000 \
  --seed 42 \
  --as-of-date 2026-01-01
```

All four counts are explicit. Users and Accounts must be at least 1; Contacts and Opportunities may be 0.

The generated relationships are:

```text
users.Id
  └── accounts.OwnerId
        ├── contacts.AccountId + contacts.OwnerId
        └── opportunities.AccountId + opportunities.OwnerId
```

Contacts and Opportunities inherit their Account's region, district, and owner. Opportunity names also use the linked Account name. Account ownership prefers a User in the same district, then the same region, then any generated User.

### Bundle output

```text
output/sales_scenario/
├── users.csv
├── accounts.csv
├── contacts.csv
├── opportunities.csv
└── manifest.json
```

Import the files in that order. `manifest.json` records the generator version, seed, as-of date, configuration checksum, filters, exact counts, relationships, filenames, and SHA-256 checksum of each CSV.

The command refuses to use a non-empty bundle directory by default. Use `--overwrite` to replace the five generated files; unrelated files are preserved.

## Territory-planning user story

A sales operations manager wants to redesign EMEA territories without sharing production CRM data. They need enough linked records to compare UKI, DACH, France, Benelux, and Nordics while preserving account ownership and pipeline relationships.

```bash
sf-synthetic-data \
  --bundle-dir output/emea_redesign \
  --users 40 \
  --accounts 3000 \
  --contacts 6000 \
  --opportunities 15000 \
  --regions EMEA \
  --districts UKI,DACH,France,Benelux,Nordics \
  --won-rate 0.22 \
  --lost-rate 0.18 \
  --seed 2026 \
  --as-of-date 2026-01-01
```

The resulting files can be loaded into a territory-balancing script or BI dashboard to compare coverage, open pipeline, wins, and losses by district.

## Single-object generation

The original interface remains available:

```bash
python salesforce_synthetic_data.py --object opportunity --rows 5000
```

Generate 15,000 accounts in selected regions:

```bash
sf-synthetic-data \
  --object account \
  --rows 15000 \
  --regions EMEA,APAC \
  --as-of-date 2026-01-01 \
  --output synthetic_accounts.csv
```

Paste a comma-, tab-, semicolon-, or newline-separated column list. Friendly labels such as `Stage`, `Closed Won Amount`, and `Sales District` are accepted:

```bash
sf-synthetic-data \
  --object opportunity \
  --rows 2000 \
  --columns 'Id,Opportunity Name,Stage,Amount,CloseDate,Closed,Won,Sales Region,Sales District,Closed Won Amount'
```

You can also put one column per line in a file and pass `--columns-file columns.txt`.

### Presets

```bash
sf-synthetic-data --list-presets
sf-synthetic-data --list-fields opportunity
```

The presets include commonly used standard fields plus practical territory fields such as `Sales_Region__c`, `Sales_District__c`, `Closed_Won_Amount__c`, `Closed_Lost_Amount__c`, and `Open_Pipeline_Amount__c`. The `__c` fields are illustrative custom fields; rename them to match your Salesforce org.

### Output formats

CSV is the default. JSON Lines is inferred from `.jsonl` or `.ndjson`, or selected explicitly:

```bash
sf-synthetic-data --object contact --rows 5000 --format jsonl --output contacts.jsonl
```

## Reproducibility

Provide both `--seed` and `--as-of-date` for repeatable output:

```bash
sf-synthetic-data --object opportunity --rows 5000 --seed 42 --as-of-date 2026-01-01
```

The same version, configuration, filters, counts, seed, and as-of date produce byte-identical bundle files. Reordering requested single-object columns does not change the value generated for a field.

Without `--as-of-date`, the current date is used for backward compatibility, so output can change on a later day.

## Configuration

Copy `salesforce_generator_config.example.json`, then edit its region-to-district mapping, opportunity stages, and picklists:

```bash
sf-synthetic-data \
  --object opportunity \
  --rows 5000 \
  --config salesforce_generator_config.example.json
```

Write all built-in defaults to a new file:

```bash
sf-synthetic-data --write-example-config my_config.json
```

Configuration is validated before generation. Invalid regions, districts, stage fields, weights, probabilities, booleans, or empty picklists produce a concise error instead of a Python traceback.

## Optional Groq enrichment

Groq remains optional and is available only in single-object mode. Only the selected fields and limited rows are sent to the API.

```bash
export GROQ_API_KEY='your-key'
sf-synthetic-data \
  --object opportunity \
  --rows 2000 \
  --groq-fields Description,NextStep \
  --groq-limit 100
```

The default model is `openai/gpt-oss-20b`; override it with `--groq-model`. API usage may incur costs according to the provider's pricing.

## Migration from 0.1

- Existing single-object commands, presets, imports, defaults, and output formats remain supported.
- `--as-of-date` is optional, but recommended for reproducible tests.
- Bundle mode does not accept single-object output, column, format, row, or Groq flags.
- The generated IDs are fictional dataset keys. They resemble Salesforce IDs but are not intended for insertion into Salesforce's standard `Id` field.

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite covers single-object compatibility, IDs, opportunity consistency, configuration errors, deterministic output, relational integrity, territory inheritance, manifest checksums, zero-child bundles, CLI conflicts, and output-directory protection.

## Data-safety note

All built-in names, companies, contact details, IDs, and transaction values are generated fiction. Do not treat the output as production data, and review your organization's policies before sending generated records to a third-party API.
