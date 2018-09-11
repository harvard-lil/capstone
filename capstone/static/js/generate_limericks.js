function generate_limerick(){
    return $.getJSON("/static/js/limerick_lines.json")
      .then(function(json) {
        let line_types = json;

        let long_lines = get_lines(line_types['long'], 3);
        let short_lines = get_lines(line_types['short'], 2);
        let limerick = [
            long_lines[0],
            long_lines[1],
            short_lines[0],
            short_lines[1],
            long_lines[2]];
        return limerick;
      })
        .fail(function(){
          console.log('failed');
        });
}

function get_lines(emphasis_patterns, count){
  let last_syllables = dict_random_choice(emphasis_patterns);
  let last_tokens = dict_random_choice(last_syllables);
  let line_sets = dict_random_sample(last_tokens, count);
  let lines = [];
  for(k in line_sets){
    let index = Math.floor(Math.random() * (line_sets[k].length));
    let line = format_line(line_sets[k][index]);
    lines.push(line);
  }
  return lines;
}


function format_line(line) {
  return line;
}

function dict_random_choice(population) {
    let keys = Object.keys(population)
    let max = keys.length;
    // creating random choice key
    let index = Math.floor(Math.random() * max);
    let key = keys[index];
    return population[key];
}

function dict_random_sample(population, size){
    let arr = Object.keys(population);
    let shuffled = arr.slice(0),
        i = arr.length,
        temp,
        index;

    while (i--) {
        index = Math.floor((i + 1) * Math.random());
        temp = shuffled[index];
        shuffled[index] = shuffled[i];
        shuffled[i] = temp;
    }
    let keys = shuffled.slice(0, size);
    let lines = [];
    for (idx in keys) {
      let key = keys[idx];
      lines.push(population[key])
    }
    return lines;
}


let generate = function() {
  $(".limerick-body").empty();
  generate_limerick().then(function(limerick){
    console.log("limericks", limerick);
    for(l in limerick) {
      $(".limerick-body").append(limerick[l] + "<br/>");
    }
  })
};
// run on ready
$(function() {
  generate();

  $("#generate-limericks").click(
    function() { generate(); });
});