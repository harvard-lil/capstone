let min_year = 1640;
let max_year = (new Date()).getFullYear();

let levels = [3000, 2000, 1000, 500, 1];

let populateForYear = function(year) {
  for (let jur in jurisdiction_data) {
    let slug = jurisdiction_data[jur].slug;
    let total_for_year = data[year][jur];
    let id = "#US-" + slug;
    $(id).removeClass('level-0 level-1 level-2 level-3');
    // add name of jurisdiction and total for hover state
    $(id).html("<title>" + jurisdiction_data[jur].name_long + ": " + total_for_year + " cases</title>");
    for(var i=0; i<levels.length; i++) {
      if (total_for_year === 0) {
        continue;
      }
      if (total_for_year >= levels[i]) {
        $(id).addClass('level-'+ i);
        break;
      }
    }
  }
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

let populateLegend = function() {
  for(var i=0; i<levels.length; i++) {
    $('li.level-'+i).find('span.label').text(levels[i] + '+');
  }
};

$(function () {
  let year_input = $('#year-value');
  let first_year = 1880;
  populateLegend();
  // Initialize with min_year
  year_input.val(first_year);
  populateForYear(first_year);
  // On update input val, load pertinent data
  year_input.on('change', function() {
    updateForYear(this, year_input);
  });

  // // On state click, redirect to more details
  // $('.land-total').on('click', function() {
  //   window.location.href = this.id.split('US-')[1];
  // });
});