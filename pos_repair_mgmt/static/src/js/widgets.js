/* Copyright 2018 GRAP - Sylvain LE GAL
   Copyright 2018 Tecnativa - David Vidal
   Copyright 2019 Druidoo - Ivan Todorovich
   License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */

   odoo.define('pos_repair_mgmt.widgets', function(require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var chrome = require('point_of_sale.chrome');
    var pos = require('point_of_sale.models');
    var rpc = require('web.rpc');

    var QWeb = core.qweb;
    var ScreenWidget = screens.ScreenWidget;
    var DomCache = screens.DomCache;

    // screens.ReceiptScreenWidget.include({
    //     // render_receipt: function() {
    //     //     if (!this.pos.reloaded_order) {
    //     //         return this._super();
    //     //     }
    //     //     var order = this.pos.reloaded_order;
    //     //     this.$('.pos-receipt-container').html(QWeb.render('OrderReceipt', {
    //     //         widget: this,
    //     //         pos: this.pos,
    //     //         order: order,
    //     //         receipt: order.export_for_printing(),
    //     //         orderlines: order.get_orderlines(),
    //     //         paymentlines: order.get_paymentlines(),
    //     //     }));
    //     //     this.pos.from_loaded_order = true;
    //     // },
    //     // click_next: function() {
    //     //     if (!this.pos.from_loaded_order) {
    //     //         return this._super();
    //     //     }
    //     //     this.pos.from_loaded_order = false;
    //     //     // When reprinting a loaded order we temporarily set it as the
    //     //     // active one. When we get out from the printing screen, we set
    //     //     // it back to the one that was active
    //     //     if (this.pos.current_order) {
    //     //         this.pos.set_order(this.pos.current_order);
    //     //         this.pos.current_order = false;
    //     //     }

    //     //     return this.gui.show_screen(this.gui.startup_screen);
    //     // },
    // });
    
    var RepairListScreenWidget = ScreenWidget.extend({
        template: 'RepairListScreenWidget',

        init: function(parent, options) {
            this._super(parent, options);
            this.repair_cache = new DomCache();
            this.repairs = [];
            this.unknown_products = [];
            this.search_query = false;
            this.perform_search();
        },


        auto_back: true,

        show: function() {
            var self = this;
            var previous_screen = false;
            // if (this.pos.get_order()) {
            //     previous_screen = this.pos.get_order().get_screen_data(
            //         'previous-screen');
            // }
            if (previous_screen === 'receipt') {
                this.gui.screen_instances.receipt.click_next();
                this.gui.show_screen('repairlist');
            }
            this._super();
            this.renderElement();
            this.old_order = this.pos.get_order();
            this.$('.back').click(function() {
                return self.gui.show_screen(self.gui.startup_screen);
            });

            if (this.pos.config.iface_vkeyboard &&
                this.chrome.widget.keyboard) {
                this.chrome.widget.keyboard.connect(
                    this.$('.searchbox input'));
            }

            var search_timeout = null;
            this.$('.searchbox input').on('keyup', function() {
                self.search_query = this.value;
                clearTimeout(search_timeout);
                search_timeout = setTimeout(function() {
                    self.perform_search();
                }, 70);
            });

            this.$('.searchbox .search-clear').click(function() {
                self.clear_search();
            });

            this.perform_search();
        },

        render_list: function() {

            var self = this;
            var repairs = this.repairs;

            var contents = this.$el[0].querySelector('.repair-list-contents');
            contents.innerHTML = "";
            for (
                var i = 0, len = Math.min(repairs.length, 1000); i < len; i++
            ) {
                var repair = repairs[i];
                var repairline = this.repair_cache.get_node(
                    repair.id || repair.uid);
                if (!repairline) {
                    var repairline_html = QWeb.render('RepairLine', {
                        widget: this,
                        repair: repair,
                    });
                    repairline = document.createElement('tbody');
                    repairline.innerHTML = repairline_html;
                    repairline = repairline.childNodes[1];
                    this.repair_cache.cache_node(
                        repair.id || repair.uid, repairline);
                }
                if (repair === this.old_repair) {
                    repairline.classList.add('highlight');
                } else {
                    repairline.classList.remove('highlight');
                }
                contents.appendChild(repairline);
            }
            // FIXME: Everytime the list is rendered we need to reassing the
            // button events.

            // this.$('.order-list-return').off('click');
            // this.$('.order-list-reprint').off('click');
            this.$('.order-list-copy').off('click');
            // this.$('.order-list-reprint').click(function(event) {
            //     self.order_list_actions(event, 'print');
            // });
            this.$('.order-list-copy').click(function(event) {
                self.order_list_actions(event, 'copy');
            });
            // this.$('.order-list-return').click(function(event) {
            //     self.order_list_actions(event, 'return');
            // });
        },

        order_list_actions: function(event, action) {
            var self = this;
            var dataset = event.target.parentNode.dataset;
            self.load_repair_data(parseInt(dataset.orderId, 10))
                .then(function(repair_data) {
                    self.order_action(repair_data, action);
                });
        },

        order_action: function(repair_data, action) {
            // if (this.old_order !== null) {
            //     this.gui.back();
            // }
            var repair = this.load_repair_from_data(repair_data, action);
            if (!repair) {
                // The load of the order failed. (products not found, ...
                // We cancel the action
                return;
            }
            this['action_' + action](repair_data, repair);
        },

        // action_print: function(order_data, order) {
        //     // We store temporarily the current order so we can safely compute
        //     // taxes based on fiscal position
        //     this.pos.current_order = this.pos.get_order();

        //     this.pos.set_order(order);

        //     if (this.pos.config.iface_print_via_proxy) {
        //         this.pos.proxy.print_receipt(QWeb.render(
        //             'OrderReceipt', {
        //                 widget: this,
        //                 pos: this.pos,
        //                 order: order,
        //                 receipt: order.export_for_printing(),
        //                 orderlines: order.get_orderlines(),
        //                 paymentlinesf: order.get_paymentlines(),
        //             }));
        //         this.pos.set_order(this.pos.current_order);
        //         this.pos.current_order = false;
        //     } else {
        //         this.pos.reloaded_order = order;
        //         this.gui.show_screen('receipt');
        //         this.pos.reloaded_order = false;
        //     }

        //     // If it's invoiced, we also print the invoice
        //     if (order_data.to_invoice) {
        //         this.pos.chrome.do_action('point_of_sale.pos_invoice_report', {
        //             additional_context: { 
        //                 active_ids: [order_data.id] 
        //             }
        //         })
        //     }

        //     // Destroy the order so it's removed from localStorage
        //     // Otherwise it will stay there and reappear on browser refresh
        //     order.destroy();
        // },

        action_copy: function(repair_data, repair) {
            repair.trigger('change');
            this.pos.get('orders').add(repair);
            this.pos.set('selectedOrder', repair);
            return repair;
        },

        // action_return: function(order_data, order) {
        //     order.trigger('change');
        //     this.pos.get('orders').add(order);
        //     this.pos.set('selectedOrder', order);
        //     return order;
        // },

        _prepare_repair_from_repair_data: function(repair_data, action) {
            var self = this;
            var repair = new pos.Order({}, {
                pos: this.pos,
            });

            
            // console.log('_prepare_repair_from_repair_data');
            // console.log(repair)
            // console.log(repair_data);

            // Article à réparer
            if (repair_data.product_repair){
                repair['product_repair'] = repair_data.product_repair;
            }

            // Bon de réparation
            if (repair_data.repair_order){
                repair['repair_order'] = repair_data.repair_order;
            }

            // Numéro de série du téléphone
            if(repair_data.serial_number){
                repair['serial_number'] = repair_data.serial_number;
            }

            // Appareil déposé
            if(repair_data.device_dropped){
                repair['device_dropped'] = repair_data.device_dropped;
            }

            // Get Customer
            if (repair_data.partner_id) {
                repair.set_client(
                    this.pos.db.get_partner_by_id(repair_data.partner_id));
            }

            // Get fiscal position
            if (repair_data.fiscal_position && this.pos.fiscal_positions) {
                var fiscal_positions = this.pos.fiscal_positions;
                repair.fiscal_position = fiscal_positions.filter(function(p) {
                    return p.id === repair_data.fiscal_position;
                })[0];
                repair.trigger('change');
            }

            // Get repair lines
            self._prepare_repairlines_from_repair_data(
                repair, repair_data, action);

            // Get Name
            // if (['print'].indexOf(action) !== -1) {
            //     repair.name = repair_data.pos_reference;
            // } else if (['return'].indexOf(action) !== -1) {
            //     repair.name = _t("Refund ") + repair.uid;
            // }

            // Get to invoice
            if (['return', 'copy'].indexOf(action) !== -1) {
                // If previous order was invoiced, we need a refund too
                repair.set_to_invoice(repair_data.to_invoice);
            }

            // Get returned Repair
            // if (['print'].indexOf(action) !== -1) {
            //     // Get the same value as the original
            //     repair.returned_order_id = order_data.returned_order_id;
            //     order.returned_order_reference =
            //     order_data.returned_order_reference;
            // } else if (['return'].indexOf(action) !== -1) {
            //     order.returned_order_id = order_data.id;
            //     order.returned_order_reference = order_data.pos_reference;
            // }

            // // Get Date
            // if (['print'].indexOf(action) !== -1) {
            //     order.formatted_validation_date =
            //     moment(order_data.date_order).format('YYYY-MM-DD HH:mm:ss');
            // }

            // // Get Payment lines
            // if (['print'].indexOf(action) !== -1) {
            //     var paymentLines = order_data.payment_lines || [];
            //     _.each(paymentLines, function(paymentLine) {
            //         var line = paymentLine;
            //         // In case of local data
            //         if (line.length === 3) {
            //             line = line[2];
            //         }
            //         _.each(self.pos.payment_methods, function(payment_method) {
            //             if (payment_method.id === line.payment_method_id) {
            //                 if (line.amount > 0) {
            //                     // If it is not change
            //                     order.add_paymentline(payment_method);
            //                     order.selected_paymentline.set_amount(
            //                         line.amount);
            //                 }
            //             }
            //         });
            //     });
            // }

            return repair;
        },

        _prepare_repairlines_from_repair_data: function(
            repair, repair_data, action) {
            var repairLines = repair_data.line_ids || repair_data.lines || [];

            // console.log('*** 3 ***');
            // console.log(repair);
            // console.log(repair_data);
            
            var self = this;

            rpc.query({
                model: 'product.product',
                method: 'search_product_advance_payment',
                args: [1],
            }).then(function(result){

                var product = self.pos.db.get_product_by_id(result);

                if(product)
                var obj = {
                    'product_id':product.id,
                    'discount':0,
                    'price_unit':1,
                    'qty':1,
                }
                for (var line of repairLines){

                    var product_id = self.pos.db.get_product_by_id(line.product_id);
                    if(product_id.radio_advance_mgmt == 'left_to_pay'){
                        // Remplace le prix par le montant du solde restant
                        obj['price_unit'] = line.price_unit;
                        var index = repairLines.indexOf(line);
                        // Supprime la ligne du solde restant dans l'array repairLines
                        repairLines.splice(index,1);
                    }
                }
                repairLines.push(obj);

                _.each(repairLines, function(repairLine) {
                    var line = repairLine;
                    
                    // Total de la commande avec TVA
                    var get_total_with_tax = self.pos.get_order().get_total_with_tax();

                    if (line.length === 3) {
                        line = line[2];
                    }
                    var product = self.pos.db.get_product_by_id(line.product_id);


                    if(product.radio_advance_mgmt == 'advance_payment'){
                        // Calcul du prix de l'acompte
                        line['price_unit'] = -(get_total_with_tax + line.price_unit);
                    } 
                
    
                    // Check if product are available in pos
                    if (_.isUndefined(product)) {
                        self.unknown_products.push(String(line.product_id));
                    } else {
                        var qty = line.qty;
                        if (['return'].indexOf(action) !== -1) {
                            // Invert line quantities
                            qty *= -1;
                        }
                        // Create a new order line
                        repair.add_product(product, {
                            price: line.price_unit,
                            quantity: qty,
                            discount: line.discount,
                            merge: false,
                        });
                    }
                });
                // console.log(repair);
                // Changement de statut "price_manually_set" sinon modification du prix après un CHANGE
                for (var orderline of repair.get_orderlines()) {
                    var product_id = orderline.product.id
                    // console.log(product_id);
                    if (product_id == result) {
                        
                        orderline['price_manually_set'] = true;
                    }
                }
            });
            // console.log('*** 4 ***');
            // console.log(repair);
                        
        },

        load_repair_data: function(repair_id) {
            var self = this;
            return this._rpc({
                model: 'repair.order',
                method: 'load_done_repair_for_pos',
                args: [repair_id],
            }).guardedCatch(function(reason) {
                if (parseInt(reason.message.code, 10) === 200) {
                    // Business Logic Error, not a connection problem
                    self.gui.show_popup(
                        'error-traceback', {
                            'title': error.data.message,
                            'body': error.data.debug,
                        }
                    );
                } else {
                    self.gui.show_popup('error', {
                        'title': _t('Connection error'),
                        'body': _t(
                            'Can not execute this action because the POS' +
                            ' is currently offline'),
                    });
                }
            });
        },

        load_repair_from_data: function(repair_data, action) {
            var self = this;
            this.unknown_products = [];
            var repair = self._prepare_repair_from_repair_data(
                repair_data, action);
            // Forbid POS Order loading if some products are unknown
            if (self.unknown_products.length > 0) {
                self.gui.show_popup('error-traceback', {
                    'title': _t('Unknown Products'),
                    'body': _t('Unable to load some order lines because the ' +
                        'products are not available in the POS cache.\n\n' +
                        'Please check that lines :\n\n  * ') +
                    self.unknown_products.join("; \n  *"),
                });
                return false;
            }
            return repair;
        },

        // Search Part
       
        search_done_orders: function(query) {
            var self = this;
            return this._rpc({
                model: 'repair.order',
                method: 'search_done_orders_for_pos',
                args: [query || '', this.pos.pos_session.id],
            }).then(function(result) {
                self.repairs = result;
                // Get the date in local time
                _.each(self.repairs, function(repair) {
                    if (repair.date_orderactivity_date_deadline) {
                        repair.activity_date_deadline = moment.utc(repair.activity_date_deadline)
                            .local().format('YYYY-MM-DD HH:mm:ss');
                    }
                });
            }).guardedCatch(function(reason) {
                if (parseInt(reason.message.code, 10) === 200) {
                    // Business Logic Error, not a connection problem
                    self.gui.show_popup(
                        'error-traceback', {
                            'title': error.data.message,
                            'body': error.data.debug,
                        }
                    );
                } else {
                    self.gui.show_popup('error', {
                        'title': _t('Connection error'),
                        'body': _t(
                            'Can not execute this action because the POS' +
                            ' is currently offline'),
                    });
                }
                reason.event.preventDefault();
            });
        },

        perform_search: function() {
            var self = this;
            return this.search_done_orders(self.search_query)
                .then(function() {
                    self.render_list();
                });
        },

        clear_search: function() {
            var self = this;
            self.$('.searchbox input')[0].value = '';
            self.$('.searchbox input').focus();
            self.search_query = false;
            self.perform_search();
        },
    });
    
    gui.define_screen({
        name: 'repairlist',
        widget: RepairListScreenWidget,
    });

    var ListRepairButtonWidget = PosBaseWidget.extend({
        template: 'ListRepairButtonWidget',
        init: function(parent, options) {
            var opts = options || {};
            this._super(parent, opts);
            this.action = opts.action;
            this.label = opts.label;
        },

        button_click: function() {
            this.gui.show_screen('repairlist');
        },

        renderElement: function() {
            var self = this;
            this._super();
            this.$el.click(function() {
                self.button_click();
            });
        },
    });

    var widgets = chrome.Chrome.prototype.widgets;
    widgets.push({
        'name': 'list_repairs',
        'widget': ListRepairButtonWidget,
        'prepend': '.pos-rightheader',
        'args': {
            'label': 'All Repairs',
        },
    });

    return {
        ListRepairButtonWidget: ListRepairButtonWidget,
        RepairListScreenWidget: RepairListScreenWidget,
    };

});