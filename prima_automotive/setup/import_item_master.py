"""Import the client's Item Master Format (xlsx) as stage-wise items.

bench --site <site> execute prima_automotive.setup.import_item_master.run --kwargs '{"path": "<xlsx>"}'
"""

import re

import frappe
from frappe.utils import cint, flt

COMPANY = "Prima Automotive"
# client group -> (ERPNext item group, batch prefix, default warehouse)
GROUPS = {
	"RAW MATERIAL": ("Raw Material", "RM", "Raw Material - PA"),
	"CUTTING": ("Cutting", "CT", "Work In Progress - PA"),
	"BORE": ("Boring", "BR", "Work In Progress - PA"),
	"STAMP": ("Stamping", "ST", "Work In Progress - PA"),
	"CHAMFER": ("Chamfering", "CH", "Work In Progress - PA"),
}
STAGE_ORDER = ["RAW MATERIAL", "CUTTING", "BORE", "STAMP", "CHAMFER"]
# last stage of each chain is the finished good (Chamfer, or Stamp where there is no Chamfer)
FG = ("Finished Goods", "FG", "Finished Goods - PA")
SFG_PARENT = "Semi Finished Goods"
# old local codes: 7090 Chamfer clashed with P-6 RM (100001-100016) and became 1000001-1000016
RECODE = {("CHAMFER", "Standard:7090")}


def read_rows(path):
	from openpyxl import load_workbook

	ws = load_workbook(path, data_only=True, read_only=True).active
	rows = list(ws.iter_rows(values_only=True))
	head = [str(h).strip() for h in rows[0]]
	out = [dict(zip(head, r)) for r in rows[1:] if any(v is not None for v in r)]
	for row in out:
		name = str(row["Item Name"]).replace("M120", "M20")  # client typo, size is M20 (21 Nov)
		if "7090" in str(row["Description"]):  # sheet repeats M33's dimension for M30 (21 Nov)
			name = name.replace("M30(122-123X4.80-5.10)", "M30(114-115X3.80-4.00)")
		row["Item Name"] = name
	return out


def old_code(row):
	code = str(row["Item Code"]).strip()
	if (row["Item Group"].strip(), str(row["Description"]).strip()) in RECODE:
		code = "10" + code[1:].rjust(5, "0")
	return code


def size(row):
	"""'FLAT M30 DIA 50MM(...)' -> 'M30D50', 'CUT M12 (...)' -> 'M12'"""
	m = re.match(r"\s*(M\d+)\s*(?:DIA\s*(\d+))?", str(row["Item Name"]).strip().split(None, 1)[1].upper())
	return m.group(1) + (f"D{m.group(2)}" if m.group(2) else "")


def item_code(row):
	"""STAGE-SIZE-STANDARD, e.g. RM-M12-P6, CH-M20-P6, ST-M30D50-7089"""
	stage = GROUPS[row["Item Group"].strip()][1]
	return f"{stage}-{size(row)}-{standard(row).replace('-', '')}"


def recode_existing(path):
	"""One-off: rename items imported with the client's numeric codes to the new format."""
	renamed = []
	for row in read_rows(path):
		old, new = old_code(row), item_code(row)
		if frappe.db.exists("Item", old) and not frappe.db.exists("Item", new):
			frappe.rename_doc("Item", old, new, force=True, show_alert=False)
			frappe.db.set_value("Item", new, "item_code", new)
			renamed.append(f"{old} -> {new}")
	frappe.db.commit()
	print(f"renamed {len(renamed)}")
	return renamed


def standard(row):
	"""'Standard: P-6' -> 'P-6'"""
	return str(row["Description"] or "").split(":", 1)[-1].strip() or None


def chain_key(row):
	"""Same standard + same size text = one chain (e.g. FLAT/CUT/BORE/STAMP M12(...))."""
	size = str(row["Item Name"]).strip().split(None, 1)[1]
	return re.sub(r"\s+", "", str(row["Description"])).upper(), re.sub(r"\s+", "", size).upper()


def final_stages(rows):
	last = {}
	for row in rows:
		key, stage = chain_key(row), row["Item Group"].strip()
		if STAGE_ORDER.index(stage) > STAGE_ORDER.index(last.get(key, "RAW MATERIAL")):
			last[key] = stage
	return last


def setup_groups():
	"""Only Cutting/Boring/Stamping are semi-finished; Chamfering moves out of SFG."""
	if frappe.db.get_value("Item Group", "Chamfering", "parent_item_group") == SFG_PARENT:
		doc = frappe.get_doc("Item Group", "Chamfering")
		doc.parent_item_group = "All Item Groups"
		doc.save()


def run(path, company=COMPANY):
	setup_groups()
	rows = read_rows(path)
	last = final_stages(rows)
	created, updated, fg = [], [], []
	for row in rows:
		group, prefix, wh = GROUPS[row["Item Group"].strip()]
		code = item_code(row)
		is_rm = group == "Raw Material"
		is_fg = last[chain_key(row)] == row["Item Group"].strip()
		if is_fg:
			group, prefix, wh = FG
			fg.append(code)
		values = {
			"item_name": str(row["Item Name"]).strip(),
			"item_group": group,
			"description": str(row["Description"] or "").strip(),
			"standard": standard(row),
			"stock_uom": "Kg" if is_rm else "Nos",
			"is_stock_item": cint(row["Maintain Stock"]),
			"is_sales_item": 1 if is_fg else cint(row["Allow Sales"]),
			"is_purchase_item": cint(row["Allow Purchase"]),
			"include_item_in_manufacturing": cint(row["Include Item In Manufacturing"]),
			"has_batch_no": cint(row["Has Batch No"]),
			"has_serial_no": cint(row["Has Serial No"]),
			"create_new_batch": 1,
			"batch_number_series": f"{prefix}/.FY./.#####",
			"gst_hsn_code": frappe.db.get_value("Item Group", group, "gst_hsn_code"),
		}
		if is_rm:  # stock in Kg, purchase in Tonne (BRD); client price is per tonne
			values["purchase_uom"] = "Tonne"
			values["min_order_qty"] = 10000
			values["over_delivery_receipt_allowance"] = 10  # receipt may be up to 10% over PO qty

		if frappe.db.exists("Item", code):
			doc = frappe.get_doc("Item", code)
			doc.update({k: v for k, v in values.items() if k != "stock_uom"})
			updated.append(code)
		else:
			doc = frappe.get_doc({"doctype": "Item", "item_code": code, **values})
			created.append(code)
		if is_rm and not any(u.uom == "Tonne" for u in doc.uoms):
			doc.append("uoms", {"uom": "Tonne", "conversion_factor": 1000})
		default = next((d for d in doc.item_defaults if d.company == company), None)
		if default:
			default.default_warehouse = wh
		else:
			doc.append("item_defaults", {"company": company, "default_warehouse": wh})
		doc.save()

		rate = flt(row.get("Standard Purchase Price"))
		if rate:
			set_buying_price(code, rate)

	frappe.db.commit()
	print(f"created {len(created)}, updated {len(updated)}, finished goods {len(fg)}")
	return {"created": created, "updated": updated, "finished_goods": fg}


def set_buying_price(code, rate, price_list="Standard Buying"):
	name = frappe.db.get_value("Item Price", {"item_code": code, "price_list": price_list, "uom": "Tonne"})
	doc = frappe.get_doc("Item Price", name) if name else frappe.new_doc("Item Price")
	doc.update({"item_code": code, "price_list": price_list, "uom": "Tonne", "price_list_rate": rate})
	doc.save()
