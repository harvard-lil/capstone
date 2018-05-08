$(function() {
  $(".a-item").click(function() {
    var id = $(this).attr('id').split('jurisdiction-item-')[1];
    populateCaseChart(id);
    populateJurisdictionData(this, name, id);
  });
});

var populateJurisdictionData = function(el, name, id) {
  // on click in long jurisdiction list
  // show reporter, court, case totals
  $(el).toggleClass('active');
  $(".land").removeClass('active');
  $("#US-" + id).toggleClass('active');

  $('h5.selected-jurisdiction').text(name);
  if (id === 'totals') {
    $('#reporter-count').text(reporter_count[id]['total']);
    $('#court-count').text(court_count['total']);
  } else {
    $('#reporter-count').text(reporter_count[id]);
    $('#court-count').text(court_count[id]);
  }
  $('#volume-count').text(reporter_count[id]['volume_count']);
  $('#case-count').text(case_count[id]['total']);
};

var populateCaseChart = function (id) {
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

