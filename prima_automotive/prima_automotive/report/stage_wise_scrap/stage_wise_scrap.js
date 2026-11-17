frappe.query_reports["Stage-wise Scrap"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{
			fieldname: "stage", label: __("Stage"), fieldtype: "Link", options: "Item Group",
			get_query: () => ({ filters: { parent_item_group: ["in", ["Semi Finished Goods", "All Item Groups"]] } }),
		},
		{ fieldname: "production_item", label: __("Produced Item"), fieldtype: "Link", options: "Item" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "variance" && data && data.variance > 0) {
			value = `<span style="color: var(--red-600)">${value}</span>`;
		}
		return value;
	},
};
