odoo.define('skit_pay_later.pay_later', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;
var chrome = require('point_of_sale.chrome');
var _t = core._t;
var gui = require('point_of_sale.gui');
var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var utils = require('web.utils');
var session = require('web.session');
var round_pr = utils.round_precision;
var PopupWidget = require('point_of_sale.popups');
var round_di = utils.round_decimals;
var PaymentScreenWidget = screens.PaymentScreenWidget;

/**Load is pay later field for account journal **/
var _super_posmodel = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({

	initialize : function(session, attributes) {
		var account_model = _.find(this.models, function(model) {
			return model.model === 'pos.payment.method';
		});
		account_model.fields.push('is_pay_later');

		return _super_posmodel.initialize.call(this, session, attributes);
	},

});

var _super = models.Order.prototype;
models.Order = models.Order.extend({
	initialize: function(attributes,options){
		_super.initialize.apply(this,arguments);
		 this.is_pending = false;
		 this.is_pay_later = false;
		 this.p_invoice_id = 0;
		 this.p_invoice_amt = 0;
		 this.p_porder_id = 0;
		 this.p_order_type = 'POS';
		 this.save_to_db();
	},
    
	/* ---- Pending Invoice  --- */
    set_is_pending: function(is_pending) {
        this.is_pending = is_pending;
        this.trigger('change');
    },
    get_pending: function(){
        return this.is_pending;
    },
    set_pending_invoice: function(p_invoice_id) {
        this.p_invoice_id = p_invoice_id;
        this.trigger('change');
    },
    get_pending_invoice: function(){
        return this.p_invoice_id;
    },
    set_pending_amt: function(p_invoice_amt) {
        this.p_invoice_amt = p_invoice_amt;
        this.trigger('change');
    },
    get_pending_amt: function(){
        return this.p_invoice_amt;
    },
    set_pending_porder: function(p_porder_id) {
        this.p_porder_id = p_porder_id;
        this.trigger('change');
    },
    get_pending_porder: function(){
        return this.p_porder_id;
    },
    set_pending_order_type: function(p_order_type) {
        this.p_order_type = p_order_type;
        this.trigger('change');
    },
    get_pending_order_type: function(){
        return this.p_order_type;
    },
    /* ---- Reprint Order array  --- */
    set_print_orders: function(order_arr) {
        this.print_orders = order_arr;
        this.trigger('change');
    },
    get_print_orders: function(){
        return this.print_orders;
    },
	/* ---- Reprint Order id  --- */
    set_is_reprint_order: function(is_reprint_order) {
        this.is_reprint_order = is_reprint_order;
        this.trigger('change');
    },
    get_is_reprint_order: function(){
        return this.p_porder_id;
    },
    /* Journal */
    set_is_pay_later: function(pay_later) {
        this.assert_editable();
        var self =this;
        this.is_pay_later = pay_later;
        self.is_pay_later = pay_later;
    },
    get_is_pay_later: function(){
    	var self = this;
		return self.is_pay_later;
	},
    get_change: function(paymentline) {
    	_super.get_change.apply(this,arguments);
    	if (!paymentline) {
    		if(this.get_pending())
    			var change = this.get_total_paid() - this.get_pending_amt();
    		else
    			var change = this.get_total_paid() - this.get_total_with_tax();
        } else {
        	if(this.get_pending())
        		var change = -this.get_pending_amt();
        	else
        		var change = -this.get_total_with_tax(); 
            var lines  = this.paymentlines.models;
            for (var i = 0; i < lines.length; i++) {
                change += lines[i].get_amount();
                if (lines[i] === paymentline) {
                    break;
                }
            }
        }
        return round_pr(Math.max(0,change), this.pos.currency.rounding);
    },
    get_due: function(paymentline) {
    	_super.get_due.apply(this,arguments);
    	if (!paymentline) {
    		if(this.get_pending())
    			var due = this.get_pending_amt() - this.get_total_paid();
    		else
    			var due = this.get_total_with_tax() - this.get_total_paid();
        } else {
        	if(this.get_pending())
    			var due = this.get_pending_amt();
    		else
    			var due = this.get_total_with_tax();
            var lines = this.paymentlines.models;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i] === paymentline) {
                    break;
                } else {
                    due -= lines[i].get_amount();
                }
            }
        }

    	return round_pr(Math.max(0,due), this.pos.currency.rounding);
    },
    export_as_JSON: function() {
    	var self =this;
        var json = _super.export_as_JSON.apply(this,arguments);
        json.is_pay_later =self.get_is_pay_later();
        return json;
    },
  });

