import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

// Read the Speed Insights module
const insightsPath = resolve('node_modules/@vercel/speed-insights/dist/index.js');
const insightsCode = readFileSync(insightsPath, 'utf-8');

// Create a standalone bundle
const bundle = `
(function() {
  ${insightsCode}
})();
`;

writeFileSync('vercel-speed-insights.js', bundle);
console.log('Speed Insights bundle created successfully!');
