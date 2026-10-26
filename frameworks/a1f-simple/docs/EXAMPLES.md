# Examples for a1f-simple Framework

## Input Format

Worker JSON must contain these fields (flattened structure):

```json
{
  "person": {
    "insurance_number": "12345678",
    "surname": "NOVÁK",
    "given_name": "Jan",
    "maiden_name": "",
    "dob": "01.01.1990",
    "nationality": "CZ",
    "birth_place": "Praha",
    "sex": "M"
  },
  "residence": {
    "street": "Wilsonova",
    "house_number": "1234",
    "city": "Praha",
    "postal_code": "100 00",
    "country_code": "CZ"
  },
  "certificate": {
    "member_state": "CZ",
    "start_date": "01.01.2025",
    "end_date": "31.12.2025",
    "document_id": "N65023S444/2025/CZ"
  },
  "employment": {
    "employer_id": "EMPL001",
    "employer_name": "Firma s.r.o.",
    "street": "Kolejna",
    "house_number": "5",
    "city": "Praha",
    "postal_code": "110 00",
    "country_code": "CZ"
  },
  "institution": {
    "name": "Úřad práce",
    "street": "Národní",
    "house_number": "23",
    "city": "Praha",
    "postal_code": "110 00",
    "country_code": "CZ",
    "code": "01234567",
    "issue_date": "01.01.2025",
    "signed_by": "Jméno Příjmení"
  },
  "activity": {},
  "meta": {
    "employee_id": "EMP123"
  }
}
```

## Usage

```bash
# Generate from worker JSON
python scripts/generate_simple.py --form worker.json --output a1_output.pdf

# With empty placeholder erase
python scripts/generate_simple.py --form worker.json --output a1_output.pdf --erase-empty
```

## Expected Output

- PDF with all `{{...}}` placeholders replaced with worker values
- NO watermarks, notices, or stamps added
- Template structure preserved
- Checkboxes toggled only if specified in layout

## Placeholders in Template

The template `a1_template_v1.pdf` has these placeholders:

**Page 1:**
- `{{person.insurance_number}}`
- `{{person.surname}}`
- `{{person.given_name}}`
- `{{person.maiden_name}}`
- `{{person.dob}}`
- `{{person.nationality}}`
- `{{person.birth_place}}`
- `{{residence.address}}`
- `{{residence.postal_code}}`
- `{{residence.city}}`
- `{{residence.country_code}}`
- `{{certificate.member_state}}`
- `{{certificate.start_date}}`
- `{{certificate.end_date}}`
- `{{document_id_p1}}`

**Page 2:**
- `{{employment.employer_id}}`
- `{{employment.employer_name}}`
- `{{employment.address}}`
- `{{employment.country_code}}`
- `{{employment.city}}`
- `{{employment.postal_code}}`
- `{{document_id_p2}}`

**Page 3:**
- `{{activity.address}}`
- `{{institution.name}}`
- `{{institution.address}}`
- `{{institution.city}}`
- `{{institution.postal_code}}`
- `{{institution.country_code}}`
- `{{institution.code}}`
- `{{institution.phone_fax}}`
- `{{institution.phone_tel}}`
- `{{institution.email}}`
- `{{institution.issue_date}}`
- `{{institution.signed_by}}`
- `{{document_id_p3}}`

## Verification Results (Working)

```
Generated: /tmp/tmp_xxx/test.pdf
Size: 1569145 bytes
Pages: 3
Placeholders remaining: 0
Notice present: False       # ✅ No notices added
Draft notice present: False # ✅ No drafts
Correct value (NOVÁK): True # ✅ Values replaced
```