var OrderReprintReceiptScreenWidget = screens.ScreenWidget.extend({
	   template: 'OrderReprintReceiptScreenWidget',
	   init: function(parent, options){
	       this._super(parent, options);
	   },
	   auto_back: true,
	   show: function(){
	   	var self = this;
	       this._super();
	       this.renderElement();
	       this.$('.back').click(function(){
	       	self.chrome.widget.order_selector.view_paylater_click_handler(this.event,$(this));
	       }); 
	       this.$('.order_reprint_next').click(function(){
	    	   self.pos.get_order().finalize();
	       }); 
	       /** Print receipt button*/
	       this.$('.button.reprintrec').click(function(){	        	
	       	var order_id = self.pos.get_order().get_is_reprint_order();//get order_id for reprint
		    	var to_print_orders = self.pos.get_order().print_orders;//get reprint order details
	       	self.print_receipt_xml(to_print_orders,order_id);
	       });
	   }, 
	   renderElement: function(){
	   	this._super();
	   	var self = this;
	   	if(self.pos.get_order()!=null)
	   	{
	   		var order_id = self.pos.get_order().get_is_reprint_order();//get order_id to reprint
	   		if(order_id){
	   			//get reprint order details
	   			self.order_receipt_reprint(order_id);
	   		}
	   	}
	   },
	   print_receipt_xml: function(to_print_orders,order_id){
	   	var self = this;
	   	var lines = [];
	       var payments = [];
	       var orders = [];
	       var discount = 0;
	   	if(to_print_orders)
	   	{
	   		var result = to_print_orders;
	   		lines = result[0];
	           orders = result[3];
	           payments = result[2];
	           discount = result[1];
	          	var receipt = QWeb.render('PosTicketReceipt',{
		 	        		widget:self,
		 	                orders: orders,
		 	                change: result[4],
		 	                orderlines: lines,
		 	                discount_total: discount,
		 	                paymentlines: payments,
		         });
	          	self.print(receipt);
	          	self.pos.get_order()._printed = true;	
	          	self.pos.get_order().set_is_reprint_order(order_id); //set order_id for reprint order
	       }
	   },
	   print: function(receipt){
	   	var self = this;
	   	 if (!self.pos.config.iface_print_via_proxy) 
	   	 {           		 
	       	window.print();
	   	 }
	        else
	        {
	       	 self.pos.proxy.print_receipt(receipt);// proxy (xml) printing
	        }	    	 	             
	   },
	   order_receipt_reprint: function(order_id){
	   	var self = this;
	   	if(order_id){
	   		 var lines = [];
	            var payments = [];
	            var orders = [];
	            var discount = 0;
	            self._rpc({
		                model: 'pos.order',
		                method: 'get_order_orderlines',
		                args: [order_id],
		            }).then(function(result) {	
		                 lines = result[0];
		                 orders = result[3];
		                 payments = result[2];
		                 discount = result[1];
		                // var print_orders = self.pos.get_order().set_print_orders(result);
		                 var data = {
		                		 widget:self,
			                     orders: orders,
			                     change: result[4],
			                     orderlines: lines,
			                     discount_total: discount,
			                     paymentlines: payments,
			                     balance: result[5],
		                     };
		                 self.$('.pos-receipt-container').html(QWeb.render('PosTicketReceipt', data));
		                     //var receipt = QWeb.render('OrderReceipt', data);
		                 /*self.$('.pos-receipt-container').html(QWeb.render('OrderReceipt',{
			                     widget:self,
			                     orders: orders,
			                     change: result[4],
			                     orderlines: lines,
			                     discount_total: discount,
			                     paymentlines: payments,
			                     balance: result[5],
			             }));*/
		                 //self.pos.get_order().set_is_reprint_order(order_id); //set order_id for reprint order
		            });	  
	   	}
	   },
	});
	gui.define_screen({name:'order_reprint_receipt', widget: OrderReprintReceiptScreenWidget});

