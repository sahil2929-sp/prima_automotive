# Demo masters + opening stock for Prima Automotive production flow.
# Run: bench --site <site> execute prima_automotive.setup.demo_data.run

import frappe
from frappe.utils import add_days, getdate, today

COMPANY = "Prima Automotive"
ABBR = "PA"
FY_NAME = "26-27"
STAGES = [  # (item group, item suffix, batch prefix)
	("Cutting", "CT", "CT"),
	("Boring", "BR", "BR"),
	("Stamping", "ST", "ST"),
	("Chamfering", "CH", "CH"),
]


def wh(name):
	return f"{name} - {ABBR}"


def run():
	frappe.flags.mute_emails = True
	setup_wizard()
	setup_company()
	setup_groups_and_warehouses()
	setup_parties()
	setup_items()
	setup_boms()
	setup_prices()
	setup_gst()
	frappe.db.commit()
	setup_transactions()
	frappe.db.commit()
	sample_production()
	frappe.db.commit()
	print("Prima Automotive demo data ready.")


def setup_wizard():
	if frappe.is_setup_complete():
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(
		{
			"language": "English",
			"country": "India",
			"timezone": "Asia/Kolkata",
			"currency": "INR",
			"company_name": COMPANY,
			"company_abbr": ABBR,
			"chart_of_accounts": "Standard",
			"fy_start_date": "2026-04-01",
			"fy_end_date": "2027-03-31",
			"full_name": "Administrator",
			"email": "admin@prima.localhost",
		}
	)
	frappe.db.commit()


def setup_company():
	# batch series use .FY. -> want "26-27" instead of "2026-2027"
	if frappe.db.exists("Fiscal Year", "2026-2027") and not frappe.db.exists("Fiscal Year", FY_NAME):
		frappe.rename_doc("Fiscal Year", "2026-2027", FY_NAME, force=True)

	# Finance out of scope: no GL entries from stock transactions
	frappe.db.set_value("Company", COMPANY, "enable_perpetual_inventory", 0)
	settings = frappe.get_single("Stock Settings")
	settings.allow_negative_stock = 0
	settings.enable_serial_and_batch_no_for_item = 1
	settings.use_serial_batch_fields = 1
	settings.save()
	mfg = frappe.get_single("Manufacturing Settings")
	mfg.backflush_raw_materials_based_on = "BOM"
	mfg.save()


def insert(doc, key=None):
	"""Insert if not exists (by name / filters); return name."""
	key = key or doc.get("name")
	if key and frappe.db.exists(doc["doctype"], key):
		return key if isinstance(key, str) else frappe.db.get_value(doc["doctype"], key)
	return frappe.get_doc(doc).insert(ignore_permissions=True).name


def setup_groups_and_warehouses():
	insert({"doctype": "Item Group", "item_group_name": "Semi Finished Goods",
		"parent_item_group": "All Item Groups", "is_group": 1}, "Semi Finished Goods")
	for group, _sfx, _pfx in STAGES:
		insert({"doctype": "Item Group", "item_group_name": group,
			"parent_item_group": "Semi Finished Goods"}, group)
	for group in ("Finished Goods", "Scrap", "Packing Material"):
		insert({"doctype": "Item Group", "item_group_name": group,
			"parent_item_group": "All Item Groups"}, group)

	parent = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 1, "parent_warehouse": ["is", "not set"]})
	for name in ("Raw Material", "Work In Progress", "Finished Goods", "Scrap", "Rejected"):
		insert({"doctype": "Warehouse", "warehouse_name": name, "company": COMPANY,
			"parent_warehouse": parent}, wh(name))

	frappe.db.set_value("Company", COMPANY, {
		"default_wip_warehouse": wh("Work In Progress"),
		"default_fg_warehouse": wh("Finished Goods"),
		"default_scrap_warehouse": wh("Scrap"),
	})


