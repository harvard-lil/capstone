let populateForYear = function(year) {
  for (let jur in jurisdiction_data) {
    let slug = jurisdiction_data[jur].slug;
    let total_for_year = case_count[jur][year];
    let id = "#US-" + slug;
    $(id).removeClass('level-1', 'level-2', 'level-3', 'level-4', 'level-5');
    if (total_for_year > 50000) {
      $(id).addClass('level-1');

      console.log("total_for_year level-1:::", total_for_year, year)
    } else if (total_for_year > 3000) {
      $(id).addClass('level-2');
      console.log("total_for_year level-2:::", total_for_year, year)
    } else if (total_for_year > 100) {
      $(id).addClass('level-3');
      console.log("total_for_year level-3:::", total_for_year, year)
    } else if (total_for_year >= 0) {
      $(id).addClass('level-4');
      console.log("total_for_year level-4:::", total_for_year, year)
    } else {
      $(id).addClass('level-5');
      console.log("total_for_year level-5:::", total_for_year, year)
    }

  }
};

$(function(){
  let slider = document.getElementById('slider');
  noUiSlider.create(slider, {
    start: 1600,
    range: {
        min: 1600,
        max: 2018
    },

  });


  slider.noUiSlider.on('update', function ( ) {
    let year = Math.floor(slider.noUiSlider.get());
    console.log('updating for year', year);
    populateForYear(year);
  });

  for (let jur in jurisdiction_data) {
    let slug = jurisdiction_data[jur].slug;
    let total = case_count[jur]['total'];
    let id = "#US-" + slug;
    $(id).on('click', function() {
      console.log('redirecting to', slug);
    });
    if (total > 100000) {
      $(id).addClass('level-1');
    } else if (total > 80000 && total < 100000) {
      $(id).addClass('level-2');
    } else if (total > 60000 && total < 80000) {
      $(id).addClass('level-3');
    } else if (total > 30000 && total < 60000) {
      $(id).addClass('level-4');
    } else if (total < 30000) {
      $(id).addClass('level-5');
    }
  }

});