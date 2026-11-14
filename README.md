# Salesforce Synthetic Data Generator

Generate thousands of coherent, fictional Salesforce-style records locally with Python. The generator is free to run, has no required dependencies, and supports common fields for Account, Opportunity, Contact, Lead, Case, and User.

Use it when a free sample is limited to 1,000 rows but you need 2,000, 5,000, 15,000, or more rows to test an app, dashboard, import, or territory-planning workflow.

## Highlights

- Standard-object field presets for `account`, `opportunity`, `contact`, `lead`, `case`, and `user`
- Paste your own comma-, tab-, semicolon-, or newline-separated column list
- Configure sales regions, districts, opportunity stages, and picklists
- Control Closed Won and Closed Lost shares
- Keep opportunity stage, probability, status, and amount fields internally consistent
- Produce deterministic CSV or JSONL output with `--seed`
- Generate Salesforce-style 18-character IDs
- Optionally enrich selected text fields through Groq; no API is needed for normal generation
- Uses only the Python standard library

## Requirements

Python 3.10 or newer.

## Quick start

Clone the repository and generate 5,000 opportunities:

```bash
python salesforce_synthetic_data.py --object opportunity --rows 5000
```

Generate 15,000 accounts in selected regions:

```bash
python salesforce_synthetic_data.py \
  --object account \
  --rows 15000 \
  --regions EMEA,APAC \
  --output synthetic_accounts.csv
```

Generate a custom set of columns by pasting friendly names:

```bash
python salesforce_synthetic_data.py \
  --object opportunity \
  --rows 2000 \
  --columns 'Id,Opportunity Name,Stage,Amount,CloseDate,Closed,Won,Sales Region,Sales District,Closed Won Amount'
```

You can also put one column per line in a file:

```text
Id
Name
StageName
Amount
Sales_Region__c
Sales_District__c
```

```bash
python salesforce_synthetic_data.py --object opportunity --rows 5000 --columns-file columns.txt
```

## Presets

List the available objects:

```bash
python salesforce_synthetic_data.py --list-presets
```

List the preset fields for an object:

```bash
python salesforce_synthetic_data.py --list-fields opportunity
```

The presets include frequently used standard fields plus practical territory-planning fields such as `Sales_Region__c`, `Sales_District__c`, `Closed_Won_Amount__c`, `Closed_Lost_Amount__c`, and `Open_Pipeline_Amount__c`. These `__c` fields are illustrative custom fields, so rename them to match your Salesforce org.

## Territory-planning scenario

Imagine a sales operations manager redesigning the EMEA territory model. They need enough opportunity data to compare UKI, DACH, France, Benelux, and Nordics, but production CRM data cannot be shared with the development team.

Generate 15,000 fictional opportunities with a 22% Closed Won share and an 18% Closed Lost share:

```bash
python salesforce_synthetic_data.py \
  --object opportunity \
  --rows 15000 \
  --regions EMEA \
  --districts UKI,DACH,France,Benelux,Nordics \
  --won-rate 0.22 \
  --lost-rate 0.18 \
  --seed 2026 \
  --output emea_territory_scenario.csv
```

The resulting dataset can be loaded into a territory-balancing script or BI dashboard to compare pipeline, wins, losses, and account coverage by district without exposing customer data.

## Configuration file

Copy `salesforce_generator_config.example.json`, then edit the region-to-district mapping, opportunity stages, and picklists:

```bash
python salesforce_synthetic_data.py \
  --object opportunity \
  --rows 5000 \
  --config salesforce_generator_config.example.json
```

To write a fresh file containing all built-in defaults:

```bash
python salesforce_synthetic_data.py --write-example-config my_config.json
```

## Output formats

CSV is the default. JSON Lines is inferred from a `.jsonl` or `.ndjson` extension, or can be selected explicitly:

```bash
python salesforce_synthetic_data.py \
  --object contact \
  --rows 5000 \
  --format jsonl \
  --output contacts.jsonl
```

## Optional Groq enrichment

The local generator is normally enough. Groq is optional when you want more varied fictional descriptions or next steps. Only the selected fields and the limited number of rows are sent to the API.

```bash
export GROQ_API_KEY='your-key'
python salesforce_synthetic_data.py \
  --object opportunity \
  --rows 2000 \
  --groq-fields Description,NextStep \
  --groq-limit 100
```

The default model is `openai/gpt-oss-20b`; override it with `--groq-model`. API usage may incur costs according to the provider's pricing.

## Tests

```bash
python -m unittest discover -s tests -v
```

The test suite checks ID format, pasted-column aliases, opportunity consistency, region and district filters, win/loss overrides, and CSV row counts.

## Data-safety note

All built-in names, companies, contact details, IDs, and transaction values are generated fiction. Do not treat the output as production data, and review your organization's policies before sending any generated records to a third-party API.

