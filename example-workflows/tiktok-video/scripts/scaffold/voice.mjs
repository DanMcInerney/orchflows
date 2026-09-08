// Reuses the qualified local Kokoro route; phrase lengths are measured samples.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {env} from '@huggingface/transformers';
process.chdir(path.dirname(fileURLToPath(import.meta.url)));
const hash = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
for (const asset of JSON.parse(fs.readFileSync('model-provenance.json')))
  if (hash(asset.path) !== asset.sha256) throw Error(`model hash mismatch: ${asset.path}`);
const voicePath = 'node_modules/kokoro-js/voices/af_heart.bin';
if (hash(voicePath) !== 'd583ccff3cdca2f7fae535cb998ac07e9fcb90f09737b9a41fa2734ec44a8f0b')
  throw Error('af_heart hash mismatch');
globalThis.fetch = async () => {throw Error('Network fetch forbidden in frozen local voice route');};
env.allowRemoteModels = false;
env.allowLocalModels = true;
env.useFSCache = false;
const {KokoroTTS} = await import('kokoro-js');
const phrases = JSON.parse(fs.readFileSync(process.argv[2] || 'phrases.json', 'utf8'));
if (!Array.isArray(phrases) || !phrases.length || phrases.some(x => typeof x !== 'string' || !x.trim() || x.length > 240))
  throw Error('phrases must be nonempty short strings (maximum 240 characters each)');
const tts = await KokoroTTS.from_pretrained(path.resolve('model'), {dtype: 'q8', device: 'cpu'});
fs.mkdirSync('public/voice', {recursive: true});
let cursor = 0;
const captions = [];
for (const [i, text] of phrases.entries()) {
  const audio = await tts.generate(text, {voice: 'af_heart', speed: 1});
  if (!audio.audio.length || audio.audio.some(x => !Number.isFinite(x) || Math.abs(x) >= 1))
    throw Error(`invalid/clipped samples in phrase ${i}`);
  const duration = audio.audio.length / audio.sampling_rate;
  const file = `voice/${String(i).padStart(3, '0')}.wav`;
  await audio.save(`public/${file}`);
  captions.push({text, file, samples: audio.audio.length, sampleRate: audio.sampling_rate,
    startSeconds: cursor, endSeconds: cursor + duration, sha256: hash(`public/${file}`)});
  cursor += duration;
}
fs.writeFileSync('public/captions.json', JSON.stringify(captions, null, 2) + '\n');
console.log(JSON.stringify({phrases: captions.length, seconds: cursor, gaps: ['listening', 'word alignment']}));