def setup_parties():
	for name, group in (("Shree Ganesh Steels (Demo)", "Raw Material"),
			("Precision Turned Parts (Demo)", "Hardware"),
			("Packwell Cartons (Demo)", "Local")):
		insert({"doctype": "Supplier", "supplier_name": name, "supplier_group": group}, name)
	for name in ("Alpha Auto Industries (Demo)", "Zenith Motors (Demo)"):
		insert({"doctype": "Customer", "customer_name": name, "customer_type": "Company",
			"customer_group": "Commercial", "territory": "India"}, name)


def item(code, name, group, uom, warehouse, prefix=None, purchase=0, sale=0, rate=0, extra=None):
	if frappe.db.exists("Item", code):
		frappe.db.set_value("Item", code, "item_name", name)  # keep names in sync
		return
	doc = {
		"doctype": "Item", "item_code": code, "item_name": name, "item_group": group,
		"stock_uom": uom, "is_stock_item": 1, "include_item_in_manufacturing": 1,
		"is_purchase_item": purchase, "is_sales_item": sale, "valuation_rate": rate,
		"item_defaults": [{"company": COMPANY, "default_warehouse": warehouse}],
	}
	if prefix:
		doc.update({"has_batch_no": 1, "create_new_batch": 1,
			"batch_number_series": f"{prefix}/.FY./.#####"})
	doc.update(extra or {})
	frappe.get_doc(doc).insert(ignore_permissions=True)


def setup_items():
	rm, wip, fg = wh("Raw Material"), wh("Work In Progress"), wh("Finished Goods")
	# Raw material: stock in Kg, bought in Tonne, supplier MOQ 10 MT
	for code, name in (("RM-EN8-BAR-25", "EN8 Steel Round Bar 25mm"),
			("RM-EN8-BAR-32", "EN8 Steel Round Bar 32mm")):
		item(code, name, "Raw Material", "Kg", rm, "RM", purchase=1, rate=62,
			extra={"min_order_qty": 10000, "purchase_uom": "Tonne",
				"uoms": [{"uom": "Kg", "conversion_factor": 1}, {"uom": "Tonne", "conversion_factor": 1000}]})

	item("SCRAP-STEEL", "Steel Scrap (Turnings)", "Scrap", "Kg", wh("Scrap"), sale=1, rate=25)
	item("PKG-BOX-1000", "Corrugated Box (1000 pcs)", "Packing Material", "Nos", rm, purchase=1, rate=18)

	# Internal route products: RM -> CT -> BR -> ST -> CH -> FG
	for size in ("M10", "M12"):
		for n, (group, sfx, pfx) in enumerate(STAGES, 1):
			item(f"WSH-{size}-{sfx}", f"Washer {size} - {n} {group}", group, "Nos", wip, pfx,
				purchase=1 if sfx == "BR" else 0)  # BR also buyable (mixed route)
		item(f"WSH-{size}-FG", f"Washer {size} - 5 Packed", "Finished Goods", "Nos", fg, "FG", sale=1)

	# Purchased route (BRD 12.2): bought Cut & Bored -> ST -> CH -> FG
	item("WSH-M16-CB", "Washer M16 - 2 Cut & Bored (Purchased)", "Boring", "Nos", wip, "BR", purchase=1, rate=4.5)
	for n, (group, sfx, pfx) in list(enumerate(STAGES, 1))[2:]:
		item(f"WSH-M16-{sfx}", f"Washer M16 - {n} {group}", group, "Nos", wip, pfx)
	item("WSH-M16-FG", "Washer M16 - 5 Packed", "Finished Goods", "Nos", fg, "FG", sale=1)


def default_wh(code):
	return frappe.db.get_value("Item Default", {"parent": code, "company": COMPANY}, "default_warehouse")


