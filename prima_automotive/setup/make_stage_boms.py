"""Boring / Stamping / Chamfer BOMs: 1 Nos output from 1 Nos of the previous stage,
linked to that stage's BOM so the chain works as a multi-level BOM.

bench --site <site> execute prima_automotive.setup.make_stage_boms.run
"""

import frappe

COMPANY = "Prima Automotive"
WIP = "Work In Progress - PA"
# standard (as in item code) -> stages after Cutting
CHAINS = {"P6": ["BR", "ST", "CH"], "7090": ["BR", "ST", "CH"], "7089": ["BR", "ST"]}


def run(company=COMPANY, dry_run=0):
	created, skipped, missing = [], [], []
	for ct in frappe.get_all("Item", {"name": ["like", "CT-%"], "disabled": 0}, pluck="name", order_by="name"):
		_stage, size, std = ct.split("-", 2)
		prev = ct
		for stage in CHAINS.get(std, []):
			item = f"{stage}-{size}-{std}"
			prev_bom = frappe.db.get_value("Item", prev, "default_bom")
			if not frappe.db.exists("Item", item) or not prev_bom:
				missing.append(f"{item} (input {prev}, input BOM {prev_bom})")
				break
			if frappe.db.exists("BOM", {"item": item, "is_active": 1, "docstatus": 1}):
				skipped.append(item)
			elif not int(dry_run):
				bom = frappe.get_doc({
					"doctype": "BOM", "item": item, "company": company, "quantity": 1,
					"is_active": 1, "is_default": 1,
					"items": [{"item_code": prev, "qty": 1, "uom": "Nos", "bom_no": prev_bom, "source_warehouse": WIP}],
				})
				bom.insert(); bom.submit()
				created.append(bom.name)
			prev = item
	if not int(dry_run):
		frappe.db.commit()
	print(f"created {len(created)}, skipped {len(skipped)}, missing {len(missing)}")
	return {"created": created, "skipped": skipped, "missing": missing}
