// Render and still use the same composition, explicit color, and verified browser.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {bundle} = require('@remotion/bundler');
const {ensureBrowser, selectComposition, renderMedia, renderStill} = require('@remotion/renderer');
process.chdir(__dirname);
const hash = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
(async () => {
  const seconds = Number(process.argv[2] || 1);
  if (!Number.isFinite(seconds) || seconds < 1 || seconds > 120) throw Error('seconds must be 1..120');
  const outputLocation = path.resolve(process.argv[3] || 'output/final.mp4');
  const audio = process.argv[4] || null; // a path relative to public/
  const provenance = JSON.parse(fs.readFileSync('browser-provenance.json'));
  const browser = process.env.REMOTION_BROWSER_EXECUTABLE || (await ensureBrowser()).path;
  if (process.platform !== 'win32' || hash(browser) !== provenance.executable_sha256)
    throw Error('browser/platform differs from qualified pin; qualify and record a new provenance first');
  for (const font of JSON.parse(fs.readFileSync('font-provenance.json')))
    if (hash(font.path) !== font.sha256) throw Error(`font hash mismatch: ${font.path}`);
  const serveUrl = await bundle({entryPoint: path.resolve('index.tsx'), outDir: path.resolve('build')});
  const inputProps = {seconds, audio};
  const composition = await selectComposition({serveUrl, id: 'Video', inputProps, browserExecutable: browser});
  fs.mkdirSync(path.dirname(outputLocation), {recursive: true});
  await renderMedia({serveUrl, composition, inputProps, browserExecutable: browser,
    codec: 'h264', pixelFormat: 'yuv420p', colorSpace: 'bt709',
    audioCodec: 'aac', sampleRate: 48000, muted: audio === null,
    outputLocation, concurrency: 2,
    // The qualified parallel encoder omitted transfer/primaries from H264 VUI
    // with colorSpace alone. Preserve explicit tags in the encoded bitstream.
    ffmpegOverride: ({args, type}) => type === 'pre-stitcher'
      ? [...args.slice(0, -1), '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709', args.at(-1)]
      : args});
  await renderStill({serveUrl, composition, inputProps, browserExecutable: browser,
    frame: Math.floor(composition.durationInFrames / 2), output: outputLocation + '.png'});
  console.log(JSON.stringify({outputLocation, frames: composition.durationInFrames,
    browser: provenance, sha256: hash(outputLocation)}));
})().catch((error) => {console.error(error); process.exitCode = 1;});
