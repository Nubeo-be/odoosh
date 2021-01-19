odoo.define('pos_mrp_order.models_mrp_order', function (require) {
    "use strict";
    var pos_model = require('point_of_sale.models');
    var pos_screens = require('point_of_sale.screens');
    var models = pos_model.PosModel.prototype.models;
    var core = require('web.core');
    var gui = require('point_of_sale.gui');
    var _t = core._t;
    var rpc = require('web.rpc');
    
    
    for(var i=0; i<models.length; i++){
        var model=models[i];
            if(model.model === 'product.product'){
                model.fields.push('to_make_repair');
    
            }
    }

    pos_screens.PaymentScreenWidget.include({
            validate_order: function(force_validation) {
                var self = this
                
                var order = self.pos.get_order();

                var partner_id = order.get_client();

                var order_line = order.orderlines.models;            
                var due = order.get_due();
                for (var i in order_line)
                {
                    var list_product = [];
                    if (order_line[i].product.to_make_repair)
                    {
                        if (order_line[i].quantity>0)
                        {
                            if (partner_id != null){
                                var product_dict = {
                                    'id': order_line[i].product.id,
                                    'qty': order_line[i].quantity,
                                    'product_tmpl_id': order_line[i].product.product_tmpl_id,
                                    'pos_reference_bis': order.name,
                                    'uom_id': order_line[i].product.uom_id[0],
                                    // 'partner_id': order.attributes.client.id,
                                    'partner_id': partner_id.id,
                                    'discount': order_line[i].discount,
                                };
                                list_product.push(product_dict);
                                
                            } else{
                                this.gui.show_popup('error',{
                                    title: _t('Problème de validation'),
                                    body:  _t('Veuillez encoder un client'),
                                });
                            }
                        }
                    }
    
                    this._super(force_validation);

                }
    
            },
    
        });
    });
    