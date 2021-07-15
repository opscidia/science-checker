function get_id(clicked_id) {
    Shiny.setInputValue("report_id", clicked_id, {priority: "event"});
}

$(function () {
  $('[data-toggle="popover"]').popover({
    container: "body",
      html: true,
      content: function () {
        return '<div class="popover-message">' + $(this).data("message") + '</div>';
      }
  });
});


$(function () {
  $('.details > div:has(.d-none)').addClass('d-none');
});