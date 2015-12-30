// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/utils.js");

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	cur_frm.set_value("company", frappe.defaults.get_user_default("Company"))
	cur_frm.set_value("use_multi_level_bom", 1)
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.disable_save();
}

cur_frm.cscript.sales_order = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.sales_order) {
		return get_server_fields('get_so_details', d.sales_order, 'sales_orders', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.item_code = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return get_server_fields('get_item_details', d.item_code, 'items', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.raise_purchase_request = function(doc, cdt, cdn) {
	return frappe.call({
		method: "raise_purchase_request",
		doc:doc
	})
}

cur_frm.cscript.download_materials_required = function(doc, cdt, cdn) {
	return $c_obj(doc, 'validate_data', '', function(r, rt) {
		if (!r['exc'])
			$c_obj_csv(doc, 'download_raw_materials', '', '');
	});
}


cur_frm.fields_dict['sales_orders'].grid.get_field('sales_order').get_query = function(doc) {
	var args = { "docstatus": 1 };
	if(doc.customer) {
		args["customer"] = doc.customer;
	}

 	return { filters: args }
}

cur_frm.fields_dict['items'].grid.get_field('item_code').get_query = function(doc) {
 	return erpnext.queries.item({
		'is_pro_applicable': 1
	});
}

cur_frm.fields_dict['items'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return {
			query: "erpnext.controllers.queries.bom",
			filters:{'item': cstr(d.item_code)}
		}
	} else msgprint(__("Please enter Item first"));
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.customer_query"
	}
}

cur_frm.fields_dict.sales_orders.grid.get_field("customer").get_query =
	cur_frm.fields_dict.customer.get_query;

cur_frm.cscript.planned_start_date = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_row(doc, cdt, cdn, "items", "planned_start_date");
}
