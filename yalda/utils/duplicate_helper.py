import re

def extract_root_and_number(name: str) -> tuple[str, int]:
    """
    Extracts root and sequence number.
    'حرکت سفارشی' -> ('حرکت سفارشی', 1)
    'حرکت سفارشی (2)' -> ('حرکت سفارشی', 2)
    'حرکت سفارشی (۳)' -> ('حرکت سفارشی', 3)
    """
    if not name:
        return ("", 1)
    clean = name.strip()
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    num_pattern = re.compile(r'^(.*?)\s*[\(（]([0-9۰-۹]+)[\)）]$')
    m = num_pattern.match(clean)
    if m:
        root = m.group(1).strip()
        num_str = m.group(2).translate(persian_to_eng)
        num = int(num_str) if num_str.isdigit() else 1
        return (root, num)
    return (clean, 1)

def get_next_numbered_name(base_name: str, existing_names: list[str]) -> str:
    """
    Given a base name and a list of existing names,
    finds the next available numbered name in the sequence:
    'base', 'base (2)', 'base (3)', ...
    
    Handles both English and Persian digits and parentheses.
    """
    if not base_name:
        return base_name
    
    clean_base = base_name.strip()
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    
    # Check if base_name already ends with a number in parentheses, e.g. "حرکت (2)" or "حرکت (۲)"
    num_pattern = re.compile(r'^(.*?)\s*[\(（]([0-9۰-۹]+)[\)）]$')
    match = num_pattern.match(clean_base)
    
    if match:
        root = match.group(1).strip()
        num_str = match.group(2).translate(persian_to_eng)
        start_num = int(num_str) + 1 if num_str.isdigit() else 2
    else:
        root = clean_base
        start_num = 2

    used_numbers = set()
    root_lower = root.lower()
    
    for name in existing_names:
        if not name:
            continue
        cand = name.strip()
        cand_lower = cand.lower()
        
        if cand_lower == root_lower:
            used_numbers.add(1)
            continue
            
        m = num_pattern.match(cand)
        if m:
            cand_root = m.group(1).strip()
            if cand_root.lower() == root_lower:
                cand_num_str = m.group(2).translate(persian_to_eng)
                if cand_num_str.isdigit():
                    used_numbers.add(int(cand_num_str))

    next_num = max(2, start_num)
    while next_num in used_numbers:
        next_num += 1

    return f"{root} ({next_num})"

def get_resequenced_names(deleted_name: str, existing_items: list) -> list[tuple[any, str]]:
    """
    Given a deleted item's name and a list of (item_obj, current_name) for remaining items,
    identifies sibling items sharing the same root and returns a list of (item_obj, new_name)
    for items whose names need to be updated to maintain a continuous, gapless sequence (1, 2, 3...).
    """
    if not deleted_name or not existing_items:
        return []
    
    del_root, _ = extract_root_and_number(deleted_name)
    if not del_root:
        return []
    del_root_lower = del_root.lower()
    
    siblings = []
    for item, name in existing_items:
        if not name:
            continue
        root, num = extract_root_and_number(name)
        if root.lower() == del_root_lower:
            siblings.append((item, name, num))
            
    if not siblings:
        return []
        
    # Sort siblings by their existing sequence number
    siblings.sort(key=lambda x: x[2])
    
    updates = []
    for idx, (item, current_name, _) in enumerate(siblings):
        if idx == 0:
            target_name = del_root
        else:
            target_name = f"{del_root} ({idx + 1})"
            
        if current_name.strip() != target_name:
            updates.append((item, target_name))
            
    return updates
