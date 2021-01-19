/* Copyright 2018 Tecnativa - David Vidal
   License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */

odoo.define('pos_repair_mgmt.models', function (require) {
    'use strict';

    var models = require('point_of_sale.models');

    var order_super = models.Order.prototype;

    models.Order = models.Order.extend({
        init_from_JSON: function (json) {
            order_super.init_from_JSON.apply(this, arguments);
            // console.log(json);
            this.repair_order = false;
            // console.log(this.repair_order);
            this.serial_number = false;
            this.device_dropped = false;
            this.product_repair = false;
        },
        export_as_JSON: function () {
            var res = order_super.export_as_JSON.apply(this, arguments);
            res.repair_order = this.repair_order ? this.repair_order : false;
            res.serial_number = this.serial_number ? this.serial_number : false;
            res.device_dropped = this.device_dropped ? this.device_dropped : false;
            res.product_repair = this.product_repair ? this.product_repair : false;
            // console.log(res)
            return res;
        },
    });

});
