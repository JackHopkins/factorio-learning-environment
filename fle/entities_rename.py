#!/usr/bin/env python3
import os
import re
from pathlib import Path

# ent.classes that should be prefixed with ent.
ENTITY_CLASSES = [
    '', '', '', '', 
    '', '', '', '', '',
    '', '', '', '', '', '',
    '', '', '', '', '', 'alProducer',
    '', '', '', '', '',
    '', 'MiningDrill', '', '',
    '', '', '', '', '',
    '', '', '', '', '',
    '', '', '', '', '', '',
    'ityPole', '', 'Furnace', '', '',
    '', '', '', '', '', 'Group', '',
    '', 'Group', 'ityGroup'
]

def refactor_file(file_path):
    """Refactor a single Python file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Add import if there are entity references
    if any(cls in content for cls in ENTITY_CLASSES):
        # Check if the import already exists
        if 'import fle.env.entities as ent' not in content:
            # Add the import after existing fle.env imports
            content = re.sub(
                r'(from fle\.env import[^\n]+)',
                r'\1\nimport fle.env.entities as ent',
                content, count=1
            )
    
    # Replace entity class names with ent.ClassName
    for class_name in ENTITY_CLASSES:
        # Don't replace if it's already prefixed or in import statements
        pattern = rf'\b(?<!ent\.){class_name}\b(?!["\'])'
        content = re.sub(pattern, f'ent.{class_name}', content)
    
    # Clean up imports - remove individual entity imports
    entity_pattern = '|'.join(ENTITY_CLASSES)
    content = re.sub(rf'\b({entity_pattern}),?\s*', '', content)
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Refactored: {file_path}")

# Run on all Python files
for py_file in Path('.').rglob('*.py'):
    if 'fle/env/entities.py' not in str(py_file):  # Skip the entities.py file itself
        refactor_file(py_file)