odoo.define('pos_advance_payment.pos', function(require) {
    "use strict"

    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var chrome = require('point_of_sale.chrome');
    var core = require('web.core');
    var gui = require('point_of_sale.gui');
    var popups = require('point_of_sale.popups');
    var rpc = require('web.rpc');  
    var QWeb = core.qwed;
    var _t = core._t;
    var pos_model = models.PosModel.prototype.models;

    var PosBaseWidget = require('point_of_sale.BaseWidget');

    for(var i=0; i<pos_model.length; i++){
        var model=pos_model[i];
            if(model.model === 'product.product'){
                model.fields.push('radio_advance_mgmt');
            }
    }


    var AdvancePaiementButtonWidget = PosBaseWidget.extend({
        template: 'AdvancePaiementButtonWidget',
        init: function(parent, options) {
            var opts = options || {};
            this._super(parent, opts);
            this.action = opts.action;
            this.label = opts.label;
        },

        button_click: function() {
            this.gui.show_popup('add-advance-payment-popup');
        },

        renderElement: function() {
            var self = this;
            this._super();
            this.$el.click(function() {
                self.button_click();
            });
        },
    });

    

    var AddRepairAdvancePaymentPopup = popups.extend({
        template: 'AddRepairAdvancePaymentPopup',
        init: function(parent, args){
            this._super(parent, args);
            this.options = {};
        },
        show: function(options) {
            options = options || {};
            var self = this;
            this._super(options);
            this.partner = options.partner || [];
            this.renderElement();
        },

        renderElement: function() {
            var self = this;
            this._super();
            var partner = this.partner;
            // var that = this;

            this.$('#device_dropped').change(function()
            {
                // if(this.checked != true)
                // {
                //     console.log('checked');
                // }
                // console.log($("#device_dropped").prop('checked'));
                var checked = $("#device_dropped").prop('checked');
                console.log(checked)
                if (checked == true){
                    $("#emplacement").removeClass('invisible');
                } else {
                    $("#emplacement").addClass('invisible');
                }
            }
            );
            


            this.$('#create_advance_payment').click(function(){
                
                console.log('renderElement');

                // Field : Produit à réparer
                var product_repair = $("#product_repair").val();
                self.pos.get_order()['product_repair'] = product_repair;
                console.log(product_repair)

                // Field : Acompte
                var advance_payment = $("#advance_payment").val();

                // Field : Numéro de série
                var serial_number = $("#serial_number").val();
                self.pos.get_order()['serial_number'] = serial_number;

                // Field : Appareil déposé
                var device_dropped = $("#device_dropped").prop('checked')
                self.pos.get_order()['device_dropped'] = device_dropped;

                console.log(device_dropped);



                advance_payment = parseFloat(advance_payment);

                var get_total_with_tax = self.pos.get_order().get_total_with_tax();
                

                
                
                var price = advance_payment - get_total_with_tax;
                // console.log(price);
                
                rpc.query({
                    model: 'product.product',
                    method: 'search_template_id',
                    args: [1],
                }).then(function(result){
                    // Produit = Acompte
                    var product = self.pos.db.get_product_by_id(result);
                    // console.log('product : '+ product);
                    // Ajout du produit dans les orderlines
                    self.pos.get_order().add_product(product, {price:price});
                    var orderlines = self.pos.get_order().get_orderlines();
                    // console.log(orderlines);

                    // Liste des articles
                    for (var orderline of orderlines) {
                        var product_id = orderline.product.id
                        if (product_id == result) {
                            // changement de statut sinon modification du prix après un change
                            orderline['price_manually_set'] = true;
                        }
                    }
                    
                });
            });
        },
    });

    gui.define_popup({
		name: 'add-advance-payment-popup',
		widget: AddRepairAdvancePaymentPopup
	});

    var widgets = chrome.Chrome.prototype.widgets;
    widgets.push({
        'name': 'sa_lut',
        'widget': AdvancePaiementButtonWidget,
        'prepend': '.pos-rightheader',
        'args': {
            'label': 'Salut',
        },
    });

    return {
        AdvancePaiementButtonWidget: AdvancePaiementButtonWidget,
    };
    
    
})