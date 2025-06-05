#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

console.log('=== Testing .env.tunnel loading ===\n');

const tunnelPath = path.resolve(__dirname, '..', '.env.tunnel');
console.log('Tunnel path:', tunnelPath);
console.log('File exists:', fs.existsSync(tunnelPath));

if (fs.existsSync(tunnelPath)) {
  console.log('\nFile contents:');
  const content = fs.readFileSync(tunnelPath, 'utf-8');
  console.log(content);
  
  console.log('\nParsed values:');
  const tunnelEnv = {};
  content.split('\n').forEach(line => {
    if (line && !line.startsWith('#') && line.includes('=')) {
      const [key, value] = line.split('=', 2);
      tunnelEnv[key.trim()] = value.trim();
    }
  });
  
  console.log('AGENTS_SERVICE_URL:', tunnelEnv.AGENTS_SERVICE_URL);
  console.log('AUTH_SERVICE_URL:', tunnelEnv.AUTH_SERVICE_URL);
  console.log('HOMEPAGE_URL:', tunnelEnv.HOMEPAGE_URL);
} else {
  console.log('\n❌ .env.tunnel file not found!');
}