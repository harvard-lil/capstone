$(function() {
  $(".a-item").click(function() {
    var id = $(this).attr('id').split('jurisdiction-item-')[1];
    if (id === 'total') {
      // populateTotalData();
      populateCaseChart();
    }
    // var name = results[id].name_long;
    populateJurisdictionData(this, name, id);
    populateCaseChart(id);
  });
});

var populateJurisdictionData = function(el, name, id) {
  // on click in long jurisdiction list
  // show reporter, court, case totals
  $(el).toggleClass('active');
  $(".land").removeClass('active');
  $("#US-" + id).toggleClass('active');

  $('h5.selected-jurisdiction').text(name);

  $('#reporter-count').text(reporter_count[id]['count']);
  $('#volume-count').text(reporter_count[id]['volume_count']);
  $('#court-count').text(court_count[id]);
  $('#case-count').text(case_count[id]['total']);
};

var populateCaseChart = function (id) {
  var years = Object.keys(case_count[id]);
  years.pop();
  var caseNumber = Object.values(case_count[id]);
  caseNumber.pop();
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

