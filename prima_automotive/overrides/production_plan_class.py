import frappe
from frappe.utils import cint
from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan

STAGE_ORDER = ["Cutting", "Boring", "Stamping"]


class PrimaProductionPlan(ProductionPlan):
	"""Work Orders follow the shop floor, one finished good at a time:
	item 1 Cutting > Boring > Stamping > FG, then item 2 ..., so WO numbers read in sequence."""

	@frappe.whitelist()  # the form's Create > Work Order button calls this
	def make_work_order(self):
		from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse

		self.validate_plan_is_open()
		self.reload()
		wo_list, po_list, subcontracted_po = [], [], {}
		warehouses = get_default_warehouse(self.company)
		all_fg, all_sub = self.po_items, self.sub_assembly_items
		try:
			for fg in all_fg:
				self.sub_assembly_items = [r for r in all_sub if r.production_plan_item == fg.name]
				self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, warehouses)
				self.po_items = [fg]
				self.make_work_order_for_finished_goods(wo_list, warehouses)
			self.po_items = all_fg
			fg_names = {fg.name for fg in all_fg}
			self.sub_assembly_items = [r for r in all_sub if r.production_plan_item not in fg_names]
			self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, warehouses)
		finally:
			self.po_items, self.sub_assembly_items = all_fg, all_sub

		self.make_subcontracted_purchase_order(subcontracted_po, po_list)
		self.show_list_created_message("Work Order", wo_list)
		self.show_list_created_message("Purchase Order", po_list)
		if not wo_list:
			frappe.msgprint(frappe._("No Work Orders were created"))

	def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
		rows = self.sub_assembly_items
		self.sub_assembly_items = sorted(rows, key=self.stage_rank)
		try:
			super().make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
		finally:
			self.sub_assembly_items = rows

	@staticmethod
	def stage_rank(row):
		group = frappe.get_cached_value("Item", row.production_item, "item_group")
		stage = STAGE_ORDER.index(group) if group in STAGE_ORDER else len(STAGE_ORDER)
		return (stage, -cint(row.bom_level), row.idx)