def bom(code, components, scrap=None, qty=1000):
	if name := frappe.db.get_value("BOM", {"item": code, "docstatus": 1, "is_default": 1}):
		for row in frappe.get_all("BOM Item", {"parent": name}, ["name", "item_code"]):
			frappe.db.set_value("BOM Item", row.name, "source_warehouse", default_wh(row.item_code))
		return
	doc = frappe.get_doc({
		"doctype": "BOM", "item": code, "company": COMPANY, "quantity": qty,
		"rm_cost_as_per": "Valuation Rate", "is_default": 1,
		"items": [{"item_code": c, "qty": q, "source_warehouse": default_wh(c)} for c, q in components],
		"secondary_items": [{"secondary_item_type": "Scrap", "item_code": "SCRAP-STEEL",
			"qty": scrap, "valuation_type": "Manual", "cost": 25}] if scrap else [],
	})
	doc.insert(ignore_permissions=True)
	doc.submit()


def setup_boms():
	# Per 1000 Nos. Kg figures are illustrative; replace with client data.
	for size, bar, rm_kg in (("M10", "RM-EN8-BAR-25", 22), ("M12", "RM-EN8-BAR-32", 30)):
		bom(f"WSH-{size}-CT", [(bar, rm_kg)], scrap=1.5)
		bom(f"WSH-{size}-BR", [(f"WSH-{size}-CT", 1000)], scrap=2)
		bom(f"WSH-{size}-ST", [(f"WSH-{size}-BR", 1000)])
		bom(f"WSH-{size}-CH", [(f"WSH-{size}-ST", 1000)], scrap=0.3)
		bom(f"WSH-{size}-FG", [(f"WSH-{size}-CH", 1000), ("PKG-BOX-1000", 1)])
	bom("WSH-M16-ST", [("WSH-M16-CB", 1000)])
	bom("WSH-M16-CH", [("WSH-M16-ST", 1000)], scrap=0.4)
	bom("WSH-M16-FG", [("WSH-M16-CH", 1000), ("PKG-BOX-1000", 1)])


def setup_prices():
	prices = [("Standard Buying", "RM-EN8-BAR-25", 62), ("Standard Buying", "RM-EN8-BAR-32", 64),
		("Standard Buying", "WSH-M16-CB", 4.5), ("Standard Buying", "WSH-M12-BR", 3.8),
		("Standard Buying", "PKG-BOX-1000", 18), ("Standard Selling", "SCRAP-STEEL", 25),
		("Standard Selling", "WSH-M10-FG", 6.5), ("Standard Selling", "WSH-M12-FG", 8),
		("Standard Selling", "WSH-M16-FG", 9.5)]
	for pl, code, rate in prices:
		insert({"doctype": "Item Price", "price_list": pl, "item_code": code, "price_list_rate": rate},
			{"price_list": pl, "item_code": code})


def new_batch(code):
	return frappe.get_doc({"doctype": "Batch", "item": code}).insert(ignore_permissions=True).name


