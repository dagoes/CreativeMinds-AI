odoo.define("creativeminds_ai.script", function (require) {
  "use strict";

  var core = require("web.core");
  var config = require("web.config");
  var session = require("web.session");
  var utils = require("web.utils");

  $(document).ready(function () {
    // Selector del elemento que representa el módulo CreativeMinds AI
    var creativeMindsAI = $(
      '.o_main_navbar [data-menu-xmlid^="creativeminds_ai"]'
    );

    if (creativeMindsAI.length) {
      creativeMindsAI.on("click", function () {
        // Añade la clase 'o_active_creative_minds' al body cuando se hace clic en el módulo
        $("body").addClass("o_active_creative_minds");
      });

      // Quita la clase 'o_active_creative_minds' al hacer clic fuera del módulo
      $(document).on("click", function (event) {
        if (
          !creativeMindsAI.is(event.target) &&
          !creativeMindsAI.has(event.target).length
        ) {
          $("body").removeClass("o_active_creative_minds");
        }
      });
    }
  });
});
