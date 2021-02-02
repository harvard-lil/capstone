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
const collect = (value, previous) => previous.concat([value]);  // put multiple instances of a command line option in a list
const program = new commander.Command();
program
  .option('-t, --target <selector>', 'target query selector to include in screenshot (can repeat)', collect, [])
  .option('-w, --wait <selector>', 'wait for query selector to appear (can repeat)', collect, [])
  .option('-m, --timeout <milliseconds>', 'milliseconds to wait before exiting with error code 1', 10000)
  .option('-d, --disable <selector>', 'query selector to set to display: none', collect, [])
  .option('--no-sandbox', 'run puppeteer with --no-sandbox flag (for debugging only!)')
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
  const puppeteerArgs = {};
  if (!program.sandbox)
    puppeteerArgs.args = ['--no-sandbox'];
  debug("opening browser with args", puppeteerArgs);
  const browser = await puppeteer.launch(puppeteerArgs);
  try {

    // load page
    const page = await browser.newPage();
    const url = program.args[0];
    debug("navigating to", url);
    await page.goto(url);

    // wait for --wait selectors to load
    const waitSelectors = program.wait.concat(program.target);
    if (waitSelectors.length) {
      debug("waiting for elements to render:", waitSelectors);
      await Promise.all(waitSelectors.map(page.waitForSelector, page));
    }

    // disable elements
    if (program.disable) {
      debug("disabling", program.disable);
      await page.evaluate((selectors) => {
        for (const selector of selectors) {
          document.querySelector(selector).style.display = 'none';
        }
      }, program.disable);
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
        return [handle, await handle.boundingBox()];
      }));
      debug("got dimensions:", boxes);

      // aggregate dimensions
      let left = Infinity, top = Infinity, right = 0, bottom = 0, scrollHandle;
      for (const [handle, box] of boxes) {
        left = Math.min(left, box.x);
        top = Math.min(top, box.y);
        right = Math.max(right, box.x + box.width);
        bottom = Math.max(bottom, box.y + box.height);
        if (box.y + box.height === bottom)
          scrollHandle = handle;
      }

      // scroll bottom element into view
      const [scrollRight, scrollBottom] = await scrollHandle.evaluate(node => {
        node.scrollIntoView();
        const rect = node.getBoundingClientRect();
        return [rect.right, rect.bottom];
      });

      // adjust clipping region based on new scroll position
      left -= right - scrollRight;
      top -= bottom - scrollBottom;
      right = scrollRight;
      bottom = scrollBottom;

      // screenshot
      screenshotArgs.clip = {x: left, y: top, width: right - left, height: bottom - top};
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