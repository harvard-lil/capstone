const puppeteer = require('puppeteer');
const commander = require('commander');

/*
  Capture screenshot of target selectors in given URL. Example:

    node scripts/screenshot.js -t .target-selector https://case.law/trends

  Can optionally wait for other selectors to load first:

    node scripts/screenshot.js -w .load-me-first -t .target-selector https://case.law/trends

  Screenshot is written as .png to stdout.
*/

// parse command line args
collect = (value, previous) => previous.concat([value]);  // put multiple instances of a command line option in a list
const program = new commander.Command();
program
  .option('-t, --target <selector>', 'target query selector to include in screenshot (can repeat)', collect, [])
  .option('-w, --wait <selector>', 'wait for query selector to appear (can repeat)', collect, [])
  .option('-m, --timeout <milliseconds>', 'milliseconds to wait before exiting with error code 1', 10000)
  .option('-v, --verbose', 'verbose logging');
program.parse(process.argv);

// handle verbose logging
function debug(...args) {
  if (program.verbose)
    console.error(...args);
}

// worker
async function capture() {

  // open headless chrome
  debug("opening browser");
  const browser = await puppeteer.launch();
  try {

    // load page
    const page = await browser.newPage();
    const url = program.args[0];
    debug("navigating to", url);
    await page.goto(url);

    // wait for --wait selectors to load
    if (program.wait.length) {
      debug("waiting for elements to render:", program.wait);
      await Promise.all(program.wait.map(page.waitForSelector));
    }

    // get screenshot dimensions based on --target selectors
    let screenshotArgs = {};
    if (program.target.length) {
      // get dimensions of each selector
      debug("getting dimensions for selectors:", program.target);
      const boxes = await Promise.all(program.target.map(async (target)=>{
        debug("evaluateHandle", target);
        const handle = await page.evaluateHandle(
          (target) => document.querySelector(target),
          target
        );
        return await handle.boundingBox();
      }));
      debug("got dimensions:", boxes);

      // aggregate dimensions
      const x = Math.min(...boxes.map((box)=>box.x));
      const y = Math.min(...boxes.map((box)=>box.y));
      const width = Math.max(...boxes.map((box)=>box.x+box.width)) - x;
      const height = Math.max(...boxes.map((box)=>box.y+box.height)) - y;
      screenshotArgs.clip = {x, y, width, height};
      debug("capturing dimensions:", screenshotArgs.clip);

    } else {
      // if no --target, capture whole page
      screenshotArgs.fullPage = true;
      debug("capturing full page");
    }

    // capture screenshot
    const data = await page.screenshot(screenshotArgs);

    // return contents
    debug("closing browser");
    process.stdout.write(data);
    process.exit();

  } finally {
    // close browser
    browser.close();
  }
}

async function main() {
  capture();

  // kill browser after --timeout milliseconds
  await new Promise(resolve=>{setTimeout(resolve,program.timeout)});
  process.exit(1);
}

main();