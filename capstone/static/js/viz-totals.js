let min_year = 1640;
let max_year = (new Date()).getFullYear();

let levels = [3000, 2000, 1000, 500, 1];
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

let populateLegend = function() {
  for(let i=0; i<levels.length; i++) {
    $('li.level-'+i).find('span.label').text(levels[i] + '+');
  }
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

  populateLegend();
  // Initialize with min_year
  year_input.val(first_year);
  populateForYear(first_year);
  // On update input val, load pertinent data
  year_input.on('change', function() {
    updateForYear(this, year_input);
  });
});

//https://github.com/PimpTrizkit/PJs/wiki/12.-Shade,-Blend-and-Convert-a-Web-Color-(pSBC.js)

const pSBC = function (p, from, to) {
    if(typeof(p)!=="number"||p<-1||p>1||typeof(from)!=="string"||(from[0]!=='r'&&from[0]!=='#')||(to&&typeof(to)!=="string"))return null; //ErrorCheck
    if(!this.pSBCr)this.pSBCr=(d)=>{
        let l=d.length,RGB={};
        if(l>9){
            d=d.split(",");
            if(d.length<3||d.length>4)return null;//ErrorCheck
            RGB[0]=i(d[0].split("(")[1]),RGB[1]=i(d[1]),RGB[2]=i(d[2]),RGB[3]=d[3]?parseFloat(d[3]):-1;
        }else{
            if(l==8||l==6||l<4)return null; //ErrorCheck
            if(l<6)d="#"+d[1]+d[1]+d[2]+d[2]+d[3]+d[3]+(l>4?d[4]+""+d[4]:""); //3 or 4 digit
            d=i(d.slice(1),16),RGB[0]=d>>16&255,RGB[1]=d>>8&255,RGB[2]=d&255,RGB[3]=-1;
            if(l==9||l==5)RGB[3]=r((RGB[2]/255)*10000)/10000,RGB[2]=RGB[1],RGB[1]=RGB[0],RGB[0]=d>>24&255;
        }
        return RGB;}
    var i=parseInt,r=Math.round,h=from.length>9,h=typeof(to)=="string"?to.length>9?true:to=="c"?!h:false:h,b=p<0,p=b?p*-1:p,to=to&&to!="c"?to:b?"#000000":"#FFFFFF",f=this.pSBCr(from),t=this.pSBCr(to);
    if(!f||!t)return null; //ErrorCheck
    if(h)return "rgb"+(f[3]>-1||t[3]>-1?"a(":"(")+r((t[0]-f[0])*p+f[0])+","+r((t[1]-f[1])*p+f[1])+","+r((t[2]-f[2])*p+f[2])+(f[3]<0&&t[3]<0?")":","+(f[3]>-1&&t[3]>-1?r(((t[3]-f[3])*p+f[3])*10000)/10000:t[3]<0?f[3]:t[3])+")");
    else return "#"+(0x100000000+r((t[0]-f[0])*p+f[0])*0x1000000+r((t[1]-f[1])*p+f[1])*0x10000+r((t[2]-f[2])*p+f[2])*0x100+(f[3]>-1&&t[3]>-1?r(((t[3]-f[3])*p+f[3])*255):t[3]>-1?r(t[3]*255):f[3]>-1?r(f[3]*255):255)).toString(16).slice(1,f[3]>-1||t[3]>-1?undefined:-2);
};