"""Import the client's BOM sheet (one component + one secondary item per BOM).

Items are matched on Standard + item name, so codes we changed in the item master still resolve.
bench --site <site> execute prima_automotive.setup.import_bom.run --kwargs '{"path": "<xlsx>", "dry_run": 1}'
"""

import re

import frappe
from frappe.utils import cint, flt

COMPANY = "Prima Automotive"
UOM = {"KG": "Kg", "NOS": "Nos", "PCS": "Nos"}
WAREHOUSE = {"Raw Material": "Raw Material - PA", "Work In Progress": "Work In Progress - PA"}
SCRAP_ITEM = {"item_code": "SCR-001", "item_name": "SCRAP", "item_group": "Scrap"}


def norm(text):
	# client typos: M120 is M20; 7090 M30 was given M33's dimension
	text = re.sub(r"\s+", "", str(text or "")).upper().replace("M120", "M20")
	return text.replace("M30(122-123X4.80-5.10)", "M30(114-115X3.80-4.00)")


def read_rows(path):
	from openpyxl import load_workbook

	rows = list(load_workbook(path, data_only=True, read_only=True).active.iter_rows(values_only=True))
	head = [str(h).strip() if h else "" for h in rows[1]]  # row 1 is the section banner
	out, standard = [], None
	for r in rows[2:]:
		if not any(v is not None for v in r):
			continue
		row = dict(zip(head, r))
		standard = str(row["Standard"]).strip() if row["Standard"] else standard  # filled on first row only
		row["Standard"] = standard
		out.append(row)
	return out


def resolve(code, name, standard, problems, label):
	"""Local item matching the sheet row on Standard + item name."""
	match = frappe.db.get_all("Item", {"standard": standard, "disabled": 0}, ["name", "item_name"])
	by_name = [m.name for m in match if norm(m.item_name) == norm(name)]
	if len(by_name) == 1:
		return by_name[0]
	code = str(code)
	if frappe.db.exists("Item", code):
		local = frappe.db.get_value("Item", code, ["item_name", "standard"], as_dict=True)
		problems.append(f"{label}: {code} name differs, sheet '{name}' vs item '{local.item_name}' ({local.standard})")
		return code
	problems.append(f"{label}: {code} '{name}' not found")


def ensure_scrap_item(company):
	if frappe.db.exists("Item", SCRAP_ITEM["item_code"]):
		return
	frappe.get_doc({
		"doctype": "Item", **SCRAP_ITEM, "stock_uom": "Kg", "is_stock_item": 1, "is_sales_item": 1,
		"is_purchase_item": 0, "include_item_in_manufacturing": 0,
		"gst_hsn_code": frappe.db.get_value("Item Group", "Scrap", "gst_hsn_code"),
		"item_defaults": [{"company": company, "default_warehouse": "Scrap - PA"}],
	}).insert()


def run(path, company=COMPANY, dry_run=0):
	rows, problems, created, skipped = read_rows(path), [], [], []
	if not cint(dry_run):
		ensure_scrap_item(company)
	for i, row in enumerate(rows, start=3):
		std = row["Standard"]
		fg = resolve(row["Item Code to Manufacture"], row["Item Name to Manufacture"], std, problems, f"row {i} item")
		rm = resolve(row["Item Code (Components)"], row["Item Name (Components)"], std, problems, f"row {i} component")
		if not fg or not rm:
			continue
		if frappe.db.exists("BOM", {"item": fg, "docstatus": 1, "is_active": 1}):
			skipped.append(fg)
			continue
		if cint(dry_run):
			continue
		bom = frappe.get_doc({
			"doctype": "BOM", "item": fg, "company": company, "quantity": flt(row["Quantity (Output Qty)"]) or 1,
			"is_active": cint(row["Is Active"]), "is_default": cint(row["Is Default"]),
			"items": [{
				"item_code": rm, "qty": flt(row["Qty (Components) Including Scrap Qty"]),
				"uom": UOM.get(norm(row["UOM (Components)"]), row["UOM (Components)"]),
				"bom_no": row["BOM No (Components)"] or None,
				"source_warehouse": WAREHOUSE.get(row["Source Warehouse (Components)"]),
			}],
		})
		sec_code = row["Item Code (Secondary Items)"]
		if sec_code:
			bom.append("secondary_items", {
				"item_code": sec_code, "secondary_item_type": str(row["Type (Secondary Items)"]).title(),
				"uom": UOM.get(norm(row["UOM (Secondary Items)"]), row["UOM (Secondary Items)"]),
				"qty": flt(row["Qty (Secondary Items)"]),
			})
		bom.insert()
		bom.submit()
		created.append(bom.name)

	if not cint(dry_run):
		frappe.db.commit()
	print(f"rows {len(rows)}, created {len(created)}, skipped {len(skipped)}, problems {len(problems)}")
	return {"created": created, "skipped": skipped, "problems": problems}
