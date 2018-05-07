$(function() {
  $(".a-item").click(function() {
    var slug = this.href.split('#')[1];
    var name = results[slug].name_long;
    populateJurisdictionData(this, name, slug);
    populateChart(slug);
  });
});

var populateJurisdictionData = function(el, name, slug) {
  // on click in long jurisdiction list
  // show reporter, court, case totals
  $(el).toggleClass('active');
  $(".land").removeClass('active');
  $("#US-" + slug).toggleClass('active');

  $('h5.selected-jurisdiction').text(name);
  $('#reporter-count').text(results[slug]['reporters']['count']);
  $('#court-count').text(results[slug]['courts']);
  $('#case-count').text(results[slug]['cases']['total']);
};

var populateChart = function (slug) {
  var years = Object.keys(results[slug]['cases']);
  years.pop();
  var caseNumber = Object.values(results[slug]['cases']);
  caseNumber.pop();
  var ctx = document.getElementById("myChart").getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: years,
      datasets: [{
          label: '# of Cases',
          data: caseNumber,
          borderWidth: 1
      }]
    },
    options: {
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero:true
          }
        }]
      }
    }
  });

};

