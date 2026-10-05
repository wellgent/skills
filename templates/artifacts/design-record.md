## Design record

### Data model changes

- <table or type>: <fields>, <why>

### Module seams

- <module>: interface <...>; hides <...>
- Module-shaping call: design A <...>; design B <...>; pick <...>, <why>

### Behavioural contracts

- <public operation>
  - Preconditions: <...>
  - Postconditions: <...>
  - Invariants: <...>
  - Examples: <input with literal values> -> <expected literal result>

### Test seams

- <where `tdd` tests attach>

### Hard-to-reverse calls

- <call>: <ADR link>; second opinion: <verdict>

### Migrations and production writes

- <migration or write this spec needs>
