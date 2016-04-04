# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShiftRunSummary(Document):
	def on_submit(self):
		prod_order = frappe.get_doc("Production Order", self.production_order);
		prod_order.make_time_logs();
