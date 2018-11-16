module.exports = {
  presets: [
    ['@vue/app', {
      // disable the default polyfills included by https://www.npmjs.com/package/@vue/babel-preset-app?activeTab=readme#polyfills
      // because they cause nondeterministic builds. See https://github.com/vuejs/vue-cli/issues/2983
      polyfills: [],
    }]
  ]
}