screens.PaymentScreenWidget.include({
	template: 'PaymentScreenWidget',
	renderElement: function() {
        var self = this;
        var order = this.pos.get_order();
        this._super();

    },
    click_back: function() {
        // Placeholder method for ReceiptScreen extensions that
        // can go back ...
    	this._super();
    	var order = this.pos.get_order();
    	if(order.get_pending()){
    		order.set_is_pending(false);
    		this.gui.show_screen('paylater');
    	}
    },
    order_changes: function(){
    	this._super();
        var self = this;
        var order = this.pos.get_order();
        if(order){
	        if(order.get_pending()){
	        	if(this.pending_is_valid()){
	        		self.$('.next').addClass('highlight');
	        	}
	        }else{
	        	if (!order) {
		            return;
		        } else if (order.is_paid()) {
		            self.$('.next').addClass('highlight');
		        }else{
		            self.$('.next').removeClass('highlight');
		        }
	        }
        }else{
        	return;
        }
        
    },
	pending_is_valid: function() {
    	var self = this;
    	var order = this.pos.get_order();
    	var plines = order.get_paymentlines();
    	if(plines.length > 0){
    		for (var i = 0; i < plines.length; i++) {
	   			 if (plines[i].get_amount() <= 0) {
	   				 return false;
	   			 }
	    	}
	    	return true;
    	}else{
    		return false;
    	}
    },
    
    click_pending: function() {
    	var self = this;
    	var order = this.pos.get_order();
    	var invoice_id = order.p_invoice_id;
    	var invoice_amt = order.p_invoice_amt;
    	var porder_id = order.p_porder_id;
    	var payment_lines = order.paymentlines;
    	var porder_type = order.p_order_type;
    	var i = 0;
    	var paylines = [];
    	_.every(payment_lines.models, function(line){	
    		var lchange = self.pos.get_order().get_change(line)
    		return paylines.push({"amount":line.amount,"paymethod":line.payment_method,"name":line.name, "change":lchange});
    	});
    	/** Fetch Invoice Details **/
    	this._rpc({
            model: 'account.move',
            method: 'get_pending_invoice_details',
            args: [invoice_id,paylines,self.pos.pos_session.id],
        }).then(function (result) {
//	    		self.chrome.do_action('point_of_sale.pos_invoice_report',{additional_context:{ 
//                    active_ids:[porder_id],
//                }}).done(function () {
//                	$('.next').css("pointer-events", "auto"); //enable click action on validate button after complete.
//                	$('.paylater').trigger('click');
//                });
        	
        	
        	
        	
        	 self.chrome.do_action('point_of_sale.pos_invoice_report',{additional_context:{
                 active_ids:[porder_id],
             }}).then(function () {
            	 
                // resolveInvoiced(order_server_id);
                // resolveDone();
            		//$('.next').css("pointer-events", "auto"); //enable click action on validate button after complete.
                	//$('.paylater').trigger('click');
            	 	self.gui.show_screen('order_reprint_receipt');
             }).guardedCatch(function (error) {
                 rejectInvoiced({code:401, message:'Backend Invoice', data:{order: order}});
                 rejectDone();
             });
        	
        	
        	
        	
        	
        },function(err,event){
        	$('.next').css("pointer-events", "auto"); //enable click action on validate button after complete.
            event.preventDefault();
            var err_msg = 'Please check the Internet Connection.';
            if(err.data.message)
            	err_msg = err.data.message;
            self.gui.show_popup('alert',{
                'title': _t('Error: Could not get order details.'),
                'body': _t(err_msg),
            });
        });
    },
	 validate_order: function(force_validation) {
		    var order = this.pos.get_order();
	    	var plines = order.get_paymentlines();
	    	if(order.get_pending() == true){
	    		var client = order.get_client();
	    		if(!client){
        			this.gui.show_popup('confirm',{
        				'title': _t('Please select the Customer'),
        				'body': _t('You need to select the customer before you can proceed.'),
        				confirm: function(){
        					this.gui.show_screen('clientlist');
        				},
        			});
        			return false;
        		}
	    		else{
	    			if(this.pending_is_valid()){
	    				//$('.next').css("pointer-events", "none");// restrict to click once again.
		    			this.click_pending();
		    			order.set_is_pending(false);
		    		}
	    		}
	    		
	    	}else{
	    		var is_pending_invoice_id = order.p_invoice_id;
	    		if (is_pending_invoice_id==0) {
	                this._super(force_validation);
	                $('.PayLaterButton').css({"display":"none"});
	                $('.customerlog-button').css({"display":"none"});
	                $('.OrderListButton').css({"display":"none"});
	            }
	    	}
	    },
	
});

