import frappe
from frappe import _


def item_warehouse(item_code, company):
	"""Item's default warehouse, else its Item Group's."""
	return frappe.db.get_value(
		"Item Default", {"parenttype": "Item", "parent": item_code, "company": company}, "default_warehouse"
	) or frappe.db.get_value(
		"Item Default",
		{"parenttype": "Item Group", "parent": frappe.db.get_value("Item", item_code, "item_group"), "company": company},
		"default_warehouse",
	)


def bom_source_warehouse(bom_no, item_code):
	return bom_no and frappe.db.get_value(
		"BOM Item", {"parent": bom_no, "item_code": item_code}, "source_warehouse"
	)


@frappe.whitelist()
def get_item_warehouse(item_code: str, company: str):
	return item_warehouse(item_code, company)


@frappe.whitelist()
def get_wo_warehouses(item_code: str, company: str, bom_no: str | None = None):
	"""Target = item default; per-input source from BOM / item default; header only if all agree."""
	bom_no = bom_no or frappe.db.get_value("Item", item_code, "default_bom")
	rows = bom_no and frappe.get_all("BOM Item", {"parent": bom_no}, ["item_code", "source_warehouse"])
	by_item = {r.item_code: r.source_warehouse or item_warehouse(r.item_code, company) for r in rows or []}
	sources = set(by_item.values())
	return {
		"target": item_warehouse(item_code, company),
		"source": sources.pop() if len(sources) == 1 else None,
		"rows": by_item,
		"skip_transfer": int(frappe.db.get_value("Item", item_code, "item_group") != "Cutting"),
	}


def before_validate(doc, method=None):
	if not doc.is_new():
		return
	# Stage-wise production: a WO must consume the previous stage, never explode to RM
	if doc.use_multi_level_bom:
		doc.use_multi_level_bom = 0
		doc.set("required_items", [])  # validate rebuilds them single-level
		frappe.msgprint(_("Use Multi-Level BOM was turned off: each stage is a separate Work Order."), alert=True)

	set_target_and_scrap(doc)
	set_skip_transfer(doc)


def set_skip_transfer(doc):
	"""Only Cutting moves RM from its store to WIP; later stages already sit in WIP."""
	group = frappe.db.get_value("Item", doc.production_item, "item_group")
	doc.skip_transfer = 0 if group == "Cutting" else 1


def set_target_and_scrap(doc):
	"""Target = production item's warehouse unless the user picked another one.
	ERPNext pre-fills the company FG warehouse, so that value counts as not picked."""
	company_fg, company_scrap = frappe.get_cached_value(
		"Company", doc.company, ["default_fg_warehouse", "default_scrap_warehouse"]
	)
	target = item_warehouse(doc.production_item, doc.company)
	if target and (doc.production_plan or doc.fg_warehouse in (None, "", company_fg)):
		doc.fg_warehouse = target
	if not doc.scrap_warehouse:
		doc.scrap_warehouse = company_scrap


def before_insert(doc, method=None):
	"""Production Plan inserts WOs with ignore_validate, so fill warehouses here too."""
	set_target_and_scrap(doc)
	set_skip_transfer(doc)
	set_sources(doc)
	set_finished_good(doc)


def validate(doc, method=None):
	set_sources(doc)
	set_finished_good(doc)


def set_finished_good(doc):
	group = doc.get("item_group") or frappe.db.get_value("Item", doc.production_item, "item_group")
	doc.is_finished_good = int(group == "Finished Goods")


def set_sources(doc):
	"""Source per row = BOM row warehouse, else the component's default warehouse.
	New WOs always take it (the header source copies one value to every row)."""
	for row in doc.required_items:
		if doc.is_new() or not row.source_warehouse:
			wh = bom_source_warehouse(doc.bom_no, row.item_code) or item_warehouse(row.item_code, doc.company)
			if wh:
				row.source_warehouse = wh
	sources = {r.source_warehouse for r in doc.required_items}
	if doc.is_new() or not doc.source_warehouse:
		# header source copies to every row, so set it only when all rows agree
		doc.source_warehouse = sources.pop() if len(sources) == 1 else None

