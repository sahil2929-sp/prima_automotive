frappe.query_reports["Daily Production"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "stage", label: __("Stage"), fieldtype: "Select", options: ["", "Cutting", "Boring", "Stamping", "Chamfering"] },
		{ fieldname: "work_order", label: __("Work Order"), fieldtype: "Link", options: "Work Order" },
		{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "operator_name", label: __("Operator"), fieldtype: "Data" },
		{ fieldname: "machine_no", label: __("Machine"), fieldtype: "Data" },
		{ fieldname: "sales_order", label: __("Sales Order"), fieldtype: "Link", options: "Sales Order" },
		{ fieldname: "production_plan", label: __("Production Plan"), fieldtype: "Link", options: "Production Plan" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "balance_qty") {
			const color = data.balance_qty > 0 ? "var(--orange-600)" : "var(--green-600)";
			value = `<span style="color: ${color}; font-weight: 600">${value}</span>`;
		}
		if (column.fieldname === "produced_qty") value = `<b>${value}</b>`;
		return value;
	},
};
