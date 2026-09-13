const fs = require('node:fs');
const path = require('node:path');
const validator = require('./validator/node_modules/gltf-validator');
const project = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(project, 'public/models/manifest.json')));
(async () => {
  const reports = [];
  for (const asset of manifest.assets) {
    const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(project, 'public', asset.file))), {uri: asset.file, maxIssues: 1000});
    reports.push({id: asset.id, sha256: asset.sha256, report});
    console.log(asset.id, JSON.stringify({errors: report.issues.numErrors, warnings: report.issues.numWarnings, infos: report.issues.numInfos}));
  }
  fs.writeFileSync(path.join(project, 'evidence/assets/gltf-validation.json'), JSON.stringify({validatorVersion: validator.version(), reports}, null, 2));
  if (reports.some(r => r.report.issues.numErrors)) process.exitCode = 1;
})();