var PayLaterScreenWidget = screens.ScreenWidget.extend({
    template: 'PayLaterScreenWidget',

    init: function(parent, options){
        this._super(parent, options);
    },
    auto_back: true,
    show: function(){
        var self = this;
        this._super();      
        this.renderElement();
        this.old_client = this.pos.get_order().get_client();
        var order = self.pos.get_order();
    	var partner = order.get_client();   
    	this.$('.back').click(function(){
       	 self.gui.show_screen('products');
       });
    	self.render_order(self.get_data(),order); 
    	
    	$('.pendingpay').on('click',function(event){
        	//self.pos.proxy.open_cashbox();
        	// self.pos.printer.open_cashbox();
    		//self.pos.proxy.printer.open_cashbox();
    		//self.pos.proxy.printer.open_cashbox();
        	 order.set_is_pending(true);
        	 var tr = $(this).closest('tr');   	
 	    	 var invoice_id = tr.find('.pending_invoice_id').text();
 	    	 var amount = tr.find('.unpaid_amount').text();
 	    	 var porder_id = tr.find('.pending_porder_id').text();
 	    	 var porder_type = tr.find('.pending_order_type').text();
 	    	 order.set_pending_invoice(invoice_id);
 	    	 order.set_pending_amt(amount);
 	    	 order.set_pending_porder(porder_id);
 	    	 order.set_pending_order_type(porder_type);
        	 self.gui.show_screen('payment');
        });
    },
    renderElement: function(scrollbottom){
    	this._super();
    	var self = this;
    	 /**Floating icon action **/      
    },
    get_data: function(){
        return this.gui.get_current_screen_param('dldata');
    },
    render_order: function(result, order){
   	 // Renewal Details
   	 var lines = jQuery.extend(true, {}, order['orderlines']['models']);   		        
   	 //looping through each line  		
   	 var self = this;
   	 var current_session_id = this.pos.pos_session.id  
     var pending_invoices = result['pendinginvoice'];
   	 $('#pending_invoice_otable').bootstrapTable({
	            height: function() {
	                return $(window).height() - $('h1').outerHeight(true);
	            },
	            locale:'en-US',
	            columns: [{field: 'id', class: 'pending_invoice_id',title: 'ID',sortable: true,},
	             {field: 'sno', class: 'sno',title: 'S.no',sortable: true,},
	             {field: 'type',class:'pending_order_type',title: 'Order Type',visible: true,},
	             {field: 'porder_id',class:'pending_porder_id',title: 'Order ID',visible: true,},
	             {field: 'name',title: 'OrderRef', sortable: true,},
			     {field: 'invoice_ref',title: 'InvoiceRef',sortable: true,},
			     {field: 'date_invoice',title: 'InvoiceDate',sortable: true,
			    	 formatter: function(value, row, index) {						    			
			    			var momentObj = moment(value, 'YYYY/MM/DD');
			    			var momentString = momentObj.format('DD/MM/YYYY');			
			    			   return momentString;		   
			    		}
			     },
			     {field: 'amount_total',class: 'amount_total',title: 'InvoiceAmount',sortable: true,},
	             {field: 'unpaid_amount',class: 'unpaid_amount',title: 'UnPaidAmount', align: 'right',},
	             {field: 'unpaid_amount',title: '',align: 'right', 
			    	 formatter: function (value) {
			    		 if(value != '' && value > 0){
			    			 return '<a class="pendingpay"><span class="pay-button">Pay Now</span></a>';
			    		 }else{
			    			 return '';
			    		 }
			     }},
	            ],
	            data: pending_invoices,
	            pagination: true,
	            detailView: true,   
	      });
	      $('#pending_invoice_otable').on('expand-row.bs.table', function (e, index, row, $detail) {
		    		
	    		 var invoice_id = row.id;
	    		 
	    		 self._rpc({
	                 model: 'pos.order',
	                 method: 'fetch_invoice_lines',
	                 args: [invoice_id],
	             }).then(function (result) {
	            	 var rline_html = QWeb.render('PInvoiceLineScreenWidget',{widget: this, lines:result}); 		    			 
	    			   $detail.html(rline_html);
	             });
	      });
   },
});
gui.define_screen({name:'paylater', widget: PayLaterScreenWidget});

