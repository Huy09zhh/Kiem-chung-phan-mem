import os
import yaml

root = 'postman/collections/Green Shop - Orders'
errors = []
count = 0
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        if f.endswith('.yaml'):
            count += 1
            full_path = os.path.join(dirpath, f)
            try:
                with open(full_path, 'r', encoding='utf-8') as fp:
                    yaml.safe_load(fp)
            except Exception as e:
                errors.append((full_path, str(e)))

print(f"Checked {count} YAML files. Errors found: {len(errors)}")
if errors:
    for p, err in errors:
        print(f"ERR in {p}: {err}")
else:
    print("SUCCESS: All YAML files are valid and well-formed!")
