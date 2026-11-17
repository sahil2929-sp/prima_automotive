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
			"insert_after": "item_name", "fetch_from": "production_item.item_group", "read_only": 1,
			"in_list_view": 1, "in_standard_filter": 1},
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
]


def after_migrate():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	for doctype, field, prop, value, ptype in PROPERTY_SETTERS:
		make_property_setter(doctype, field, prop, value, ptype, validate_fields_for_doctype=False)
	backfill_work_order_item_group()


def backfill_work_order_item_group():
	frappe.db.sql(
		"""update `tabWork Order` wo join `tabItem` i on i.name = wo.production_item
		set wo.item_group = i.item_group where ifnull(wo.item_group, '') = ''"""
	)
