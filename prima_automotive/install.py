import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

CUSTOM_FIELDS = {
	"Stock Entry": [
		{"fieldname": "machine_no", "label": "Machine No.", "fieldtype": "Data", "insert_after": "fg_completed_qty",
			"depends_on": "eval:doc.purpose=='Manufacture'", "mandatory_depends_on": "eval:doc.purpose=='Manufacture'",
			"in_standard_filter": 1},
		{"fieldname": "operator_name", "label": "Operator Name", "fieldtype": "Data", "insert_after": "machine_no",
			"depends_on": "eval:doc.purpose=='Manufacture'", "mandatory_depends_on": "eval:doc.purpose=='Manufacture'",
			"in_standard_filter": 1},
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
		{"fieldname": "is_finished_good", "label": "Finished Good", "fieldtype": "Check",
			"insert_after": "item_group", "read_only": 1, "in_standard_filter": 1,
			"description": "Production item is in the Finished Goods item group"},
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
		{"fieldname": "work_order", "label": "Work Order", "fieldtype": "Link", "options": "Work Order",
			"insert_after": "trace_lot", "read_only": 1, "no_copy": 1, "in_list_view": 1, "in_standard_filter": 1},
		{"fieldname": "sales_order", "label": "Sales Order", "fieldtype": "Link", "options": "Sales Order",
			"insert_after": "work_order", "read_only": 1, "no_copy": 1, "in_list_view": 1, "in_standard_filter": 1},
		{"fieldname": "production_plan", "label": "Production Plan", "fieldtype": "Link", "options": "Production Plan",
			"insert_after": "sales_order", "read_only": 1, "no_copy": 1, "in_standard_filter": 1},
		{"fieldname": "source_batches", "label": "Source Batches", "fieldtype": "Table",
			"options": "Batch Source", "insert_after": "production_plan", "read_only": 1, "no_copy": 1},
	],
}


PROPERTY_SETTERS = [
	# stage-wise WOs: don't explode BOM down to raw material
	("Work Order", "use_multi_level_bom", "default", "0", "Text"),
	# WO list: item id, name, group (BOM moved off the list to make room)
	("Work Order", "item_name", "in_list_view", "1", "Check"),
	("Work Order", "bom_no", "in_list_view", "0", "Check"),
	("Work Order", "item_name", "in_standard_filter", "1", "Check"),
	# WO list and filters: which Sales Order / Production Plan the order belongs to
	("Work Order", "sales_order", "in_list_view", "1", "Check"),
	("Work Order", "sales_order", "in_standard_filter", "1", "Check"),
	("Work Order", "production_plan", "in_list_view", "1", "Check"),
	("Work Order", "production_plan", "in_standard_filter", "1", "Check"),
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
	# operator now enters scrap directly; the confirmation tick is no longer used
	if frappe.db.exists("Custom Field", "Stock Entry-actual_scrap_entered"):
		frappe.delete_doc("Custom Field", "Stock Entry-actual_scrap_entered", ignore_permissions=True)
	for doctype, field, prop, value, ptype in PROPERTY_SETTERS:
		make_property_setter(doctype, field, prop, value, ptype, validate_fields_for_doctype=False)
	# show standard in item dropdowns (same names exist under different standards)
	make_property_setter("Item", None, "search_fields", "item_name,standard,item_group,customer_code",
		"Data", for_doctype=True, validate_fields_for_doctype=False)
	backfill_work_order_item_group()
	move_field("Work Order", "production_plan", after="sales_order")
	frappe.db.sql("""update `tabBOM` b join `tabItem` i on i.name = b.item
		set b.item_group = i.item_group, b.standard = i.standard""")


def move_field(doctype, fieldname, after):
	"""Reorder a standard field via the field_order property setter (as Customize Form does)."""
	import json

	order = [f.fieldname for f in frappe.get_meta(doctype).fields]
	if fieldname not in order or after not in order or order.index(fieldname) == order.index(after) + 1:
		return
	order.remove(fieldname)
	order.insert(order.index(after) + 1, fieldname)
	make_property_setter(doctype, None, "field_order", json.dumps(order), "Data",
		for_doctype=True, validate_fields_for_doctype=False)


def backfill_work_order_item_group():
	frappe.db.sql(
		"""update `tabWork Order` wo join `tabItem` i on i.name = wo.production_item
		set wo.item_group = i.item_group where ifnull(wo.item_group, '') = ''"""
	)
	frappe.db.sql("""update `tabWork Order` set is_finished_good = (item_group = 'Finished Goods')""")
