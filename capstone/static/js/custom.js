let setupDropdown = function () {
    let dropdown = ".dropdown";
    $(dropdown).click(function(e) {
        let showingDropdown = $(this).hasClass("show");
        $(dropdown).removeClass("show");
        showingDropdown ? $(this).removeClass("show") : $(this).addClass("show");

        e.stopPropagation();
    });

    $(document).click(function(){
      $(dropdown).removeClass("show");
    });
};

let setupBurgerAction = function() {
  $("#burger-icon").click(function() {
    this.classList.toggle("transform");
  });
};

$(function() {
    setupDropdown();
    setupBurgerAction();
});