let min_year = 1640;
let max_year = (new Date()).getFullYear();

//max cases seems to be 10,000
let max_cases = 10000;
let no_color = "rgb(255, 255, 255)";
let min_color = "rgb(210, 231, 255)";
let max_color = "rgb(34, 52, 154)";

let populateForYear = function(year) {
  for (let jur in jurisdiction_data) {
    let slug = jurisdiction_data[jur].slug;
    let total_for_year = data[year][jur];
    let id = "#US-" + slug;
    console.log("populateForYear", year, slug, jur, total_for_year);
    // add name of jurisdiction and total for hover state
    $(id).html("<title>" + jurisdiction_data[jur].name_long + ": " + total_for_year + " cases</title>");
    if (total_for_year === 0) {
      colorSVG(id, no_color);
      return
    }
    let percentStep = total_for_year > max_cases ? 1 : total_for_year/max_cases
    let color = pSBC(percentStep, min_color, max_color);
    colorSVG(id, color);
  }
};

let colorSVG = function(id, color) {
  $(id).css('fill', color);
};

let updateForYear = function(el, year_input_el) {
  let chosen_year = el.value;
  if (chosen_year > max_year || chosen_year === '') {
    year_input_el.val(max_year);
  } else if (chosen_year < min_year) {
    year_input_el.val(min_year);
  }
  populateForYear(el.value);
};


let goToDetailsView = function(element) {
  let id = element.id;
  let slug = id.split("US-")[1];
  window.location.href = "/data/details?slug=" + slug;
};

$(function () {
  let year_input = $('#year-value');
  let first_year = 1880;
  let states = $('polygon.land-total');
  states.on('click', function() {
    goToDetailsView(this);
  });
  // Initialize with min_year
  year_input.val(first_year);
  populateForYear(first_year);
  // On update input val, load pertinent data
  year_input.on('change', function() {
    updateForYear(this, year_input);
  });
});
