$(function() {
  $(".a-item").click(function() {
    var id = $(this).attr('id').split('jurisdiction-item-')[1];
    var slug;
    if (id === 'totals') {
      slug = 'totals';
    } else {
      slug = jurisdiction_data[id].slug;
    }
    populateCaseChart(id);
    populateJurisdictionData(this, name, id, slug);
  });

  // on load, display totals
  $('#jurisdiction-item-totals').click();
});

var populateJurisdictionData = function(el, name, id, slug) {
  // on click in long jurisdiction list
  // show reporter, court, case totals
  $(el).toggleClass('active');
  $(".land").removeClass('active');
  if (slug === 'totals') {
    $('#US-all').toggleClass('active');
  } else {
    $("#US-" + slug).toggleClass('active');
  }

  $('h5.selected-jurisdiction').text(name);
  if (id === 'totals') {
    $('#court-count').text(court_count['total']);
  } else {
    $('#court-count').text(court_count[id]);
  }

  if (id in reporter_count) {
    $('#reporter-count').text(reporter_count[id]['total']);
    $('#volume-count').text(reporter_count[id]['volume_count']);
  }
  if (id in case_count) {
    $('#case-count').text(case_count[id]['total']);
  }
};

var populateCaseChart = function (id) {
  if (!(id in case_count)) {
    return
  }
  var years = Object.keys(case_count[id]);
  if (years[years.length-1] === 'total') {
    years.pop();
  }
  var caseNumber = Object.values(case_count[id]);
  if (caseNumber[caseNumber.length-1] === 'total') {
    caseNumber.pop();
  }

  var ctx = document.getElementById("caseChart").getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: years,
      datasets: [{
          label: 'Number of Cases',
          data: caseNumber,
          borderWidth: 1
      }]
    },
    options: {
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero: true
          }
        }]
      }
    }
  });
};