def setup_transactions():
	if frappe.db.exists("Stock Reconciliation", {"company": COMPANY, "purpose": "Opening Stock", "docstatus": 1}):
		return
	date = getdate("2026-04-01")
	rm, wip, fg = wh("Raw Material"), wh("Work In Progress"), wh("Finished Goods")

	# Opening stock, incl. WIP sitting at different stages
	opening = [("RM-EN8-BAR-25", rm, 2500, 60), ("RM-EN8-BAR-32", rm, 1800, 63),
		("PKG-BOX-1000", rm, 200, 18, False), ("WSH-M10-CT", wip, 5000, 1.5),
		("WSH-M10-ST", wip, 3000, 2.4), ("WSH-M12-BR", wip, 2000, 3.2),
		("WSH-M10-FG", fg, 1000, 3.5)]
	sr = frappe.get_doc({"doctype": "Stock Reconciliation", "company": COMPANY,
		"purpose": "Opening Stock", "posting_date": date, "set_posting_time": 1,
		"expense_account": frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Temporary Opening"}),
		"items": []})
	for row in opening:
		code, warehouse, qty, rate = row[:4]
		batched = row[4] if len(row) > 4 else True
		sr.append("items", {"item_code": code, "warehouse": warehouse, "qty": qty,
			"valuation_rate": rate, "batch_no": new_batch(code) if batched else None,
			"use_serial_batch_fields": 1 if batched else 0})
	sr.insert(ignore_permissions=True)
	sr.submit()

	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	def po(supplier, code, qty, rate, warehouse, uom=None, receive=True):
		row = {"item_code": code, "qty": qty, "rate": rate, "warehouse": warehouse,
			"schedule_date": add_days(today(), 7)}
		if uom:
			row.update({"uom": uom, "conversion_factor": 1000})
		doc = frappe.get_doc({"doctype": "Purchase Order", "supplier": supplier, "company": COMPANY,
			"transaction_date": today(), "schedule_date": add_days(today(), 7), "items": [row]})
		doc.insert(ignore_permissions=True)
		doc.submit()
		if receive:
			pr = make_purchase_receipt(doc.name)
			pr.posting_date = today()
			pr.insert(ignore_permissions=True)
			pr.submit()

	# MOQ scenario: 10 MT bought though need is ~2 MT
	po("Shree Ganesh Steels (Demo)", "RM-EN8-BAR-25", 10, 62000, rm, uom="Tonne")
	# Direct SFG purchase scenario: received into WIP
	po("Precision Turned Parts (Demo)", "WSH-M16-CB", 8000, 4.5, wip)
	# Open PO (not yet received) for the second RM
	po("Shree Ganesh Steels (Demo)", "RM-EN8-BAR-32", 10, 64000, rm, uom="Tonne", receive=False)

	for customer, lines in (("Alpha Auto Industries (Demo)", [("WSH-M10-FG", 20000, 6.5), ("WSH-M16-FG", 5000, 9.5)]),
			("Zenith Motors (Demo)", [("WSH-M12-FG", 10000, 8)])):
		so = frappe.get_doc({"doctype": "Sales Order", "customer": customer, "company": COMPANY,
			"transaction_date": today(), "delivery_date": add_days(today(), 15),
			"items": [{"item_code": c, "qty": q, "rate": r, "warehouse": fg} for c, q, r in lines]})
		so.insert(ignore_permissions=True)
		so.submit()


# ---------------- GST (India Compliance) ----------------
# Test GSTIN/PAN only (valid check digit, not real registrations).
STATE_CODES = {"Punjab": ("03", "Ludhiana", "141001"), "Haryana": ("06", "Gurugram", "122001"),
	"Maharashtra": ("27", "Pune", "411001")}
PARTIES = [  # (doctype, name, PAN, state)
	("Company", COMPANY, "AAMCP4821K", "Punjab"),
	("Supplier", "Shree Ganesh Steels (Demo)", "AAPCS7314M", "Punjab"),
	("Supplier", "Precision Turned Parts (Demo)", "AAHCP5527R", "Haryana"),
	("Supplier", "Packwell Cartons (Demo)", "AAQFP3398D", "Punjab"),
	("Customer", "Alpha Auto Industries (Demo)", "AAJCA6612L", "Haryana"),
	("Customer", "Zenith Motors (Demo)", "AAZCZ9045B", "Maharashtra"),
]
HSN = {  # confirm with client's CA
	"Raw Material": "72142090", "Semi Finished Goods": "73182200", "Cutting": "73182200",
	"Boring": "73182200", "Stamping": "73182200", "Chamfering": "73182200",
	"Finished Goods": "73182200", "Scrap": "72044900", "Packing Material": "48191010",
}


def make_gstin(state_code, pan):
	chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	body = f"{state_code}{pan}1Z"
	total, factor = 0, 1
	for ch in body:
		d = factor * chars.find(ch)
		total += d // 36 + d % 36
		factor = 2 if factor == 1 else 1
	return body + chars[(36 - total % 36) % 36]


