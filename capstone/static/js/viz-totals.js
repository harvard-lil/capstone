let min_year = 1640;
let max_year = (new Date()).getFullYear();

let populateForYear = function(year) {
  for (let jur in jurisdiction_data) {
    let slug = jurisdiction_data[jur].slug;
    let total_for_year = data[year][jur];
    let id = "#US-" + slug;
    $(id).removeClass('level-1 level-2 level-3 level-4');
    if (total_for_year > 50000) {
      $(id).addClass('level-1');
    } else if (total_for_year > 3000) {
      $(id).addClass('level-2');
    } else if (total_for_year > 2) {
      $(id).addClass('level-3');
    } else if (total_for_year > 0) {
      $(id).addClass('level-4');
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

$(function () {
  let year_input = $('#year-value');
  // Initialize with min_year
  year_input.val(min_year);
  populateForYear(min_year);
  // On update input val, load pertinent data
  year_input.on('change', function() {
    updateForYear(this, year_input);
  });

  // // On state click, redirect to more details
  // $('.land-total').on('click', function() {
  //   window.location.href = this.id.split('US-')[1];
  // });
});