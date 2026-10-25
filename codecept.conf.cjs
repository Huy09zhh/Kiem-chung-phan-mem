exports.config = {
  tests: './tests/*_test.js',
  output: './output',
  helpers: {
    Playwright: {
      browser: 'chromium',
      url: 'http://127.0.0.1:8000',
      show: true,
    },
  },
  include: {
    I: './steps_file.cjs',
  },
  name: 'kiem-chung-phan-mem',
};