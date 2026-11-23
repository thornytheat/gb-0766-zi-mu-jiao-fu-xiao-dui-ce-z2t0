def account(rows, isolated, copies, headings, blanks, data_lines):
    categories = dict(rows=len(rows), isolated=len(isolated), copies=len(copies), headings=headings, blanks=blanks)
    accepted_total = sum(categories.values()) - 1
    return dict(categories, data_lines=data_lines, balanced=accepted_total == data_lines)
