import $ from "jquery"

function generate_limerick() {
  let line_types = limericks;  // eslint-disable-line

  let long_lines = get_lines(line_types['long'], 3);
  let short_lines = get_lines(line_types['short'], 2);
  return [long_lines[0],
    long_lines[1],
    short_lines[0],
    short_lines[1],
    long_lines[2]];
}

function get_lines(emphasis_patterns, count){
  let last_syllables = dict_random_choice(emphasis_patterns);
  let last_tokens = dict_random_choice(last_syllables);
  let line_sets = dict_random_sample(last_tokens, count);
  let lines = [];
  for(let k in line_sets){
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
  let keys = Object.keys(population);
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
  for (let idx in keys) {
    let key = keys[idx];
    lines.push(population[key])
  }
  return lines;
}


let generate = function() {
  let limerick_body = $(".limerick-body");
  limerick_body.empty();
  let limerick = generate_limerick();
    for(let l in limerick) {
      limerick_body.append(limerick[l] + "<br/>");
    }
};
// run on ready
$(function() {
  generate();
  $("#generate-limericks").click(
      function() { generate(); });
});