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

let vueConfig = {
  outputDir: 'static/dist',

  // When running `npm run serve`, paths in webpack-stats.json will point to the live dev server.
  // Otherwise they will point to the compiled assets URL.
  baseUrl: devMode ? 'http://localhost:8080/static/dist' : '/static/dist',

  pages: {
    base: 'static/js/base.js',
    map: 'static/js/map-actions.js',
    limericks: 'static/js/generate_limericks.js',
    witchcraft: 'static/js/witchcraft.js',
    search: 'static/js/search.js',
  },

  configureWebpack: {
    plugins: [
      // output location of bundles so they can be found by django
      new RelativeBundleTracker({filename: './webpack-stats.json'}),
    ],
    resolve: {
      alias: {
        'vue$': 'vue/dist/vue.esm.js'
      }
    }
  },

  devServer: {
    host: '127.0.0.1',
    headers: { 'Access-Control-Allow-Origin': '*' },
  },

  // static assets are hashed by whitenoise
  filenameHashing: false,

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
        vendors: {
          name: `chunk-vendors`,
          test: /[\\/]node_modules[\\/]/,
          priority: -10,
          chunks: 'initial'
        },
        common: {
          name: `chunk-common`,
          minChunks: 2,
          priority: -20,
          chunks: 'initial',
          reuseExistingChunk: true
        }
      }
    });
  },

};

module.exports = vueConfig;
