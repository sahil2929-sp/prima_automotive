// No purchase invoices at Prima: drop the invoice buttons from PO / PR forms.
// ERPNext adds them inside its own refresh, so remove after that has run.
if (!window.prima_no_bill) {
	window.prima_no_bill = true;
	const drop = (frm) =>
		frappe.after_ajax(() =>
			setTimeout(() => {
				frm.remove_custom_button(__("Purchase Invoice"), __("Create"));
				frm.remove_custom_button(__("Purchase Invoice"), __("Get Items From"));
			}, 0)
		);
	frappe.ui.form.on("Purchase Order", { refresh: drop });
	frappe.ui.form.on("Purchase Receipt", { refresh: drop });
}
