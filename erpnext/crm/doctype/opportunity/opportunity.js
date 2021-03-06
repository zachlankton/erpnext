// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.crm");
frappe.require("assets/erpnext/js/utils.js");
cur_frm.email_field = "contact_email";
frappe.ui.form.on("Opportunity", {
	customer: function(frm) {
		erpnext.utils.get_party_details(frm);
	},
	customer_address: erpnext.utils.get_address_display,
	contact_person: erpnext.utils.get_contact_details,
	enquiry_from: function(frm) {
		frm.toggle_reqd("lead", frm.doc.enquiry_from==="Lead");
		frm.toggle_reqd("customer", frm.doc.enquiry_from==="Customer");
	},
	refresh: function(frm) {
		frm.events.enquiry_from(frm);
	}
})

// TODO commonify this code
erpnext.crm.Opportunity = frappe.ui.form.Controller.extend({
	onload: function() {
		if(!this.frm.doc.enquiry_from && this.frm.doc.customer)
			this.frm.doc.enquiry_from = "Customer";
		if(!this.frm.doc.enquiry_from && this.frm.doc.lead)
			this.frm.doc.enquiry_from = "Lead";

		if(!this.frm.doc.status)
			set_multiple(cdt, cdn, { status:'Draft' });
		if(!this.frm.doc.company && frappe.defaults.get_user_default("Company"))
			set_multiple(cdt, cdn, { company:frappe.defaults.get_user_default("Company") });
		if(!this.frm.doc.fiscal_year && sys_defaults.fiscal_year)
			set_multiple(cdt, cdn, { fiscal_year:sys_defaults.fiscal_year });

		this.setup_queries();
	},

	setup_queries: function() {
		var me = this;

		if(this.frm.fields_dict.contact_by.df.options.match(/^User/)) {
			this.frm.set_query("contact_by", erpnext.queries.user);
		}

		this.frm.set_query("customer_address", function() {
			if(me.frm.doc.lead) return {filters: { lead: me.frm.doc.lead } };
			else if(me.frm.doc.customer) return {filters: { customer: me.frm.doc.customer } };
		});

		this.frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: me.frm.doc.enquiry_type === "Maintenance" ?
					{"is_service_item": 1} : {"is_sales_item":1}
			};
		});

		$.each([["lead", "lead"],
			["customer", "customer"],
			["contact_person", "customer_filter"],
			["territory", "not_a_group_filter"]], function(i, opts) {
				me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});
	},

	create_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
			frm: cur_frm
		})
	}
});

$.extend(cur_frm.cscript, new erpnext.crm.Opportunity({frm: cur_frm}));

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	erpnext.toggle_naming_series();

	if(doc.status!=="Lost") {
		cur_frm.add_custom_button(__('Create Quotation'),
			cur_frm.cscript.create_quotation, frappe.boot.doctype_icons["Quotation"],
			"btn-default");
		if(doc.status!=="Quotation")
			cur_frm.add_custom_button(__('Opportunity Lost'),
				cur_frm.cscript['Declare Opportunity Lost'], "icon-remove", "btn-default");
	}

	var frm = cur_frm;
	if(frm.perm[0].write && doc.docstatus==0) {
		if(frm.doc.status==="Open") {
			frm.add_custom_button(__("Close"), function() {
				frm.set_value("status", "Closed");
				frm.save();
			});
		} else {
			frm.add_custom_button(__("Reopen"), function() {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	}

}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.enquiry_from == 'Lead' && doc.lead)
		cur_frm.cscript.lead(doc, cdt, cdn);
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return frappe.call({
			method: "erpnext.crm.doctype.opportunity.opportunity.get_item_details",
			args: {"item_code":d.item_code},
			callback: function(r, rt) {
				if(r.message) {
					$.each(r.message, function(k, v) {
						frappe.model.set_value(cdt, cdn, k, v);
					});
				refresh_field('image_view', d.name, 'items');
				}
			}
		})
	}
}

cur_frm.cscript.lead = function(doc, cdt, cdn) {
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	frappe.model.map_current_doc({
		method: "erpnext.crm.doctype.lead.lead.make_opportunity",
		source_name: cur_frm.doc.lead,
		frm: cur_frm
	});
}

cur_frm.cscript['Declare Opportunity Lost'] = function() {
	var dialog = new frappe.ui.Dialog({
		title: __("Set as Lost"),
		fields: [
			{"fieldtype": "Text", "label": __("Reason for losing"), "fieldname": "reason",
				"reqd": 1 },
			{"fieldtype": "Button", "label": __("Update"), "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		return cur_frm.call({
			doc: cur_frm.doc,
			method: "declare_enquiry_lost",
			args: args.reason,
			callback: function(r) {
				if(r.exc) {
					msgprint(__("There were errors."));
				} else {
					dialog.hide();
					cur_frm.refresh();
				}
			},
			btn: this
		})
	});
	dialog.show();
}



cur_frm.cscript.company = function(doc, cdt, cdn) {
	erpnext.get_fiscal_year(doc.company, doc.transaction_date);
}

cur_frm.cscript.transaction_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.transaction_date);
}