def setup_gst():
	for doctype, name, pan, state in PARTIES:
		code, city, pin = STATE_CODES[state]
		gstin = make_gstin(code, pan)
		frappe.db.set_value(doctype, name, {"gstin": gstin, "pan": pan, "gst_category": "Registered Regular"})
		if not frappe.db.exists("Address", {"address_title": name}):
			frappe.get_doc({"doctype": "Address", "address_title": name, "address_type": "Billing",
				"address_line1": "Plot 12, Industrial Area", "city": city, "state": state,
				"pincode": pin, "country": "India", "gstin": gstin, "gst_category": "Registered Regular",
				"is_your_company_address": int(doctype == "Company"), "is_primary_address": 1,
				"links": [{"link_doctype": doctype, "link_name": name}]}).insert(ignore_permissions=True)

	for group, hsn in HSN.items():
		frappe.db.set_value("Item Group", group, "gst_hsn_code", hsn)
	tax = f"GST 18% - {ABBR}"  # GST rates to be confirmed with CA
	for code, group in frappe.get_all("Item", fields=["name", "item_group"], as_list=True):
		doc = frappe.get_doc("Item", code)
		doc.gst_hsn_code = HSN.get(group)
		if not doc.taxes:
			doc.append("taxes", {"item_tax_template": tax})
		doc.save(ignore_permissions=True)


# ---------------- Sample production (full M10 chain) ----------------
def produce(item_code, qty, actual_scrap=None):
	"""Work Order (no RM->WIP transfer) + Manufacture entry for one stage."""
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

	wo = frappe.get_doc({"doctype": "Work Order", "production_item": item_code,
		"bom_no": frappe.db.get_value("BOM", {"item": item_code, "is_default": 1}),
		"qty": qty, "company": COMPANY, "skip_transfer": 1, "use_multi_level_bom": 0,
		"wip_warehouse": wh("Work In Progress"), "fg_warehouse": default_wh(item_code),
		"scrap_warehouse": wh("Scrap")})
	wo.set_work_order_operations()
	wo.set_required_items()
	for row in wo.required_items:
		row.source_warehouse = default_wh(row.item_code)
	wo.insert(ignore_permissions=True)
	wo.submit()

	se = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", qty))
	for row in se.items:
		if row.secondary_item_type == "Scrap" and actual_scrap is not None:
			row.qty = actual_scrap
	se.actual_scrap_entered = 1
	se.insert(ignore_permissions=True)
	se.submit()
	print(f"  {item_code}: {wo.name} / {se.name}")
	return se


def sample_production():
	"""Cutting -> Packed for 1000 Nos of M10, with actual scrap per stage."""
	from prima_automotive.overrides import stock_entry as hooks

	# backfill entries made before the hooks existed
	for name in frappe.get_all("Stock Entry", {"purpose": "Manufacture", "docstatus": 1}, pluck="name"):
		se = frappe.get_doc("Stock Entry", name)
		if not frappe.db.exists("Batch Source", {"stock_entry": name}):
			hooks.set_standard_scrap_qty(se)
			for d in hooks.scrap_rows(se):
				d.db_set("standard_scrap_qty", d.standard_scrap_qty)
			hooks.link_batches(se)

	if frappe.db.exists("Work Order", {"production_item": "WSH-M10-FG", "docstatus": 1}):
		return
	if not frappe.db.exists("Work Order", {"production_item": "WSH-M10-CT", "docstatus": 1}):
		produce("WSH-M10-CT", 1000, actual_scrap=1.8)
	produce("WSH-M10-BR", 1000, actual_scrap=2.3)
	produce("WSH-M10-ST", 1000)
	produce("WSH-M10-CH", 1000, actual_scrap=0.25)
	produce("WSH-M10-FG", 1000)
