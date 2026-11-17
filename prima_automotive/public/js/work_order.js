// Target warehouse follows the production item's default warehouse
frappe.ui.form.on("Work Order", {
	production_item(frm) {
		if (!frm.doc.production_item || !frm.doc.company) return;
		frappe
			.xcall("prima_automotive.overrides.work_order.get_item_warehouse", {
				item_code: frm.doc.production_item,
				company: frm.doc.company,
			})
			.then((wh) => wh && frm.set_value("fg_warehouse", wh));
	},
});
