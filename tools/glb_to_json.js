// Turns a .glb into a self-contained glTF JSON file (binary embedded as base64).
// Usage: node tools/glb_to_json.js downloads/player.glb assets/player.gltf.json
const fs = require('fs');
const [src, dst] = process.argv.slice(2);
const glb = fs.readFileSync(src);
if (glb.readUInt32LE(0) !== 0x46546c67) throw new Error('not a GLB file');
let off = 12, json = null, bin = null;
while (off < glb.length) {
  const len = glb.readUInt32LE(off), type = glb.readUInt32LE(off + 4);
  const chunk = glb.subarray(off + 8, off + 8 + len);
  if (type === 0x4e4f534a) json = JSON.parse(chunk.toString('utf8'));
  if (type === 0x004e4942) bin = chunk;
  off += 8 + len;
}
json.buffers[0].uri = 'data:application/octet-stream;base64,' + bin.toString('base64');
fs.writeFileSync(dst, JSON.stringify(json));
console.log(`wrote ${dst} (${(fs.statSync(dst).size / 1e6).toFixed(2)} MB)`);
