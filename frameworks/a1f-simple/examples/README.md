# Example Worker Forms

This directory contains sample worker forms for testing `generate_simple.py`.

## sample_worker.json

A complete example with:
- Worker data (name, insurance, birthplace)
- Residence address (Praha)
- Certificate details
- Employment information
- Activity address (Germany)
- Checkbox selections (gender_male, status_posted_employee)

## Usage

```bash
python scripts/generate_simple.py --form examples/sample_worker.json --output output.pdf
```

## Notes

- Empty fields like `maiden_name: ""` will remain as empty (can be erased with `--erase-empty`)
- Checkbox fields should be boolean (`true`/`false`) or omitted
- All placeholder tokens are replaced with worker values