chrome.OrderSelectorWidget.include({
    template: 'OrderSelectorWidget',
    init: function(parent, options) {
        this._super(parent, options);
    },   
    view_paylater_click_handler: function(event, $el) {
    	var self = this;
    	var order = self.pos.get_order();
    	var partner = order.get_client();
    	 var lines = self.pos.get_order().get_paymentlines();
         for ( var i = 0; i < lines.length; i++ ) {
                self.pos.get_order().remove_paymentline(lines[i]);
         }
    	if(partner){
    		// Render Devotee Log Screen - Refresh screen on every click
            /** Fetch order detail from Server**/
    		this._rpc({
                model: 'pos.order',
                method: 'fetch_partner_order',
                args: [partner.id, self.pos.pos_session.id],
            }).then(function (result) {
            	self.gui.show_screen('paylater',{dldata:result},'refresh');
            },function(err,event){
  	            event.preventDefault();
  	            var err_msg = 'Please check the Internet Connection./n';
  	            if(err.data.message)
  	            	err_msg = err.data.message;
  	            self.gui.show_popup('alert',{
  	                'title': _t('Error: Could not get order details.'),
  	                'body': _t(err_msg),
  	            });
  	        });

    	}else{
    		 self.gui.show_popup('alert',{
                 'title': _t('Please select the Customer'), 
                 cancel: function(){
                	 self.gui.show_screen('clientlist');
                 }
                 
             });
    	}    	
    },
    renderElement: function(){
    	var self = this;
        this._super();
        /** Paylater Button click **/
        this.$('.paylater').click(function(event){
            self.view_paylater_click_handler(event,$(this));
        });
    },
  });
PaymentScreenWidget.include({
    template: 'PaymentScreenWidget',
    
    order_is_valid: function(force_validation) {
    	var self =this;
    	var order = self.pos.get_order();
    	var is_order_valid = this._super();
    	/**If entered 0.0 in payment line allows to validate the order.
    	 * While call super - check the condition- is_order_valid is true***/
    	if(is_order_valid){	    	
        var plines = order.get_paymentlines();
        for (var i = 0; i < plines.length; i++) {
        	var payment_name = plines[i].name;
        	//console.log("plines"+JSON.stringify(plines))
        	/**Check the customer for order only if pay later journal is used.**/
        	var line_payment_method = plines[i].payment_method;
        	//var is_paylaterline = line_payment_method.payment_method_id.is_pay_later;
        	var is_paylaterline = line_payment_method.is_pay_later;
        	if(is_paylaterline && plines[i].get_amount() > 0)
        	{ 	
        		var client = order.get_client();
        		if(!client){
        			this.gui.show_popup('confirm',{
        				'title': _t('Please select the Customer'),
        				'body': _t('You need to select the customer before you can proceed.'),
        				confirm: function(){
        					self.gui.show_screen('clientlist');
        				},
        			});
        			return false;
        		}else{
        			order.set_is_pay_later(true);
            	    order.set_to_invoice(true); // by default set create invoice for order is true if pay later journal is added in order.
        		}
        	}
            if (plines[i].get_payment_status() === 'bank' && plines[i].get_amount() < 0) {	
                this.gui.show_popup('error',{
                    'message': _t('Negative Bank Payment'),
                    'comment': _t('You cannot have a negative amount in a Bank payment. Use a cash payment method to return money to the customer.'),
                });
                return false;
            }
        }
        return true;
     }
    },
});
});