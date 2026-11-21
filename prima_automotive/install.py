import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

CUSTOM_FIELDS = {
	"Stock Entry": [
		{"fieldname": "actual_scrap_entered", "label": "Actual Scrap Qty Entered", "fieldtype": "Check",
			"insert_after": "from_bom", "depends_on": "eval:doc.purpose=='Manufacture'",
			"description": "Tick after updating scrap rows with the actual shop-floor qty"},
	],
	"Stock Entry Detail": [
		{"fieldname": "standard_scrap_qty", "label": "Standard Scrap Qty (BOM)", "fieldtype": "Float",
			"insert_after": "qty", "read_only": 1, "no_copy": 1,
			"depends_on": "eval:doc.secondary_item_type=='Scrap'"},
	],
	"Work Order": [
		{"fieldname": "item_group", "label": "Item Group", "fieldtype": "Link", "options": "Item Group",
			"insert_after": "bom_no", "fetch_from": "production_item.item_group", "read_only": 1,
			"in_list_view": 1, "in_standard_filter": 1},
	],
	"Item": [
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "insert_after": "item_group",
			"in_list_view": 1, "in_standard_filter": 1, "bold": 1,
			"description": "Client standard, e.g. P-6 / 7090 / 7089"},
	],
	"BOM": [
		{"fieldname": "item_group", "label": "Item Group", "fieldtype": "Link", "options": "Item Group",
			"insert_after": "item_name", "fetch_from": "item.item_group", "read_only": 1,
			"in_list_view": 1, "in_standard_filter": 1},
		{"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "insert_after": "item_group",
			"fetch_from": "item.standard", "read_only": 1, "in_list_view": 1, "in_standard_filter": 1},
	],
	"Purchase Receipt": [
		{"fieldname": "po_received_percent", "label": "PO Received %", "fieldtype": "Percent",
			"insert_after": "supplier_name", "read_only": 1, "no_copy": 1, "allow_on_submit": 1,
			"description": "Share of the PO qty received up to this receipt; 90% or more counts as fully received"},
	],
	"Batch": [
		{"fieldname": "traceability_section", "label": "Traceability", "fieldtype": "Section Break",
			"insert_after": "reference_name", "collapsible": 0},
		{"fieldname": "trace_lot", "label": "Trace Lot (Origin Batch)", "fieldtype": "Small Text",
			"insert_after": "traceability_section", "read_only": 1, "no_copy": 1},
		{"fieldname": "source_batches", "label": "Source Batches", "fieldtype": "Table",
			"options": "Batch Source", "insert_after": "trace_lot", "read_only": 1, "no_copy": 1},
	],
}


PROPERTY_SETTERS = [
	# stage-wise WOs: don't explode BOM down to raw material
	("Work Order", "use_multi_level_bom", "default", "0", "Text"),
	# WO list: item id, name, group (BOM moved off the list to make room)
	("Work Order", "item_name", "in_list_view", "1", "Check"),
	("Work Order", "bom_no", "in_list_view", "0", "Check"),
	("Work Order", "item_name", "in_standard_filter", "1", "Check"),
	# BOM list: item name, group, standard; filters on active / default; no cost columns
	("BOM", "item_name", "in_list_view", "1", "Check"),
	("BOM", "is_active", "in_standard_filter", "1", "Check"),
	("BOM", "is_default", "in_standard_filter", "1", "Check"),
	("BOM", "total_cost", "in_list_view", "0", "Check"),
	("BOM", "has_variants", "in_list_view", "0", "Check"),
	# no purchase invoices: hide billed % on PO / PR
	("Purchase Order", "per_billed", "in_list_view", "0", "Check"),
	("Purchase Order", "per_billed", "hidden", "1", "Check"),
	("Purchase Receipt", "per_billed", "in_list_view", "0", "Check"),
	("Purchase Receipt", "per_billed", "hidden", "1", "Check"),
]


def after_migrate():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	for doctype, field, prop, value, ptype in PROPERTY_SETTERS:
		make_property_setter(doctype, field, prop, value, ptype, validate_fields_for_doctype=False)
	# show standard in item dropdowns (same names exist under different standards)
	make_property_setter("Item", None, "search_fields", "item_name,standard,item_group,customer_code",
		"Data", for_doctype=True, validate_fields_for_doctype=False)
	backfill_work_order_item_group()
	frappe.db.sql("""update `tabBOM` b join `tabItem` i on i.name = b.item
		set b.item_group = i.item_group, b.standard = i.standard""")


def backfill_work_order_item_group():
	frappe.db.sql(
		"""update `tabWork Order` wo join `tabItem` i on i.name = wo.production_item
		set wo.item_group = i.item_group where ifnull(wo.item_group, '') = ''"""
	)
