const BundleTracker = require('webpack-bundle-tracker');
const path = require('path');

/*** helpers ***/

const devMode = process.env.NODE_ENV !== 'production';

// BundleTracker includes absolute paths, which causes webpack-stats.json to change when it shouldn't.
// We use this RelativeBundleTracker workaround via https://github.com/owais/webpack-bundle-tracker/issues/25
const RelativeBundleTracker = function(options) {
    BundleTracker.call(this, options);
};
RelativeBundleTracker.prototype = Object.create(BundleTracker.prototype);
RelativeBundleTracker.prototype.writeOutput = function(compiler, contents) {
  if(contents.chunks){
    const relativePathRoot = path.join(__dirname) + path.sep;
    for(const bundle of Object.values(contents.chunks)){
      for(const chunk of bundle){
        if (chunk.path.startsWith(relativePathRoot)) {
          chunk.path = chunk.path.substr(relativePathRoot.length);
        }
      }
    }
  }
  BundleTracker.prototype.writeOutput.call(this, compiler, contents);
};

/*** Vue config ***/
let devServerHost = process.env.DOCKERIZED ? '0.0.0.0' : '127.0.0.1';

let vueConfig = {
  outputDir: 'static/dist',

  // When running `npm run serve`, paths in webpack-stats.json will point to the live dev server.
  // Otherwise they will point to the compiled assets URL.
  publicPath: devMode ? 'http://localhost:8080/static/dist' : '/static/dist',

  pages: {
    base: 'static/js/base.js',
    map: 'static/js/homepage-map/main.js',
    limericks: 'static/js/generate_limericks.js',
    witchcraft: 'static/js/witchcraft/main.js',
    search: 'static/js/search/main.js',
    trends: 'static/js/trends/main.js',
    case: 'static/js/case/main.js',
    'cite-grid': 'static/js/cite-grid/main.js',
    'case-editor': 'static/js/case-editor/main.js',
    'labs-chronolawgic': 'static/js/labs/chronolawgic/main.js',
  },

  configureWebpack: {
    plugins: [
      // output location of bundles so they can be found by django
      new RelativeBundleTracker({filename: './webpack-stats.json'}),
    ],
    resolve: {
      alias: {
        'vue$': 'vue/dist/vue.esm.js',
        static: path.resolve(__dirname, 'static'),
      }
    }
  },

  devServer: {
    public: devServerHost + ':8080',
    host: devServerHost,
    headers: { 'Access-Control-Allow-Origin': '*' },
    allowedHosts: [
        '.case.test'
    ],
    // watchOptions: {
    //   poll: true
    // }

  },

  chainWebpack: config => {
    // delete HTML related webpack plugins
    // via https://github.com/vuejs/vue-cli/issues/1478
    Object.keys(vueConfig.pages).forEach(function (key) {
      config.plugins.delete('html-' + key);
      config.plugins.delete('preload-' + key);
      config.plugins.delete('prefetch-' + key);
    });

    // use same chunks config for dev as prod so {% render_bundle %} works on both
    // copied from node_modules/@vue/cli-service/lib/config/app.js
    config.optimization.splitChunks({
      cacheGroups: {
        // vendors: {
        //   name: `chunk-vendors`,
        //   test: /[\\/]node_modules[\\/]/,
        //   priority: -10,
        //   chunks: 'initial'
        // },
        common: {
          name: `chunk-common`,
          minChunks: 2,
          priority: -20,
          chunks: 'initial',
          reuseExistingChunk: true
        }
      }
    });

    // exlude moment.js from chart.js build: https://www.chartjs.org/docs/latest/getting-started/integration.html#bundlers-webpack-rollup-etc
    config.externals({
      moment: 'moment'
    });

    // embed svgs
    // via https://github.com/visualfanatic/vue-svg-loader
    const svgRule = config.module.rule('svg');
    svgRule.uses.clear();
    svgRule
      .use('babel-loader')
      .loader('babel-loader')
      .end()
      .use('vue-svg-loader')
      .loader('vue-svg-loader')
      // don't strip IDs from SVGs
      // via https://github.com/visualfanatic/vue-svg-loader/issues/97
      .options({
        svgo: {
          plugins: [
            { cleanupIDs: false },
          ],
        },
      });
  },

};

module.exports = vueConfig;
